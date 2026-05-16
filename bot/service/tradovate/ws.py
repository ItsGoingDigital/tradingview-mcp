from __future__ import annotations

"""Tradovate WebSocket listener — Phase 4. Wired but not yet started by main.py."""

import asyncio
import json

import websockets

from ..config import settings
from ..db import get_session
from ..logging import log
from ..models import Fill, Order, Zone
from .client import get_client


async def run() -> None:
    """Long-running task. Subscribes to user order/fill events on the trading WS."""
    backoff = 1.0
    while True:
        try:
            await _connect_and_loop()
            backoff = 1.0
        except Exception as e:
            log.warning("ws_disconnected", error=str(e), retry_in_s=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


async def _connect_and_loop() -> None:
    client = await get_client()
    token = await client._ensure_token()  # noqa: SLF001
    async with websockets.connect(settings.tradovate_ws_url) as ws:
        # Tradovate framing: "<endpoint>\n<request_id>\n<query>\n<body>"
        await ws.send(f"authorize\n0\n\n{token}")
        await ws.send(
            f"user/syncrequest\n1\n\n"
            + json.dumps({"users": [settings.tradovate_account_id]})
        )
        # Periodic reconcile on connect
        await _reconcile_orders()

        async for raw in ws:
            await _handle_frame(raw)


async def _reconcile_orders() -> None:
    try:
        client = await get_client()
        live_orders = await client.list_orders()
        live_by_id = {o["id"]: o for o in live_orders}
        with get_session() as s:
            for db_order in s.query(Order).filter(Order.status == "working").all():
                if db_order.tradovate_order_id and db_order.tradovate_order_id not in live_by_id:
                    db_order.status = "cancelled"  # disappeared upstream
    except Exception:
        log.exception("reconcile_failed")


async def _handle_frame(raw: str) -> None:
    # First char is the frame type per Tradovate framing.
    if not raw or raw[0] != "a":
        return
    try:
        body = json.loads(raw[1:])
    except Exception:
        return
    for evt in body:
        ent = evt.get("e")
        d = evt.get("d") or {}
        if ent == "order":
            _on_order_event(d)
        elif ent == "fill":
            _on_fill_event(d)


def _on_order_event(d: dict) -> None:
    oid = d.get("id")
    status = (d.get("ordStatus") or "").lower()
    if not oid:
        return
    with get_session() as s:
        order = s.query(Order).filter(Order.tradovate_order_id == oid).one_or_none()
        if not order:
            return
        if status in ("filled", "cancelled", "rejected"):
            order.status = status
            if order.kind == "entry" and status == "filled":
                zone = s.get(Zone, order.zone_id)
                if zone and zone.status == "armed":
                    zone.status = "filled"


def _on_fill_event(d: dict) -> None:
    fid = d.get("id")
    oid = d.get("orderId")
    qty = d.get("qty")
    price = d.get("price")
    side = (d.get("action") or "").lower()
    if not (fid and oid):
        return
    with get_session() as s:
        order = s.query(Order).filter(Order.tradovate_order_id == oid).one_or_none()
        if not order:
            return
        zone = s.get(Zone, order.zone_id)
        if not zone:
            return
        pnl = None
        # If this fill closes a position (stop or target), compute PnL vs the entry fill.
        if order.kind in ("stop", "target"):
            entry_fill = (
                s.query(Fill)
                .filter(Fill.zone_id == zone.id)
                .order_by(Fill.ts.asc())
                .first()
            )
            if entry_fill and price is not None and qty is not None:
                # Long: pnl = (close - entry) * qty * pt_val. Short: inverse.
                direction_mult = 1 if zone.direction == "long" else -1
                pnl = (price - entry_fill.price) * qty * settings.mnq_point_value * direction_mult
            zone.status = "closed" if zone.status != "mitigated_after_fill" else "closed"
        s.add(
            Fill(
                tradovate_fill_id=fid,
                zone_id=zone.id,
                side=side or ("buy" if zone.direction == "long" else "sell"),
                qty=qty or 0,
                price=price or 0.0,
                pnl_usd=pnl,
            )
        )


# Lazy settings import to avoid circular at module load
from ..config import settings  # noqa: E402
