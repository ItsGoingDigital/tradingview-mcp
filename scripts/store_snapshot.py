#!/usr/bin/env python3
"""
Supabase storage layer for gamma snapshots.

Used by refresh scripts to persist a point-in-time snapshot of UW gamma data
so we can build a history (intraday drift, day-over-day comparisons, etc).

Two tables:
    gamma_snapshots  — one row per refresh per ticker (high-level levels)
    gamma_strikes    — one row per strike per snapshot (raw per-strike data)

Env:
    SUPABASE_URL          e.g. https://kobxjebvckrlxkbkgvuh.supabase.co
    SUPABASE_SERVICE_KEY  service_role key (bypasses RLS)

Usage as a module:
    from store_snapshot import store_snapshot
    snap_id = store_snapshot(ticker='SPX', expiry='2026-05-13',
                             levels={...}, strikes=[...], raw={...})

CLI smoke test:
    python3 scripts/store_snapshot.py --selftest
"""
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def _supabase_request(method, path, body=None):
    url = os.environ['SUPABASE_URL'].rstrip('/') + path
    key = os.environ['SUPABASE_SERVICE_KEY']
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    data = None
    if body is not None:
        headers['Prefer'] = 'return=representation'
        data = json.dumps(body).encode()
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except HTTPError as e:
        body_txt = e.read().decode()[:500]
        raise RuntimeError(f'Supabase {e.code} on {path}: {body_txt}')


def _supabase_post(path, body):
    return _supabase_request('POST', path, body)


def _supabase_get(path):
    return _supabase_request('GET', path)


def get_latest_snapshot(ticker):
    """Return the most recent snapshot for a ticker, or None.

    Useful for the draw script — reads pre-computed levels rather than re-pulling
    UW. Returns the snapshot row as a dict (includes all level columns).
    """
    rows = _supabase_get(
        f'/rest/v1/gamma_snapshots?ticker=eq.{ticker}'
        f'&order=captured_at.desc&limit=1'
    )
    return rows[0] if rows else None


def store_snapshot(ticker, expiry, levels, strikes, raw=None):
    """Insert a snapshot + per-strike rows. Returns snapshot id.

    levels: dict with optional keys
        tv_price, uw_ref_price, data_time,
        total_oi_gamma, total_vol_gamma, total_dir_gamma,
        pin_strike, pin_gamma,
        wall_up_strike, wall_up_gamma,
        wall_down_strike, wall_down_gamma,
        put_mag_strike, put_mag_gamma,
        flip_strike

    strikes: list of dicts with keys
        strike, call_gamma_oi, put_gamma_oi,
        call_gamma_vol, put_gamma_vol,
        call_delta_oi, put_delta_oi, net_gamma
    """
    if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_KEY'):
        raise RuntimeError('SUPABASE_URL or SUPABASE_SERVICE_KEY not set')

    snap_body = {'ticker': ticker, 'expiry': expiry, **levels}
    if raw is not None:
        snap_body['raw'] = raw
    snap_rows = _supabase_post('/rest/v1/gamma_snapshots', snap_body)
    snap_id = snap_rows[0]['id']

    if strikes:
        strike_rows = [{'snapshot_id': snap_id, **s} for s in strikes]
        _supabase_post('/rest/v1/gamma_strikes', strike_rows)

    return snap_id


def _selftest():
    """Insert a tiny dummy snapshot to prove the pipe works end-to-end."""
    levels = {
        'tv_price': 7400.97,
        'uw_ref_price': 7395.0,
        'pin_strike': 7400,
        'pin_gamma': 1.2e9,
        'flip_strike': 7385,
    }
    strikes = [
        {'strike': 7400, 'call_gamma_oi': 8e8, 'put_gamma_oi': 4e8, 'net_gamma': 1.2e9},
        {'strike': 7395, 'call_gamma_oi': 3e8, 'put_gamma_oi': 5e8, 'net_gamma': 8e8},
    ]
    snap_id = store_snapshot('TEST', '2026-05-13', levels, strikes)
    print(f'✓ Inserted test snapshot {snap_id}')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        _selftest()
    else:
        print(__doc__)
