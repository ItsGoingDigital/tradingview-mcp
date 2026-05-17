from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from ..auth import verify_payload_secret, verify_signature
from ..logging import log
from .lifecycle import handle_event
from .schemas import SBAlertPayload

router = APIRouter()


@router.post("/webhook/silverbullet")
async def silverbullet_webhook(
    request: Request,
    background: BackgroundTasks,
    x_bot_signature: str | None = Header(default=None, alias="X-Bot-Signature"),
):
    body = await request.body()
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="invalid_json") from e

    header_ok = verify_signature(body, x_bot_signature) if x_bot_signature else False
    payload_secret = data.get("secret", "")
    payload_ok = bool(payload_secret) and verify_payload_secret(payload_secret)
    if not (header_ok or payload_ok):
        log.warning("sb_auth_failed", header_present=bool(x_bot_signature))
        raise HTTPException(status_code=401, detail="bad_signature")

    try:
        payload = SBAlertPayload(**data)
    except Exception as e:
        log.warning("sb_invalid_payload", error=str(e))
        raise HTTPException(status_code=400, detail="invalid_payload") from e

    log.info(
        "sb_alert_received",
        event_kind=payload.event,
        id=payload.id,
        direction=payload.direction,
        entry=payload.entry,
        sl=payload.sl,
    )
    background.add_task(_safe_handle, payload)
    return {"accepted": True, "id": payload.id, "event": payload.event}


async def _safe_handle(payload: SBAlertPayload) -> None:
    try:
        await handle_event(payload)
    except Exception:
        log.exception("sb_handler_error", id=payload.id, event_kind=payload.event)
