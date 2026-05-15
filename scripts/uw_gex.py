"""
Compute VOLUME-weighted gamma exposure per strike from /greeks + /option-contracts.

Why volume and not OI:
- Open interest updates after settlement (~end of trading day). It's effectively
  yesterday's positioning carried forward. OI-weighted GEX does NOT change
  intraday — it's a daily snapshot.
- Volume (`/option-contracts`'s `volume` field) accumulates intraday with every
  trade. It reflects today's flow being built right now. Volume-weighted GEX
  moves second-by-second.

Field naming caveat: we still write into `call_gamma_oi` / `put_gamma_oi` keys
to keep the downstream level math + Supabase schema unchanged. The fields hold
volume-weighted gex despite the name — adjust comments not column names.

Sign convention (matches UW's spot-exposures so existing level logic still works):
  call_gex_at_strike =  call_gamma × call_VOLUME × 100   (positive)
  put_gex_at_strike  = −put_gamma × put_VOLUME × 100     (negative)
  net_gex_at_strike  =  call_gex + put_gex

Note on remaining staleness: UW's `call_gamma` / `put_gamma` per share values
themselves are computed daily (no `time` field on /greeks). They reflect EOD
spot. The intraday signal comes from volume, not from the gamma curve
recomputing as spot moves. If gamma per share matters at high precision,
that's only available via /spot-exposures/strike (full data on paid tier).
"""
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def _fetch(endpoint, token, timeout=20):
    req = Request(
        f'https://api.unusualwhales.com{endpoint}',
        headers={
            'Authorization': f'Bearer {token}',
            'UW-CLIENT-API-ID': '100001',
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()[:300]
        raise RuntimeError(f'UW API error {e.code} on {endpoint}: {body}')


def pull_spot_gex(ticker, token, window_below=500, window_above=500):
    """Pull intraday-fresh GEX from /spot-exposures/strike with proper params.

    UW's `/spot-exposures/strike` is the authoritative GEX endpoint — values
    are scaled in dollars (spot² adjusted), have a real intraday `time` field
    that updates throughout the session, and the response includes both OI-
    and volume-weighted gex per strike + ask/bid side breakdowns.

    The endpoint silently caps to ~50 rows when called without `limit` and
    returns deep-OTM strikes by default. With `limit=500` plus `min_strike` /
    `max_strike` centered on current price, we get ~80-160 near-price strikes
    in one call — exactly what the heatmap needs.

    Strategy:
      1. Tiny `limit=1` probe to learn current spot price
      2. Full pull with min/max_strike = price ± window

    Returns dict matching the compute_live_gex shape (same field names) so
    callers can swap implementations cleanly:
      {
        'parsed': [ {strike, call_gamma_oi, put_gamma_oi, call_gamma_vol,
                     put_gamma_vol, call_delta_oi, put_delta_oi}, ... ],
        'price':       float (UW spot reference at fetch time),
        'time':        ISO timestamp from UW (intraday),
        'expiries':    [],   # this endpoint aggregates all expiries; field
                              # kept for compatibility with compute_live_gex
        'oldest_time': str,  # alias of `time` for downstream code
      }

    Note: UW's call_gamma_oi is positive, put_gamma_oi is negative by their
    convention. Field semantics match exactly what the rest of the pipeline
    expects (no sign or scale conversion needed).
    """
    # Step 1: cheap price probe
    probe = _fetch(f'/api/stock/{ticker}/spot-exposures/strike?limit=1', token)
    probe_rows = probe.get('data', [])
    if not probe_rows:
        return {'parsed': [], 'price': 0, 'time': None,
                'expiries': [], 'oldest_time': None}
    price = float(probe_rows[0].get('price') or 0)
    if price <= 0:
        return {'parsed': [], 'price': 0, 'time': None,
                'expiries': [], 'oldest_time': None}

    # Step 2: filtered full pull, centered on price
    lo = max(0, price - window_below)
    hi = price + window_above
    endpoint = (
        f'/api/stock/{ticker}/spot-exposures/strike'
        f'?limit=500&min_strike={lo:.0f}&max_strike={hi:.0f}'
    )
    payload = _fetch(endpoint, token)
    rows = payload.get('data', [])
    if not rows:
        return {'parsed': [], 'price': price, 'time': None,
                'expiries': [], 'oldest_time': None}

    # Normalize to the shape downstream code expects. Field names match the
    # raw UW fields so no conversion is needed (call_gamma_oi etc.).
    parsed = []
    for r in rows:
        try:
            s = float(r['strike'])
        except (KeyError, ValueError):
            continue
        parsed.append({
            'strike':         s,
            'call_gamma_oi':  float(r.get('call_gamma_oi')  or 0),
            'put_gamma_oi':   float(r.get('put_gamma_oi')   or 0),
            'call_gamma_vol': float(r.get('call_gamma_vol') or 0),
            'put_gamma_vol':  float(r.get('put_gamma_vol')  or 0),
            'call_delta_oi':  float(r.get('call_delta_oi')  or 0),
            'put_delta_oi':   float(r.get('put_delta_oi')   or 0),
        })
    parsed.sort(key=lambda x: x['strike'])

    timestamp = rows[0].get('time')
    return {
        'parsed':      parsed,
        'price':       price,
        'time':        timestamp,
        'expiries':    [],
        'oldest_time': timestamp,
    }


def list_expiries(ticker, token, max_dte=7, min_oi=1000):
    """Return near-term expiries within max_dte days, sorted ascending.

    `min_oi` filters out illiquid expiries (sparse OI = unreliable gex).
    Caller can also override by passing max_dte=0 for just today.
    """
    data = _fetch(f'/api/stock/{ticker}/expiry-breakdown', token)
    rows = data.get('data', [])
    today = datetime.now().date()
    keep = []
    for r in rows:
        exp = r.get('expires')
        if not exp:
            continue
        try:
            exp_d = datetime.strptime(exp, '%Y-%m-%d').date()
        except ValueError:
            continue
        dte = (exp_d - today).days
        if dte < 0:
            continue
        if dte > max_dte:
            continue
        if (r.get('open_interest') or 0) < min_oi:
            continue
        keep.append((exp, dte, r.get('open_interest', 0), r.get('volume', 0)))
    # If max_dte was tight and nothing landed, fall back to the nearest expiry
    if not keep and rows:
        for r in rows:
            try:
                exp_d = datetime.strptime(r['expires'], '%Y-%m-%d').date()
            except (ValueError, KeyError):
                continue
            if (exp_d - today).days >= 0:
                keep = [(r['expires'], (exp_d - today).days,
                         r.get('open_interest', 0), r.get('volume', 0))]
                break
    keep.sort(key=lambda x: x[1])
    return keep


def compute_live_gex(ticker, token, max_dte=7, min_oi=1000):
    """Return a dict with live VOLUME-weighted GEX per strike + metadata.

    Aggregates gamma × today's volume across the near-term expiry window.
    Strikes with zero call+put volume today contribute nothing — they
    naturally drop out of the heatmap. As today's volume accumulates,
    the gex shape shifts in real time.

    Field-name caveat: the result uses `call_gamma_oi` / `put_gamma_oi` keys
    for downstream compatibility, but the values are volume-weighted.

    Result shape:
      {
        'parsed':   [ {strike, call_gamma_oi, put_gamma_oi,
                       call_delta_oi, put_delta_oi,
                       call_gamma_vol, put_gamma_vol}, ... ],
        'expiries': [ {exp, dte, oi, vol}, ... ],
        'oldest_time': latest observation timestamp string from /option-contracts
      }
    """
    expiries = list_expiries(ticker, token, max_dte=max_dte, min_oi=min_oi)
    if not expiries:
        return {'parsed': [], 'expiries': [], 'oldest_time': None}

    # Aggregator: strike → {call_gex, put_gex, call_delta_oi, put_delta_oi, ...}
    agg = {}
    latest_time = None

    expiry_meta = []
    for exp, dte, oi, vol in expiries:
        greeks_payload = _fetch(
            f'/api/stock/{ticker}/greeks?expiry={exp}', token,
        )
        greeks_rows = greeks_payload.get('data', [])
        contracts_payload = _fetch(
            f'/api/stock/{ticker}/option-contracts?expiry={exp}', token,
        )
        contracts_rows = contracts_payload.get('data', [])

        # Build symbol → (open_interest, volume, last_fill) lookup
        info_by_sym = {}
        for c in contracts_rows:
            sym = c.get('option_symbol')
            if not sym:
                continue
            info_by_sym[sym] = {
                'oi':  int(c.get('open_interest') or 0),
                'vol': int(c.get('volume') or 0),
                'last_fill': c.get('last_fill') or '',
            }

        rows_used = 0
        for g in greeks_rows:
            try:
                strike = float(g['strike'])
            except (KeyError, ValueError):
                continue
            cg = float(g.get('call_gamma') or 0)
            pg = float(g.get('put_gamma') or 0)
            cd = float(g.get('call_delta') or 0)
            pd = float(g.get('put_delta') or 0)
            csym = g.get('call_option_symbol')
            psym = g.get('put_option_symbol')
            cinfo = info_by_sym.get(csym, {})
            pinfo = info_by_sym.get(psym, {})
            cvi = cinfo.get('vol', 0)      # today's call volume at this strike
            pvi = pinfo.get('vol', 0)      # today's put volume at this strike

            # Skip strike if no volume today on either side — nothing to weight
            if cvi == 0 and pvi == 0:
                continue
            rows_used += 1

            bucket = agg.setdefault(strike, {
                'strike':         strike,
                'call_gamma_oi':  0.0,   # holds VOLUME-weighted gex (legacy field name)
                'put_gamma_oi':   0.0,
                'call_gamma_vol': 0.0,
                'put_gamma_vol':  0.0,
                'call_delta_oi':  0.0,
                'put_delta_oi':   0.0,
            })
            # PRIMARY: volume-weighted GEX (intraday-fresh)
            bucket['call_gamma_oi']  += cg * cvi * 100               # positive
            bucket['put_gamma_oi']   += -1 * pg * pvi * 100          # negative
            # SECONDARY: stash same numbers in _vol fields too for clarity
            bucket['call_gamma_vol'] += cg * cvi * 100
            bucket['put_gamma_vol']  += -1 * pg * pvi * 100
            # Delta: also volume-weighted
            bucket['call_delta_oi']  += cd * cvi * 100
            bucket['put_delta_oi']   += pd * pvi * 100

            # Track latest fill for "freshness" reporting
            for lf in (cinfo.get('last_fill'), pinfo.get('last_fill')):
                if lf and (latest_time is None or lf > latest_time):
                    latest_time = lf

        expiry_meta.append({
            'exp': exp, 'dte': dte, 'oi': oi, 'vol': vol,
            'strikes_used': rows_used,
        })

    parsed = sorted(agg.values(), key=lambda x: x['strike'])
    return {
        'parsed':   parsed,
        'expiries': expiry_meta,
        'oldest_time': latest_time,
    }
