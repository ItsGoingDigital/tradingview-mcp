from datetime import datetime
from zoneinfo import ZoneInfo

from service.guardrails import in_session


def _et(dt: str) -> datetime:
    return datetime.fromisoformat(dt).replace(tzinfo=ZoneInfo("America/New_York")).astimezone(
        ZoneInfo("UTC")
    )


def test_session_open_monday_morning():
    assert in_session(_et("2026-05-18T09:30:00")) is True


def test_session_closed_saturday():
    assert in_session(_et("2026-05-16T12:00:00")) is False


def test_session_closed_sunday_morning():
    assert in_session(_et("2026-05-17T12:00:00")) is False


def test_session_open_sunday_evening():
    assert in_session(_et("2026-05-17T19:00:00")) is True


def test_session_closed_friday_evening():
    assert in_session(_et("2026-05-22T18:30:00")) is False


def test_session_closed_in_maintenance_window():
    assert in_session(_et("2026-05-19T17:30:00")) is False
