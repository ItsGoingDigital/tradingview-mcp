from __future__ import annotations

import pytest

from service.db import get_session
from service.models import Zone
from service.silverbullet.lifecycle import handle_event
from service.silverbullet.schemas import SBAlertPayload


@pytest.fixture(autouse=True)
def _force_open_window(monkeypatch):
    """Pretend we're inside the SB window so guardrails pass during tests."""
    monkeypatch.setattr(
        "service.silverbullet.guardrails.in_sb_window", lambda *a, **k: True
    )


def _payload(**overrides):
    base = dict(
        symbol="CME_MINI:MNQ1!",
        tf="1",
        event="new_signal",
        id="sb-test-1",
        direction="long",
        entry=20010.0,
        sl=20000.0,
        ts=1700000000,
        secret="test-secret",
    )
    base.update(overrides)
    return SBAlertPayload(**base)


@pytest.mark.asyncio
async def test_new_signal_dry_run_arms_with_2r_tp():
    res = await handle_event(_payload())
    assert res["action"] == "armed"
    assert res["dry_run"] is True
    # risk = 10 pts, contracts = floor($50 / (10 * $2)) = 2; tp = 20010 + 2*10 = 20030
    assert res["contracts"] == 2
    assert res["tp"] == 20030.0
    with get_session() as s:
        z = s.get(Zone, "sb-test-1")
        assert z is not None
        assert z.source == "silverbullet"
        assert z.status == "armed"
        assert z.tp == 20030.0


@pytest.mark.asyncio
async def test_short_signal_tp_below_entry():
    res = await handle_event(
        _payload(direction="short", entry=20000.0, sl=20010.0, id="sb-short")
    )
    assert res["action"] == "armed"
    # short: tp = 20000 - 2*10 = 19980
    assert res["tp"] == 19980.0


@pytest.mark.asyncio
async def test_wide_zone_skipped():
    # risk = 30 pts → floor($50 / (30 * $2)) = 0 → skipped
    res = await handle_event(_payload(entry=20030.0, sl=20000.0, id="sb-wide"))
    assert res["action"] == "skipped"
    assert res["reason"] == "wide_zone"
    with get_session() as s:
        assert s.get(Zone, "sb-wide").status == "skipped"


@pytest.mark.asyncio
async def test_duplicate_signal_ignored():
    await handle_event(_payload(id="sb-dup"))
    res = await handle_event(_payload(id="sb-dup"))
    assert res["action"] == "ignored"
    assert res["reason"] == "duplicate"


@pytest.mark.asyncio
async def test_one_per_day_blocks_second_signal(monkeypatch):
    monkeypatch.setattr(
        "service.silverbullet.guardrails.in_sb_window", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "service.silverbullet.guardrails.settings.bypass_guardrails", False
    )
    res1 = await handle_event(_payload(id="sb-first"))
    assert res1["action"] == "armed"
    res2 = await handle_event(_payload(id="sb-second"))
    assert res2["action"] == "skipped"
    assert res2["reason"] == "already_traded_today"


@pytest.mark.asyncio
async def test_cancel_event_marks_armed_zone_cancelled():
    await handle_event(_payload(id="sb-cancel"))
    res = await handle_event(_payload(id="sb-cancel", event="cancel"))
    assert res["action"] == "cancelled"
    with get_session() as s:
        z = s.get(Zone, "sb-cancel")
        assert z.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_unknown_zone_is_noop():
    res = await handle_event(_payload(id="never-seen", event="cancel"))
    assert res["action"] == "ignored"
    assert res["reason"] == "unknown_zone"
