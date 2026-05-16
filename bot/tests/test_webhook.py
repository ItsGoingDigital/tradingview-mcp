import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from service.main import app

    return TestClient(app)


def _body(**overrides) -> dict:
    base = dict(
        symbol="CME_MINI:MNQ1!",
        tf="240",
        event="new_zone",
        id="webhook-1",
        direction="long",
        entry=20000.0,
        sl=19995.0,
        ts=1700000000,
        secret="test-secret",
    )
    base.update(overrides)
    return base


def test_webhook_accepts_payload_secret(client):
    r = client.post("/webhook/tradingview", json=_body())
    assert r.status_code == 200
    assert r.json()["accepted"] is True


def test_webhook_rejects_bad_secret(client):
    r = client.post("/webhook/tradingview", json=_body(secret="wrong"))
    assert r.status_code == 401


def test_webhook_accepts_hmac_header(client):
    body = json.dumps(_body(secret="")).encode()
    sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    r = client.post(
        "/webhook/tradingview",
        content=body,
        headers={"X-Bot-Signature": sig, "content-type": "application/json"},
    )
    assert r.status_code == 200


def test_webhook_rejects_bad_json(client):
    r = client.post(
        "/webhook/tradingview",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
