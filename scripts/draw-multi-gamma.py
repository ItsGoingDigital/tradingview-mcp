#!/usr/bin/env python3
"""
Draw multi-ticker gamma levels on TradingView (SPX | SPY | QQQ side-by-side).

Sets up a 3-horizontal-pane TradingView layout, loads SPX/SPY/QQQ into each
pane, clears prior drawings, and overlays PIN / WALL ↑ / WALL ↓ / PUT MAG /
FLIP from the latest Supabase snapshot for each ticker.

Run scripts/refresh-multi-0dte.py first to populate Supabase. This script reads
pre-computed levels — it does not call UW.

Usage:
    python3 scripts/draw-multi-gamma.py

Requires:
    TradingView running with CDP
    SUPABASE_URL, SUPABASE_SERVICE_KEY (for reading latest snapshot)
"""
import json
import os
import subprocess
import sys
import time as _time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store_snapshot import get_latest_snapshot

TV_CLI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'src', 'cli', 'index.js',
)

# pane_index → (ticker, full TV symbol)
PANES = [
    (1, 'SPX', 'SP:SPX'),
    (2, 'SPY', 'AMEX:SPY'),
    (3, 'QQQ', 'NASDAQ:QQQ'),
]

COLOR_PIN     = '#22c55e'
COLOR_WALL    = '#fbbf24'
COLOR_PUT_MAG = '#ef4444'
COLOR_FLIP    = '#cbd5e1'


def tv_cli(*args, capture=True, timeout=12):
    cmd = ['node', TV_CLI] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'tv CLI timeout: {" ".join(args)}', file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f'tv CLI error ({" ".join(args)}): {result.stderr.strip()}', file=sys.stderr)
        return None
    return result.stdout.strip() if capture else None


def clear_active_pane_drawings():
    """Wipe all drawings on the currently-focused pane.

    The CLI's `draw clear` relies on a chart-API path that isn't always bound;
    `removeAllDrawingTools()` on the active widget works across versions.
    """
    js = (
        '(function(){'
        'const w=window._exposed_chartWidgetCollection?.activeChartWidget;'
        'const wv=typeof w==="object"&&w.value?w.value():w;'
        'if(!wv)return"no widget";'
        'try{wv.removeAllDrawingTools();return"cleared";}'
        'catch(e){return"error: "+e.message;}'
        '})()'
    )
    return tv_cli('ui', 'eval', '-e', js)


def draw_line(price, color, label, linestyle=0, linewidth=1):
    """Draw a horizontal line on the active pane via tv CLI."""
    overrides = {
        'linecolor': color,
        'linewidth': linewidth,
        'linestyle': linestyle,
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
    if v is None:
        return ''
    sign = '+' if v >= 0 else '−'
    return f'{sign}${abs(v)/1e9:.1f}B'


def draw_levels_from_snapshot(ticker, snap):
    """Draw PIN / WALL ↑ / WALL ↓ / PUT MAG / FLIP from a snapshot row."""
    drawn = []

    def maybe_draw(strike, gamma, color, kind, linestyle, linewidth):
        if strike is None:
            return
        gtxt = f' ({fmt_b(gamma)})' if gamma else ''
        label = f'{kind} ${int(float(strike))}{gtxt}'.strip()
        draw_line(float(strike), color, label, linestyle=linestyle, linewidth=linewidth)
        drawn.append((kind, strike, gamma))

    maybe_draw(snap.get('pin_strike'),       snap.get('pin_gamma'),       COLOR_PIN,     'PIN',     0, 2)
    maybe_draw(snap.get('wall_up_strike'),   snap.get('wall_up_gamma'),   COLOR_WALL,    'WALL ↑',  2, 1)
    maybe_draw(snap.get('wall_down_strike'), snap.get('wall_down_gamma'), COLOR_WALL,    'WALL ↓',  2, 1)
    maybe_draw(snap.get('put_mag_strike'),   snap.get('put_mag_gamma'),   COLOR_PUT_MAG, 'PUT MAG', 0, 2)

    # Flip has no gamma value; draw distinctly (dotted gray)
    if snap.get('flip_strike') is not None:
        flip = float(snap['flip_strike'])
        draw_line(flip, COLOR_FLIP, f'FLIP ${int(flip)}', linestyle=1, linewidth=1)
        drawn.append(('FLIP', flip, None))

    return drawn


def main():
    if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_KEY'):
        sys.exit('SUPABASE_URL or SUPABASE_SERVICE_KEY not set')

    # Layout: 3 panes side-by-side
    print('Setting layout to 3 horizontal panes…')
    layout_out = tv_cli('pane', 'layout', '3h')
    if layout_out is None:
        sys.exit('Failed to set 3h layout — is TradingView running with CDP?')

    # Brief pause so the layout settles before we start switching symbols
    _time.sleep(0.8)

    for pane_idx, ticker, tv_symbol in PANES:
        print(f'\n[Pane {pane_idx}] {ticker} ({tv_symbol})')

        snap = get_latest_snapshot(ticker)
        if snap is None:
            print(f'  ! No Supabase snapshot for {ticker}. Run refresh-multi-0dte.py first.', file=sys.stderr)
            continue

        tv_cli('pane', 'symbol', str(pane_idx), tv_symbol)
        _time.sleep(0.4)
        tv_cli('pane', 'focus', str(pane_idx))
        _time.sleep(0.3)

        clear_active_pane_drawings()
        drawn = draw_levels_from_snapshot(ticker, snap)

        if not drawn:
            print('  No levels in snapshot (all null).')
            continue

        for kind, s, g in drawn:
            gtxt = f' {fmt_b(g)}' if g else ''
            print(f'  ✓ {kind:8s} ${int(float(s)):>7d}{gtxt}')

    # Restore focus to pane 1 by convention
    tv_cli('pane', 'focus', '1')
    print('\nDone.')


if __name__ == '__main__':
    main()
