from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Fill, Zone

ET = ZoneInfo("America/New_York")


@dataclass
class Decision:
    allow: bool
    reason: str | None = None


def in_session(now_utc: datetime | None = None) -> bool:
    """Futures session: Sun 18:00 ET → Fri 17:00 ET, exclude daily 17:00–18:00 maintenance."""
    now = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    wd = now.weekday()  # Mon=0 .. Sun=6
    hh = now.hour
    if wd == 5:  # Saturday — closed all day
        return False
    if wd == 6:  # Sunday — open from 18:00 ET
        return hh >= 18
    if wd == 4 and hh >= 17:  # Friday after 17:00 ET
        return False
    # Mon–Fri: closed during the 17:00–18:00 maintenance window every day
    if hh == 17:
        return False
    return True


def _et_session_start(now_utc: datetime | None = None) -> datetime:
    """Return the start of the *current* trading day in ET (18:00 prior calendar day)."""
    now = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    anchor = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now.hour < 18:
        anchor -= timedelta(days=1)
    return anchor.astimezone(ZoneInfo("UTC"))


def daily_pnl(session: Session, now_utc: datetime | None = None) -> float:
    start = _et_session_start(now_utc)
    total = session.execute(
        select(func.coalesce(func.sum(Fill.pnl_usd), 0.0)).where(Fill.ts >= start)
    ).scalar_one()
    return float(total or 0.0)


def allow_new(session: Session, now_utc: datetime | None = None) -> Decision:
    if not in_session(now_utc):
        return Decision(False, "outside_session")

    pnl = daily_pnl(session, now_utc)
    if pnl <= -abs(settings.daily_loss_limit_usd):
        return Decision(False, "daily_loss_limit")

    armed = session.execute(
        select(func.count()).select_from(Zone).where(Zone.status == "armed")
    ).scalar_one()
    if armed >= settings.max_armed_orders:
        return Decision(False, "max_armed_orders")

    open_positions = session.execute(
        select(func.count()).select_from(Zone).where(Zone.status == "filled")
    ).scalar_one()
    if open_positions >= settings.max_concurrent_positions:
        return Decision(False, "max_concurrent_positions")

    return Decision(True)
