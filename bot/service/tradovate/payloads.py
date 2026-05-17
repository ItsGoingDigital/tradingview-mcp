from __future__ import annotations

from ..sizing import round_to_tick


def build_oso(
    *,
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    qty: int,
    account_id: int,
    account_spec: str,
    use_gtc: bool = False,
    parent_order_type: str = "Limit",
) -> dict:
    """Tradovate placeOSO body. Parent order + OCO bracket (stop + limit-tp).

    `parent_order_type` is "Limit" (MNQ S&D bot — passive entry at zone edge) or
    "Stop" (Silver Bullet bot — breakout entry at MSS candle's high/low). When
    "Stop", Tradovate's payload uses `stopPrice` instead of `price` for the parent.

    Tradovate expects the explicit contract symbol (e.g. MNQM6), not the TradingView
    continuous notation (MNQ1!). Caller must resolve before calling this.
    """
    is_long = direction == "long"
    parent_action = "Buy" if is_long else "Sell"
    bracket_action = "Sell" if is_long else "Buy"
    tif = "GTC" if use_gtc else "Day"

    parent: dict = {
        "accountSpec": account_spec,
        "accountId": account_id,
        "action": parent_action,
        "symbol": symbol,
        "orderQty": qty,
        "orderType": parent_order_type,
        "timeInForce": tif,
        "isAutomated": True,
    }
    if parent_order_type == "Limit":
        parent["price"] = round_to_tick(entry)
    elif parent_order_type == "Stop":
        parent["stopPrice"] = round_to_tick(entry)
    else:
        raise ValueError(f"unsupported parent_order_type: {parent_order_type!r}")

    parent["bracket1"] = {
        "action": bracket_action,
        "orderType": "Stop",
        "stopPrice": round_to_tick(sl),
        "timeInForce": tif,
    }
    parent["bracket2"] = {
        "action": bracket_action,
        "orderType": "Limit",
        "price": round_to_tick(tp),
        "timeInForce": tif,
    }
    return parent
