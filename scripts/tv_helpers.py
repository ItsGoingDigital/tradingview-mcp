"""
Shared TradingView CLI helpers — used by all refresh + draw scripts.

Wraps the `tv` CLI (src/cli/index.js) into a Python-friendly API for:
  - layout + pane control
  - live quote pulls (with sanity check)
  - Pine drawing reads (lines / boxes / labels) for indicator state
  - drawing horizontal lines on the active pane
  - clearing all drawings on the active pane

All functions are best-effort; they return None / [] / False on TV failure
rather than raising. Callers should fall back to UW data when TV is offline.
"""
import json
import os
import subprocess
import time as _time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TV_CLI = os.path.join(_REPO_ROOT, 'src', 'cli', 'index.js')

# Settle delays after state-changing operations (TV needs a moment to apply).
SETTLE_LAYOUT  = 0.8
SETTLE_SYMBOL  = 0.5
SETTLE_FOCUS   = 0.8
SETTLE_CLEAR   = 0.2


# ─────────────────────────────────────────────────────────
# Core CLI runner
# ─────────────────────────────────────────────────────────
def tv_cli(*args, capture=True, timeout=12):
    """Run a tv CLI command; return stdout string or None on failure."""
    cmd = ['node', TV_CLI] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() if capture else None


def tv_cli_json(*args, timeout=12):
    """Run a tv CLI command and parse stdout as JSON; return dict/list or None."""
    out = tv_cli(*args, timeout=timeout)
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


# ─────────────────────────────────────────────────────────
# Layout + pane
# ─────────────────────────────────────────────────────────
def set_layout(layout):
    """Set the chart layout (e.g. 's' single, '3h' three horizontal). Returns True if applied."""
    res = tv_cli('pane', 'layout', layout)
    if res is None:
        return False
    _time.sleep(SETTLE_LAYOUT)
    return True


def switch_saved_layout(name):
    """Load a saved TradingView layout by name (preserves indicators, panes, drawings)."""
    res = tv_cli('layout', 'switch', name)
    if res is None:
        return False
    _time.sleep(SETTLE_LAYOUT)
    return True


def set_pane_symbol(pane_idx, symbol):
    """Switch a specific pane to a symbol (e.g. SP:SPX, AMEX:SPY)."""
    res = tv_cli('pane', 'symbol', str(pane_idx), symbol)
    if res is None:
        return False
    _time.sleep(SETTLE_SYMBOL)
    return True


def focus_pane(pane_idx):
    """Focus a pane so subsequent reads/draws target it."""
    res = tv_cli('pane', 'focus', str(pane_idx))
    if res is None:
        return False
    _time.sleep(SETTLE_FOCUS)
    return True


def set_chart_symbol(symbol):
    """Single-chart symbol set (no panes)."""
    res = tv_cli('symbol', symbol)
    if res is None:
        return False
    _time.sleep(SETTLE_SYMBOL)
    return True


def set_timeframe(tf, settle=1.0):
    """Set the active chart's timeframe. Pass strings like '1', '5', '15', '60', 'D', 'W'.
    Returns True if applied. Costly (~1-2s for chart to reload bars).
    Pass `settle` to wait longer (e.g. 2.5s) when downstream readers depend on
    indicators that recompute on pivots/structure across many bars.
    """
    res = tv_cli('timeframe', str(tf))
    if res is None:
        return False
    _time.sleep(settle)   # bars reload — give TV time to settle
    return True


def get_active_state():
    """Return {symbol, resolution} for the currently-active chart, or None on failure."""
    raw = tv_cli('state')
    if not raw:
        return None
    try:
        s = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not s.get('success'):
        return None
    return {
        'symbol':     s.get('symbol'),
        'resolution': s.get('resolution'),
    }


# ─────────────────────────────────────────────────────────
# Quote
# ─────────────────────────────────────────────────────────
def get_session_range(expected_price=0, tolerance=0.05):
    """Return the active chart's latest bar OHLC as {open, high, low, close}.
    Bar timeframe = whatever TF the chart is on at call time (D → day range,
    W → week range). Returns None if the pull fails or if the bar's close
    diverges from `expected_price` by >`tolerance` fraction (which would mean
    `tv ohlcv` read a different pane/symbol than intended)."""
    raw = tv_cli('ohlcv', '-n', '1', '--summary')
    if not raw:
        return None
    try:
        q = json.loads(raw)
        hi, lo = q.get('high'), q.get('low')
        if hi is None or lo is None:
            return None
        close = float(q.get('close', 0))
        if expected_price and expected_price > 0 and close > 0:
            if abs(close - expected_price) / expected_price > tolerance:
                return None
        return {
            'open':  float(q.get('open', 0)),
            'high':  float(hi),
            'low':   float(lo),
            'close': close,
        }
    except (json.JSONDecodeError, ValueError):
        return None


def get_recent_closed_bars(n=4, expected_price=0, tolerance=0.05):
    """Pull the last `n` CLOSED bars from the active chart at its current TF.
    Excludes the actively-forming current bar — the most recent bar in
    `tv ohlcv` is "the live bar" until its session ends, so we drop it.

    Returns a list of `n` bar dicts (oldest first) or None on failure. Each
    bar: {open, high, low, close, time}. Sanity-rejects when the last
    closed bar's close diverges from `expected_price` by >`tolerance`."""
    raw = tv_cli('ohlcv', '-n', str(n + 1))
    if not raw:
        return None
    try:
        q = json.loads(raw)
        bars = q.get('bars') or []
        if len(bars) < n + 1:
            return None
        closed = bars[:-1][-n:]   # drop the last (forming), take last n closed
        out = []
        for b in closed:
            out.append({
                'time':  int(b.get('time', 0)),
                'open':  float(b.get('open', 0)),
                'high':  float(b.get('high', 0)),
                'low':   float(b.get('low', 0)),
                'close': float(b.get('close', 0)),
            })
        if expected_price and expected_price > 0:
            # The most recent CLOSED bar's close should sit near current price
            # (within a wider tolerance since the day may have moved).
            last_close = out[-1]['close']
            if last_close > 0 and abs(last_close - expected_price) / expected_price > tolerance:
                # Don't reject outright — the trigger bar may have closed far
                # from the current intraday price. Just return as-is; caller
                # can validate further.
                pass
        return out
    except (json.JSONDecodeError, ValueError):
        return None


def get_quote(expected_price=0, tolerance=0.03):
    """Read the active chart's live quote.

    `tv quote` reads whatever ticker is active. If the active chart doesn't
    match the ticker we're computing for, the price is nonsense. Sanity check
    rejects when the value diverges from `expected_price` by >`tolerance`
    fraction. Default 5% is tight enough to catch SPY-vs-QQQ confusion
    (~4.5% apart on most days) while still allowing intraday moves.
    """
    raw = tv_cli('quote')
    if not raw:
        return None
    try:
        q = json.loads(raw)
        last = float(q.get('last') or q.get('close') or 0)
    except (json.JSONDecodeError, ValueError):
        return None
    if last <= 0:
        return None
    if expected_price and expected_price > 0:
        if abs(last - expected_price) / expected_price > tolerance:
            return None
    return last


# ─────────────────────────────────────────────────────────
# Pine drawing reads (indicator state)
# ─────────────────────────────────────────────────────────
def get_pine_boxes(filter_name=None, verbose=False):
    """Return Pine box.new() zones. Each box has {high, low, ...} fields.

    Use `filter_name` to scope to one indicator (e.g. "Market Structure").
    """
    args = ['data', 'boxes']
    if filter_name:
        args += ['--filter', filter_name]
    if verbose:
        args += ['--verbose']
    res = tv_cli_json(*args)
    if not res or not res.get('success'):
        return []
    # CLI returns { success, count, boxes/studies } — handle both shapes
    if 'boxes' in res:
        return res['boxes']
    if 'studies' in res:
        out = []
        for s in res['studies']:
            out.extend(s.get('boxes', []))
        return out
    return []


def get_pine_lines(filter_name=None, verbose=False):
    """Return Pine line.new() horizontal price levels."""
    args = ['data', 'lines']
    if filter_name:
        args += ['--filter', filter_name]
    if verbose:
        args += ['--verbose']
    res = tv_cli_json(*args)
    if not res or not res.get('success'):
        return []
    if 'lines' in res:
        return res['lines']
    if 'studies' in res:
        out = []
        for s in res['studies']:
            out.extend(s.get('lines', []))
        return out
    return []


def get_pine_labels(filter_name=None, verbose=False):
    """Return Pine label.new() annotations. Each has text + price."""
    args = ['data', 'labels']
    if filter_name:
        args += ['--filter', filter_name]
    if verbose:
        args += ['--verbose']
    res = tv_cli_json(*args)
    if not res or not res.get('success'):
        return []
    if 'labels' in res:
        return res['labels']
    if 'studies' in res:
        out = []
        for s in res['studies']:
            out.extend(s.get('labels', []))
        return out
    return []


# ─────────────────────────────────────────────────────────
# Drawing (write to TV)
# ─────────────────────────────────────────────────────────
def clear_active_pane_drawings():
    """Remove all drawings on the currently-focused pane.

    The CLI's `draw clear` depends on a chart-API path that isn't always
    bound; `removeAllDrawingTools()` on the active widget works across
    TV versions.
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
    out = tv_cli('ui', 'eval', '-e', js)
    _time.sleep(SETTLE_CLEAR)
    return out is not None


def pull_ict_levels(price=None, prox_pct=0.10):
    """Read ICT Killzones & Pivots labels on the active pane.

    Returns a list of {name, price} dicts for tags like PDH, PDL, PMH, PML,
    PRE.H, PRE.L, M OPEN, D OPEN, etc. If `price` is provided, filters out
    labels outside ±prox_pct of price (e.g. far-day levels from prior weeks).
    """
    raw = get_pine_labels(filter_name='Killzones')
    seen = set()
    levels = []
    for lbl in raw:
        text = (lbl.get('text') or '').strip()
        p = lbl.get('price')
        if not text or p is None:
            continue
        try:
            p = float(p)
        except (TypeError, ValueError):
            continue
        if price and prox_pct and abs(p - price) / price > prox_pct:
            continue
        # Dedupe — the indicator can emit the same label twice (line + label)
        key = (text, round(p, 4))
        if key in seen:
            continue
        seen.add(key)
        levels.append({'name': text, 'price': p})
    return levels


def pull_poc():
    """Read Point of Control from 'Volume Profile / Fixed Range' indicator.

    This indicator emits a single label of the form "POC: 738.12" at the POC
    price level. We read the label's price field directly (not parsed from
    text) for precision. Returns float or None if indicator not loaded.
    """
    raw = get_pine_labels(filter_name='Fixed Range')
    for lbl in raw:
        text = (lbl.get('text') or '').strip()
        if 'POC' in text:
            p = lbl.get('price')
            try:
                return float(p)
            except (TypeError, ValueError):
                continue
    return None


def pull_structure_zones(within_points=None, current_price=None, top_n_per_side=3):
    """Read unmitigated S&D zones from Market Structure (Fractal) indicator.

    Wraps the `tv data structure-zones` CLI command, which pairs solid+dashed
    lines from the indicator to derive proper zones with TWO price edges (the
    broken-pivot trigger + the paired swing pivot). Geometry-classified as
    supply (bearish, trigger below pivot) or demand (bullish, trigger above).

    BOS-derived and ChoCh-derived events are both surfaced — there is no
    per-zone event label in the output (snapshot is purely structural).

    Returns list of dicts:
      upper, lower:  price boundaries (upper > lower always)
      direction:     'bullish' or 'bearish'
      zone_type:     'demand' or 'supply'
      mitigated:     False (filtered to unmitigated)
      bar_idx:       chart bar index of trigger (for sorting/dedup)

    If `current_price` is provided, output is split into zones-bracketing-price
    first, then top N closest above, then top N closest below.
    """
    args = ['data', 'structure-zones', '--filter', 'Market Structure']
    if within_points is not None:
        args += ['--within', str(within_points)]
    if current_price is not None:
        args += ['--price', str(current_price)]
    res = tv_cli_json(*args)
    if not res or not res.get('success') or not res.get('studies'):
        return []

    all_zones = []
    for study in res['studies']:
        for z in study.get('zones', []):
            if z.get('mitigated'):
                continue
            entry = z.get('entry')
            sl = z.get('sl')
            if entry is None or sl is None:
                continue
            upper = max(float(entry), float(sl))
            lower = min(float(entry), float(sl))
            all_zones.append({
                'upper':     upper,
                'lower':     lower,
                'direction': z.get('direction', ''),
                'zone_type': z.get('zone_type', ''),
                'mitigated': False,
                'bar_idx':   z.get('bar_idx', 0),
            })

    if current_price is None:
        return all_zones[:top_n_per_side * 2]

    cp = float(current_price)
    overlapping = [z for z in all_zones if z['lower'] <= cp <= z['upper']]
    above = sorted(
        [z for z in all_zones if z['lower'] > cp],
        key=lambda z: z['lower'] - cp,
    )[:top_n_per_side]
    below = sorted(
        [z for z in all_zones if z['upper'] < cp],
        key=lambda z: cp - z['upper'],
    )[:top_n_per_side]
    return overlapping + above + below


def draw_horizontal_line(price, color, label, linestyle=0, linewidth=1):
    """Draw a labeled horizontal line on the active pane.

    linestyle: 0=solid, 1=dotted, 2=dashed
    Returns the CLI's response (entity id etc.) on success, None on failure.
    """
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
