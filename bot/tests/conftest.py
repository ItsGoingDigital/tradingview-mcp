from __future__ import annotations

import os
import tempfile

import pytest

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()

# Set env BEFORE any service module imports.
os.environ["DB_PATH"] = _tmp_db.name
os.environ["WEBHOOK_SECRET"] = "test-secret"
os.environ["DRY_RUN"] = "true"
os.environ["RISK_PER_TRADE_USD"] = "50"
os.environ["MNQ_POINT_VALUE"] = "2.0"
os.environ["MAX_CONCURRENT_POSITIONS"] = "1"
os.environ["MAX_ARMED_ORDERS"] = "3"
os.environ["DAILY_LOSS_LIMIT_USD"] = "200"


@pytest.fixture(autouse=True)
def _clean_db():
    """Truncate tables between tests so they don't leak state."""
    from service.db import engine, init
    from service.models import Base

    init()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    yield
