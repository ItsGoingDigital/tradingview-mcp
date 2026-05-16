import pytest

from service.lifecycle import handle_event
from service.schemas import AlertPayload


@pytest.fixture(autouse=True)
def _force_in_session(monkeypatch):
    monkeypatch.setattr("service.guardrails.in_session", lambda *a, **k: True)


def _payload(**overrides):
    base = dict(
        symbol="CME_MINI:MNQ1!",
        tf="240",
        event="new_zone",
        id="bar-100",
        direction="long",
        entry=20000.0,
        sl=19995.0,
        ts=1700000000,
        secret="test-secret",
    )
    base.update(overrides)
    return AlertPayload(**base)


@pytest.mark.asyncio
async def test_new_zone_dry_run_arms_zone():
    from service.db import get_session
    from service.models import Zone

    res = await handle_event(_payload())
    assert res["action"] == "armed"
    assert res["dry_run"] is True
    assert res["contracts"] == 5  # $50 / (5 pts × $2)
    assert res["tp"] == 20015.0  # entry + 3*risk

    with get_session() as s:
        z = s.get(Zone, "bar-100")
        assert z is not None
        assert z.status == "armed"
        assert z.direction == "long"


@pytest.mark.asyncio
async def test_wide_zone_skipped():
    res = await handle_event(_payload(entry=20000.0, sl=19970.0))  # 30 pts → 0 contracts
    assert res["action"] == "skipped"
    assert res["reason"] == "wide_zone"


@pytest.mark.asyncio
async def test_mitigation_cancels_armed_zone():
    from service.db import get_session
    from service.models import Zone

    await handle_event(_payload())
    res = await handle_event(_payload(event="mitigated"))
    assert res["action"] == "cancelled"
    with get_session() as s:
        z = s.get(Zone, "bar-100")
        assert z.status == "mitigated"


@pytest.mark.asyncio
async def test_mitigation_for_unknown_zone_is_noop():
    res = await handle_event(_payload(event="mitigated", id="never-seen"))
    assert res["action"] == "ignored"
    assert res["reason"] == "unknown_zone"


@pytest.mark.asyncio
async def test_duplicate_new_zone_is_idempotent():
    await handle_event(_payload())
    res = await handle_event(_payload())  # same id
    assert res["action"] == "ignored"
    assert res["reason"] == "duplicate"


@pytest.mark.asyncio
async def test_short_zone_tp_below_entry():
    res = await handle_event(
        _payload(direction="short", entry=20000.0, sl=20005.0, id="short-1")
    )
    assert res["action"] == "armed"
    assert res["tp"] == 19985.0  # 20000 - 3*5
