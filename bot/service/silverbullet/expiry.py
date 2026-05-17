from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..config import settings
from ..db import get_session
from ..logging import log
from ..models import Order, Zone

ET = ZoneInfo("America/New_York")
SOURCE = "silverbullet"


async def run() -> None:
    """Background task: every 30s, force-cancel any armed SB zones after window close.

    Also runs once on startup to reconcile any orphans left over from a crash
    before the previous day's expiry tick.
    """
    log.info("sb_expiry_task_started")
    await _sweep()  # startup reconcile
    while True:
        await asyncio.sleep(settings.sb_expiry_tick_sec)
        try:
            await _sweep()
        except Exception:
            log.exception("sb_expiry_sweep_error")


async def _sweep(now_utc: datetime | None = None) -> int:
    """Cancel any armed SB orders whose creation day's window has ended.

    Returns number of zones expired (for tests).
    """
    now = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    end_hh, end_mm = settings.sb_window_end_hhmm.split(":")
    end_today = now.replace(
        hour=int(end_hh), minute=int(end_mm), second=0, microsecond=0
    )

    expired = 0
    with get_session() as s:
        zones = (
            s.execute(
                select(Zone).where(
                    Zone.source == SOURCE,
                    Zone.status == "armed",
                )
            )
            .scalars()
            .all()
        )
        for zone in zones:
            zone_et = zone.created_at.astimezone(ET) if zone.created_at.tzinfo else zone.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ET)
            zone_end = zone_et.replace(
                hour=int(end_hh), minute=int(end_mm), second=0, microsecond=0
            )
            if now >= zone_end:
                await _expire_zone(s, zone)
                expired += 1
    if expired:
        log.info("sb_expired_armed_zones", count=expired)
    return expired


async def _expire_zone(session, zone: Zone) -> None:
    entry_order = session.execute(
        select(Order).where(Order.zone_id == zone.id, Order.kind == "entry")
    ).scalar_one_or_none()
    if not settings.dry_run and entry_order and entry_order.tradovate_order_id:
        try:
            from ..tradovate.client import get_client

            client = await get_client()
            await client.cancel_order(entry_order.tradovate_order_id)
            entry_order.status = "cancelled"
        except Exception:
            log.exception("sb_expire_cancel_failed", id=zone.id)
    zone.status = "expired"
    log.info("sb_zone_expired", id=zone.id)
