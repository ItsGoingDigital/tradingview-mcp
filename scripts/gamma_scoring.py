"""Shared gamma-scoring primitives used by scan_mega.py and scan-eow.py.

Same scoring logic across both scanners so a Grade A on one means the same
thing on the other.

Public functions:
  detect_regime(strikes_net, price)
  detect_cluster(strikes_net, price, side='positive', above=None)
  path_clarity(strikes_net, price, target)
  next_strike_beyond(strikes_net, anchor, direction, price)
  grade_setup(mode, dominance, path_clear, gap_pct, cluster_size)
  score_ticker(ticker, name, strikes_net, price)

Conventions:
  - strikes_net: dict {strike_price: net_gex} where net_gex > 0 = call-dominant,
    net_gex < 0 = put-dominant
  - "side='positive'" = scan positive-gex (call magnet) strikes
  - "side='negative'" = scan negative-gex (put magnet) strikes
  - "above=True"  = restrict to strikes above current price
  - "above=False" = restrict to strikes below current price
  - Positive gex BELOW price = support floor (NOT a downside target)
  - Negative gex ABOVE price = supply ceiling (NOT an upside target)
"""

# Tunables — change here, affects both scanners equally
CLUSTER_PRICE_PCT = 0.012     # strikes within 1.2% of each other → cluster candidates
CLUSTER_GEX_RATIO = 0.50      # peer must be ≥ 50% of cluster leader to join
FLIP_BAND_PCT     = 0.15      # ±15% around price for regime calc
MATERIAL_RATIO    = 0.05      # cluster total must be ≥ 5% of max chain |gex| to count
BAND_PCT          = 0.10      # cluster search restricted to ±10% of price


def detect_regime(strikes_net, price):
    """Cumulative band-sum + flip detection. Returns (regime, flip_price)."""
    band = price * FLIP_BAND_PCT
    band_strikes = [s for s in strikes_net.keys() if abs(s - price) <= band]
    if not band_strikes:
        return None, None
    cum = 0.0
    flip = None
    for s in sorted(band_strikes, reverse=True):
        cum += strikes_net[s]
        if cum < 0:
            flip = s
            break
    band_sum = sum(strikes_net[s] for s in band_strikes)
    if flip is not None:
        regime = 'positive' if price > flip else 'negative'
    elif band_sum > 0:
        regime = 'positive'
    elif band_sum < 0:
        regime = 'negative'
    else:
        regime = None
    return regime, flip


def detect_cluster(strikes_net, price, side='positive', above=None):
    """Group adjacent dominant strikes on `side` (positive = call gex, negative = put gex).

    `above` filter restricts to strikes ABOVE price (True), BELOW price (False),
    or both sides (None). Critical for direction-correct pin trade targets.

    Returns dict {strikes, gex_list, center, width, total_gex, dominance,
                  leader_strike, leader_gex, size} or None if no cluster found.
    """
    if not strikes_net:
        return None
    # Take strikes whose gex sign matches `side`; flip sign for negative side
    if side == 'positive':
        candidates = {s: g for s, g in strikes_net.items() if g > 0}
    else:
        candidates = {s: -g for s, g in strikes_net.items() if g < 0}
    if not candidates:
        return None

    band = price * BAND_PCT
    near = {s: g for s, g in candidates.items() if abs(s - price) <= band}
    if above is True:
        near = {s: g for s, g in near.items() if s > price}
    elif above is False:
        near = {s: g for s, g in near.items() if s < price}
    if not near:
        return None

    sorted_strikes = sorted(near.items(), key=lambda x: -x[1])
    leader_strike, leader_gex = sorted_strikes[0]
    cluster = [(leader_strike, leader_gex)]

    for s, g in sorted_strikes[1:]:
        if g < leader_gex * CLUSTER_GEX_RATIO:
            break
        if any(abs(s - cs) / price <= CLUSTER_PRICE_PCT for cs, _ in cluster):
            cluster.append((s, g))

    cluster.sort(key=lambda x: x[0])
    cluster_strikes = [s for s, _ in cluster]
    cluster_gex = [g for _, g in cluster]
    total_gex = sum(cluster_gex)
    weighted_center = sum(s * g for s, g in cluster) / total_gex
    width = max(cluster_strikes) - min(cluster_strikes)

    outside = sorted([g for s, g in near.items() if s not in cluster_strikes], reverse=True)
    top5_outside = outside[:5]
    if top5_outside:
        median_outside = top5_outside[len(top5_outside) // 2]
    else:
        median_outside = max(1.0, total_gex * 0.01)
    dominance = total_gex / max(median_outside, 1.0)

    return {
        'strikes':       cluster_strikes,
        'gex_list':      cluster_gex,
        'center':        weighted_center,
        'width':         width,
        'total_gex':     total_gex,
        'dominance':     dominance,
        'leader_strike': leader_strike,
        'leader_gex':    leader_gex,
        'size':          len(cluster),
    }


def path_clarity(strikes_net, price, target):
    """0..1 — how clear the runway is from price to target.

    Sums |gex| of strikes BETWEEN price and target (exclusive), in trade direction.
    Lower obstruction = higher score. 1.0 = nothing in the way.
    """
    lo, hi = (price, target) if price < target else (target, price)
    between = [g for s, g in strikes_net.items()
               if lo < s < hi and (g > 0 if target > price else g < 0)]
    if not between:
        return 1.0
    blocking = sum(abs(g) for g in between)
    total_in_window = sum(abs(g) for s, g in strikes_net.items() if lo <= s <= hi)
    if total_in_window == 0:
        return 1.0
    return max(0.0, 1.0 - (blocking / total_in_window))


def next_strike_beyond(strikes_net, anchor, direction, price):
    """Breakout target: largest |gex| strike beyond `anchor` in trade direction,
    within ±15% of price. Returns strike or None."""
    if direction > 0:
        candidates = sorted([s for s in strikes_net.keys() if s > anchor])
    else:
        candidates = sorted([s for s in strikes_net.keys() if s < anchor], reverse=True)
    if not candidates:
        return None
    band = price * 0.15
    in_reach = [s for s in candidates if abs(s - anchor) <= band]
    if not in_reach:
        return None
    return max(in_reach, key=lambda s: abs(strikes_net[s]))


def grade_setup(mode, dominance, path_clear, gap_pct, cluster_size):
    """A / B / C / D / F based on conviction.

    Sweet-spot gap bands:
      pin     : 2% – 6%
      breakout: 0.5% – 3%
    """
    abs_gap = abs(gap_pct)
    if mode == 'pin':
        in_sweet = 2.0 <= abs_gap <= 6.0
        in_acceptable = 1.5 <= abs_gap <= 8.0
    else:
        in_sweet = 0.5 <= abs_gap <= 3.0
        in_acceptable = 0.3 <= abs_gap <= 4.5

    if not in_acceptable:
        return 'F'

    if cluster_size >= 4 and mode == 'pin':
        if dominance >= 2.5 and path_clear >= 0.7 and in_sweet:
            return 'C'
        return 'D'

    if in_sweet and dominance >= 2.5 and path_clear >= 0.75:
        return 'A'
    if in_sweet and dominance >= 1.5 and path_clear >= 0.6:
        return 'B'
    if in_sweet and (dominance >= 1.2 or path_clear >= 0.5):
        return 'C'
    if in_acceptable and dominance >= 1.5:
        return 'D'
    return 'F'


def score_ticker(ticker, name, strikes_net, price):
    """The shared scoring entry point. Returns the same schema regardless of
    universe. Used by both scan_mega.py and scan-eow.py.

    Output dict (always populated):
      ticker, name, price, grade (A/B/C/D/F or skip_reason set on F)
    On qualified setups (grade ≠ F-skipped) also:
      regime, mode (PIN | BREAKOUT), direction (LONG | SHORT),
      target, gap_pct, path_clarity,
      cluster (for PIN) or launch_pad/dominance (for BREAKOUT),
      suggested_strike, tight, wide, flip
    """
    regime, flip = detect_regime(strikes_net, price)
    if regime is None:
        return {'ticker': ticker, 'name': name, 'price': price,
                'grade': 'F', 'skip_reason': 'no regime'}

    if regime == 'positive':
        # Pin mode: two directional candidates
        call_magnet = detect_cluster(strikes_net, price, side='positive', above=True)
        put_magnet  = detect_cluster(strikes_net, price, side='negative', above=False)
        # Magnitude floor — clusters must be material vs the chain's max strike
        max_abs = max(abs(g) for g in strikes_net.values())
        min_material = max_abs * MATERIAL_RATIO
        if call_magnet and call_magnet['total_gex'] < min_material:
            call_magnet = None
        if put_magnet and put_magnet['total_gex'] < min_material:
            put_magnet = None
        candidates = []
        if call_magnet: candidates.append(('LONG',  call_magnet))
        if put_magnet:  candidates.append(('SHORT', put_magnet))
        if not candidates:
            return {'ticker': ticker, 'name': name, 'price': price, 'regime': regime,
                    'grade': 'F', 'skip_reason': 'no material magnet'}
        candidates.sort(key=lambda c: -c[1]['total_gex'])
        direction, cluster = candidates[0]
        target = cluster['center']
        gap_pct = (target - price) / price * 100
        clarity = path_clarity(strikes_net, price, target)
        grade = grade_setup('pin', cluster['dominance'], clarity, gap_pct, cluster['size'])
        if cluster['size'] == 1:
            suggested = cluster['leader_strike']
        else:
            suggested = min(cluster['strikes']) if gap_pct > 0 else max(cluster['strikes'])
        return {
            'ticker': ticker, 'name': name, 'price': price,
            'regime': 'positive', 'mode': 'PIN',
            'flip': flip,
            'cluster': cluster, 'cluster_side': 'call' if direction == 'LONG' else 'put',
            'target': target, 'gap_pct': gap_pct,
            'direction': direction,
            'path_clarity': clarity,
            'suggested_strike': suggested,
            'tight': cluster['width'] / price < 0.005,
            'wide':  cluster['size'] >= 4,
            'grade': grade,
        }

    # Negative regime → breakout
    band = price * 0.05
    near = {s: abs(g) for s, g in strikes_net.items() if abs(s - price) <= band}
    if not near:
        return {'ticker': ticker, 'name': name, 'price': price, 'regime': regime,
                'grade': 'F', 'skip_reason': 'no launch pad'}
    launch_pad = max(near, key=lambda s: near[s])
    if launch_pad > price:
        direction = +1
    elif launch_pad < price:
        direction = -1
    else:
        above = sum(strikes_net.get(s, 0) for s in strikes_net if s > launch_pad)
        below = sum(strikes_net.get(s, 0) for s in strikes_net if s < launch_pad)
        direction = -1 if below < above else +1

    target = next_strike_beyond(strikes_net, launch_pad, direction, price) or flip
    if target is None:
        return {'ticker': ticker, 'name': name, 'price': price, 'regime': regime,
                'grade': 'F', 'skip_reason': 'no downstream target'}
    gap_pct = (target - price) / price * 100
    outside = [g for s, g in strikes_net.items() if s != launch_pad]
    outside_abs = sorted([abs(g) for g in outside], reverse=True)[:5]
    median_outside = outside_abs[len(outside_abs) // 2] if outside_abs else 1.0
    dominance = abs(strikes_net[launch_pad]) / max(median_outside, 1.0)
    clarity = path_clarity(strikes_net, price, target)
    grade = grade_setup('breakout', dominance, clarity, gap_pct, 1)
    return {
        'ticker': ticker, 'name': name, 'price': price,
        'regime': 'negative', 'mode': 'BREAKOUT',
        'flip': flip,
        'launch_pad': launch_pad,
        'dominance': dominance,
        'target': target, 'gap_pct': gap_pct,
        'direction': 'LONG' if direction > 0 else 'SHORT',
        'path_clarity': clarity,
        'suggested_strike': launch_pad,
        'grade': grade,
    }
