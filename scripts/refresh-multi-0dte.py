#!/usr/bin/env python3
"""
Refresh the multi-ticker 0DTE gamma heatmap (SPX + SPY + QQQ).

Pulls UW strike-level gamma for each ticker, derives pin / walls / put magnet /
flip per ticker, computes a cross-asset confluence verdict (ALIGNED / MIXED /
DIVERGING), persists each snapshot to Supabase, then rewrites the CONFIG block
in /tmp/gamma-heatmap-multi.html and opens it.

Usage:
    python3 scripts/refresh-multi-0dte.py

Requires:
    UW_API_TOKEN
    SUPABASE_URL, SUPABASE_SERVICE_KEY
    TradingView running with CDP (for cross-validating live prices)
"""
import json
import os
import re
import subprocess
import sys
import time as _time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from store_snapshot import store_snapshot, get_session_snapshots
from signal_engine import detect_session_signals
from uw_gex import pull_spot_gex
from strat import match_3_candle_setup
import tv_helpers as tv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(_REPO_ROOT, 'charts', 'templates', 'gamma-heatmap-multi.html')
RENDERED_PATH = os.path.join(_REPO_ROOT, 'charts', 'rendered', 'gamma-heatmap-multi.html')

# Per-ticker config — window around price, strike step, friendly name, TV symbol,
# pane index for the 3h layout. Window/step are sized for readable heatmaps;
# tighter on upside since 0DTE walls cluster near ATM, more room below for put mags.
# Pane indices are 0-based and match the saved "SPX / QQQ / SPY SCRIPT" layout:
# pane 0 = SPX, pane 1 = QQQ, pane 2 = SPY. Saved layout owns the symbol-to-pane
# binding; this script no longer calls set_pane_symbol to avoid races.
TICKERS = {
    'SPX': {
        'name': 'S&P 500',
        'tv_symbol': 'SP:SPX',
        'pane': 0,
        'window_below': 280, 'window_above': 100, 'step': 5,
        # API window: wider than the heatmap window so level-derivation
        # proximity bands (±10% of price) have headroom on both sides.
        'api_window_below': 500, 'api_window_above': 500,
    },
    'QQQ': {
        'name': 'Invesco QQQ Trust',
        'tv_symbol': 'NASDAQ:QQQ',
        'pane': 1,
        'window_below': 30, 'window_above': 12, 'step': 1,
        'api_window_below': 100, 'api_window_above': 100,
    },
    'SPY': {
        'name': 'SPDR S&P 500 ETF',
        'tv_symbol': 'AMEX:SPY',
        'pane': 2,
        'window_below': 28, 'window_above': 10, 'step': 1,
        'api_window_below': 100, 'api_window_above': 100,
    },
}

# Gamma-line colors used when drawing on the TV panes
COLOR_PIN     = '#22c55e'
COLOR_WALL    = '#fbbf24'
COLOR_PUT_MAG = '#ef4444'
COLOR_FLIP    = '#cbd5e1'
COLOR_ICT     = '#fbbf24'        # amber for ICT reference levels

WALL_MIN_RATIO = 0.05        # 5% of max |gex| — the only magnitude filter we need
PIN_PROX_PCT   = 0.05
PUT_PROX_PCT   = 0.10        # put magnet must be within ±10% of price
WALL_PROX_PCT  = 0.10        # walls must be within ±10% of price (tradeable range)
FLIP_PROX_PCT  = 0.15        # only consider strikes in ±15% band for flip calc


# ─────────────────────────────────────────────────────────
# IO helpers
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


# (TV quote / drawing / indicator reads are in tv_helpers; this module focuses
# on UW data + level math + persistence.)


# ─────────────────────────────────────────────────────────
# Gamma math — pin, walls, put magnet, flip
# ─────────────────────────────────────────────────────────
def derive_levels(strikes_net, price):
    """Return dict of levels + walls. Same logic as draw-spx-gamma.py.

    Pin: largest +gex strike within ±PIN_PROX_PCT of price.
    Put magnet: most negative strike above wall-threshold magnitude.
    Walls: single biggest +gex strike on each side, filtered by 5% threshold,
           wall_up above pin, wall_down between price and put magnet.
    Flip: first strike (descending) where cumulative net gamma crosses < 0.
    """
    if not strikes_net:
        return {}

    max_abs = max(abs(v) for v in strikes_net.values())
    threshold = max_abs * WALL_MIN_RATIO

    # Pin — biggest positive gex inside ±5% of price, must clear the relative
    # threshold so noise doesn't qualify.
    prox = price * PIN_PROX_PCT
    near = {s: g for s, g in strikes_net.items()
            if abs(s - price) <= prox and g >= threshold}
    pin = max(near.items(), key=lambda x: x[1]) if near else None

    # Put magnet — most negative, above threshold magnitude, within proximity band.
    # Proximity filter matters for ETFs (SPY/QQQ) where deep-OTM structural OI
    # would otherwise dominate the most-negative pick.
    put_band = price * PUT_PROX_PCT
    neg = [(s, g) for s, g in strikes_net.items()
           if g < -threshold and abs(s - price) <= put_band]
    put_mag = min(neg, key=lambda x: x[1]) if neg else None

    # Walls — single biggest positive on each directional side
    upper_bound = pin[0] if pin else price
    lower_bound = put_mag[0] if put_mag else float('-inf')

    wall_band = price * WALL_PROX_PCT
    wall_up = None
    wall_down = None
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

    # Flip — cumulative net gamma sign change from highest strike downward.
    # Restricted to ±FLIP_PROX_PCT band around price so deep-OTM puts on
    # aggregate-expiry data don't drag the regime line into nonsense.
    flip_band = price * FLIP_PROX_PCT
    band_strikes = [s for s in strikes_net.keys() if abs(s - price) <= flip_band]
    cum = 0.0
    flip = None
    for s in sorted(band_strikes, reverse=True):
        cum += strikes_net[s]
        if cum < 0:
            flip = s
            break

    # Regime — explicit classification so the UI doesn't have to infer from
    # flip-presence. 'positive' when price > flip (or no flip and band stays
    # positive); 'negative' when price < flip (or band stays negative).
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
        'pin': pin,
        'put_mag': put_mag,
        'wall_up': wall_up,
        'wall_down': wall_down,
        'flip': flip,
        'regime': regime,
    }


def compute_confluence(per_ticker):
    """Derive cross-asset confluence verdict.

    Per-ticker regime: 'pos' if price > flip else 'neg'.
    All three same regime → ALIGNED (with direction).
    Mixed → MIXED.
    """
    regimes = []
    for tk, data in per_ticker.items():
        r = data.get('regime')
        if r == 'positive':
            regimes.append('pos')
        elif r == 'negative':
            regimes.append('neg')
        else:
            regimes.append(None)

    valid = [r for r in regimes if r is not None]
    if not valid:
        return {'verdict': 'PENDING', 'tone': 'mixed',
                'note': 'Could not determine regime — flip levels missing.'}

    pos_count = valid.count('pos')
    neg_count = valid.count('neg')

    tickers_list = list(per_ticker.keys())
    detail_parts = []
    for tk, r in zip(tickers_list, regimes):
        if r == 'pos':
            detail_parts.append(f'<span class="pos">{tk}+</span>')
        elif r == 'neg':
            detail_parts.append(f'<span class="neg">{tk}−</span>')
        else:
            detail_parts.append(f'<span class="mute">{tk}?</span>')
    detail = ' · '.join(detail_parts)

    if pos_count == 3:
        return {
            'verdict': 'ALIGNED ↑', 'tone': 'aligned-pos',
            'note': f'All three above flip — positive-gamma compression regime. {detail}. Dealers sell rallies, buy dips; expect mean-reversion around pin levels. Fade strength toward put magnets only if walls break.',
        }
    if neg_count == 3:
        return {
            'verdict': 'ALIGNED ↓', 'tone': 'aligned-neg',
            'note': f'All three below flip — negative-gamma expansion regime. {detail}. Dealers buy rallies, sell dips; expect trending moves and amplified volatility. Trade with momentum, not against it.',
        }
    if pos_count == 2 and neg_count == 1:
        odd = tickers_list[regimes.index('neg')]
        return {
            'verdict': 'DIVERGING', 'tone': 'diverging',
            'note': f'Two above flip, one below — {detail}. {odd} is the outlier in negative gamma; cross-checking it against the other two before going long is the cheapest tell on whether the broader tape can hold.',
        }
    if neg_count == 2 and pos_count == 1:
        odd = tickers_list[regimes.index('pos')]
        return {
            'verdict': 'DIVERGING', 'tone': 'diverging',
            'note': f'Two below flip, one above — {detail}. {odd} is holding up; if it cracks the whole tape gets sloppy. Watch its flip line as the canary.',
        }
    return {'verdict': 'MIXED', 'tone': 'mixed', 'note': f'Regimes split: {detail}.'}


# ─────────────────────────────────────────────────────────
# Per-ticker pull
# ─────────────────────────────────────────────────────────
def pull_ticker(ticker, cfg, token):
    """Pull strikes, derive levels, fetch TV price; return packaged data.

    Pulls textbook GEX from /spot-exposures/strike with proper params
    (limit=500 + min/max_strike centered on price). UW's values are already
    spot²-scaled in dollars and time-stamped intraday, so we use them
    directly without aggregation.
    """
    print(f'\n[{ticker}] Pulling /spot-exposures/strike (textbook intraday GEX)...')
    pull = pull_spot_gex(
        ticker, token,
        window_below=cfg['api_window_below'],
        window_above=cfg['api_window_above'],
    )
    parsed = pull['parsed']
    source = 'spot-exposures'

    if not parsed:
        print(f'  ! No data for {ticker}')
        return None

    uw_ref_price = pull['price']
    data_time = pull['time'] or datetime.now(timezone.utc).isoformat()
    print(f'  strikes: {len(parsed)}  ref_price: ${uw_ref_price}  time: {data_time}')
    if uw_ref_price <= 0:
        print(f'  ! Could not determine reference price for {ticker}')
        return None

    # TradingView price cross-check. By now the caller has switched this
    # ticker's pane in front of us, so `tv quote` reads the right symbol.
    # 30% sanity band guards against edge cases (pane not yet settled, etc.).
    tv_last = tv.get_quote(expected_price=uw_ref_price)
    if tv_last:
        ref_price = tv_last
        delta = ref_price - uw_ref_price
        if abs(delta) > max(1, uw_ref_price * 0.001):
            print(f'  Note: TV last ${ref_price} differs from UW gamma ref ${uw_ref_price} by {delta:+.2f}')
    else:
        ref_price = uw_ref_price

    # === Intraday-TF TV reads ===
    # Killzones labels and POC only render on intraday TFs; explicitly switch
    # to 5m so the indicator has bars to compute against. Record whatever the
    # pane was on before for Phase 3 restoration.
    original_state = tv.get_active_state() or {}
    original_tf = original_state.get('resolution')
    INTRADAY_TF = '5'
    tv.set_timeframe(INTRADAY_TF)

    ict_levels = tv.pull_ict_levels(price=ref_price, prox_pct=0.10)
    poc_raw = tv.pull_poc()
    # Sanity filter: POC must be within 5% of price to be useful. Otherwise
    # it's a stale VP range carried over from a different symbol (e.g. MNQ).
    poc = poc_raw if (poc_raw and abs(poc_raw - ref_price) / ref_price < 0.05) else None
    if poc_raw and not poc:
        print(f'  Note: POC ${poc_raw:g} out of proximity band — discarded as stale')

    # === Daily-TF read for S&D structural zones ===
    # Switch active pane to daily so the Market Structure indicator surfaces
    # daily-bar BOS/ChoCh events. Pull proper paired zones (top 3 closest per
    # side, unmitigated only) via the structure-zones CLI subcommand — each
    # zone has TWO price edges (upper + lower) from the broken-pivot trigger
    # + paired swing pivot.
    weekly_zones = []
    session_range = None
    strat_bars = None
    # Longer settle for the D switch: LuxAlgo MS Fractal has to recompute
    # pivots/structure across the full daily history. 1s isn't always enough
    # — 0-zone results were intermittent until we waited longer.
    if tv.set_timeframe('D', settle=5.0):
        # Re-focus pane after TF switch — keeps the structure-zones pull
        # locked on this pane's chart, not whatever last took activeChart.
        tv.focus_pane(cfg['pane'])
        _time.sleep(0.5)
        # Gate 1 (chart-data SKILL) — pull twice with 2s gap, re-pull until
        # two consecutive pulls agree.
        def _pull():
            return tv.pull_structure_zones(
                current_price=ref_price, top_n_per_side=10,
            )
        def _sig(zs):
            return tuple(sorted((z.get('zone_type'), z.get('bar_idx'),
                                 z.get('upper'), z.get('lower')) for z in (zs or [])))
        pull_a = _pull()
        _time.sleep(2)
        pull_b = _pull()
        attempts = 1
        while _sig(pull_a) != _sig(pull_b) and attempts < 4:
            _time.sleep(2)
            pull_a = pull_b
            pull_b = _pull()
            attempts += 1
        all_zones = pull_b if _sig(pull_a) == _sig(pull_b) else []
        # Heatmap shows only the most-recent unmitigated supply and demand.
        sups = sorted([z for z in all_zones if z.get('zone_type') == 'supply'],
                      key=lambda z: -z.get('bar_idx', 0))
        dems = sorted([z for z in all_zones if z.get('zone_type') == 'demand'],
                      key=lambda z: -z.get('bar_idx', 0))
        if sups: weekly_zones.append(sups[0])
        if dems: weekly_zones.append(dems[0])
        # While on daily TF, also pull the latest daily bar's OHLC so the
        # heatmap can show today's range. Re-focus the pane first because
        # set_timeframe doesn't guarantee `_activeChartWidget` is this pane,
        # and `tv ohlcv` reads from the global active widget. Sanity-check
        # the close against ref_price — rejects cross-pane bleed.
        tv.focus_pane(cfg['pane'])
        session_range = tv.get_session_range(expected_price=ref_price, tolerance=0.05)
        if session_range is None:
            print(f'  Note: {ticker} session-range pull rejected (cross-pane bleed?)')
        # Strat Phase 1 — pull last 4 closed daily bars (anchor + P1/P2/P3).
        # Excludes the actively-forming intraday bar. Classification deferred
        # to Phase 2 (pure function) so this stays I/O-only.
        strat_bars = tv.get_recent_closed_bars(n=4, expected_price=ref_price)
        # NOTE: TF is left on daily here — Phase 3 will restore original_tf
        # after drawing zones on the daily view.

    strikes_net = {r['strike']: r['call_gamma_oi'] + r['put_gamma_oi'] for r in parsed}

    total_oi = sum(r['call_gamma_oi'] + r['put_gamma_oi'] for r in parsed)
    total_vol = sum(r['call_gamma_vol'] + r['put_gamma_vol'] for r in parsed)
    total_dir = sum(r['call_gamma_vol'] - r['put_gamma_vol'] for r in parsed)

    step = cfg['step']
    atm = round(ref_price / step) * step
    low = int((ref_price - cfg['window_below']) / step) * step
    high = int((ref_price + cfg['window_above']) / step + 1) * step

    in_range_strikes = {s: g for s, g in strikes_net.items() if low <= s <= high}

    # Derive levels from the WINDOWED strikes — the same set that lands in the
    # HTML and that the JS will recompute pin/walls/put-mag from. This way the
    # Python print output, the Supabase snapshot, and the TV draw lines all
    # agree with what the heatmap actually displays. Earlier we ran derive_levels
    # on the full chain, which produced e.g. wall_up $7500 (outside window) that
    # the HTML rendered as $7450 — three sources of truth, all different.
    levels = derive_levels(in_range_strikes, ref_price)

    return {
        'ticker': ticker,
        'name': cfg['name'],
        'source': source,
        'parsed': parsed,
        'strikes_net': strikes_net,
        'in_range_strikes': in_range_strikes,
        'levels': levels,
        'ict_levels': ict_levels,
        'poc': poc,
        'weekly_zones': weekly_zones,
        'session_range': session_range,
        'strat_bars': strat_bars,
        'original_tf': original_tf,
        'tv_price': ref_price,
        'uw_ref_price': uw_ref_price,
        'data_time': data_time,
        'total_oi_gamma': total_oi,
        'total_vol_gamma': total_vol,
        'total_dir_gamma': total_dir,
        'atm': atm,
        'low': low,
        'high': high,
        'step': step,
        'pin_strike': levels.get('pin', (None, 0))[0] if levels.get('pin') else None,
        'pin_gamma': levels.get('pin', (None, 0))[1] if levels.get('pin') else None,
        'wall_up_strike': levels.get('wall_up', (None, 0))[0] if levels.get('wall_up') else None,
        'wall_up_gamma': levels.get('wall_up', (None, 0))[1] if levels.get('wall_up') else None,
        'wall_down_strike': levels.get('wall_down', (None, 0))[0] if levels.get('wall_down') else None,
        'wall_down_gamma': levels.get('wall_down', (None, 0))[1] if levels.get('wall_down') else None,
        'put_mag_strike': levels.get('put_mag', (None, 0))[0] if levels.get('put_mag') else None,
        'put_mag_gamma': levels.get('put_mag', (None, 0))[1] if levels.get('put_mag') else None,
        'flip_strike': levels.get('flip'),
        'regime': levels.get('regime'),
    }


# ─────────────────────────────────────────────────────────
# Supabase persistence
# ─────────────────────────────────────────────────────────
def persist(ticker_data, expiry_iso):
    levels = {
        'tv_price': ticker_data['tv_price'],
        'uw_ref_price': ticker_data['uw_ref_price'],
        'data_time': ticker_data['data_time'],
        'total_oi_gamma': ticker_data['total_oi_gamma'],
        'total_vol_gamma': ticker_data['total_vol_gamma'],
        'total_dir_gamma': ticker_data['total_dir_gamma'],
        'pin_strike': ticker_data['pin_strike'],
        'pin_gamma': ticker_data['pin_gamma'],
        'wall_up_strike': ticker_data['wall_up_strike'],
        'wall_up_gamma': ticker_data['wall_up_gamma'],
        'wall_down_strike': ticker_data['wall_down_strike'],
        'wall_down_gamma': ticker_data['wall_down_gamma'],
        'put_mag_strike': ticker_data['put_mag_strike'],
        'put_mag_gamma': ticker_data['put_mag_gamma'],
        'flip_strike': ticker_data['flip_strike'],
    }
    strike_rows = []
    for r in ticker_data['parsed']:
        net = r['call_gamma_oi'] + r['put_gamma_oi']
        strike_rows.append({
            'strike': r['strike'],
            'call_gamma_oi': r['call_gamma_oi'],
            'put_gamma_oi': r['put_gamma_oi'],
            'call_gamma_vol': r['call_gamma_vol'],
            'put_gamma_vol': r['put_gamma_vol'],
            'call_delta_oi': r['call_delta_oi'],
            'put_delta_oi': r['put_delta_oi'],
            'net_gamma': net,
        })
    snap_id = store_snapshot(
        ticker=ticker_data['ticker'],
        expiry=expiry_iso,
        levels=levels,
        strikes=strike_rows,
    )
    return snap_id


# ─────────────────────────────────────────────────────────
# CONFIG block rewriter
# ─────────────────────────────────────────────────────────
def build_config_js(per_ticker, confluence, expiry_iso, signals=None):
    now = datetime.now()
    today_iso = now.strftime('%Y-%m-%d')
    expiry_label = f'Aggregate · {now.strftime("%-m/%-d")}'
    as_of = datetime.now(timezone.utc).isoformat()

    def fmt_strike_key(s):
        # JS object keys: integers prefer no decimals, else 2dp
        return f'{int(s)}' if s == int(s) else f'{s:.2f}'

    ticker_blocks = []
    for tk, data in per_ticker.items():
        strikes_lines = []
        for s in sorted(data['in_range_strikes'].keys(), reverse=True):
            key = fmt_strike_key(s)
            val = int(round(data['in_range_strikes'][s]))
            strikes_lines.append(f'      {key}: {val},')
        strikes_block = '\n'.join(strikes_lines).rstrip(',')

        flip_js = 'null' if data['flip_strike'] is None else fmt_strike_key(data['flip_strike'])
        regime_js = 'null' if data.get('regime') is None else f"'{data['regime']}'"

        ict_items = []
        for lvl in (data.get('ict_levels') or []):
            name_safe = (lvl['name'] or '').replace("'", "\\'")
            ict_items.append(f"{{ name: '{name_safe}', price: {lvl['price']} }}")
        ict_js = '[' + ', '.join(ict_items) + ']'

        # Daily S&D zones — emitted as `weeklyZones` (existing CONFIG field
        # the heatmap JS already renders as rectangle boxes).
        zone_items = []
        for z in (data.get('weekly_zones') or []):
            zone_items.append(
                f"{{ upper: {z['upper']}, lower: {z['lower']}, "
                f"type: '{z['zone_type']}', direction: '{z['direction']}', "
                f"mitigated: false, bar_idx: {z.get('bar_idx', 0)} }}"
            )
        weekly_zones_js = '[' + ', '.join(zone_items) + ']'

        flag_items = []
        for f in (data.get('confluence_flags') or []):
            safe = f.replace("'", "\\'")
            flag_items.append(f"'{safe}'")
        flags_js = '[' + ', '.join(flag_items) + ']'

        poc = data.get('poc')
        poc_js = 'null' if poc is None else str(poc)

        sr = data.get('session_range') or {}
        if sr.get('high') is not None and sr.get('low') is not None:
            session_range_js = (
                f"{{ high: {sr['high']}, low: {sr['low']}, "
                f"open: {sr.get('open', 'null')}, close: {sr.get('close', 'null')}, label: 'Day' }}"
            )
        else:
            session_range_js = 'null'

        ss = data.get('strat_setup')
        if ss:
            ss_pattern = ss['pattern'].replace("'", "\\'")
            strat_setup_js = (
                f"{{ pattern: '{ss_pattern}', direction: '{ss['direction']}', "
                f"target: {ss['target']}, p1Type: '{ss['p1_type']}', "
                f"p2Type: '{ss['p2_type']}', p3Type: '{ss['p3_type']}' }}"
            )
        else:
            strat_setup_js = 'null'

        block = f"""    {tk}: {{
      name: '{data['name']}',
      currentPrice: {data['tv_price']},
      atmStrike: {data['atm']},
      gammaFlip: {flip_js},
      regime: {regime_js},
      poc: {poc_js},
      sessionRange: {session_range_js},
      stratSetup: {strat_setup_js},
      strikeRange: {{ low: {data['low']}, high: {data['high']}, step: {data['step']} }},
      strikes: {{
{strikes_block}
      }},
      ictLevels: {ict_js},
      weeklyZones: {weekly_zones_js},
      confluenceFlags: {flags_js},
    }}"""
        ticker_blocks.append(block)

    tickers_js = ',\n'.join(ticker_blocks)

    # Escape any single quotes in the confluence note
    note_safe = confluence['note'].replace("\\", "\\\\").replace("'", "\\'")

    source_bits = []
    for tk, data in per_ticker.items():
        tag = '0DTE' if data.get('source') == '0dte' else 'aggregate'
        source_bits.append(f'{tk}: {tag}')
    sources_str = ' · '.join(source_bits)
    analysis_note = (
        f"Live pull · Unusual Whales · {now.strftime('%H:%M:%S')} local · "
        f"sources [{sources_str}] · snapshots persisted to Supabase."
    ).replace("'", "\\'")

    signals_js = json.dumps(signals or [], default=str)

    return f"""const CONFIG = {{
  expiry: '{expiry_iso}',
  expiryLabel: '{expiry_label}',
  asOf: '{as_of}',
  confluence: {{ verdict: '{confluence['verdict']}', tone: '{confluence['tone']}', note: '{note_safe}' }},
  analysisNote: '{analysis_note}',
  tickers: {{
{tickers_js}
  }},
  signals: {signals_js},
}};"""


def patch_html(config_js):
    with open(TEMPLATE_PATH, 'r') as f:
        html = f.read()
    pattern = r'const CONFIG = \{[\s\S]*?\n\};'
    if not re.search(pattern, html):
        sys.exit(f'Could not find CONFIG block in {TEMPLATE_PATH}')
    new_html = re.sub(pattern, lambda _: config_js, html, count=1)
    os.makedirs(os.path.dirname(RENDERED_PATH), exist_ok=True)
    with open(RENDERED_PATH, 'w') as f:
        f.write(new_html)


# ─────────────────────────────────────────────────────────
# TV drawing — call only when this pane is focused
# ─────────────────────────────────────────────────────────
def _fmt_b(v):
    if v is None:
        return ''
    sign = '+' if v >= 0 else '−'
    return f'{sign}${abs(v)/1e9:.1f}B'


def _draw_pane_lines(ticker_data):
    """Draw only GEX-derived levels (PIN / WALL ↑ / WALL ↓ / PUT MAG / FLIP).
    POC and S&D zones are NOT drawn — they come from native indicators on the
    chart and we already read from them; redrawing would duplicate.

    Caller is responsible for clearing existing drawings + focusing the right
    pane before invoking this.
    """
    def maybe(strike, gamma, color, kind, linestyle, linewidth):
        if strike is None:
            return
        gtxt = f' ({_fmt_b(gamma)})' if gamma else ''
        label = f'{kind} ${int(float(strike))}{gtxt}'.strip()
        tv.draw_horizontal_line(float(strike), color, label,
                                 linestyle=linestyle, linewidth=linewidth)

    maybe(ticker_data.get('pin_strike'),       ticker_data.get('pin_gamma'),
          COLOR_PIN,     'PIN',     0, 2)
    maybe(ticker_data.get('wall_up_strike'),   ticker_data.get('wall_up_gamma'),
          COLOR_WALL,    'WALL ↑',  2, 1)
    maybe(ticker_data.get('wall_down_strike'), ticker_data.get('wall_down_gamma'),
          COLOR_WALL,    'WALL ↓',  2, 1)
    maybe(ticker_data.get('put_mag_strike'),   ticker_data.get('put_mag_gamma'),
          COLOR_PUT_MAG, 'PUT MAG', 0, 2)
    if ticker_data.get('flip_strike') is not None:
        flip = float(ticker_data['flip_strike'])
        tv.draw_horizontal_line(flip, COLOR_FLIP, f'FLIP ${int(flip)}',
                                 linestyle=1, linewidth=1)


# ─────────────────────────────────────────────────────────
# Data Report — Phase 1 audit
# ─────────────────────────────────────────────────────────
def print_data_report(per_ticker):
    """Print a clear table of what was collected for each ticker."""
    print('\n╭─ Data Report ─────────────────────────────────────────╮')
    for ticker, data in per_ticker.items():
        price_ok = data.get('tv_price', 0) > 0
        tv_used = data.get('tv_price') and abs(data['tv_price'] - data['uw_ref_price']) / max(data['uw_ref_price'], 1) < 0.03
        ict_n = len(data.get('ict_levels') or [])
        poc = data.get('poc')
        zones_n = len(data.get('weekly_zones') or [])
        strikes_n = len(data.get('in_range_strikes') or [])
        og_tf = data.get('original_tf') or '?'

        tv_tag = 'TV' if tv_used else 'UW'
        print(f'  {ticker:4} '
              f'price ${data["tv_price"]:.2f} ({tv_tag})  '
              f'ICT {ict_n:>2}  '
              f'POC {"$"+str(poc) if poc else "—":>9}  '
              f'S&D {zones_n:>2}  '
              f'strikes {strikes_n:>3}  '
              f'tf:{og_tf}')
    print('╰───────────────────────────────────────────────────────╯')


# ─────────────────────────────────────────────────────────
# Confluence flags — Phase 2 cross-source checks
# ─────────────────────────────────────────────────────────
def compute_confluence_flags(ticker_data, price_tol_pct=0.002):
    """Return a list of short human-readable flags noting where gamma levels
    align with ICT levels, POC, or S&D events. Tolerance default 0.2% of price.
    """
    flags = []
    price = ticker_data.get('tv_price') or 0
    if price <= 0:
        return flags
    tol = price * price_tol_pct

    def near(a, b):
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol

    pin = ticker_data.get('pin_strike')
    wall_up = ticker_data.get('wall_up_strike')
    wall_down = ticker_data.get('wall_down_strike')
    poc = ticker_data.get('poc')

    # Pin ↔ POC alignment — strong magnetic stack
    if near(pin, poc):
        flags.append(f'PIN ${int(pin)} ≈ POC ${poc:g} (stacked magnet)')

    # Walls ↔ ICT levels (e.g. wall at PDH = important test)
    for ict in (ticker_data.get('ict_levels') or []):
        for wall_label, wall_strike in (('WALL ↑', wall_up), ('WALL ↓', wall_down)):
            if near(wall_strike, ict['price']):
                flags.append(f'{wall_label} ${int(wall_strike)} ≈ {ict["name"]} ${ict["price"]:g}')

    # S&D zones ↔ gamma levels — daily zone edge confirming a gamma level.
    # Check both upper and lower edges of each zone.
    for z in (ticker_data.get('weekly_zones') or []):
        sigil = 'D' if z['zone_type'] == 'demand' else 'S'
        for lbl, strike in (('pin', pin), ('wall ↑', wall_up), ('wall ↓', wall_down)):
            for edge_name, edge_val in (('upper', z['upper']), ('lower', z['lower'])):
                if near(strike, edge_val):
                    flags.append(f'{lbl} ${int(strike)} ≈ daily {sigil} {edge_name} ${edge_val:g}')

    return flags


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def main():
    token = os.environ.get('UW_API_TOKEN')
    if not token:
        sys.exit('UW_API_TOKEN not set')
    if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_KEY'):
        sys.exit('SUPABASE_URL or SUPABASE_SERVICE_KEY not set — required for snapshot persistence')
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f'Template not found: {TEMPLATE_PATH}')

    print('━' * 60)
    print('PHASE 1 — COLLECT (read TV + UW, no mutations)')
    print('━' * 60)

    # Load the curated saved layout that has LuxAlgo MS Fractal, Volume Profile,
    # ICT Killzones already configured on each pane — read tools need them visible.
    saved_layout = 'SPX / QQQ / SPY SCRIPT'
    print(f'Switching to saved TV layout: {saved_layout}…')
    if not tv.switch_saved_layout(saved_layout):
        print(f'  ! Could not switch to "{saved_layout}" — falling back to 3-pane geometry', file=sys.stderr)
        if not tv.set_layout('3h'):
            print('  ! 3-pane fallback also failed — proceeding anyway', file=sys.stderr)

    per_ticker = {}
    for ticker, cfg in TICKERS.items():
        print(f'\n[Pane {cfg["pane"]}] {ticker} ({cfg["tv_symbol"]})')
        # Saved layout already binds symbol-to-pane. Just focus + settle so
        # `_activeChartWidget` lands cleanly before any reads happen.
        tv.focus_pane(cfg['pane'])
        _time.sleep(1.5)

        result = pull_ticker(ticker, cfg, token)
        if result is None:
            print(f'  ! {ticker} returned no data — skipping')
            continue
        per_ticker[ticker] = result

    if not per_ticker:
        sys.exit('No ticker data — aborting')

    print_data_report(per_ticker)

    print('\n' + '━' * 60)
    print('PHASE 2 — ANALYZE (pure functions, no I/O)')
    print('━' * 60)

    # Per-ticker Strat 3-bar setup (pure-function match against last 4 daily bars)
    for ticker, data in per_ticker.items():
        bars = data.get('strat_bars')
        setup = match_3_candle_setup(bars) if bars else None
        data['strat_setup'] = setup
        if setup:
            arrow = '↑' if setup['direction'] == 'bullish' else '↓'
            print(f'  {ticker} Strat: {setup["pattern"]} {arrow} · target ${setup["target"]:g}')
        else:
            print(f'  {ticker} Strat: no qualified 3-bar setup')

    # Per-ticker confluence flags (gamma ↔ ICT / POC / S&D)
    for ticker, data in per_ticker.items():
        flags = compute_confluence_flags(data)
        data['confluence_flags'] = flags
        if flags:
            print(f'\n  {ticker} confluence:')
            for f in flags:
                print(f'    · {f}')
        else:
            print(f'\n  {ticker} confluence: (no overlaps within tolerance)')

    confluence = compute_confluence(per_ticker)
    print(f'\nCross-asset verdict: {confluence["verdict"]}')

    print('\n' + '━' * 60)
    print('PHASE 3 — OUTPUT (persist + draw + render)')
    print('━' * 60)

    # 3a. Persist
    expiry_iso = datetime.now().strftime('%Y-%m-%d')
    print('Persisting snapshots to Supabase…')
    for ticker, data in per_ticker.items():
        try:
            snap_id = persist(data, expiry_iso)
            print(f'  ✓ {ticker} → {snap_id}')
        except Exception as e:
            print(f'  ! {ticker} persistence failed: {e}', file=sys.stderr)

    # 3a.5. Notification signals — accumulate today's session by diffing
    # consecutive Supabase snapshots per ticker. Interleaved chronologically.
    session_signals = []
    try:
        # Session window: today's 9:30 ET = 13:30 UTC (Z suffix — '+' breaks URL encoding)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        since_iso = f'{today}T13:30:00Z'
        snaps = get_session_snapshots(list(per_ticker.keys()), since_iso)
        session_signals = detect_session_signals(snaps)
        if session_signals:
            print(f'\nSession signals ({len(session_signals)} events):')
            for s in session_signals[-8:]:
                print(f'  {s["time"]} · {s["ticker"]} · {s["code"]} · {s["text"]}')
        else:
            print('\nSession signals: none yet (need ≥2 snapshots per ticker)')
    except Exception as e:
        print(f'  ! signal engine failed: {e}', file=sys.stderr)

    # 3b. TV drawings — for each pane: clear, draw S&D on DAILY, switch back
    # to original intraday TF, draw gamma + POC. Daily zones stay visible
    # across all timeframes because TV preserves drawings per pane.
    print('\nDrawing on TV panes…')
    for ticker, data in per_ticker.items():
        cfg = TICKERS[ticker]
        tv.focus_pane(cfg['pane'])
        tv.clear_active_pane_drawings()
        # Restore original TF and draw gamma + POC. S&D zones are NOT drawn —
        # the LuxAlgo MS indicator already renders them natively, and our
        # heatmap reads from that.
        if data.get('original_tf'):
            tv.set_timeframe(data['original_tf'])
        _draw_pane_lines(data)
        print(f'  ✓ pane {cfg["pane"]} ({ticker}): gamma lines (POC + {len(data.get("weekly_zones") or [])} zones from indicators)')

    # 3c. Render HTML once with the full picture
    config_js = build_config_js(per_ticker, confluence, expiry_iso, session_signals)
    patch_html(config_js)
    print(f'\n✓ Rendered {RENDERED_PATH}')

    # Per-ticker summary
    for ticker, data in per_ticker.items():
        levels = data['levels']
        bits = []
        if levels.get('pin'):    bits.append(f'pin ${int(levels["pin"][0])}')
        if levels.get('wall_up'): bits.append(f'wall↑ ${int(levels["wall_up"][0])}')
        if levels.get('wall_down'): bits.append(f'wall↓ ${int(levels["wall_down"][0])}')
        if levels.get('put_mag'): bits.append(f'put ${int(levels["put_mag"][0])}')
        if levels.get('flip'):    bits.append(f'flip ${int(levels["flip"])}')
        poc = data.get('poc')
        if poc: bits.append(f'POC ${poc:g}')
        print(f'  {ticker}: ${data["tv_price"]} | ' + ' · '.join(bits))

    if not os.environ.get('GAMMA_NO_OPEN'):
        subprocess.run(['open', RENDERED_PATH])


if __name__ == '__main__':
    main()
