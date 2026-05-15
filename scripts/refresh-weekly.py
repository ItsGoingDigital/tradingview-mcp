#!/usr/bin/env python3
"""
Refresh the weekly EOW gamma heatmap for a single stock ticker.

Pulls UW per-expiry greeks for this Friday (or --expiry override), joins with
option-contracts OI to compute OI-weighted net gamma per strike, derives
pin/walls/put-magnet/flip with proximity filters, persists to Supabase,
rewrites the CONFIG block in charts/templates/gamma-heatmap.html, and opens
the rendered output.

Usage:
    python3 scripts/refresh-weekly.py MRNA
    python3 scripts/refresh-weekly.py SNOW --expiry 2026-05-22
    python3 scripts/refresh-weekly.py ORCL --window 0.25

Requires:
    UW_API_TOKEN
    SUPABASE_URL, SUPABASE_SERVICE_KEY
    TradingView running (optional — used for price cross-check)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time as _time
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store_snapshot import store_snapshot
from strat import match_3_candle_setup
import tv_helpers as tv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'gamma-heatmap.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'gamma-heatmap.html')
TV_CLI = os.path.join(_REPO_ROOT, 'src', 'cli', 'index.js')

# Thresholds — match the multi-ticker conventions, all relative.
WALL_MIN_RATIO = 0.05
PIN_PROX_PCT   = 0.05
PUT_PROX_PCT   = 0.10
WALL_PROX_PCT  = 0.10
FLIP_PROX_PCT  = 0.15


# ─────────────────────────────────────────────────────────
# IO
# ─────────────────────────────────────────────────────────
def fetch_uw(endpoint, token):
    req = Request(
        f'https://api.unusualwhales.com{endpoint}',
        headers={
            'Authorization': f'Bearer {token}',
            'UW-CLIENT-API-ID': '100001',
        },
    )
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()[:300]
        sys.exit(f'UW API error {e.code} on {endpoint}: {body}')


def get_tv_quote(expected_price):
    """Pull active TV chart's quote; reject if >30% off expected (likely wrong symbol)."""
    try:
        result = subprocess.run(
            ['node', TV_CLI, 'quote'],
            capture_output=True, text=True, timeout=8,
        )
        if result.returncode != 0:
            return None
        q = json.loads(result.stdout)
        last = float(q.get('last') or q.get('close') or 0)
        if last <= 0:
            return None
        if expected_price > 0 and abs(last - expected_price) / expected_price > 0.30:
            return None
        return last
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
        return None


def pull_weekly_chart_data(expected_price=0, tolerance=0.30):
    """Single TV interaction: swap chart to W timeframe, then pull both:
      - This week's OHLC bar (for the range strip)
      - LuxAlgo Market Structure zones on weekly bars (for weekly S&D)
    Restores the original TF when done. Returns {session_range, zones}, with
    either field possibly None / [] on failure.

    session_range is rejected when bar close diverges from `expected_price` by
    >`tolerance` fraction (guards against chart being on the wrong symbol)."""
    original_state = tv.get_active_state() or {}
    original_tf = original_state.get('resolution')

    # Long settle on the W switch — LuxAlgo MS Fractal needs time to recompute
    # pivots/structure across full weekly history before zones become readable.
    if not tv.set_timeframe('W', settle=5.0):
        return {'session_range': None, 'zones': []}

    # Weekly OHLC
    bar_raw = tv.tv_cli('ohlcv', '-n', '1', '--summary')
    session_range = None
    if bar_raw:
        try:
            b = json.loads(bar_raw)
            hi, lo = b.get('high'), b.get('low')
            if hi is not None and lo is not None:
                close = float(b.get('close', 0))
                ok = True
                if expected_price and expected_price > 0 and close > 0:
                    if abs(close - expected_price) / expected_price > tolerance:
                        ok = False
                if ok:
                    session_range = {
                        'open':  float(b.get('open', 0)),
                        'high':  float(hi),
                        'low':   float(lo),
                        'close': close,
                    }
        except (json.JSONDecodeError, ValueError):
            pass

    # Weekly S&D zones — chart-data SKILL Gate 1: pull twice with 2s gap,
    # values must match across both pulls. Re-pull until stable.
    def _pull_zones():
        return tv.pull_structure_zones(
            current_price=expected_price if expected_price > 0 else None,
            top_n_per_side=10,
        )
    pull_a = _pull_zones()
    _time.sleep(2)
    pull_b = _pull_zones()
    attempts = 1
    while _zones_signature(pull_a) != _zones_signature(pull_b) and attempts < 4:
        _time.sleep(2)
        pull_a = pull_b
        pull_b = _pull_zones()
        attempts += 1
    zones = pull_b if _zones_signature(pull_a) == _zones_signature(pull_b) else []

    # Select only the most-recent unmitigated supply and most-recent demand
    supplies = sorted([z for z in zones if z.get('zone_type') == 'supply'],
                      key=lambda z: -z.get('bar_idx', 0))
    demands  = sorted([z for z in zones if z.get('zone_type') == 'demand'],
                      key=lambda z: -z.get('bar_idx', 0))
    final = []
    if supplies: final.append(supplies[0])
    if demands:  final.append(demands[0])

    # Strat — last 4 closed WEEKLY bars (anchor + P1/P2/P3) for the matcher.
    strat_bars = tv.get_recent_closed_bars(n=4, expected_price=expected_price)

    if original_tf and original_tf != 'W':
        tv.set_timeframe(original_tf, settle=0.8)

    return {'session_range': session_range, 'zones': final, 'strat_bars': strat_bars}


def _zones_signature(zones):
    """Stable hashable summary of a zones list — for cross-pull equality."""
    if not zones:
        return ()
    return tuple(sorted(
        (z.get('zone_type'), z.get('bar_idx'), z.get('upper'), z.get('lower'))
        for z in zones
    ))


# ─────────────────────────────────────────────────────────
# Expiry helpers
# ─────────────────────────────────────────────────────────
def next_friday(from_date=None):
    """Return ISO date of the next Friday at or after from_date (today if None)."""
    d = from_date or datetime.now().date()
    # weekday(): Mon=0 ... Fri=4 ... Sun=6
    days_ahead = (4 - d.weekday()) % 7
    return (d + timedelta(days=days_ahead)).strftime('%Y-%m-%d')


# ─────────────────────────────────────────────────────────
# Gamma math
# ─────────────────────────────────────────────────────────
def derive_levels(strikes_net, price):
    """Same proximity-filtered math as the multi-ticker script."""
    if not strikes_net:
        return {}
    max_abs = max(abs(v) for v in strikes_net.values())
    threshold = max_abs * WALL_MIN_RATIO

    prox = price * PIN_PROX_PCT
    near = {s: g for s, g in strikes_net.items()
            if abs(s - price) <= prox and g >= threshold}
    pin = max(near.items(), key=lambda x: x[1]) if near else None

    put_band = price * PUT_PROX_PCT
    neg = [(s, g) for s, g in strikes_net.items()
           if g < -threshold and abs(s - price) <= put_band]
    put_mag = min(neg, key=lambda x: x[1]) if neg else None

    wall_band = price * WALL_PROX_PCT
    upper_bound = pin[0] if pin else price
    lower_bound = put_mag[0] if put_mag else float('-inf')
    wall_up, wall_down = None, None
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
        'pin': pin, 'put_mag': put_mag,
        'wall_up': wall_up, 'wall_down': wall_down,
        'flip': flip, 'regime': regime,
    }


# ─────────────────────────────────────────────────────────
# Data pull — EOW-first, aggregate-fallback
# ─────────────────────────────────────────────────────────
def pull_eow(ticker, expiry, token):
    """Combine /greeks + /option-contracts for OI-weighted per-strike gamma.

    /greeks gives raw gamma per share per option (filtered to one expiry).
    /option-contracts gives open_interest per option symbol.
    Multiply gamma × OI × 100 (contract size) and sign puts negative to match
    UW's spot-exposures convention (call_gex positive, put_gex negative).
    """
    greeks = fetch_uw(f'/api/stock/{ticker}/greeks?expiry={expiry}', token).get('data', [])
    if not greeks:
        return None

    contracts = fetch_uw(f'/api/stock/{ticker}/option-contracts?expiry={expiry}', token).get('data', [])
    oi_by_sym = {c['option_symbol']: int(c.get('open_interest') or 0) for c in contracts}

    by_strike = {}
    for g in greeks:
        s = float(g['strike'])
        cg = float(g.get('call_gamma') or 0)
        pg = float(g.get('put_gamma') or 0)
        coi = oi_by_sym.get(g.get('call_option_symbol'), 0)
        poi = oi_by_sym.get(g.get('put_option_symbol'), 0)
        call_gex = cg * coi * 100
        put_gex  = -1 * pg * poi * 100
        # Approximate per-strike fields. Match Supabase schema.
        by_strike[s] = {
            'strike': s,
            'call_gamma_oi': call_gex,
            'put_gamma_oi':  put_gex,
            'call_gamma_vol': 0.0,
            'put_gamma_vol':  0.0,
            'call_delta_oi':  float(g.get('call_delta') or 0) * coi * 100,
            'put_delta_oi':   float(g.get('put_delta')  or 0) * poi * 100,
        }
    return sorted(by_strike.values(), key=lambda x: x['strike'])


def pull_aggregate(ticker, token):
    """Fallback: /greek-exposure/strike (aggregate across all expiries)."""
    data = fetch_uw(f'/api/stock/{ticker}/greek-exposure/strike', token)
    rows = data.get('data', [])
    if not rows:
        return None
    by_strike = {}
    for r in rows:
        by_strike[float(r['strike'])] = {
            'strike': float(r['strike']),
            'call_gamma_oi': float(r.get('call_gex') or 0),
            'put_gamma_oi':  float(r.get('put_gex') or 0),
            'call_gamma_vol': 0.0,
            'put_gamma_vol':  0.0,
            'call_delta_oi': float(r.get('call_delta') or 0),
            'put_delta_oi':  float(r.get('put_delta')  or 0),
        }
    return sorted(by_strike.values(), key=lambda x: x['strike'])


def fetch_price(ticker, token):
    """/spot-exposures/strike rows carry a `price` field for every ticker."""
    data = fetch_uw(f'/api/stock/{ticker}/spot-exposures/strike', token)
    rows = data.get('data', [])
    if not rows:
        return 0
    return float(rows[0].get('price') or 0)


def pull_flow(ticker, token, top_n=5, lookback_minutes=60):
    """Pull recent flow alerts, filter to last <lookback> minutes, return top N by premium.

    Each row gets normalized to a compact shape for the heatmap sidecar:
        time_local  — HH:MM:SS in local time, second precision (per user ask)
        time_iso    — full ISO timestamp for tooltips
        type        — 'C' or 'P'
        strike      — float
        premium     — float
        size        — int
        side        — 'bid' / 'ask' / 'mid' (where the trade hit)
        sentiment   — 'bullish' / 'bearish' / null (UW classification)
        sweep       — bool (UW tags whether this was a sweep)
        underlying_price — spot at execution
    Sorted newest-first within the top-N premium slice so the most recent
    big print appears at the top of the strip.
    """
    raw = fetch_uw(f'/api/stock/{ticker}/flow-recent', token)
    rows = raw if isinstance(raw, list) else raw.get('data', [])
    if not rows:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    cleaned = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r['executed_at'].replace('Z', '+00:00'))
        except (KeyError, ValueError):
            continue
        if ts < cutoff:
            continue
        tags = r.get('tags') or []
        side = 'ask' if 'ask_side' in tags else 'bid' if 'bid_side' in tags else 'mid'
        sentiment = 'bullish' if 'bullish' in tags else 'bearish' if 'bearish' in tags else None
        cleaned.append({
            'time_local': ts.astimezone().strftime('%H:%M:%S'),
            'time_iso':   ts.astimezone().isoformat(timespec='seconds'),
            'type':       'C' if (r.get('option_type') or '').lower() == 'call' else 'P',
            'strike':     float(r.get('strike') or 0),
            'premium':    float(r.get('premium') or 0),
            'size':       int(r.get('size') or 0),
            'side':       side,
            'sentiment':  sentiment,
            'sweep':      'sweep' in tags,
            'underlying_price': float(r.get('underlying_price') or 0),
            '_ts': ts,
        })

    cleaned.sort(key=lambda x: x['premium'], reverse=True)
    top = cleaned[:top_n]
    top.sort(key=lambda x: x['_ts'], reverse=True)
    for t in top:
        t.pop('_ts', None)
    return top


# ─────────────────────────────────────────────────────────
# CONFIG block rewriter
# ─────────────────────────────────────────────────────────
def fmt_strike_key(s):
    return f'{int(s)}' if s == int(s) else f'{s:.2f}'


def build_flow_js(flow_rows):
    """Render the flow array as JS object literals."""
    if not flow_rows:
        return '[]'
    parts = []
    for r in flow_rows:
        parts.append(
            "    { "
            f"time: '{r['time_local']}', "
            f"timeIso: '{r['time_iso']}', "
            f"type: '{r['type']}', "
            f"strike: {fmt_strike_key(r['strike'])}, "
            f"premium: {int(round(r['premium']))}, "
            f"size: {r['size']}, "
            f"side: '{r['side']}', "
            f"sentiment: {('null' if r['sentiment'] is None else repr(r['sentiment']))}, "
            f"sweep: {'true' if r['sweep'] else 'false'}, "
            f"spot: {r['underlying_price']}"
            " }"
        )
    return '[\n' + ',\n'.join(parts) + '\n  ]'


def build_config_js(ticker, expiry, source, parsed, price, levels, window_pct, flow_rows=None, session_range=None, weekly_zones=None, strat_setup=None):
    """Render the JS CONFIG block expected by gamma-heatmap.html template.

    Schema:
      ticker, name, expiry, expiryLabel, today, currentPrice, priceContext,
      netGex, gammaFlip, poc, strikeRange{low,high,step}, strikes{},
      weeklyZones[], stratWeekly{}
    """
    now = datetime.now()
    today_iso = now.strftime('%Y-%m-%d')
    exp_date = datetime.strptime(expiry, '%Y-%m-%d').date()
    exp_label = f"EOW {exp_date.strftime('%-m/%-d')}"

    strikes_net = {p['strike']: p['call_gamma_oi'] + p['put_gamma_oi'] for p in parsed}

    # Strike window — ±window_pct of price, infer step from data
    band = price * window_pct
    low = max(0, price - band)
    high = price + band
    in_range = {s: g for s, g in strikes_net.items() if low <= s <= high}

    # Strike step inference — median gap between consecutive strikes
    sorted_strikes = sorted(in_range.keys())
    if len(sorted_strikes) >= 2:
        gaps = [sorted_strikes[i+1] - sorted_strikes[i] for i in range(len(sorted_strikes)-1)]
        step = min(gaps)
    else:
        step = 1

    # Round low/high to step grid
    low_g = int(low / step) * step
    high_g = int(high / step + 1) * step

    strikes_lines = []
    for s in sorted(in_range.keys(), reverse=True):
        key = fmt_strike_key(s)
        val = int(round(in_range[s]))
        strikes_lines.append(f'    {key}: {val},')
    strikes_block = '\n'.join(strikes_lines).rstrip(',')

    flip = levels.get('flip')
    flip_js = 'null' if flip is None else fmt_strike_key(flip)
    net_gex = int(round(sum(strikes_net.values())))

    price_ctx = (
        f"Live UW pull · expiry {expiry} ({'EOW filtered' if source == 'eow' else 'aggregate fallback'}) · "
        f"{now.strftime('%H:%M:%S')} local · snapshot persisted to Supabase."
    ).replace("'", "\\'")

    step_str = fmt_strike_key(step) if step % 1 != 0 else str(int(step))
    flow_block = build_flow_js(flow_rows or [])

    as_of = datetime.now(timezone.utc).isoformat()
    if session_range and session_range.get('high') is not None and session_range.get('low') is not None:
        session_range_js = (
            f"{{ high: {session_range['high']}, low: {session_range['low']}, "
            f"open: {session_range.get('open', 'null')}, close: {session_range.get('close', 'null')}, label: 'Week' }}"
        )
    else:
        session_range_js = 'null'

    zone_items = []
    for z in (weekly_zones or []):
        zone_items.append(
            f"{{ upper: {z['upper']}, lower: {z['lower']}, "
            f"type: '{z['zone_type']}', direction: '{z['direction']}', "
            f"mitigated: false, bar_idx: {z.get('bar_idx', 0)} }}"
        )
    weekly_zones_js = '[' + ', '.join(zone_items) + ']'

    if strat_setup:
        _ssp = strat_setup['pattern'].replace("'", "\\'")
        strat_setup_js = (
            f"{{ pattern: '{_ssp}', direction: '{strat_setup['direction']}', "
            f"target: {strat_setup['target']}, p1Type: '{strat_setup['p1_type']}', "
            f"p2Type: '{strat_setup['p2_type']}', p3Type: '{strat_setup['p3_type']}' }}"
        )
    else:
        strat_setup_js = 'null'

    return f"""const CONFIG = {{
  ticker: '{ticker}',
  name: '{ticker}',
  expiry: '{expiry}',
  expiryLabel: '{exp_label}',
  today: '{today_iso}',
  asOf: '{as_of}',
  currentPrice: {price},
  atmStrike: null,
  dayChange: null,
  dayChangePct: null,
  priceContext: '{price_ctx}',
  netGex: {net_gex},
  gammaFlip: {flip_js},
  poc: null,
  sessionRange: {session_range_js},
  stratSetup: {strat_setup_js},
  strikeRange: {{ low: {low_g}, high: {high_g}, step: {step_str} }},
  strikes: {{
{strikes_block}
  }},
  flow: {flow_block},
  weeklyZones: {weekly_zones_js},
  stratWeekly: {{ triggered: false, scenario: '', note: '' }}
}};"""


def patch_html(config_js):
    with open(TEMPLATE_PATH, 'r') as f:
        html = f.read()
    pattern = r'const CONFIG = \{[\s\S]*?\n\};'
    if not re.search(pattern, html):
        sys.exit(f'Could not find CONFIG block in {TEMPLATE_PATH}')
    new_html = re.sub(pattern, config_js, html, count=1)
    os.makedirs(os.path.dirname(RENDERED_PATH), exist_ok=True)
    with open(RENDERED_PATH, 'w') as f:
        f.write(new_html)


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='Refresh weekly EOW gamma heatmap for a stock ticker.')
    ap.add_argument('ticker', help='Stock ticker (e.g. MRNA, SNOW, ORCL)')
    ap.add_argument('--expiry', help='ISO expiry date (default: next Friday)', default=None)
    ap.add_argument('--window', type=float, default=0.20,
                    help='Strike window as fraction of price (default 0.20)')
    ap.add_argument('--lookback', type=int, default=60,
                    help='Flow lookback window in minutes (default 60)')
    args = ap.parse_args()

    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set')
    if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_KEY'):
        sys.exit('SUPABASE_URL or SUPABASE_SERVICE_KEY not set')
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Template not found: {TEMPLATE_PATH}')

    ticker = args.ticker.upper()
    expiry = args.expiry or next_friday()
    print(f'[{ticker}] Target expiry: {expiry}')

    # Try EOW-filtered first
    print(f'[{ticker}] Pulling /greeks?expiry={expiry} + /option-contracts…')
    parsed = pull_eow(ticker, expiry, token)
    source = 'eow'
    if not parsed:
        print(f'[{ticker}] No EOW data — falling back to /greek-exposure/strike (aggregate)')
        parsed = pull_aggregate(ticker, token)
        source = 'aggregate'
    if not parsed:
        sys.exit(f'[{ticker}] No data from either endpoint')

    uw_price = fetch_price(ticker, token)
    if uw_price <= 0:
        sys.exit(f'[{ticker}] Could not determine reference price')

    tv_last = get_tv_quote(uw_price)
    price = tv_last if (tv_last and tv_last > 0) else uw_price
    if tv_last and tv_last > 0 and abs(tv_last - uw_price) > max(0.5, uw_price * 0.005):
        print(f'  Note: TV last ${tv_last} differs from UW gamma ref ${uw_price} by {tv_last - uw_price:+.2f}')

    strikes_net = {p['strike']: p['call_gamma_oi'] + p['put_gamma_oi'] for p in parsed}
    levels = derive_levels(strikes_net, price)

    # Persist to Supabase
    snap_levels = {
        'tv_price': price, 'uw_ref_price': uw_price,
        'data_time': datetime.now(timezone.utc).isoformat(),
        'total_oi_gamma': sum(strikes_net.values()),
        'total_vol_gamma': 0, 'total_dir_gamma': 0,
        'pin_strike':       levels['pin'][0]       if levels.get('pin')       else None,
        'pin_gamma':        levels['pin'][1]       if levels.get('pin')       else None,
        'wall_up_strike':   levels['wall_up'][0]   if levels.get('wall_up')   else None,
        'wall_up_gamma':    levels['wall_up'][1]   if levels.get('wall_up')   else None,
        'wall_down_strike': levels['wall_down'][0] if levels.get('wall_down') else None,
        'wall_down_gamma': levels['wall_down'][1] if levels.get('wall_down') else None,
        'put_mag_strike':   levels['put_mag'][0]   if levels.get('put_mag')   else None,
        'put_mag_gamma':    levels['put_mag'][1]   if levels.get('put_mag')   else None,
        'flip_strike':      levels.get('flip'),
    }
    strike_rows = [{'snapshot_id': None, **{k: p[k] for k in (
        'strike', 'call_gamma_oi', 'put_gamma_oi', 'call_gamma_vol',
        'put_gamma_vol', 'call_delta_oi', 'put_delta_oi'
    )}, 'net_gamma': p['call_gamma_oi'] + p['put_gamma_oi']} for p in parsed]
    # store_snapshot adds snapshot_id itself; strip the placeholder
    for r in strike_rows:
        r.pop('snapshot_id', None)
    snap_id = store_snapshot(ticker=ticker, expiry=expiry, levels=snap_levels, strikes=strike_rows)
    print(f'  ✓ Supabase snapshot {snap_id}')

    # Pull recent unusual flow for the sidecar
    print(f'[{ticker}] Pulling /flow-recent (last {args.lookback} min)…')
    flow_rows = pull_flow(ticker, token, top_n=5, lookback_minutes=args.lookback)
    print(f'  {len(flow_rows)} flow prints kept (top 5 by premium)')

    # Pull this week's OHLC + weekly S&D zones from active TV chart. Switch
    # to the dedicated Swing Trading layout first so we don't disturb the
    # index 0DTE layout, then set the chart to the target ticker.
    saved_layout = 'Swing Trading'
    print(f'  Switching to TV layout: {saved_layout}…')
    tv.switch_saved_layout(saved_layout)
    try:
        subprocess.run(['node', TV_CLI, 'symbol', ticker],
                       capture_output=True, text=True, timeout=8)
    except (subprocess.TimeoutExpired, OSError):
        pass
    # Gate 1 (chart-data SKILL): after chart_set_symbol, sleep ≥5s so the
    # indicator can recompute on the new symbol before we read its drawings.
    _time.sleep(5)
    weekly_chart = pull_weekly_chart_data(expected_price=price, tolerance=0.30)
    session_range = weekly_chart['session_range']
    weekly_zones = weekly_chart['zones']
    strat_bars = weekly_chart.get('strat_bars')
    if session_range:
        print(f'  Weekly range: ${session_range["low"]:.2f} – ${session_range["high"]:.2f}')
    else:
        print(f'  Note: weekly range pull rejected — switch TV to {ticker} chart and re-run')
    print(f'  Weekly S&D zones: {len(weekly_zones)} pulled')

    # Phase 2 — Strat 3-bar setup (pure function)
    strat_setup = match_3_candle_setup(strat_bars) if strat_bars else None
    if strat_setup:
        arrow = '↑' if strat_setup['direction'] == 'bullish' else '↓'
        print(f'  Weekly Strat: {strat_setup["pattern"]} {arrow} · target ${strat_setup["target"]:g}')
    else:
        print(f'  Weekly Strat: no qualified 3-bar setup')

    # Render HTML
    config_js = build_config_js(ticker, expiry, source, parsed, price, levels,
                                args.window, flow_rows, session_range, weekly_zones,
                                strat_setup=strat_setup)
    patch_html(config_js)
    print(f'\n✓ Rendered {RENDERED_PATH}')
    print(f'  Source:   {source} ({"OI-weighted EOW" if source == "eow" else "aggregate, all expiries"})')
    print(f'  Price:    ${price}')
    bits = []
    if levels.get('pin'):       bits.append(f'pin ${fmt_strike_key(levels["pin"][0])}')
    if levels.get('wall_up'):   bits.append(f'wall↑ ${fmt_strike_key(levels["wall_up"][0])}')
    if levels.get('wall_down'): bits.append(f'wall↓ ${fmt_strike_key(levels["wall_down"][0])}')
    if levels.get('put_mag'):   bits.append(f'put ${fmt_strike_key(levels["put_mag"][0])}')
    if levels.get('flip'):      bits.append(f'flip ${fmt_strike_key(levels["flip"])}')
    print(f'  Levels:   {" · ".join(bits) if bits else "(none in proximity)"}')
    print(f'  Regime:   {levels.get("regime")}')

    subprocess.run(['open', RENDERED_PATH])


if __name__ == '__main__':
    main()
