#!/usr/bin/env python3
"""
Refresh the unusual-flow screener page (`charts/rendered/screener.html`).

Pulls /api/screener/option-contracts twice — once for aggressive call buying,
once for aggressive put buying — applies the agreed-upon "institutional, this-
week DTE" filter set, normalizes each row, and rewrites the CONFIG block.

Usage:
    python3 scripts/refresh-screener.py
    python3 scripts/refresh-screener.py --min-premium 250000 --limit 50

Requires:
    UW_API_TOKEN
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'screener.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'screener.html')


# Default filter set — short DTE, institutional size, opening flow, aggressive
# directional buying. Tuned to surface real positioning, not retail.
DEFAULTS = {
    'max_dte':              3,
    'min_dte':              0,
    'is_otm':               'true',
    'min_premium':          100_000,
    'min_volume':           500,
    'min_volume_oi_ratio':  1.0,
    'vol_greater_oi':       'true',
    'min_ask_perc':         0.65,
    'max_multileg_volume_ratio': 0.1,
    'limit':                30,
}


def fetch_uw(endpoint, params, token):
    """GET with query params. Properly encodes issue_types[] as repeated keys."""
    qs_pairs = []
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            for item in v:
                qs_pairs.append((k, item))
        else:
            qs_pairs.append((k, v))
    url = f'https://api.unusualwhales.com{endpoint}?{urlencode(qs_pairs)}'
    req = Request(url, headers={
        'Authorization': f'Bearer {token}',
        'UW-CLIENT-API-ID': '100001',
    })
    try:
        with urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()[:400]
        sys.exit(f'UW API error {e.code} on {endpoint}: {body}')
    if isinstance(payload, list):
        return payload
    return payload.get('data', [])


# ─────────────────────────────────────────────────────────
# Option-symbol parsing
# ─────────────────────────────────────────────────────────
_OCC_RE = re.compile(r'^([A-Z\.\-]+)(\d{6})([CP])(\d{8})$')


def parse_option_symbol(sym):
    """OCC format: TICKER + YYMMDD + C/P + strike*1000 (8 digits).
    e.g. AAPL260515C00200000 → (AAPL, 2026-05-15, C, 200.0)
    Returns (ticker, expiry_iso, type, strike) or None.
    """
    m = _OCC_RE.match(sym or '')
    if not m:
        return None
    ticker, yymmdd, cp, strike_str = m.groups()
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    year = 2000 + yy
    expiry = f'{year:04d}-{mm:02d}-{dd:02d}'
    strike = int(strike_str) / 1000
    return ticker, expiry, cp, strike


def days_to(expiry_iso, today):
    try:
        exp = datetime.strptime(expiry_iso, '%Y-%m-%d').date()
        return (exp - today).days
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────
# Normalize each UW row → compact dict the HTML expects
# ─────────────────────────────────────────────────────────
def normalize_row(r, side, today):
    sym = r.get('option_symbol') or ''
    parsed = parse_option_symbol(sym)
    if not parsed:
        return None
    ticker, expiry, cp, strike = parsed
    if (side == 'calls' and cp != 'C') or (side == 'puts' and cp != 'P'):
        return None

    volume = int(r.get('volume') or 0)
    if volume <= 0:
        return None
    ask_vol = int(r.get('ask_side_volume') or 0)
    ask_perc = ask_vol / volume if volume else 0

    last_fill = r.get('last_fill') or ''
    if last_fill:
        try:
            ts = datetime.fromisoformat(last_fill.replace('Z', '+00:00')).astimezone()
            last_fill = ts.strftime('%H:%M:%S')
        except ValueError:
            pass

    # Earnings-within-N-days flag for risk-aware reading
    earnings_soon = None
    ner = r.get('next_earnings_date') or ''
    if ner:
        d = days_to(ner, today)
        if d is not None and 0 <= d <= 7:
            earnings_soon = f'{d}d' if d > 0 else 'TODAY'

    spot = float(r.get('stock_price') or 0)
    oi = int(r.get('open_interest') or 0)
    premium = float(r.get('premium') or 0)
    sweep = int(r.get('sweep_volume') or 0) > 0
    dte = days_to(expiry, today) or 0
    vol_oi = (volume / oi) if oi > 0 else float('inf')
    move_pct = ((strike - spot) / spot * 100) if spot > 0 else 0  # signed: +OTM calls, −OTM puts

    grade = grade_flow(
        premium=premium, vol_oi=vol_oi, ask_perc=ask_perc,
        sweep=sweep, dte=dte, move_pct=move_pct, cp=cp,
    )

    return {
        'ticker':   ticker,
        'type':     cp,
        'strike':   strike,
        'spot':     spot,
        'dte':      dte,
        'premium':  premium,
        'volume':   volume,
        'oi':       oi,
        'vol_oi':   vol_oi if vol_oi != float('inf') else 999.0,
        'ask_perc': ask_perc,
        'sweep':    sweep,
        'sector':   (r.get('sector') or '')[:24],
        'earnings_soon': earnings_soon,
        'last_fill': last_fill,
        'option_symbol': sym,
        'move_pct': move_pct,
        'grade':    grade,
    }


# ─────────────────────────────────────────────────────────
# Quality grading (mirror mega-scan approach: absolute thresholds
# gate quality; magnitude (move%) is the rank)
# ─────────────────────────────────────────────────────────
def grade_flow(*, premium, vol_oi, ask_perc, sweep, dte, move_pct, cp):
    """A / B / C / D / F based on conviction + sanity bounds.

    A — institutional size, fresh positioning, aggressive buying, urgency
    B — solid signal missing one A factor
    C — tradeable but mid-conviction
    D — meets minimum thresholds, low confidence
    F — outside sane bounds (move% too extreme, etc.)

    move_pct sweet spot for calls: +1.5% to +6% OTM (room to run, not lottery)
    move_pct sweet spot for puts:  −6% to −1.5% OTM (mirror)
    """
    abs_move = abs(move_pct)
    if abs_move > 12 or abs_move < 0.3:
        return 'F'   # too far OTM = lottery; too close = ATM noise

    in_sweet = 1.5 <= abs_move <= 6.0
    # A: heavy premium + very fresh + aggressive + urgency + sweet OTM band + short DTE
    if (premium >= 500_000 and vol_oi >= 5.0 and ask_perc >= 0.80
            and sweep and in_sweet and dte <= 2):
        return 'A'
    # B: solid premium + fresh + aggressive + sweet band (one factor can relax)
    if (premium >= 250_000 and vol_oi >= 3.0 and ask_perc >= 0.70 and in_sweet):
        return 'B'
    # C: meets minimum thresholds + acceptable move band
    if (premium >= 100_000 and vol_oi >= 1.5 and ask_perc >= 0.65
            and 1.0 <= abs_move <= 8.0):
        return 'C'
    # D: marginal — keep visible but flagged
    if premium >= 100_000 and 0.5 <= abs_move <= 10.0:
        return 'D'
    return 'F'


# ─────────────────────────────────────────────────────────
# CONFIG block builder
# ─────────────────────────────────────────────────────────
def build_config_js(filters, calls, puts):
    as_of = datetime.now(timezone.utc).isoformat()

    def js_row(r):
        # Compact JS object literal — keep order consistent for diff sanity
        return ('{ '
                f"ticker: {json.dumps(r['ticker'])}, "
                f"type: '{r['type']}', "
                f"strike: {r['strike']}, "
                f"spot: {r['spot']}, "
                f"dte: {r['dte']}, "
                f"premium: {int(round(r['premium']))}, "
                f"volume: {r['volume']}, "
                f"oi: {r['oi']}, "
                f"vol_oi: {r['vol_oi']:.2f}, "
                f"ask_perc: {r['ask_perc']:.4f}, "
                f"sweep: {'true' if r['sweep'] else 'false'}, "
                f"sector: {json.dumps(r['sector'])}, "
                f"earnings_soon: {json.dumps(r['earnings_soon'])}, "
                f"last_fill: {json.dumps(r['last_fill'])}, "
                f"move_pct: {r['move_pct']:.2f}, "
                f"grade: '{r['grade']}'"
                ' }')

    calls_block = '[\n    ' + ',\n    '.join(js_row(r) for r in calls) + '\n  ]' if calls else '[]'
    puts_block  = '[\n    ' + ',\n    '.join(js_row(r) for r in puts)  + '\n  ]' if puts  else '[]'

    return f"""const CONFIG = {{
  asOf: '{as_of}',
  filters: {{
    max_dte: {filters['max_dte']},
    min_premium: {filters['min_premium']},
    min_ask_perc: {filters['min_ask_perc']},
    min_volume: {filters['min_volume']}
  }},
  calls: {calls_block},
  puts: {puts_block},
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
    ap = argparse.ArgumentParser(description='Refresh the unusual-flow screener page.')
    ap.add_argument('--max-dte',     type=int,   default=DEFAULTS['max_dte'])
    ap.add_argument('--min-premium', type=int,   default=DEFAULTS['min_premium'])
    ap.add_argument('--min-volume',  type=int,   default=DEFAULTS['min_volume'])
    ap.add_argument('--min-ask-perc', type=float, default=DEFAULTS['min_ask_perc'])
    ap.add_argument('--min-vol-oi',  type=float, default=DEFAULTS['min_volume_oi_ratio'])
    ap.add_argument('--limit',       type=int,   default=DEFAULTS['limit'])
    args = ap.parse_args()

    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set')
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Template not found: {TEMPLATE_PATH}')

    base_params = {
        'max_dte':                    args.max_dte,
        'min_dte':                    DEFAULTS['min_dte'],
        'is_otm':                     DEFAULTS['is_otm'],
        'min_premium':                args.min_premium,
        'min_volume':                 args.min_volume,
        'min_volume_oi_ratio':        args.min_vol_oi,
        'vol_greater_oi':             DEFAULTS['vol_greater_oi'],
        'min_ask_perc':               args.min_ask_perc,
        'max_multileg_volume_ratio':  DEFAULTS['max_multileg_volume_ratio'],
        'limit':                      args.limit,
        'issue_types[]':              ['Common Stock', 'ADR'],
    }
    filters_for_template = {
        'max_dte': args.max_dte,
        'min_premium': args.min_premium,
        'min_ask_perc': args.min_ask_perc,
        'min_volume': args.min_volume,
    }

    today = datetime.now().date()

    # Sort key: grade tier first (A < B < C), then |move%| desc (bigger move wins within tier).
    # F's are dropped — they failed sanity bounds and shouldn't display.
    GRADE_RANK = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}
    def rank_key(r):
        return (GRADE_RANK.get(r['grade'], 9), -abs(r['move_pct']))

    print(f'[Screener] Pulling bullish calls (max_dte={args.max_dte}, prem≥${args.min_premium:,})…')
    raw_calls = fetch_uw('/api/screener/option-contracts',
                         {**base_params, 'type': 'Calls'}, token)
    calls = [n for n in (normalize_row(r, 'calls', today) for r in raw_calls) if n]
    calls = [c for c in calls if c['grade'] != 'F']
    calls.sort(key=rank_key)
    print(f'  {len(calls)} contracts kept  '
          f"({sum(1 for c in calls if c['grade']=='A')}A "
          f"{sum(1 for c in calls if c['grade']=='B')}B "
          f"{sum(1 for c in calls if c['grade']=='C')}C "
          f"{sum(1 for c in calls if c['grade']=='D')}D)")

    print(f'[Screener] Pulling bearish puts (max_dte={args.max_dte}, prem≥${args.min_premium:,})…')
    raw_puts = fetch_uw('/api/screener/option-contracts',
                        {**base_params, 'type': 'Puts'}, token)
    puts = [n for n in (normalize_row(r, 'puts', today) for r in raw_puts) if n]
    puts = [p for p in puts if p['grade'] != 'F']
    puts.sort(key=rank_key)
    print(f'  {len(puts)} contracts kept  '
          f"({sum(1 for c in puts if c['grade']=='A')}A "
          f"{sum(1 for c in puts if c['grade']=='B')}B "
          f"{sum(1 for c in puts if c['grade']=='C')}C "
          f"{sum(1 for c in puts if c['grade']=='D')}D)")

    config_js = build_config_js(filters_for_template, calls, puts)
    patch_html(config_js)
    print(f'\n✓ Rendered {RENDERED_PATH}')

    # Quick top-3 each side preview (sorted A→D by grade, then magnitude)
    for side, rows in (('Calls', calls), ('Puts', puts)):
        if not rows:
            continue
        print(f'\n  Top 3 {side}:')
        for r in rows[:3]:
            sign = '+' if r['move_pct'] >= 0 else ''
            print(f"    [{r['grade']}] {r['ticker']:6} {r['type']} ${r['strike']:>7}  "
                  f"spot ${r['spot']:>7.2f}  {sign}{r['move_pct']:>5.1f}%  "
                  f"prem ${r['premium']/1e6:.2f}M  vol/OI {r['vol_oi']:>4.1f}x  "
                  f"ask {r['ask_perc']*100:.0f}%  dte {r['dte']}d")

    if not os.environ.get('GAMMA_NO_OPEN'):
        subprocess.run(['open', RENDERED_PATH])


if __name__ == '__main__':
    main()
