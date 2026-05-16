"""MCP-driven zone poller.

Calls `data_get_structure_zones` every N seconds on the user's live LuxAlgo chart,
diffs against the DB, and fires the lifecycle handler for new and mitigated zones.

The chart MUST be:
  - on a symbol containing `CHART_SYMBOL_MATCH` (default "MNQ")
  - on `CHART_TIMEFRAME` (default "240" = 4h)

If those don't match at poll time, we skip the cycle and log a warning (the user
might be doing manual analysis on another symbol/TF).
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from .config import settings
from .db import get_session
from .guardrails import in_session
from .lifecycle import handle_event
from .logging import log
from .mcp_client import MCPError, get_mcp
from .models import Zone
from .schemas import AlertPayload

# Statuses considered "live" — bot still cares about them.
LIVE_STATUSES = {"armed", "filled"}


def zone_id(symbol: str, direction: str, entry: float, sl: float) -> str:
    """Stable id derived from zone geometry. Survives chart reloads."""
    return f"{symbol}|{direction}|{round(entry, 2)}|{round(sl, 2)}"


async def run() -> None:
    log.info("poller_started", interval_sec=settings.poll_interval_sec)
    while True:
        try:
            await _tick()
        except Exception:
            log.exception("poller_tick_error")
        await asyncio.sleep(settings.poll_interval_sec)


async def _tick() -> None:
    if not in_session():
        log.debug("poller_skipped_outside_session")
        return

    mcp = await get_mcp()

    # Sanity-check chart state before trusting zones.
    try:
        state = await mcp.call_tool("chart_get_state", {})
    except MCPError as e:
        log.warning("mcp_chart_get_state_failed", error=str(e))
        return

    sym = (state.get("symbol") or state.get("ticker") or "").upper()
    tf = str(state.get("timeframe") or state.get("resolution") or "")
    if settings.chart_symbol_match.upper() not in sym:
        log.warning("poller_chart_symbol_mismatch", symbol=sym, want=settings.chart_symbol_match)
        return
    if tf != settings.chart_timeframe:
        log.warning("poller_chart_tf_mismatch", tf=tf, want=settings.chart_timeframe)
        return

    try:
        result = await mcp.call_tool(
            "data_get_structure_zones",
            {
                "study_filter": "Market Structure",
                "within_points": settings.zone_within_points,
                "include_mitigated": False,
            },
        )
    except MCPError as e:
        log.warning("mcp_zones_failed", error=str(e))
        return

    raw_zones = result.get("zones") or []
    seen_ids: set[str] = set()

    for z in raw_zones:
        direction = "long" if z.get("zone_type") == "demand" or z.get("direction") == "bullish" else "short"
        entry = float(z["entry"])
        sl = float(z["sl"])
        zid = zone_id(sym, direction, entry, sl)
        seen_ids.add(zid)

        with get_session() as s:
            existing = s.get(Zone, zid)
            already_known = existing is not None

        if already_known:
            continue  # nothing to do

        payload = AlertPayload(
            symbol=sym,
            tf=tf,
            event="new_zone",
            id=zid,
            direction=direction,
            entry=entry,
            sl=sl,
            ts=0,
            secret="",  # internal call; bypasses webhook auth
        )
        log.info("poller_new_zone", id=zid, direction=direction, entry=entry, sl=sl)
        await handle_event(payload)

    # Disappearance = mitigation. Any LIVE zone we previously tracked that's
    # no longer in this poll (and was within the same scan window) → mitigated.
    with get_session() as s:
        live = s.execute(select(Zone).where(Zone.status.in_(LIVE_STATUSES))).scalars().all()
        candidates = [z for z in live if z.id.startswith(f"{sym}|")]

    for db_zone in candidates:
        if db_zone.id in seen_ids:
            continue
        payload = AlertPayload(
            symbol=db_zone.symbol,
            tf=db_zone.tf,
            event="mitigated",
            id=db_zone.id,
            direction=db_zone.direction,
            entry=db_zone.entry,
            sl=db_zone.sl,
            ts=0,
            secret="",
        )
        log.info("poller_mitigation", id=db_zone.id, status=db_zone.status)
        await handle_event(payload)
