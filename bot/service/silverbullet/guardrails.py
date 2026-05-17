from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..guardrails import daily_pnl
from ..models import Zone

ET = ZoneInfo("America/New_York")


@dataclass
class Decision:
    allow: bool
    reason: str | None = None


def in_sb_window(now_utc: datetime | None = None) -> bool:
    """True iff current time is within the SB window on a weekday.

    Default window: 10:00:00 ≤ t < 11:15:00 ET, Mon–Fri.
    Configurable via SB_WINDOW_START_HHMM / SB_WINDOW_END_HHMM env vars.
    """
    now = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    if now.weekday() > 4:  # Sat/Sun
        return False
    start = _parse_hhmm(settings.sb_window_start_hhmm)
    end = _parse_hhmm(settings.sb_window_end_hhmm)
    cur = now.time()
    return start <= cur < end


def _parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(hour=int(hh), minute=int(mm))


def _today_session_start_utc(now_utc: datetime | None = None) -> datetime:
    """Return today's SB window start time as UTC."""
    now = (now_utc or datetime.now(tz=ZoneInfo("UTC"))).astimezone(ET)
    start = _parse_hhmm(settings.sb_window_start_hhmm)
    today_start_et = now.replace(
        hour=start.hour, minute=start.minute, second=0, microsecond=0
    )
    return today_start_et.astimezone(ZoneInfo("UTC"))


def already_traded_today(session: Session, now_utc: datetime | None = None) -> bool:
    """Has a SB zone already been created today? Used to enforce one-per-day.

    Any non-error status counts — even cancelled/skipped — because the slot is
    considered taken by the first valid setup attempt.
    """
    start = _today_session_start_utc(now_utc)
    cnt = session.execute(
        select(func.count())
        .select_from(Zone)
        .where(Zone.source == "silverbullet", Zone.created_at >= start)
    ).scalar_one()
    return int(cnt) >= 1


def allow_new(session: Session, now_utc: datetime | None = None) -> Decision:
    """Run all SB-specific guardrails. Returns Decision with first failure reason."""
    if settings.bypass_guardrails:
        return Decision(True)
    if not in_sb_window(now_utc):
        return Decision(False, "outside_sb_window")
    if already_traded_today(session, now_utc):
        return Decision(False, "already_traded_today")
    pnl = daily_pnl(session, now_utc)
    if pnl <= -abs(settings.daily_loss_limit_usd):
        return Decision(False, "daily_loss_limit")
    return Decision(True)
