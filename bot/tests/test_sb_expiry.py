from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from service.db import get_session
from service.models import Zone
from service.silverbullet.expiry import _sweep


def _utc(dt_iso_et: str) -> datetime:
    return (
        datetime.fromisoformat(dt_iso_et)
        .replace(tzinfo=ZoneInfo("America/New_York"))
        .astimezone(ZoneInfo("UTC"))
    )


def _make_zone(s, zid: str, created_at_utc: datetime, status: str = "armed") -> Zone:
    z = Zone(
        id=zid,
        source="silverbullet",
        symbol="CME_MINI:MNQ1!",
        tf="1",
        direction="long",
        entry=20010.0,
        sl=20000.0,
        risk_pts=10.0,
        tp=20030.0,
        contracts=2,
        status=status,
        created_at=created_at_utc,
        updated_at=created_at_utc,
    )
    s.add(z)
    s.flush()
    return z


@pytest.mark.asyncio
async def test_sweep_expires_armed_zone_after_window():
    """A zone created at 10:30 ET should be expired when sweep runs at 11:30 ET same day."""
    created = _utc("2026-05-20T10:30:00")
    now = _utc("2026-05-20T11:30:00")
    with get_session() as s:
        _make_zone(s, "expire-1", created_at_utc=created)
    n = await _sweep(now_utc=now)
    assert n == 1
    with get_session() as s:
        assert s.get(Zone, "expire-1").status == "expired"


@pytest.mark.asyncio
async def test_sweep_leaves_zone_alone_inside_window():
    created = _utc("2026-05-20T10:05:00")
    now = _utc("2026-05-20T10:30:00")  # still inside window
    with get_session() as s:
        _make_zone(s, "alive-1", created_at_utc=created)
    n = await _sweep(now_utc=now)
    assert n == 0
    with get_session() as s:
        assert s.get(Zone, "alive-1").status == "armed"


@pytest.mark.asyncio
async def test_sweep_ignores_non_armed_zones():
    created = _utc("2026-05-20T10:30:00")
    now = _utc("2026-05-20T11:30:00")
    with get_session() as s:
        _make_zone(s, "filled-1", created_at_utc=created, status="filled")
        _make_zone(s, "skip-1", created_at_utc=created, status="skipped")
    n = await _sweep(now_utc=now)
    assert n == 0
    with get_session() as s:
        assert s.get(Zone, "filled-1").status == "filled"
        assert s.get(Zone, "skip-1").status == "skipped"


@pytest.mark.asyncio
async def test_sweep_ignores_other_bots_rows():
    created = _utc("2026-05-20T10:30:00")
    now = _utc("2026-05-20T11:30:00")
    with get_session() as s:
        z = Zone(
            id="mnq-z-1",
            source="mnq_sd",
            symbol="CME_MINI:MNQ1!",
            tf="240",
            direction="long",
            entry=20000.0,
            sl=19995.0,
            risk_pts=5.0,
            tp=20015.0,
            contracts=5,
            status="armed",
            created_at=created,
            updated_at=created,
        )
        s.add(z)
    n = await _sweep(now_utc=now)
    assert n == 0
    with get_session() as s:
        assert s.get(Zone, "mnq-z-1").status == "armed"
