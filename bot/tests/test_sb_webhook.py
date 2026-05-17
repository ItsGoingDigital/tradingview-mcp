from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _force_open_window(monkeypatch):
    monkeypatch.setattr(
        "service.silverbullet.guardrails.in_sb_window", lambda *a, **k: True
    )


@pytest.fixture
def client():
    from service.main import app

    return TestClient(app)


def _body(**overrides):
    base = dict(
        symbol="CME_MINI:MNQ1!",
        tf="1",
        event="new_signal",
        id="sb-wh-1",
        direction="long",
        entry=20010.0,
        sl=20000.0,
        ts=1700000000,
        secret="test-secret",
    )
    base.update(overrides)
    return base


def test_sb_webhook_accepts_payload_secret(client):
    r = client.post("/webhook/silverbullet", json=_body())
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["event"] == "new_signal"


def test_sb_webhook_rejects_bad_secret(client):
    r = client.post("/webhook/silverbullet", json=_body(secret="wrong"))
    assert r.status_code == 401


def test_sb_webhook_rejects_invalid_payload(client):
    bad = _body()
    bad["event"] = "garbage_event"
    r = client.post("/webhook/silverbullet", json=bad)
    assert r.status_code == 400


def test_sb_and_mnq_endpoints_coexist(client):
    """Both /webhook/tradingview and /webhook/silverbullet should accept their own payloads."""
    sb = client.post("/webhook/silverbullet", json=_body(id="coexist-sb"))
    assert sb.status_code == 200
    mnq = client.post(
        "/webhook/tradingview",
        json={
            "symbol": "CME_MINI:MNQ1!",
            "tf": "240",
            "event": "new_zone",
            "id": "coexist-mnq",
            "direction": "long",
            "entry": 20000.0,
            "sl": 19995.0,
            "ts": 1700000000,
            "secret": "test-secret",
        },
    )
    assert mnq.status_code == 200
