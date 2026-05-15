"""The Strat — 3-candle setup classification and target derivation.

Pure functions. Caller pulls bars from TV (chart-data Phase 1), then passes the
3 most-recent CLOSED bars (oldest first) to `match_3_candle_setup`. No I/O.

Candle classification per Rob Smith's Strat:
  1   — inside bar: cur.high < prev.high AND cur.low > prev.low
  2u  — directional up: cur.high > prev.high AND cur.low >= prev.low
  2d  — directional down: cur.low < prev.low AND cur.high <= prev.high
  3   — outside / broadening: cur.high > prev.high AND cur.low < prev.low

Valid 3-candle setups and the mechanical target rule
(P1 = oldest, P2 = middle, P3 = trigger; P3 target = P1 high if P3 bullish,
P1 low if P3 bearish):

  | Setup                       | Pattern      | Direction | Target  |
  |-----------------------------|--------------|-----------|---------|
  | 2-1-2 Reversal Down         | 2u-1-2d      | bearish   | P1 high |
  | 2-1-2 Reversal Up           | 2d-1-2u      | bullish   | P1 low  |
  | 2-1-2 Continuation Up       | 2u-1-2u      | bullish   | P1 high |
  | 2-1-2 Continuation Down     | 2d-1-2d      | bearish   | P1 low  |
  | 3-1-2 Up                    | 3-1-2u       | bullish   | P1 high |
  | 3-1-2 Down                  | 3-1-2d       | bearish   | P1 low  |
  | 3-2-2 Continuation Up       | 3-2u-2u      | bullish   | P1 high |
  | 3-2-2 Continuation Down     | 3-2d-2d      | bearish   | P1 low  |

Any other 3-candle sequence returns None — only listed setups fire.
"""


def classify_bar(prev_bar, cur_bar):
    """Return the Strat type of `cur_bar` relative to `prev_bar`:
    '1' (inside), '2u', '2d', or '3' (outside). Both args are dicts with
    'high' and 'low' float keys."""
    ph, pl = prev_bar['high'], prev_bar['low']
    ch, cl = cur_bar['high'], cur_bar['low']
    broke_high = ch > ph
    broke_low = cl < pl
    if broke_high and broke_low:
        return '3'
    if broke_high:
        return '2u'
    if broke_low:
        return '2d'
    return '1'


# Each valid setup keyed by (P2 type, P3 type) given a non-None P1 type.
# The matcher iterates the table; first match wins.
_VALID_SETUPS = [
    # (P1 type, P2 type, P3 type, pattern label, direction, target side)
    ('2u', '1',  '2d', '2-1-2 Reversal',     'bearish', 'high'),
    ('2d', '1',  '2u', '2-1-2 Reversal',     'bullish', 'low'),
    ('2u', '1',  '2u', '2-1-2 Continuation', 'bullish', 'high'),
    ('2d', '1',  '2d', '2-1-2 Continuation', 'bearish', 'low'),
    ('3',  '1',  '2u', '3-1-2',              'bullish', 'high'),
    ('3',  '1',  '2d', '3-1-2',              'bearish', 'low'),
    ('3',  '2u', '2u', '3-2-2 Continuation', 'bullish', 'high'),
    ('3',  '2d', '2d', '3-2-2 Continuation', 'bearish', 'low'),
]


def match_3_candle_setup(bars):
    """Given exactly 4 OHLC bars (oldest first; first bar is the prior-of-P1
    used to classify P1), return a dict describing the Strat setup or None.

    Bars: list of 4 dicts with keys 'high', 'low' (and ideally 'open','close','time').
      bars[0] -> classification anchor for P1
      bars[1] -> P1 (oldest of the 3-bar window)
      bars[2] -> P2
      bars[3] -> P3 (most recent closed bar, the trigger)

    Returns: {
      'pattern':   '2-1-2 Reversal' | '2-1-2 Continuation' | '3-1-2' | '3-2-2 Continuation',
      'direction': 'bullish' | 'bearish',
      'p1_type':   '2u'|'2d'|'3',
      'p2_type':   '1'|'2u'|'2d',
      'p3_type':   '2u'|'2d',
      'target':    float,   # P1 high if bullish, P1 low if bearish
      'p1_high':   float,
      'p1_low':    float,
    }
    or None when the 3-bar sequence does not match a listed setup.
    """
    if not bars or len(bars) < 4:
        return None
    anchor, p1, p2, p3 = bars[-4], bars[-3], bars[-2], bars[-1]
    t1 = classify_bar(anchor, p1)
    t2 = classify_bar(p1, p2)
    t3 = classify_bar(p2, p3)
    for (vt1, vt2, vt3, pattern, direction, side) in _VALID_SETUPS:
        if t1 == vt1 and t2 == vt2 and t3 == vt3:
            target = p1['high'] if side == 'high' else p1['low']
            return {
                'pattern':   pattern,
                'direction': direction,
                'p1_type':   t1,
                'p2_type':   t2,
                'p3_type':   t3,
                'target':    float(target),
                'p1_high':   float(p1['high']),
                'p1_low':    float(p1['low']),
            }
    return None
