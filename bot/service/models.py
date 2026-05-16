from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String)
    tf: Mapped[str] = mapped_column(String)
    direction: Mapped[str] = mapped_column(String)  # long | short
    entry: Mapped[float] = mapped_column(Float)
    sl: Mapped[float] = mapped_column(Float)
    risk_pts: Mapped[float] = mapped_column(Float)
    tp: Mapped[float] = mapped_column(Float)
    contracts: Mapped[int] = mapped_column(Integer)
    # armed | mitigated | invalidated | filled | mitigated_after_fill | closed | cancelled | error | skipped
    status: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="zone")
    fills: Mapped[list["Fill"]] = relationship(back_populates="zone")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tradovate_order_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    zone_id: Mapped[str] = mapped_column(String, ForeignKey("zones.id"))
    kind: Mapped[str] = mapped_column(String)  # entry | stop | target
    status: Mapped[str] = mapped_column(String)  # working | filled | cancelled | rejected
    price: Mapped[float] = mapped_column(Float)
    qty: Mapped[int] = mapped_column(Integer)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    zone: Mapped[Zone] = relationship(back_populates="orders")


class Fill(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tradovate_fill_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    zone_id: Mapped[str] = mapped_column(String, ForeignKey("zones.id"))
    side: Mapped[str] = mapped_column(String)  # buy | sell
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    pnl_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    zone: Mapped[Zone] = relationship(back_populates="fills")
