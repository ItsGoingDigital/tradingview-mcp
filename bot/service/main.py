from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import init as init_db
from .logging import configure_logging, log
from .state import router as state_router
from .webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    log.info("service_started", dry_run=settings.dry_run, poller_enabled=settings.poller_enabled)

    poller_task: asyncio.Task | None = None
    if settings.poller_enabled:
        from .poller import run as poller_run

        poller_task = asyncio.create_task(poller_run())

    yield

    if poller_task:
        poller_task.cancel()
        try:
            await poller_task
        except (asyncio.CancelledError, Exception):
            pass

    # Best-effort cleanup of MCP subprocess
    try:
        from .mcp_client import _singleton

        if _singleton is not None:
            await _singleton.stop()
    except Exception:
        pass

    log.info("service_stopped")


app = FastAPI(title="MNQ Zone Bot", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(state_router)
