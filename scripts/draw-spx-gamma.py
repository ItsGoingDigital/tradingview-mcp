#!/usr/bin/env python3
"""
Draw SPX gamma levels on TradingView using live Unusual Whales data.

Pulls SPX spot-exposures from UW, identifies meaningful gamma levels (pin,
walls, put magnet, flip), clears any existing drawings, and draws labeled
horizontal lines on the active TradingView chart.

The S&D zones, POC, and Strat are already drawn natively by the TradingView
indicators you have loaded. This script only adds the gamma-specific layer
that doesn't have a TV indicator equivalent.

Requires:
    - UW_API_TOKEN in environment
    - TradingView running with CDP (launch via `node src/cli/index.js launch`
      or use the mcp_tradingview tools)

Usage:
    python3 scripts/draw-spx-gamma.py
"""
import json
import os
import subprocess
import sys
import time as _time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TICKER = 'SPX'
TV_SYMBOL = 'SP:SPX'
WALL_MIN_RATIO = 0.05       # 5% of max |gex| to qualify as a wall
PIN_PROX_PCT = 0.05         # pin must be within ±5% of current price
DRAW_WALLS = True  # draws both wall_up (above pin) and wall_down (between price and put mag) when present
TV_CLI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'src', 'cli', 'index.js',
)

# Color palette (matches the heatmap convention)
COLOR_PIN = '#22c55e'         # bright green — dominant pin
COLOR_WALL = '#fbbf24'        # amber — structural walls (neutral, not direction)
COLOR_PUT_MAG = '#ef4444'     # red — put magnet
COLOR_FLIP = '#cbd5e1'        # light gray — gamma flip (regime boundary)


def tv_cli(*args, capture=True):
    """Run a tv CLI command; return stdout or None on failure."""
    cmd = ['node', TV_CLI] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        print(f'tv CLI timeout: {" ".join(args)}', file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f'tv CLI error: {result.stderr.strip()}', file=sys.stderr)
        return None
    return result.stdout.strip() if capture else None


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
        sys.exit(f'UW API error {e.code}: {e.read().decode()[:300]}')


def draw_line(price, color, label, linestyle=0, linewidth=1):
    """Draw a horizontal line via the tv CLI.

    Note: TradingView's drawing API requires an x-anchor point even for
    horizontal lines, so we pass current Unix time as --time.
    """
    overrides = {
        'linecolor': color,
        'linewidth': linewidth,
        'linestyle': linestyle,   # 0=solid, 1=dotted, 2=dashed
        'showLabel': True,
        'text': label,
        'textcolor': color,
        'fontsize': 11,
        'horzLabelsAlign': 'right',
        'vertLabelsAlign': 'middle',
    }
    return tv_cli(
        'draw', 'shape',
        '--type', 'horizontal_line',
        '--price', str(price),
        '--time', str(int(_time.time())),
        '--overrides', json.dumps(overrides),
    )


def fmt_b(v):
    sign = '+' if v >= 0 else '−'
    return f'{sign}${abs(v)/1e9:.1f}B'


def main():
    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set — add export UW_API_TOKEN=... to ~/.zshrc')

    # Ensure chart is on SPX
    tv_cli('symbol', TV_SYMBOL)

    # Pull spot exposures
    data = fetch_uw(f'/api/stock/{TICKER}/spot-exposures/strike', token)
    rows = data.get('data', [])
    if not rows:
        sys.exit('No data from UW spot-exposures endpoint')

    # Build per-strike net gamma (OI)
    strikes_net = {}
    for r in rows:
        s = float(r['strike'])
        call_g = float(r.get('call_gamma_oi') or 0)
        put_g = float(r.get('put_gamma_oi') or 0)
        strikes_net[s] = call_g + put_g

    uw_price = float(rows[0].get('price') or 0)
    if uw_price == 0:
        sys.exit('Could not determine reference price from UW data')

    # Cross-validate with TradingView — use TV as authoritative for actual price.
    # UW's `price` is the gamma reference (often a few dollars off the last trade).
    tv_quote_out = tv_cli('quote')
    price = uw_price
    if tv_quote_out:
        try:
            q = json.loads(tv_quote_out)
            tv_last = float(q.get('last') or q.get('close') or 0)
            if tv_last > 0:
                price = tv_last
                if abs(tv_last - uw_price) > 1:
                    print(f'Note: TV last ${tv_last} differs from UW gamma ref ${uw_price} by {tv_last - uw_price:+.2f}')
        except (json.JSONDecodeError, ValueError):
            pass

    # Threshold for "meaningful wall"
    max_abs = max(abs(v) for v in strikes_net.values())
    threshold = max_abs * WALL_MIN_RATIO

    # Pin = largest +gex strike within proximity of price
    prox_dollars = price * PIN_PROX_PCT
    near = {s: g for s, g in strikes_net.items()
            if abs(s - price) <= prox_dollars and g > 0}
    pin = (max(near.items(), key=lambda x: x[1]) if near else None)

    # Put magnet = most negative strike (must pass threshold)
    neg = [(s, g) for s, g in strikes_net.items() if g < -threshold]
    put_mag = min(neg, key=lambda x: x[1]) if neg else None

    # Walls = the single biggest positive-gex blocker on each side, by direction:
    #   Wall Up:   above the pin (caps further upside past the pin)
    #   Wall Down: between current price and put magnet (supports the way down)
    # Both excluded if they collide with the pin itself.
    upper_bound = pin[0] if pin else price
    lower_bound = put_mag[0] if put_mag else float('-inf')

    wall_up = None
    wall_down = None
    for s, g in strikes_net.items():
        if g <= threshold:
            continue
        if pin and s == pin[0]:
            continue
        if s > upper_bound and (wall_up is None or g > wall_up[1]):
            wall_up = (s, g)
        if s < price and s > lower_bound and (wall_down is None or g > wall_down[1]):
            wall_down = (s, g)

    # Gamma flip = first strike (descending) where cumulative net gamma < 0
    cum = 0.0
    flip = None
    for s in sorted(strikes_net.keys(), reverse=True):
        cum += strikes_net[s]
        if cum < 0 and flip is None:
            flip = s
            break

    # Wipe prior drawings — gamma layer is idempotent (refresh = redraw).
    # The CLI's `draw clear` relies on getChartApi which isn't bound in current
    # TradingView builds; calling removeAllDrawingTools() directly on the chart
    # widget works reliably across versions.
    print('Clearing existing drawings...')
    clear_js = (
        '(function(){'
        'const w=window._exposed_chartWidgetCollection?.activeChartWidget;'
        'const wv=typeof w==="object"&&w.value?w.value():w;'
        'if(!wv)return"no widget";'
        'try{wv.removeAllDrawingTools();return"cleared";}'
        'catch(e){return"error: "+e.message;}'
        '})()'
    )
    tv_cli('ui', 'eval', '-e', clear_js)

    print(f'\nDrawing gamma levels on {TV_SYMBOL} (reference price ${price}):\n')
    drawn = []

    if pin:
        s, g = pin
        label = f'PIN ${int(s)} ({fmt_b(g)})'
        draw_line(s, COLOR_PIN, label, linestyle=0, linewidth=2)
        drawn.append(('PIN', s, g))

    if wall_up:
        s, g = wall_up
        label = f'WALL ↑ ${int(s)} ({fmt_b(g)})'
        draw_line(s, COLOR_WALL, label, linestyle=2, linewidth=1)
        drawn.append(('WALL ↑', s, g))

    if wall_down:
        s, g = wall_down
        label = f'WALL ↓ ${int(s)} ({fmt_b(g)})'
        draw_line(s, COLOR_WALL, label, linestyle=2, linewidth=1)
        drawn.append(('WALL ↓', s, g))

    if put_mag:
        s, g = put_mag
        label = f'PUT MAG ${int(s)} ({fmt_b(g)})'
        draw_line(s, COLOR_PUT_MAG, label, linestyle=0, linewidth=2)
        drawn.append(('PUT', s, g))

    if flip:
        label = f'FLIP ${int(flip)}'
        draw_line(flip, COLOR_FLIP, label, linestyle=1, linewidth=1)
        drawn.append(('FLIP', flip, 0))

    for kind, s, g in drawn:
        gtxt = f' {fmt_b(g)}' if g != 0 else ''
        print(f'  ✓ {kind:8s} ${int(s):>7d}{gtxt}')

    print(f'\n{len(drawn)} levels drawn on {TV_SYMBOL}.')


if __name__ == '__main__':
    main()
