"""Universal notification signal engine.

Detects gamma state-change events by diffing consecutive snapshots of the same
ticker. Pure functions — no I/O. Caller (refresh script) pulls snapshots from
Supabase and passes the chronological list here.

Eight signal codes, asset-agnostic (changes measured as fraction of price):

  ENTRY ↑       Bullish pin migration with clean setup
  ENTRY ↓       Bearish pin migration with clean setup
  PIN REVERT    Pin returned to a prior strike → previous setup invalidated
  COMPRESSION ↑ Wall ↑ tightened toward price (cap closing)
  COMPRESSION ↓ Wall ↓ tightened toward price (floor closing)
  LOOSEN        Wall stepped out (≥ widening threshold)
  REGIME FLIP   Positive ↔ negative gamma transition
  NEW STRIKE    New pin strike appeared between price and prior pin

Each signal is a dict:
  { time, ticker, code, severity, dir, text, raw }
"""

# Thresholds (as fraction of price — asset-agnostic)
MIGRATION_PCT = 0.001    # ≥ 0.1% of price = meaningful pin move
WIDENING_PCT  = 0.004    # ≥ 0.4% of price = meaningful wall widening
TIGHTENING_PCT = 0.001   # ≥ 0.1% of price = meaningful wall tightening

SEVERITY = {
    'ENTRY ↑':       'high',
    'ENTRY ↓':       'high',
    'PIN REVERT':    'high',
    'COMPRESSION ↑': 'medium',
    'COMPRESSION ↓': 'medium',
    'LOOSEN':        'low',
    'REGIME FLIP':   'high',
    'NEW STRIKE':    'medium',
}


def _fmt_time(captured_at):
    """Format ISO timestamp to 'HH:MM ET'. captured_at is a string from Supabase."""
    if not captured_at:
        return ''
    # captured_at is ISO with timezone; convert to ET for display.
    from datetime import datetime, timezone, timedelta
    try:
        dt = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
    except ValueError:
        return captured_at[:16]
    # ET = UTC-4 during DST (May → EDT). Crude but accurate for cash hours May–Nov.
    et = dt.astimezone(timezone(timedelta(hours=-4)))
    return et.strftime('%H:%M ET')


def _fmt_price(v):
    """Format price compactly. Handles both stock-scale and index-scale."""
    if v is None:
        return '—'
    v = float(v)
    if abs(v) >= 1000:
        return f'${v:,.0f}'
    if abs(v) >= 100:
        return f'${v:.2f}'
    return f'${v:.2f}'


def _signal(captured_at, ticker, code, direction, text, **raw):
    return {
        'time':     _fmt_time(captured_at),
        'time_iso': captured_at,
        'ticker':   ticker,
        'code':     code,
        'severity': SEVERITY.get(code, 'low'),
        'dir':      direction,    # 'up' | 'down' | None
        'text':     text,
        'raw':      raw,
    }


def _diff(prev, cur):
    """Detect signals from one pair of consecutive snapshots."""
    out = []
    ticker = cur.get('ticker') or prev.get('ticker') or '?'
    price  = float(cur.get('tv_price') or cur.get('uw_ref_price') or 0)
    t      = cur.get('captured_at')
    if price <= 0:
        return out

    p_pin  = prev.get('pin_strike')
    c_pin  = cur.get('pin_strike')
    p_wu   = prev.get('wall_up_strike')
    c_wu   = cur.get('wall_up_strike')
    p_wd   = prev.get('wall_down_strike')
    c_wd   = cur.get('wall_down_strike')
    p_reg  = prev.get('regime')
    c_reg  = cur.get('regime')

    # ── Regime flip ─────────────────────────────────────────
    if p_reg and c_reg and p_reg != c_reg:
        out.append(_signal(t, ticker, 'REGIME FLIP', None,
            f'Regime flipped {p_reg} → {c_reg}.',
            prev=p_reg, cur=c_reg))

    # ── Pin migration ───────────────────────────────────────
    if c_pin is not None and p_pin is not None:
        delta = float(c_pin) - float(p_pin)
        rel = abs(delta) / price
        if rel >= MIGRATION_PCT:
            if delta > 0:
                # Pin moved up — check entry conditions
                wall_above = (c_wu is None) or (float(c_wu) > float(c_pin))
                if price < float(c_pin) and wall_above:
                    runway = _fmt_price(c_wu) if c_wu else 'open path'
                    out.append(_signal(t, ticker, 'ENTRY ↑', 'up',
                        f'Pin {_fmt_price(p_pin)} → {_fmt_price(c_pin)}. Wall ↑ {runway} runway. Long bias.',
                        prev_pin=p_pin, cur_pin=c_pin, wall_up=c_wu, price=price))
                # else: pin moved up but conditions failed → suppress (no noise)
            else:
                # Pin moved down — check entry conditions OR revert
                wall_below = (c_wd is None) or (float(c_wd) < float(c_pin))
                if price > float(c_pin) and wall_below:
                    runway = _fmt_price(c_wd) if c_wd else 'open path'
                    out.append(_signal(t, ticker, 'ENTRY ↓', 'down',
                        f'Pin {_fmt_price(p_pin)} → {_fmt_price(c_pin)}. Wall ↓ {runway} runway. Short bias.',
                        prev_pin=p_pin, cur_pin=c_pin, wall_down=c_wd, price=price))
                else:
                    out.append(_signal(t, ticker, 'PIN REVERT', None,
                        f'Pin reverted {_fmt_price(p_pin)} → {_fmt_price(c_pin)}.',
                        prev_pin=p_pin, cur_pin=c_pin, price=price))

    # ── Wall ↑ change ───────────────────────────────────────
    if c_wu is not None and p_wu is not None:
        delta = float(c_wu) - float(p_wu)
        rel_abs = abs(delta) / price
        # Tightening: wall moved DOWN toward price (since wall ↑ is above price)
        # Widening:   wall moved UP away from price
        if rel_abs >= TIGHTENING_PCT:
            if delta < 0:   # moved down → tightened
                out.append(_signal(t, ticker, 'COMPRESSION ↑', 'up',
                    f'Wall ↑ tightened {_fmt_price(p_wu)} → {_fmt_price(c_wu)}. Cap closing.',
                    prev_wall=p_wu, cur_wall=c_wu, price=price))
            elif rel_abs >= WIDENING_PCT:   # moved up enough → loosened
                out.append(_signal(t, ticker, 'LOOSEN', None,
                    f'Wall ↑ widened {_fmt_price(p_wu)} → {_fmt_price(c_wu)}. Magnet weakening.',
                    prev_wall=p_wu, cur_wall=c_wu, price=price))

    # ── Wall ↓ change ───────────────────────────────────────
    if c_wd is not None and p_wd is not None:
        delta = float(c_wd) - float(p_wd)
        rel_abs = abs(delta) / price
        if rel_abs >= TIGHTENING_PCT:
            if delta > 0:   # wall ↓ moved up → tightened (closer to price)
                out.append(_signal(t, ticker, 'COMPRESSION ↓', 'down',
                    f'Wall ↓ tightened {_fmt_price(p_wd)} → {_fmt_price(c_wd)}. Floor closing.',
                    prev_wall=p_wd, cur_wall=c_wd, price=price))
            elif rel_abs >= WIDENING_PCT:   # wall ↓ moved down → floor giving up
                out.append(_signal(t, ticker, 'LOOSEN', None,
                    f'Wall ↓ stepped out {_fmt_price(p_wd)} → {_fmt_price(c_wd)}. Floor giving up.',
                    prev_wall=p_wd, cur_wall=c_wd, price=price))

    return out


def detect_session_signals(snapshots_by_ticker):
    """Detect all signals across a session.

    snapshots_by_ticker: dict {ticker: [snapshot, snapshot, ...]} where each
    snapshot is a dict with keys captured_at, pin_strike, wall_up_strike, etc.
    Snapshots must be sorted chronologically (oldest first).

    Returns a single chronological list of signal dicts across all tickers.
    """
    all_signals = []
    for ticker, snaps in snapshots_by_ticker.items():
        if not snaps or len(snaps) < 2:
            continue
        # Make sure each snap carries its ticker for the diff fn
        for s in snaps:
            s.setdefault('ticker', ticker)
        for i in range(1, len(snaps)):
            all_signals.extend(_diff(snaps[i - 1], snaps[i]))
    # Interleave by time_iso (ISO ascending = chronological)
    all_signals.sort(key=lambda s: s.get('time_iso') or '')
    return all_signals
