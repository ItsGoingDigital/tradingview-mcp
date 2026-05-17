from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SBAlertPayload(BaseModel):
    """Pine alerter emits one of these on every event.

    `new_signal` is fired at the MSS confirmation bar's close when a same-direction
    Super-Strict FVG was created on an earlier bar.

    `cancel` is fired when the FVG used as SL was super-strict-invalidated before
    our entry stop filled. For cancels, `entry` and `sl` may be na in the JSON;
    Optional here for permissive parsing.
    """

    symbol: str
    tf: str
    event: Literal["new_signal", "cancel"]
    id: str
    direction: Literal["long", "short"]
    entry: Optional[float] = None
    sl: Optional[float] = None
    ts: int
    secret: str = Field(repr=False)
