from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AlertPayload(BaseModel):
    symbol: str
    tf: str
    event: Literal["new_zone", "mitigated", "invalidated"]
    id: str
    direction: Literal["long", "short"]
    entry: float
    sl: float
    ts: int
    secret: str = Field(repr=False)
