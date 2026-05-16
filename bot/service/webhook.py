from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from .auth import verify_payload_secret, verify_signature
from .lifecycle import handle_event
from .logging import log
from .schemas import AlertPayload

router = APIRouter()


@router.post("/webhook/tradingview")
async def tradingview_webhook(
    request: Request,
    background: BackgroundTasks,
    x_bot_signature: str | None = Header(default=None, alias="X-Bot-Signature"),
):
    body = await request.body()

    # Accept either header HMAC or embedded `secret` in the JSON payload.
    # TradingView free/standard plans can't send custom headers, so payload-secret is the practical default.
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="invalid_json") from e

    header_ok = verify_signature(body, x_bot_signature) if x_bot_signature else False
    payload_secret = data.get("secret", "")
    payload_ok = bool(payload_secret) and verify_payload_secret(payload_secret)
    if not (header_ok or payload_ok):
        log.warning("auth_failed", header_present=bool(x_bot_signature))
        raise HTTPException(status_code=401, detail="bad_signature")

    try:
        payload = AlertPayload(**data)
    except Exception as e:
        log.warning("invalid_payload", error=str(e))
        raise HTTPException(status_code=400, detail="invalid_payload") from e

    log.info(
        "alert_received",
        event_kind=payload.event,
        id=payload.id,
        direction=payload.direction,
        entry=payload.entry,
        sl=payload.sl,
    )
    # Offload the work — return 200 fast so TradingView doesn't time out.
    background.add_task(_safe_handle, payload)
    return {"accepted": True, "id": payload.id, "event": payload.event}


async def _safe_handle(payload: AlertPayload) -> None:
    try:
        await handle_event(payload)
    except Exception:
        log.exception("handler_error", id=payload.id, event_kind=payload.event)
