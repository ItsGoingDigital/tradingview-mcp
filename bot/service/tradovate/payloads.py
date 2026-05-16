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
) -> dict:
    """Tradovate placeOSO body. Parent limit + OCO bracket (stop + limit-tp).

    Tradovate expects the explicit contract symbol (e.g. MNQM6), not the TradingView
    continuous notation (MNQ1!). Caller must resolve before calling this.
    """
    is_long = direction == "long"
    parent_action = "Buy" if is_long else "Sell"
    bracket_action = "Sell" if is_long else "Buy"
    tif = "GTC" if use_gtc else "Day"

    return {
        "accountSpec": account_spec,
        "accountId": account_id,
        "action": parent_action,
        "symbol": symbol,
        "orderQty": qty,
        "orderType": "Limit",
        "price": round_to_tick(entry),
        "timeInForce": tif,
        "isAutomated": True,
        "bracket1": {
            "action": bracket_action,
            "orderType": "Stop",
            "stopPrice": round_to_tick(sl),
            "timeInForce": tif,
        },
        "bracket2": {
            "action": bracket_action,
            "orderType": "Limit",
            "price": round_to_tick(tp),
            "timeInForce": tif,
        },
    }
