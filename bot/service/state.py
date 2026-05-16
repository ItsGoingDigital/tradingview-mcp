from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from .config import settings
from .db import get_session
from .models import Fill, Order, Zone

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "dry_run": settings.dry_run,
        "tradovate_env": settings.tradovate_env,
    }


@router.get("/state")
def state() -> dict:
    with get_session() as s:
        zones = s.execute(
            select(Zone).where(Zone.status.in_(("armed", "filled", "skipped")))
        ).scalars().all()
        orders = s.execute(
            select(Order).where(Order.status == "working")
        ).scalars().all()
        recent_fills = s.execute(
            select(Fill).order_by(Fill.ts.desc()).limit(20)
        ).scalars().all()

        return {
            "zones": [
                {
                    "id": z.id,
                    "symbol": z.symbol,
                    "direction": z.direction,
                    "entry": z.entry,
                    "sl": z.sl,
                    "tp": z.tp,
                    "contracts": z.contracts,
                    "status": z.status,
                    "created_at": z.created_at.isoformat(),
                }
                for z in zones
            ],
            "orders": [
                {
                    "id": o.id,
                    "tradovate_order_id": o.tradovate_order_id,
                    "zone_id": o.zone_id,
                    "kind": o.kind,
                    "status": o.status,
                    "price": o.price,
                    "qty": o.qty,
                }
                for o in orders
            ],
            "recent_fills": [
                {
                    "zone_id": f.zone_id,
                    "side": f.side,
                    "qty": f.qty,
                    "price": f.price,
                    "ts": f.ts.isoformat(),
                    "pnl_usd": f.pnl_usd,
                }
                for f in recent_fills
            ],
        }
