#!/usr/bin/env python3
"""
Refresh the SPX 0DTE gamma heatmap with live data from Unusual Whales.

Usage:
    python3 scripts/refresh-spx-0dte.py
    UW_API_TOKEN=xxx python3 scripts/refresh-spx-0dte.py

What it does:
    1. Pulls /api/stock/SPX/spot-exposures/strike from UW
    2. Aggregates total OI / Volume / Directionalized gamma
    3. Computes per-strike net gamma
    4. Estimates the gamma flip from cumulative sign change
    5. Rewrites the CONFIG block in /tmp/gamma-heatmap-0dte.html
    6. Opens the chart

Requires:
    - $UW_API_TOKEN set in the environment
    - /tmp/gamma-heatmap-0dte.html exists (the template chart)
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TICKER = 'SPX'
TV_SYMBOL = 'SP:SPX'
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'gamma-heatmap-0dte.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'gamma-heatmap-0dte.html')
STRIKE_WINDOW_BELOW = 280
STRIKE_WINDOW_ABOVE = 100
TV_CLI = os.path.join(_REPO_ROOT, 'src', 'cli', 'index.js')

# Shared TradingView helpers (quote, drawing, ICT label reads).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tv_helpers as tv
from strat import match_3_candle_setup

# Gamma-line colors when drawing on the TV chart
COLOR_PIN     = '#22c55e'
COLOR_WALL    = '#fbbf24'
COLOR_PUT_MAG = '#ef4444'
COLOR_FLIP    = '#cbd5e1'


def fetch(endpoint, token):
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
        sys.exit(f'API error {e.code} on {endpoint}: {body}')


def fmt_money(v):
    if v == 0:
        return '$0'
    sign = '+' if v >= 0 else '-'
    av = abs(v)
    if av >= 1e9:
        return f'{sign}${av/1e9:.1f}B'
    if av >= 1e6:
        return f'{sign}${av/1e6:.1f}M'
    if av >= 1e3:
        return f'{sign}${av/1e3:.0f}k'
    return f'{sign}${av:.0f}'


def main():
    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set — add export UW_API_TOKEN=... to ~/.zshrc')

    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Chart template not found at {TEMPLATE_PATH}')
    os.makedirs(os.path.dirname(RENDERED_PATH), exist_ok=True)

    # Pull textbook GEX from /spot-exposures/strike with proper params.
    # The endpoint's values are spot²-scaled in dollars, sign-conventioned
    # (call positive / put negative), and time-stamped intraday — exactly
    # what we want. Need limit=500 + centered min/max_strike or the default
    # returns 50 unhelpful rows.
    print('Pulling /spot-exposures/strike (textbook intraday GEX)...')
    from uw_gex import pull_spot_gex
    pull = pull_spot_gex(TICKER, token, window_below=500, window_above=500)
    parsed = pull['parsed']
    if not parsed:
        sys.exit('No data from /spot-exposures/strike')
    print(f'  strikes: {len(parsed)}  ref_price: ${pull["price"]}  time: {pull["time"]}')

    uw_ref_price = pull['price']
    data_time = pull['time'] or datetime.now(timezone.utc).isoformat()
    if uw_ref_price <= 0:
        sys.exit('Could not determine reference price from UW')

    # ━━━━━━━ PHASE 1 — TV COLLECT ━━━━━━━
    # Load the curated saved layout that has SPX on pane 1 with LuxAlgo MS
    # Fractal / Volume Profile / ICT Killzones already configured. Focus pane 1
    # so subsequent reads + draws target SPX.
    saved_layout = 'SPX / QQQ / SPY SCRIPT'
    print(f'Switching to saved TV layout: {saved_layout} (focus pane 1 = SPX)…')
    if tv.switch_saved_layout(saved_layout):
        tv.focus_pane(1)
        tv.set_pane_symbol(1, TV_SYMBOL)
    else:
        print(f'  ! Could not switch to "{saved_layout}" — falling back to single-chart', file=sys.stderr)
        tv.set_layout('s')
        tv.set_chart_symbol(TV_SYMBOL)

    # Record original TF before any switching so we can restore in Phase 3.
    state = tv.get_active_state() or {}
    original_tf = state.get('resolution')

    tv_last = tv.get_quote(expected_price=uw_ref_price)
    if tv_last:
        ref_price = tv_last
        price_source = 'TradingView'
        delta = ref_price - uw_ref_price
        if abs(delta) > 1:
            print(f'  Note: TV last (${ref_price}) differs from UW gamma ref (${uw_ref_price}) by {delta:+.2f}')
    else:
        ref_price = uw_ref_price
        price_source = 'UW gamma reference (TV unavailable)'

    # Intraday-TF reads: switch to 5m so Killzones + VP have intraday bars to
    # render against (these indicators don't produce labels on daily TF).
    INTRADAY_TF = '5'
    tv.set_timeframe(INTRADAY_TF)
    ict_levels = tv.pull_ict_levels(price=ref_price, prox_pct=0.10)
    poc_raw = tv.pull_poc()
    poc = poc_raw if (poc_raw and abs(poc_raw - ref_price) / ref_price < 0.05) else None
    if poc_raw and not poc:
        print(f'  Note: POC ${poc_raw:g} out of proximity band — discarded as stale')

    # Daily-TF read: most-recent unmitigated supply and demand zones from
    # the Market Structure indicator (paired solid + dashed lines from the
    # `tv data structure-zones` CLI). Heatmap renders at most one of each.
    weekly_zones = []
    session_range = None
    strat_bars = None
    # Longer settle for the D switch — LuxAlgo MS Fractal needs time to
    # recompute pivots/structure across full daily history.
    if tv.set_timeframe('D', settle=5.0):
        # Gate 1 stability — pull twice with 2s gap, re-pull until two
        # consecutive pulls agree on the zone set.
        import time as _t
        def _pull():
            return tv.pull_structure_zones(
                current_price=ref_price, top_n_per_side=10,
            )
        def _sig(zs):
            return tuple(sorted((z.get('zone_type'), z.get('bar_idx'),
                                 z.get('upper'), z.get('lower')) for z in (zs or [])))
        pull_a = _pull()
        _t.sleep(2)
        pull_b = _pull()
        attempts = 1
        while _sig(pull_a) != _sig(pull_b) and attempts < 4:
            _t.sleep(2)
            pull_a = pull_b
            pull_b = _pull()
            attempts += 1
        all_zones = pull_b if _sig(pull_a) == _sig(pull_b) else []
        sups = sorted([z for z in all_zones if z.get('zone_type') == 'supply'],
                      key=lambda z: -z.get('bar_idx', 0))
        dems = sorted([z for z in all_zones if z.get('zone_type') == 'demand'],
                      key=lambda z: -z.get('bar_idx', 0))
        if sups: weekly_zones.append(sups[0])
        if dems: weekly_zones.append(dems[0])
        tv.focus_pane(1)
        session_range = tv.get_session_range(expected_price=ref_price, tolerance=0.05)
        # Strat — last 4 closed daily bars (anchor + P1/P2/P3); Phase 2 matches.
        strat_bars = tv.get_recent_closed_bars(n=4, expected_price=ref_price)

    # Phase 2 — Strat 3-bar setup (pure function)
    strat_setup = match_3_candle_setup(strat_bars) if strat_bars else None
    if strat_setup:
        arrow = '↑' if strat_setup['direction'] == 'bullish' else '↓'
        print(f'  Strat:            {strat_setup["pattern"]} {arrow} · target ${strat_setup["target"]:g}')
    else:
        print(f'  Strat:            no qualified 3-bar setup')

    # Aggregates per 1% price change
    total_oi = sum(r['call_gamma_oi'] + r['put_gamma_oi'] for r in parsed)
    total_vol = sum(r['call_gamma_vol'] + r['put_gamma_vol'] for r in parsed)
    # Directionalized: approximate as call-side flow minus put-side flow (simple skew)
    total_dir = sum((r['call_gamma_vol'] - r['put_gamma_vol']) for r in parsed)

    # Per-strike net gamma (OI)
    strikes_net = {r['strike']: r['call_gamma_oi'] + r['put_gamma_oi'] for r in parsed}

    # Gamma flip estimate within ±15% band around price (matches the multi
    # script's logic so the two heatmaps agree on regime). No fallback to
    # ref_price — leave flip null when the cumulative stays one-signed across
    # the whole band, since "flip == price" is a misleading artifact that
    # tricks the HTML regime badge into showing the wrong sign.
    FLIP_BAND_PCT = 0.15
    flip_band = ref_price * FLIP_BAND_PCT
    band_strikes = [s for s in strikes_net.keys() if abs(s - ref_price) <= flip_band]
    cum = 0.0
    flip = None
    for s in sorted(band_strikes, reverse=True):
        cum += strikes_net[s]
        if cum < 0:
            flip = s
            break

    # Explicit regime classification — same rule the multi script uses.
    band_sum = sum(strikes_net.get(s, 0) for s in band_strikes)
    if flip is not None:
        regime = 'positive' if ref_price > flip else 'negative'
    elif band_sum > 0:
        regime = 'positive'
    elif band_sum < 0:
        regime = 'negative'
    else:
        regime = None

    # Strike range for the heatmap (focused on actionable area)
    atm = round(ref_price / 5) * 5
    strike_low = int((ref_price - STRIKE_WINDOW_BELOW) / 5) * 5
    strike_high = int((ref_price + STRIKE_WINDOW_ABOVE) / 5 + 1) * 5

    # Build strike entries (filter to range, keep $5 granularity)
    in_range = [s for s in strikes_net.keys()
                if strike_low <= s <= strike_high]
    in_range.sort(reverse=True)

    strike_lines = []
    for s in in_range:
        val = strikes_net[s]
        strike_lines.append(f"    {int(s) if s == int(s) else s}: {int(round(val))},")
    strikes_block = '\n'.join(strike_lines).rstrip(',')

    # Build the CONFIG block as a string
    today_iso = datetime.now().strftime('%Y-%m-%d')

    # ICT levels list — escape any quotes in the label text
    ict_items = []
    for lvl in (ict_levels or []):
        name_safe = (lvl['name'] or '').replace("'", "\\'")
        ict_items.append(f"{{ name: '{name_safe}', price: {lvl['price']} }}")
    ict_js = '[' + ', '.join(ict_items) + ']'

    # Daily S&D zones — emitted as `weeklyZones` (HTML JS already renders boxes)
    zone_items = []
    for z in (weekly_zones or []):
        zone_items.append(
            f"{{ upper: {z['upper']}, lower: {z['lower']}, "
            f"type: '{z['zone_type']}', direction: '{z['direction']}', "
            f"mitigated: false, bar_idx: {z.get('bar_idx', 0)} }}"
        )
    weekly_zones_js = '[' + ', '.join(zone_items) + ']'

    poc_js = 'null' if poc is None else str(poc)

    if session_range and session_range.get('high') is not None and session_range.get('low') is not None:
        session_range_js = (
            f"{{ high: {session_range['high']}, low: {session_range['low']}, "
            f"open: {session_range.get('open', 'null')}, close: {session_range.get('close', 'null')}, label: 'Day' }}"
        )
    else:
        session_range_js = 'null'

    if strat_setup:
        _ssp = strat_setup['pattern'].replace("'", "\\'")
        strat_setup_js = (
            f"{{ pattern: '{_ssp}', direction: '{strat_setup['direction']}', "
            f"target: {strat_setup['target']}, p1Type: '{strat_setup['p1_type']}', "
            f"p2Type: '{strat_setup['p2_type']}', p3Type: '{strat_setup['p3_type']}' }}"
        )
    else:
        strat_setup_js = 'null'

    config_block = f"""const CONFIG = {{
  ticker: 'SPX',
  name: 'S&P 500',
  expiry: '{today_iso}',
  expiryLabel: '0DTE {datetime.now().strftime("%-m/%-d")}',
  today: '{today_iso}',
  asOf: '{datetime.now(timezone.utc).isoformat()}',
  dataTime: '{data_time}',
  currentPrice: {ref_price},
  atmStrike: {atm},
  dayChange: null,
  dayChangePct: null,
  priceContext: 'Live pull · Unusual Whales API · {datetime.now().strftime("%H:%M:%S")} local',
  gamma: {{
    oi: {int(round(total_oi))},
    vol: {int(round(total_vol))},
    dir: {int(round(total_dir))}
  }},
  gammaFlip: {'null' if flip is None else flip},
  regime: {'null' if regime is None else f"'{regime}'"},
  poc: {poc_js},
  sessionRange: {session_range_js},
  stratSetup: {strat_setup_js},
  vpTimeframe: \"Today's session — POC live from Volume Profile / Fixed Range\",
  vpNote: \"Live UW data · strike-level OI gamma · refresh by re-running scripts/refresh-spx-0dte.py\",
  strikeRange: {{ low: {strike_low}, high: {strike_high}, step: 5 }},
  strikes: {{
{strikes_block}
  }},
  ictLevels: {ict_js},
  weeklyZones: {weekly_zones_js},
  stratWeekly: {{ triggered: false, scenario: '0DTE', note: '' }}
}};"""

    # Render: read template, swap CONFIG, write rendered output
    with open(TEMPLATE_PATH, 'r') as f:
        html = f.read()

    pattern = r'const CONFIG = \{[\s\S]*?\n\};'
    if not re.search(pattern, html):
        sys.exit('Could not locate CONFIG block in template — file may be malformed')

    new_html = re.sub(pattern, config_block, html, count=1)

    with open(RENDERED_PATH, 'w') as f:
        f.write(new_html)

    # Report
    print(f'✓ Rendered {RENDERED_PATH}')
    print(f'  Current price:   ${ref_price} (source: {price_source})')
    print(f'  UW gamma ref:    ${uw_ref_price} (calculation reference, not last trade)')
    print(f'  Strikes in range: {len(in_range)} (between ${strike_low} and ${strike_high})')
    print(f'  OI gamma total:   {fmt_money(total_oi)}/1%')
    print(f'  Vol gamma total:  {fmt_money(total_vol)}/1%')
    print(f'  Dir flow (skew):  {fmt_money(total_dir)}/1%')
    print(f'  Gamma flip est:   {("$"+str(flip)) if flip is not None else "—  (regime: " + (regime or "undetermined") + ")"}')
    print(f'  ICT levels:       {len(ict_levels)} pulled')
    print(f'  S&D zones:        {len(weekly_zones)} pulled')
    print(f'  Data timestamp:   {data_time}')

    # Derive pin / walls / put_mag from the WINDOWED strikes for TV drawing
    # (matches what the heatmap JS will compute on the same windowed strikes).
    in_range_net = {s: strikes_net[s] for s in in_range}
    derived = _derive_levels_for_draw(in_range_net, ref_price)

    # ━━━━━━━ PHASE 3 — TV DRAW ━━━━━━━
    # Chart is on daily from Phase 1; restore the original intraday TF, then
    # draw gamma + POC lines. S&D zones are NOT drawn on TV — the LuxAlgo MS
    # indicator already renders them natively on the chart, and our heatmap
    # reads from there.
    print('Drawing gamma lines on TV…')
    tv.clear_active_pane_drawings()
    if original_tf:
        tv.set_timeframe(original_tf)
    _draw_gamma_lines(derived, flip, poc)

    # Open the chart — suppressed when GAMMA_NO_OPEN=1 (used by refresh loops).
    if not os.environ.get('GAMMA_NO_OPEN'):
        subprocess.run(['open', RENDERED_PATH])


def _derive_levels_for_draw(strikes_net, price):
    """Lightweight derive matching the JS in gamma-heatmap-0dte.html.

    Returns dict with pin/wall_up/wall_down/put_mag (strike, gamma) tuples or None.
    Same relative-5% threshold as the multi script and the HTML template.
    """
    if not strikes_net:
        return {}
    max_abs = max(abs(v) for v in strikes_net.values()) or 0
    if max_abs == 0:
        return {}
    threshold = max_abs * 0.05

    pos = [(s, g) for s, g in strikes_net.items() if g > 0]
    neg = [(s, g) for s, g in strikes_net.items() if g < 0]
    pin     = max(pos, key=lambda x: x[1]) if pos else None
    put_mag = min(neg, key=lambda x: x[1]) if neg else None
    if pin     and pin[1]    <  threshold: pin = None
    if put_mag and put_mag[1] > -threshold: put_mag = None

    upper = pin[0] if pin else price
    lower = put_mag[0] if put_mag else float('-inf')
    wall_up = wall_down = None
    for s, g in strikes_net.items():
        if g <= threshold: continue
        if pin and s == pin[0]: continue
        if s > upper and (wall_up is None or g > wall_up[1]):
            wall_up = (s, g)
        if s < price and s > lower and (wall_down is None or g > wall_down[1]):
            wall_down = (s, g)
    return {'pin': pin, 'put_mag': put_mag, 'wall_up': wall_up, 'wall_down': wall_down}


def _draw_gamma_lines(derived, flip, poc=None):
    """Draw only the GEX-derived levels on TV. POC and S&D zones are NOT
    drawn — they come from native indicators on the chart and we already read
    from them; redrawing duplicates."""
    def maybe(lvl, color, kind, linestyle, linewidth):
        if not lvl: return
        s, g = lvl
        label = f'{kind} ${int(float(s))}'
        tv.draw_horizontal_line(float(s), color, label,
                                 linestyle=linestyle, linewidth=linewidth)
    maybe(derived.get('pin'),       COLOR_PIN,     'PIN',     0, 2)
    maybe(derived.get('wall_up'),   COLOR_WALL,    'WALL ↑',  2, 1)
    maybe(derived.get('wall_down'), COLOR_WALL,    'WALL ↓',  2, 1)
    maybe(derived.get('put_mag'),   COLOR_PUT_MAG, 'PUT MAG', 0, 2)
    if flip is not None:
        tv.draw_horizontal_line(float(flip), COLOR_FLIP, f'FLIP ${int(flip)}',
                                 linestyle=1, linewidth=1)


if __name__ == '__main__':
    main()
