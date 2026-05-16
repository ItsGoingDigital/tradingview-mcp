from __future__ import annotations

from sqlalchemy import select

from .config import settings
from .db import get_session
from .guardrails import allow_new
from .logging import log
from .models import Order, Zone
from .schemas import AlertPayload
from .sizing import compute_risk_pts, compute_tp, contracts_for, round_to_tick


async def handle_event(payload: AlertPayload) -> dict:
    """Top-level dispatcher. Returns a dict describing the action taken (for /state debug)."""
    if payload.event == "new_zone":
        return await _on_new_zone(payload)
    if payload.event in ("mitigated", "invalidated"):
        return await _on_mitigated(payload)
    return {"action": "ignored", "reason": f"unknown_event:{payload.event}"}


async def _on_new_zone(payload: AlertPayload) -> dict:
    risk_pts = compute_risk_pts(payload.entry, payload.sl)
    if risk_pts <= 0:
        log.warning("rejected", reason="zero_risk", id=payload.id)
        return {"action": "skipped", "reason": "zero_risk"}

    entry = round_to_tick(payload.entry)
    sl = round_to_tick(payload.sl)
    tp = compute_tp(entry, sl)
    contracts = contracts_for(risk_pts)

    with get_session() as s:
        # Idempotency: a duplicate alert for the same zone id is a no-op.
        if s.get(Zone, payload.id):
            log.info("duplicate_new_zone", id=payload.id)
            return {"action": "ignored", "reason": "duplicate"}

        if contracts < 1:
            zone = Zone(
                id=payload.id,
                symbol=payload.symbol,
                tf=payload.tf,
                direction=payload.direction,
                entry=entry,
                sl=sl,
                risk_pts=risk_pts,
                tp=tp,
                contracts=0,
                status="skipped",
            )
            s.add(zone)
            log.warning(
                "skipped_wide_zone",
                id=payload.id,
                risk_pts=risk_pts,
                risk_usd=settings.risk_per_trade_usd,
            )
            return {"action": "skipped", "reason": "wide_zone"}

        if settings.bypass_guardrails:
            log.warning("guardrails_bypassed", id=payload.id)
            decision = type("D", (), {"allow": True, "reason": None})()
        else:
            decision = allow_new(s)
        if not decision.allow:
            zone = Zone(
                id=payload.id,
                symbol=payload.symbol,
                tf=payload.tf,
                direction=payload.direction,
                entry=entry,
                sl=sl,
                risk_pts=risk_pts,
                tp=tp,
                contracts=contracts,
                status="skipped",
            )
            s.add(zone)
            log.warning("rejected", reason=decision.reason, id=payload.id)
            return {"action": "skipped", "reason": decision.reason}

        zone = Zone(
            id=payload.id,
            symbol=payload.symbol,
            tf=payload.tf,
            direction=payload.direction,
            entry=entry,
            sl=sl,
            risk_pts=risk_pts,
            tp=tp,
            contracts=contracts,
            status="armed",
        )
        s.add(zone)
        s.flush()

        if settings.dry_run:
            log.info(
                "dry_run_place_order",
                id=payload.id,
                direction=payload.direction,
                entry=entry,
                sl=sl,
                tp=tp,
                contracts=contracts,
            )
            return {
                "action": "armed",
                "dry_run": True,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "contracts": contracts,
            }

        # Live order placement is wired in Phase 3 via tradovate.client.place_oso.
        # Importing lazily so dry-run doesn't require live deps to be configured.
        from .tradovate.client import get_client
        from .tradovate.payloads import build_oso

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
            use_gtc=settings.tif_override_gtc,
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
        log.info("placed_oso", id=payload.id, response=response)
        return {"action": "armed", "response": response}


async def _on_mitigated(payload: AlertPayload) -> dict:
    with get_session() as s:
        zone = s.get(Zone, payload.id)
        if not zone:
            log.info("mitigation_for_unknown_zone", id=payload.id)
            return {"action": "ignored", "reason": "unknown_zone"}

        if zone.status == "armed":
            entry_order = s.execute(
                select(Order).where(Order.zone_id == zone.id, Order.kind == "entry")
            ).scalar_one_or_none()
            if not settings.dry_run and entry_order and entry_order.tradovate_order_id:
                from .tradovate.client import get_client

                client = await get_client()
                await client.cancel_order(entry_order.tradovate_order_id)
                entry_order.status = "cancelled"
            zone.status = "mitigated"
            log.info("zone_mitigated_before_fill", id=zone.id)
            return {"action": "cancelled", "id": zone.id}

        if zone.status == "filled":
            zone.status = "mitigated_after_fill"
            log.info("zone_mitigated_after_fill", id=zone.id)
            return {"action": "noted_after_fill", "id": zone.id}

        log.info("mitigation_in_terminal_state", id=zone.id, status=zone.status)
        return {"action": "ignored", "reason": f"status:{zone.status}"}


def _extract_order_ids(response: dict, entry: float, sl: float, tp: float):
    """Tradovate placeOSO returns {orderId, oso1Id, oso2Id} (or similar). Map to (kind, price, oid)."""
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
