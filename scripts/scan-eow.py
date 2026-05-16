#!/usr/bin/env python3
"""
Scan ApeWisdom WSB top-N for EOW asymmetric-breakout setups.

Pulls the day's most-mentioned WSB tickers, filters to those with this-Friday
options, runs UW spot-exposures GEX per ticker in parallel, scores each on a
deterministic asymmetric-breakout rubric, and writes a ranked HTML scan page.

Usage:
    python3 scripts/scan-eow.py
    python3 scripts/scan-eow.py --top 50

The output is `charts/rendered/scan.html` — all scanned tickers ranked top-down,
A through F (full transparency, no filtering of low-grade rows).

No TradingView dependency. UW-only. ~30s wall time for top-25.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uw_gex import pull_spot_gex
from gamma_scoring import score_ticker

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'scan.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'scan.html')

# ──────────────────────────────────────────────────────────
# Constants — scoring + thresholds
# ──────────────────────────────────────────────────────────
PIN_PROX_PCT       = 0.05   # pin must sit within ±5% of price
PUT_PROX_PCT       = 0.10   # put magnet within ±10%
WALL_PROX_PCT      = 0.10   # walls within ±10%
WALL_MIN_RATIO     = 0.05   # 5% of max |gex|
FLIP_PROX_PCT      = 0.15   # band for regime + flip
SPOT_WINDOW_PCT    = 0.20   # API pull window per ticker

GRADE_THRESHOLDS = [(0.75, 'A'), (0.55, 'B'), (0.35, 'C'), (0.15, 'D')]


# ──────────────────────────────────────────────────────────
# ApeWisdom — top-N from WSB
# ──────────────────────────────────────────────────────────
def fetch_apewisdom_top(n=25, filter_name='wallstreetbets'):
    """Return list of {ticker, name, mentions, mentions_24h, rank, rank_24h}."""
    url = f'https://apewisdom.io/api/v1.0/filter/{filter_name}'
    req = Request(url, headers={'User-Agent': 'gamma-scan/1.0'})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(f'ApeWisdom fetch failed: {e}')
    rows = data.get('results', [])[:n]
    out = []
    for r in rows:
        out.append({
            'ticker':       r.get('ticker', '').upper(),
            'name':         r.get('name', '').replace('&amp;', '&'),
            'mentions':     int(r.get('mentions') or 0),
            'mentions_24h': int(r.get('mentions_24h_ago') or 0),
            'rank':         int(r.get('rank') or 0),
            'rank_24h':     int(r.get('rank_24h_ago') or 0),
        })
    return out


def mention_velocity_score(mentions, mentions_24h):
    """Normalize mention growth to [0,1]. Cap at 3× growth = max signal."""
    if mentions <= 0:
        return 0.0
    if mentions_24h <= 0:
        # New on the board today — already heavy signal; flag separately
        return 1.0 if mentions >= 50 else 0.5
    ratio = mentions / mentions_24h
    # Map: ratio of 1× (flat) → 0, ratio of 3× → 1.0
    return max(0.0, min(1.0, (ratio - 1) / 2))


# ──────────────────────────────────────────────────────────
# UW helpers
# ──────────────────────────────────────────────────────────
def fetch_uw_json(endpoint, token, retries=3):
    """Fetch UW with retry on 429 (rate limit). UW caps at 3 concurrent
    requests; bursts from parallel workers trip this constantly. Silent
    failure was causing real-EOW tickers (like MU) to mis-flag no-eow."""
    import time
    url = f'https://api.unusualwhales.com{endpoint}'
    headers = {'Authorization': f'Bearer {token}', 'UW-CLIENT-API-ID': '100001'}
    for attempt in range(retries + 1):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(0.5 * (2 ** attempt))   # 0.5s, 1s, 2s
                continue
            return None
        except Exception:
            if attempt < retries:
                time.sleep(0.3)
                continue
            return None
    return None


def find_eow_expiry(ticker, token, target_date):
    """Return True if `target_date` is an available expiry for this ticker."""
    data = fetch_uw_json(f'/api/stock/{ticker}/expiry-breakdown', token)
    if not data:
        return False
    rows = data.get('data', [])
    return any(r.get('expires') == target_date for r in rows)


def next_friday(from_date=None):
    d = from_date or datetime.now().date()
    days_ahead = (4 - d.weekday()) % 7
    if days_ahead == 0:
        # Today IS Friday — still use today as EOW (Friday close)
        days_ahead = 0
    return (d + timedelta(days=days_ahead))


# ──────────────────────────────────────────────────────────
# Level derivation (same proximity-filter logic as refresh-multi-0dte.py)
# ──────────────────────────────────────────────────────────
def derive_levels(strikes_net, price):
    if not strikes_net:
        return {}
    max_abs = max(abs(v) for v in strikes_net.values())
    threshold = max_abs * WALL_MIN_RATIO

    prox = price * PIN_PROX_PCT
    near = {s: g for s, g in strikes_net.items() if abs(s - price) <= prox and g >= threshold}
    pin = max(near.items(), key=lambda x: x[1]) if near else None

    put_band = price * PUT_PROX_PCT
    neg = [(s, g) for s, g in strikes_net.items() if g < -threshold and abs(s - price) <= put_band]
    put_mag = min(neg, key=lambda x: x[1]) if neg else None

    wall_band = price * WALL_PROX_PCT
    upper_bound = pin[0] if pin else price
    lower_bound = put_mag[0] if put_mag else float('-inf')
    wall_up = wall_down = None
    for s, g in strikes_net.items():
        if g <= threshold:
            continue
        if pin and s == pin[0]:
            continue
        if abs(s - price) > wall_band:
            continue
        if s > upper_bound and (wall_up is None or g > wall_up[1]):
            wall_up = (s, g)
        if s < price and s > lower_bound and (wall_down is None or g > wall_down[1]):
            wall_down = (s, g)

    flip_band = price * FLIP_PROX_PCT
    band_strikes = [s for s in strikes_net.keys() if abs(s - price) <= flip_band]
    cum = 0.0
    flip = None
    for s in sorted(band_strikes, reverse=True):
        cum += strikes_net[s]
        if cum < 0:
            flip = s
            break

    band_sum = sum(strikes_net.get(s, 0) for s in band_strikes)
    if flip is not None:
        regime = 'positive' if price > flip else 'negative'
    elif band_sum > 0:
        regime = 'positive'
    elif band_sum < 0:
        regime = 'negative'
    else:
        regime = None

    return {
        'pin': pin, 'wall_up': wall_up, 'wall_down': wall_down,
        'put_mag': put_mag, 'flip': flip, 'regime': regime,
    }


# ──────────────────────────────────────────────────────────
# Dominance score — mirrors the heatmap JS dominanceScore()
# ──────────────────────────────────────────────────────────
def dominance_score(strikes_net, peak_strike):
    """How dominant is the peak |gex| strike vs the next 5 largest peers.

    Same log-ratio formula the heatmaps use to drive the bright-yellow star:
      ratio = peak_|gex| / median(|gex| of next 5 strikes)
      score = clamp( log10(ratio) / log10(8), 0, 1 )

    Score ≥ 0.8 = bright yellow star (peak ≈ 6× the typical big strike).
    """
    if peak_strike is None:
        return 0.0
    peak_abs = abs(strikes_net.get(peak_strike, 0))
    if peak_abs == 0:
        return 0.0
    others = sorted(
        (abs(v) for s, v in strikes_net.items() if s != peak_strike and abs(v) > 0),
        reverse=True,
    )[:5]
    if not others:
        return 1.0
    median = others[len(others) // 2]
    if median <= 0:
        return 1.0
    ratio = peak_abs / median
    return max(0.0, min(1.0, math.log10(ratio) / math.log10(8)))


# ──────────────────────────────────────────────────────────
# Star-distance grading — pure distance from current price to the
# dominant ("bright yellow") gex strike. Simpler, deterministic, no
# regime weighting, no Reddit influence.
#
# Grade A: 2–7% away  (sweet spot — enough room to pay, reachable EOW)
# Grade B: 1–2% away  (close but ok)
# Grade C: < 1%       (already at the magnet — pin trade, not breakout)
# Grade D: 7–12% away (real long-shot — needs catalyst)
# Grade F: > 12% away OR no bright-yellow star found
# ──────────────────────────────────────────────────────────
DOMINANCE_THRESHOLD = 0.8         # "bright yellow"
A_BAND = (2.0, 7.0)               # sweet-spot % distance
B_BAND = (1.0, 2.0)
C_MAX  = 1.0
D_MAX  = 12.0


def score_by_star_distance(strikes_net, price):
    """Find the bright-yellow star (dominant gex strike) and grade by
    distance from current price.

    Returns dict (grade, score, direction, target_price, gap_pct, dominance)
    or None when there's no scorable structure.
    """
    if not strikes_net:
        return None
    # Peak |gex| strike anywhere on the windowed chain
    peak_strike = max(strikes_net.keys(), key=lambda s: abs(strikes_net[s]))
    dominance = dominance_score(strikes_net, peak_strike)

    gap_pct = abs(peak_strike - price) / price * 100
    direction = 'up' if peak_strike > price else 'down'

    # No bright-yellow star → no clean magnet → Grade F
    if dominance < DOMINANCE_THRESHOLD:
        grade = 'F'
    elif gap_pct > D_MAX:
        grade = 'F'                          # bright star, but out of reach EOW
    elif gap_pct >= A_BAND[1]:               # 7–12% → D (long-shot)
        grade = 'D'
    elif gap_pct >= A_BAND[0]:               # 2–7% → A (sweet spot)
        grade = 'A'
    elif gap_pct >= B_BAND[0]:               # 1–2% → B (close but ok)
        grade = 'B'
    else:                                    # < 1% → C (already pinned)
        grade = 'C'

    return {
        'grade':         grade,
        'score':         round(dominance, 3),
        'dominance':     round(dominance, 3),
        'direction':     direction,
        'target_price':  peak_strike,
        'gap_pct':       round(gap_pct, 2),
        'peak_gex':      round(strikes_net[peak_strike], 0),
    }


# ──────────────────────────────────────────────────────────
# Per-ticker scan
# ──────────────────────────────────────────────────────────
def scan_one(ape_row, token, target_date_iso):
    """Run the full scan pipeline for one ticker. Returns dict with status."""
    t = ape_row['ticker']
    result = {
        'ticker':       t,
        'name':         ape_row['name'],
        'mentions':     ape_row['mentions'],
        'mentions_24h': ape_row['mentions_24h'],
        'rank':         ape_row['rank'],
        'rank_24h':     ape_row['rank_24h'],
        'status':       'ok',
        'reason':       None,
    }

    # 1. Check EOW expiry exists
    if not find_eow_expiry(t, token, target_date_iso):
        result['status'] = 'no-eow'
        result['reason'] = f'No options chain for {target_date_iso}'
        return result

    # 2. Pull spot-exposures with proper window
    # Use generous window since we don't know price yet — pull_spot_gex's
    # internal price-probe handles that.
    try:
        # Reasonable window for stocks; SPX/index would need more but those
        # aren't in WSB top list typically.
        pull = pull_spot_gex(t, token, window_below=200, window_above=200)
    except Exception as e:
        result['status'] = 'pull-failed'
        result['reason'] = str(e)[:120]
        return result

    parsed = pull.get('parsed', [])
    price = pull.get('price', 0)
    if not parsed or price <= 0:
        result['status'] = 'no-data'
        result['reason'] = 'spot-exposures returned no usable rows'
        return result

    # Re-pull with proper window if 200/200 missed (some high-priced stocks)
    if price > 500:
        try:
            pull = pull_spot_gex(t, token,
                                 window_below=price * SPOT_WINDOW_PCT,
                                 window_above=price * SPOT_WINDOW_PCT)
            parsed = pull.get('parsed', [])
        except Exception:
            pass

    strikes_net = {p['strike']: p['call_gamma_oi'] + p['put_gamma_oi'] for p in parsed}
    levels = derive_levels(strikes_net, price)

    velocity = mention_velocity_score(ape_row['mentions'], ape_row['mentions_24h'])

    # Unified scoring — same logic mega-scan uses. Directional magnet filter
    # (positive gex above price = call magnet, negative below = put magnet),
    # magnitude floor, regime-aware mode (PIN vs BREAKOUT).
    scored = score_ticker(t, ape_row['name'], strikes_net, price)

    result.update({
        'price':           price,
        'price_time':      pull.get('time'),
        'pin':             levels['pin'][0]    if levels.get('pin')    else None,
        'wall_up':         levels['wall_up'][0]  if levels.get('wall_up') else None,
        'wall_down':       levels['wall_down'][0] if levels.get('wall_down') else None,
        'put_mag':         levels['put_mag'][0]  if levels.get('put_mag') else None,
        'regime':          scored.get('regime') or levels.get('regime'),
        'velocity_score':  round(velocity, 2),
        'grade':           scored.get('grade', 'F'),
        'mode':            scored.get('mode'),
        'direction':       scored.get('direction'),   # 'LONG' | 'SHORT' | None
        'target':          scored.get('target'),
        'gap_pct':         round(scored['gap_pct'], 2) if scored.get('gap_pct') is not None else None,
        'path_clarity':    round(scored['path_clarity'], 3) if scored.get('path_clarity') is not None else None,
        'suggested_strike': scored.get('suggested_strike'),
        'skip_reason':     scored.get('skip_reason'),
    })

    # Score = absolute gap %, used for ranking within the same grade tier
    if scored.get('gap_pct') is not None:
        result['score'] = round(abs(scored['gap_pct']), 2)
    else:
        result['status'] = 'unscorable'
        result['reason'] = scored.get('skip_reason', 'No qualifying magnet')
    return result


# ──────────────────────────────────────────────────────────
# Render scan.html
# ──────────────────────────────────────────────────────────
def build_config_js(scanned, top_n, target_date_iso):
    rows = []
    for r in scanned:
        def s(v):
            # json.dumps handles embedded quotes / backslashes / unicode safely.
            # Critical for error messages from UW (which embed JSON fragments).
            if v is None:
                return 'null'
            if isinstance(v, str):
                return json.dumps(v)
            return str(v)
        rows.append(
            '{ '
            f'ticker: {s(r["ticker"])}, '
            f'name: {s(r.get("name",""))}, '
            f'status: {s(r.get("status"))}, '
            f'reason: {s(r.get("reason"))}, '
            f'price: {s(r.get("price"))}, '
            f'pin: {s(r.get("pin"))}, '
            f'wall_up: {s(r.get("wall_up"))}, '
            f'wall_down: {s(r.get("wall_down"))}, '
            f'put_mag: {s(r.get("put_mag"))}, '
            f'regime: {s(r.get("regime"))}, '
            f'mode: {s(r.get("mode"))}, '
            f'direction: {s(r.get("direction"))}, '
            f'target: {s(r.get("target"))}, '
            f'gap_pct: {s(r.get("gap_pct"))}, '
            f'path_clarity: {s(r.get("path_clarity"))}, '
            f'suggested_strike: {s(r.get("suggested_strike"))}, '
            f'score: {s(r.get("score"))}, '
            f'grade: {s(r.get("grade"))} '
            '}'
        )
    rows_js = '[\n    ' + ',\n    '.join(rows) + '\n  ]'
    as_of = datetime.now(timezone.utc).isoformat()
    return f"""const CONFIG = {{
  asOf: '{as_of}',
  topN: {top_n},
  targetDate: '{target_date_iso}',
  scanned: {rows_js},
}};"""


def patch_html(config_js):
    with open(TEMPLATE_PATH, 'r') as f:
        html = f.read()
    pattern = r'const CONFIG = \{[\s\S]*?\n\};'
    if not re.search(pattern, html):
        sys.exit(f'No CONFIG block in {TEMPLATE_PATH}')
    new_html = re.sub(pattern, config_js, html, count=1)
    os.makedirs(os.path.dirname(RENDERED_PATH), exist_ok=True)
    with open(RENDERED_PATH, 'w') as f:
        f.write(new_html)


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='EOW asymmetric-breakout scan.')
    ap.add_argument('--top', type=int, default=25, help='Top N from ApeWisdom WSB')
    ap.add_argument('--workers', type=int, default=3, help='Parallel UW pulls (UW caps at 3 concurrent)')
    args = ap.parse_args()

    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set')
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Template not found: {TEMPLATE_PATH}')

    target_date = next_friday()
    target_date_iso = target_date.strftime('%Y-%m-%d')
    print(f'Scanning ApeWisdom WSB top {args.top} for EOW {target_date_iso}…')
    started = datetime.now()

    print(f'\n[1/3] Pulling ApeWisdom top {args.top}…')
    apes = fetch_apewisdom_top(args.top)
    print(f'  {len(apes)} tickers: ' + ', '.join(a['ticker'] for a in apes))

    print(f'\n[2/3] Running per-ticker UW scans (parallel x {args.workers})…')
    scanned = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(scan_one, ape, token, target_date_iso): ape for ape in apes}
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                ape = futures[fut]
                r = {
                    'ticker': ape['ticker'], 'name': ape['name'],
                    'rank': ape['rank'], 'rank_24h': ape['rank_24h'],
                    'mentions': ape['mentions'], 'mentions_24h': ape['mentions_24h'],
                    'status': 'error', 'reason': str(e)[:120],
                }
            scanned.append(r)
            mark = r.get('grade') or {'no-eow': '-', 'unscorable': '?', 'pull-failed': '!',
                                       'no-data': '?', 'error': '!'}.get(r.get('status'), '?')
            print(f'  [{mark:>2}] {r["ticker"]:<7} {r.get("status","ok"):<12} '
                  f'{("$"+str(r.get("price","")))[:9]:<10} score={r.get("score","-")}')

    # Sort: by grade tier (A → F), then by |gap_pct| desc within each tier.
    # Skipped rows (no-eow, no-data, pull-failed) at the very bottom alphabetical.
    _GRADE_RANK = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}
    def sort_key(r):
        g = r.get('grade')
        if g in _GRADE_RANK:
            return (0, _GRADE_RANK[g], -abs(r.get('gap_pct') or 0))
        return (1, 9, r['ticker'])
    scanned.sort(key=sort_key)

    elapsed = (datetime.now() - started).total_seconds()
    print(f'\n[3/3] Rendering scan page…  (wall time {elapsed:.1f}s)')
    config_js = build_config_js(scanned, args.top, target_date_iso)
    patch_html(config_js)
    print(f'\n✓ {RENDERED_PATH}')

    # Top-line summary
    graded = [r for r in scanned if r.get('grade')]
    a_grade = [r for r in graded if r['grade'] == 'A']
    if a_grade:
        print('\nGrade-A picks:')
        for r in a_grade:
            arrow = '↑' if r.get('direction') == 'LONG' else '↓'
            tgt = r.get('target') or r.get('target_price') or 0
            print(f"  {r['ticker']:<6} {arrow} {r.get('mode','')} target ${tgt:g} "
                  f"({r['gap_pct']:+.1f}%)  velocity={r['velocity_score']}")
    else:
        print('\nNo grade-A picks today.')

    if not os.environ.get('GAMMA_NO_OPEN'):
        subprocess.run(['open', RENDERED_PATH])


if __name__ == '__main__':
    main()
