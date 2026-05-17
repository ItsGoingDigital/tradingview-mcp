from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

engine = create_engine(f"sqlite:///{settings.db_path}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init() -> None:
    Base.metadata.create_all(engine)
    _apply_migrations()


def _apply_migrations() -> None:
    """Idempotent column additions for SQLite. Safe to run on every startup."""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(zones)"))}
        if "source" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE zones ADD COLUMN source TEXT NOT NULL DEFAULT 'mnq_sd'"
                )
            )


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
