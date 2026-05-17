from __future__ import annotations

from sqlalchemy import select

from ..config import settings
from ..db import get_session
from ..logging import log
from ..models import Order, Zone
from ..sizing import compute_risk_pts, compute_tp, contracts_for, round_to_tick
from .guardrails import allow_new
from .schemas import SBAlertPayload

SOURCE = "silverbullet"
SB_R_MULTIPLE = 2.0


async def handle_event(payload: SBAlertPayload) -> dict:
    if payload.event == "new_signal":
        return await _on_new_signal(payload)
    if payload.event == "cancel":
        return await _on_cancel(payload)
    return {"action": "ignored", "reason": f"unknown_event:{payload.event}"}


async def _on_new_signal(payload: SBAlertPayload) -> dict:
    if payload.entry is None or payload.sl is None:
        log.warning("sb_missing_levels", id=payload.id)
        return {"action": "skipped", "reason": "missing_levels"}

    risk_pts = compute_risk_pts(payload.entry, payload.sl)
    if risk_pts <= 0:
        log.warning("sb_rejected", reason="zero_risk", id=payload.id)
        return {"action": "skipped", "reason": "zero_risk"}

    entry = round_to_tick(payload.entry)
    sl = round_to_tick(payload.sl)
    tp = compute_tp(entry, sl, r_multiple=SB_R_MULTIPLE)
    contracts = contracts_for(risk_pts)

    with get_session() as s:
        if s.get(Zone, payload.id):
            log.info("sb_duplicate_signal", id=payload.id)
            return {"action": "ignored", "reason": "duplicate"}

        if contracts < 1:
            s.add(_zone(payload, entry, sl, risk_pts, tp, 0, "skipped"))
            log.warning(
                "sb_skipped_wide_zone",
                id=payload.id,
                risk_pts=risk_pts,
                risk_usd=settings.risk_per_trade_usd,
            )
            return {"action": "skipped", "reason": "wide_zone"}

        decision = allow_new(s)
        if not decision.allow:
            s.add(_zone(payload, entry, sl, risk_pts, tp, contracts, "skipped"))
            log.warning("sb_rejected", reason=decision.reason, id=payload.id)
            return {"action": "skipped", "reason": decision.reason}

        zone = _zone(payload, entry, sl, risk_pts, tp, contracts, "armed")
        s.add(zone)
        s.flush()

        if settings.dry_run:
            log.info(
                "sb_dry_run_place_order",
                id=payload.id,
                direction=payload.direction,
                entry=entry,
                sl=sl,
                tp=tp,
                contracts=contracts,
                parent="Stop",
            )
            return {
                "action": "armed",
                "dry_run": True,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "contracts": contracts,
            }

        from ..tradovate.client import get_client
        from ..tradovate.payloads import build_oso

        client = await get_client()
        oso = build_oso(
            symbol=payload.symbol,
            direction=payload.direction,
            entry=entry,
            sl=sl,
            tp=tp,
            qty=contracts,
            account_id=settings.tradovate_account_id,
            account_spec=settings.tradovate_username,
            use_gtc=False,  # SB always Day TIF — window closes at 11:15 ET
            parent_order_type="Stop",
        )
        response = await client.place_oso(oso)
        for kind, price, oid in _extract_order_ids(response, entry, sl, tp):
            s.add(
                Order(
                    tradovate_order_id=oid,
                    zone_id=zone.id,
                    kind=kind,
                    status="working",
                    price=price,
                    qty=contracts,
                )
            )
        log.info("sb_placed_oso", id=payload.id, response=response)
        return {"action": "armed", "response": response}


async def _on_cancel(payload: SBAlertPayload) -> dict:
    """FVG used as SL got super-strict-invalidated before we filled — pull the entry."""
    with get_session() as s:
        zone = s.get(Zone, payload.id)
        if not zone:
            log.info("sb_cancel_unknown_zone", id=payload.id)
            return {"action": "ignored", "reason": "unknown_zone"}
        if zone.status != "armed":
            log.info("sb_cancel_terminal_state", id=zone.id, status=zone.status)
            return {"action": "ignored", "reason": f"status:{zone.status}"}

        entry_order = s.execute(
            select(Order).where(Order.zone_id == zone.id, Order.kind == "entry")
        ).scalar_one_or_none()
        if not settings.dry_run and entry_order and entry_order.tradovate_order_id:
            from ..tradovate.client import get_client

            client = await get_client()
            await client.cancel_order(entry_order.tradovate_order_id)
            entry_order.status = "cancelled"
        zone.status = "cancelled"
        log.info("sb_zone_cancelled_pre_fill", id=zone.id)
        return {"action": "cancelled", "id": zone.id}


def _zone(
    payload: SBAlertPayload,
    entry: float,
    sl: float,
    risk_pts: float,
    tp: float,
    contracts: int,
    status: str,
) -> Zone:
    return Zone(
        id=payload.id,
        source=SOURCE,
        symbol=payload.symbol,
        tf=payload.tf,
        direction=payload.direction,
        entry=entry,
        sl=sl,
        risk_pts=risk_pts,
        tp=tp,
        contracts=contracts,
        status=status,
    )


def _extract_order_ids(response: dict, entry: float, sl: float, tp: float):
    parent = response.get("orderId")
    b1 = response.get("oso1Id") or response.get("bracket1Id")
    b2 = response.get("oso2Id") or response.get("bracket2Id")
    out = []
    if parent:
        out.append(("entry", entry, parent))
    if b1:
        out.append(("stop", sl, b1))
    if b2:
        out.append(("target", tp, b2))
    return out
