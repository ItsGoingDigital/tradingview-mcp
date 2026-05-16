from __future__ import annotations

import math

from .config import settings


def round_to_tick(price: float, tick: float = 0.25) -> float:
    return round(round(price / tick) * tick, 4)


def compute_risk_pts(entry: float, sl: float) -> float:
    return abs(entry - sl)


def compute_tp(entry: float, sl: float, r_multiple: float = 3.0) -> float:
    risk = compute_risk_pts(entry, sl)
    return round_to_tick(entry + r_multiple * risk if entry > sl else entry - r_multiple * risk)


def contracts_for(
    risk_pts: float,
    risk_usd: float | None = None,
    pt_val: float | None = None,
) -> int:
    """Floor(risk_usd / (risk_pts × $/pt)). Returns 0 when zone is too wide for the budget."""
    if risk_pts <= 0:
        return 0
    r_usd = risk_usd if risk_usd is not None else settings.risk_per_trade_usd
    pv = pt_val if pt_val is not None else settings.mnq_point_value
    return math.floor(r_usd / (risk_pts * pv))
