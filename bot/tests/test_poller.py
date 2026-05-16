from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from service import poller
from service.db import get_session
from service.models import Zone


@pytest.fixture(autouse=True)
def _force_in_session(monkeypatch):
    monkeypatch.setattr("service.poller.in_session", lambda *a, **k: True)


def _mcp_returning(chart: dict, zones: list[dict]):
    """Return an AsyncMock MCP client that responds to chart_get_state then data_get_structure_zones."""

    async def call_tool(name, args=None):
        if name == "chart_get_state":
            return chart
        if name == "data_get_structure_zones":
            return {"zones": zones}
        return {}

    mock = AsyncMock()
    mock.call_tool = AsyncMock(side_effect=call_tool)
    return mock


@pytest.mark.asyncio
async def test_poller_inserts_new_zone(monkeypatch):
    monkeypatch.setattr("service.guardrails.in_session", lambda *a, **k: True)
    mock_mcp = _mcp_returning(
        chart={"symbol": "CME_MINI:MNQ1!", "timeframe": "240"},
        zones=[
            {
                "entry": 20000.0,
                "sl": 19995.0,
                "zone_type": "demand",
                "direction": "bullish",
                "mitigated": False,
            }
        ],
    )
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock_mcp))

    await poller._tick()

    with get_session() as s:
        zones = s.query(Zone).all()
        assert len(zones) == 1
        assert zones[0].direction == "long"
        assert zones[0].entry == 20000.0
        assert zones[0].status == "armed"


@pytest.mark.asyncio
async def test_poller_skips_wrong_symbol(monkeypatch):
    mock_mcp = _mcp_returning(
        chart={"symbol": "CME_MINI:MES1!", "timeframe": "240"}, zones=[]
    )
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock_mcp))

    await poller._tick()

    with get_session() as s:
        assert s.query(Zone).count() == 0


@pytest.mark.asyncio
async def test_poller_skips_wrong_timeframe(monkeypatch):
    mock_mcp = _mcp_returning(
        chart={"symbol": "CME_MINI:MNQ1!", "timeframe": "15"}, zones=[]
    )
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock_mcp))

    await poller._tick()

    with get_session() as s:
        assert s.query(Zone).count() == 0


@pytest.mark.asyncio
async def test_poller_detects_mitigation(monkeypatch):
    monkeypatch.setattr("service.guardrails.in_session", lambda *a, **k: True)

    # Tick 1 — zone appears.
    mock1 = _mcp_returning(
        chart={"symbol": "CME_MINI:MNQ1!", "timeframe": "240"},
        zones=[
            {
                "entry": 20000.0,
                "sl": 19995.0,
                "zone_type": "demand",
                "direction": "bullish",
                "mitigated": False,
            }
        ],
    )
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock1))
    await poller._tick()

    # Tick 2 — zone disappears (mitigated by LuxAlgo).
    mock2 = _mcp_returning(chart={"symbol": "CME_MINI:MNQ1!", "timeframe": "240"}, zones=[])
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock2))
    await poller._tick()

    with get_session() as s:
        zones = s.query(Zone).all()
        assert len(zones) == 1
        assert zones[0].status == "mitigated"


@pytest.mark.asyncio
async def test_poller_idempotent_same_zone(monkeypatch):
    monkeypatch.setattr("service.guardrails.in_session", lambda *a, **k: True)
    mock_mcp = _mcp_returning(
        chart={"symbol": "CME_MINI:MNQ1!", "timeframe": "240"},
        zones=[
            {
                "entry": 20000.0,
                "sl": 19995.0,
                "zone_type": "demand",
                "direction": "bullish",
                "mitigated": False,
            }
        ],
    )
    monkeypatch.setattr("service.poller.get_mcp", AsyncMock(return_value=mock_mcp))

    await poller._tick()
    await poller._tick()  # same zone, should be no-op

    with get_session() as s:
        zones = s.query(Zone).all()
        assert len(zones) == 1
