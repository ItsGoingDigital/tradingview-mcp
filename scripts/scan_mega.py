"""Mega-cap weekly gamma scanner.

Pulls EOW GEX for the QQQ top-weight universe, scores each ticker on:
  - Cluster detection (group adjacent dominant strikes into a single magnet)
  - Mode: pin (positive gamma → retracement-to-magnet) vs breakout (neg gamma → expansion)
  - Expected move % to target (the ranking metric)
  - Grade A/B/C/D/F via dominance + path clarity + tightness

Filters to grade ≥ C, sorts by absolute expected move %, renders to HTML.

Three phases, no analysis vocabulary leakage between them:
  Phase 1 — COLLECT  (UW pulls, no math)
  Phase 2 — SCORE    (pure functions, no I/O)
  Phase 3 — OUTPUT   (rank + render + persist)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gamma_scoring import score_ticker as _shared_score_ticker

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'mega-scan.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'mega-scan.html')

# Universe — QQQ top-10 weights (GOOG + GOOGL counted separately per user spec)
UNIVERSE = [
    {'ticker': 'NVDA',  'name': 'NVIDIA'},
    {'ticker': 'AAPL',  'name': 'Apple'},
    {'ticker': 'MSFT',  'name': 'Microsoft'},
    {'ticker': 'AMZN',  'name': 'Amazon'},
    {'ticker': 'MU',    'name': 'Micron Technology'},
    {'ticker': 'GOOGL', 'name': 'Alphabet (A)'},
    {'ticker': 'TSLA',  'name': 'Tesla'},
    {'ticker': 'GOOG',  'name': 'Alphabet (C)'},
    {'ticker': 'AMD',   'name': 'Advanced Micro Devices'},
    {'ticker': 'AVGO',  'name': 'Broadcom'},
]


# ─────────────────────────────────────────────────────────
# Phase 1 — COLLECT  (Unusual Whales API)
# ─────────────────────────────────────────────────────────

def fetch_uw(endpoint, token):
    """Thin wrapper around UW's REST API. Returns parsed JSON dict."""
    url = f'https://api.unusualwhales.com{endpoint}'
    req = Request(url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()[:300]
        print(f'  ! UW {endpoint} → {e.code}: {body}', file=sys.stderr)
        return {}


def pull_eow(ticker, expiry, token):
    """OI-weighted per-strike gamma for a specific expiry (this Friday by default)."""
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
        by_strike[s] = cg * coi * 100 + (-1 * pg * poi * 100)
    return by_strike


def fetch_price(ticker, token):
    """/spot-exposures/strike rows carry a `price` field — works for stocks."""
    data = fetch_uw(f'/api/stock/{ticker}/spot-exposures/strike', token)
    rows = data.get('data', [])
    if not rows:
        return 0
    return float(rows[0].get('price') or 0)


def next_friday(from_date=None):
    d = from_date or datetime.now().date()
    days_ahead = (4 - d.weekday()) % 7
    return (d + timedelta(days=days_ahead)).strftime('%Y-%m-%d')


# ─────────────────────────────────────────────────────────
# Phase 2 — SCORE  (delegates to gamma_scoring)
# ─────────────────────────────────────────────────────────
score_ticker = _shared_score_ticker




# ─────────────────────────────────────────────────────────
# Phase 3 — RANK + RENDER
# ─────────────────────────────────────────────────────────

GRADE_ORDER = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}
GRADE_KEEP  = {'A', 'B', 'C'}   # filter gate


def rank_setups(scored):
    """Filter to grade ≥ C, sort by |expected move %| desc."""
    qualified = [s for s in scored if s.get('grade') in GRADE_KEEP and s.get('gap_pct') is not None]
    qualified.sort(key=lambda s: -abs(s['gap_pct']))
    return qualified


def fmt_pct(v): return f'{v:+.2f}%'
def fmt_money(v):
    if abs(v) >= 1_000_000_000: return f'${v/1_000_000_000:.1f}B'
    if abs(v) >= 1_000_000:     return f'${v/1_000_000:.1f}M'
    if abs(v) >= 1_000:         return f'${v/1_000:.1f}k'
    return f'${v:.0f}'


def build_config_js(qualified, skipped, expiry):
    """Render the scan results as a JS CONFIG block consumed by mega-scan.html."""
    def row_js(r):
        is_pin = r['mode'] == 'PIN'
        cluster_info = ''
        if is_pin:
            c = r['cluster']
            cluster_info = (
                f"{{ size: {c['size']}, width: {c['width']:.2f}, "
                f"center: {c['center']:.2f}, dominance: {c['dominance']:.2f}, "
                f"strikes: {json.dumps(c['strikes'])}, "
                f"tight: {'true' if r.get('tight') else 'false'}, "
                f"wide: {'true' if r.get('wide') else 'false'} }}"
            )
        else:
            cluster_info = (
                f"{{ launchPad: {r['launch_pad']:.2f}, "
                f"dominance: {r['dominance']:.2f} }}"
            )
        return (
            f"  {{ ticker: '{r['ticker']}', name: {json.dumps(r['name'])}, "
            f"price: {r['price']:.2f}, regime: '{r['regime']}', mode: '{r['mode']}', "
            f"direction: '{r['direction']}', target: {r['target']:.2f}, "
            f"gapPct: {r['gap_pct']:.2f}, pathClarity: {r['path_clarity']:.3f}, "
            f"suggestedStrike: {r['suggested_strike']:.2f}, "
            f"grade: '{r['grade']}', detail: {cluster_info} }}"
        )

    skip_js = ', '.join(
        f"{{ ticker: '{s['ticker']}', reason: '{s.get('skip_reason', 'grade ' + s.get('grade', 'F'))}' }}"
        for s in skipped
    )

    rows_block = ',\n'.join(row_js(r) for r in qualified) or ''
    as_of = datetime.now(timezone.utc).isoformat()

    return f"""const CONFIG = {{
  asOf: '{as_of}',
  expiry: '{expiry}',
  expiryLabel: 'EOW {datetime.strptime(expiry, '%Y-%m-%d').strftime('%-m/%-d')}',
  setups: [
{rows_block}
  ],
  skipped: [{skip_js}],
}};"""


def patch_html(config_js):
    with open(TEMPLATE_PATH, 'r') as f:
        html = f.read()
    pattern = r'const CONFIG = \{[\s\S]*?\n\};'
    if not re.search(pattern, html):
        sys.exit('Could not locate CONFIG block in mega-scan template')
    new_html = re.sub(pattern, lambda _: config_js, html, count=1)
    os.makedirs(os.path.dirname(RENDERED_PATH), exist_ok=True)
    with open(RENDERED_PATH, 'w') as f:
        f.write(new_html)


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Mega-cap weekly gamma scanner.')
    ap.add_argument('--expiry', default=None, help='ISO expiry (default: next Friday)')
    args = ap.parse_args()

    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set')
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Template not found: {TEMPLATE_PATH}')

    expiry = args.expiry or next_friday()
    print(f'Mega-cap gamma scanner · expiry {expiry}')
    print('━' * 60)

    # Phase 1 — collect
    print('PHASE 1 — COLLECT (UW pulls)')
    raw = []
    for entry in UNIVERSE:
        ticker, name = entry['ticker'], entry['name']
        print(f'  [{ticker}]…', end='', flush=True)
        strikes = pull_eow(ticker, expiry, token)
        if not strikes:
            print(' no EOW data')
            raw.append({'ticker': ticker, 'name': name, 'strikes': None, 'price': 0})
            continue
        price = fetch_price(ticker, token)
        if price <= 0:
            print(' no price')
            raw.append({'ticker': ticker, 'name': name, 'strikes': None, 'price': 0})
            continue
        print(f' ${price:.2f} · {len(strikes)} strikes')
        raw.append({'ticker': ticker, 'name': name, 'strikes': strikes, 'price': price})

    # Phase 2 — score
    print('\nPHASE 2 — SCORE (mode, target, grade)')
    scored = []
    for r in raw:
        if not r['strikes'] or r['price'] <= 0:
            scored.append({'ticker': r['ticker'], 'name': r['name'], 'price': r['price'],
                           'grade': 'F', 'skip_reason': 'no data'})
            continue
        result = score_ticker(r['ticker'], r['name'], r['strikes'], r['price'])
        scored.append(result)
        if result['grade'] in GRADE_KEEP:
            arrow = '↑' if result['direction'] == 'LONG' else '↓'
            print(f"  {result['ticker']:5s} {result['mode']:8s} {arrow} "
                  f"{fmt_pct(result['gap_pct']):>8s}  grade {result['grade']}  "
                  f"target ${result['target']:.2f}")
        else:
            reason = result.get('skip_reason', f"grade {result['grade']}")
            print(f"  {result['ticker']:5s} skip — {reason}")

    # Phase 3 — rank + render
    print('\nPHASE 3 — RANK + RENDER')
    qualified = rank_setups(scored)
    skipped = [s for s in scored if s.get('grade') not in GRADE_KEEP]
    config_js = build_config_js(qualified, skipped, expiry)
    patch_html(config_js)
    print(f'  {len(qualified)} qualified · {len(skipped)} skipped')
    print(f'\n✓ Rendered {RENDERED_PATH}')
    if qualified:
        print(f'\n  Top pick: {qualified[0]["ticker"]} {qualified[0]["mode"]} '
              f"{qualified[0]['direction']} {fmt_pct(qualified[0]['gap_pct'])} "
              f"→ ${qualified[0]['target']:.2f} (grade {qualified[0]['grade']})")


if __name__ == '__main__':
    main()
