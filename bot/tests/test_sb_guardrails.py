from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from service.db import get_session
from service.models import Zone
from service.silverbullet.guardrails import (
    Decision,
    allow_new,
    already_traded_today,
    in_sb_window,
)


def _utc(dt_iso_et: str) -> datetime:
    return (
        datetime.fromisoformat(dt_iso_et)
        .replace(tzinfo=ZoneInfo("America/New_York"))
        .astimezone(ZoneInfo("UTC"))
    )


def test_window_open_at_1030_wed():
    assert in_sb_window(_utc("2026-05-20T10:30:00")) is True


def test_window_closed_before_1000():
    assert in_sb_window(_utc("2026-05-20T09:59:59")) is False


def test_window_closed_at_1115_exact():
    # End is exclusive
    assert in_sb_window(_utc("2026-05-20T11:15:00")) is False


def test_window_open_at_1114_59():
    assert in_sb_window(_utc("2026-05-20T11:14:59")) is True


def test_window_closed_on_saturday():
    assert in_sb_window(_utc("2026-05-23T10:30:00")) is False


def test_window_closed_on_sunday():
    assert in_sb_window(_utc("2026-05-24T10:30:00")) is False


def _make_zone(s, zid: str, status: str = "armed", created_at=None):
    z = Zone(
        id=zid,
        source="silverbullet",
        symbol="CME_MINI:MNQ1!",
        tf="1",
        direction="long",
        entry=20000.0,
        sl=19995.0,
        risk_pts=5.0,
        tp=20010.0,
        contracts=5,
        status=status,
    )
    if created_at is not None:
        z.created_at = created_at
        z.updated_at = created_at
    s.add(z)
    s.flush()
    return z


def test_already_traded_today_counts_armed():
    now_utc = _utc("2026-05-20T10:30:00")
    zone_created = _utc("2026-05-20T10:15:00")
    with get_session() as s:
        _make_zone(s, "sb-1", status="armed", created_at=zone_created)
    with get_session() as s:
        assert already_traded_today(s, now_utc) is True


def test_already_traded_today_counts_skipped():
    now_utc = _utc("2026-05-20T10:30:00")
    zone_created = _utc("2026-05-20T10:15:00")
    with get_session() as s:
        _make_zone(s, "sb-skip-1", status="skipped", created_at=zone_created)
    with get_session() as s:
        assert already_traded_today(s, now_utc) is True


def test_already_traded_today_false_when_empty():
    now_utc = _utc("2026-05-20T10:30:00")
    with get_session() as s:
        assert already_traded_today(s, now_utc) is False


def test_allow_new_blocks_outside_window(monkeypatch):
    now_utc = _utc("2026-05-20T09:00:00")  # before window
    monkeypatch.setattr(
        "service.silverbullet.guardrails.settings.bypass_guardrails", False
    )
    with get_session() as s:
        d: Decision = allow_new(s, now_utc)
    assert d.allow is False
    assert d.reason == "outside_sb_window"


def test_allow_new_blocks_after_first_trade(monkeypatch):
    now_utc = _utc("2026-05-20T10:30:00")
    zone_created = _utc("2026-05-20T10:15:00")
    monkeypatch.setattr(
        "service.silverbullet.guardrails.settings.bypass_guardrails", False
    )
    with get_session() as s:
        _make_zone(s, "sb-first", status="armed", created_at=zone_created)
    with get_session() as s:
        d = allow_new(s, now_utc)
    assert d.allow is False
    assert d.reason == "already_traded_today"


def test_allow_new_bypass_short_circuits(monkeypatch):
    now_utc = _utc("2026-05-23T10:30:00")  # Saturday — normally blocked
    monkeypatch.setattr(
        "service.silverbullet.guardrails.settings.bypass_guardrails", True
    )
    with get_session() as s:
        d = allow_new(s, now_utc)
    assert d.allow is True
