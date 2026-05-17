from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import init as init_db
from .logging import configure_logging, log
from .silverbullet.expiry import run as sb_expiry_run
from .silverbullet.webhook import router as sb_webhook_router
from .state import router as state_router
from .webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    log.info(
        "service_started",
        dry_run=settings.dry_run,
        poller_enabled=settings.poller_enabled,
        sb_enabled=settings.sb_enabled,
    )

    background_tasks: list[asyncio.Task] = []

    if settings.poller_enabled:
        from .poller import run as poller_run

        background_tasks.append(asyncio.create_task(poller_run()))

    if settings.sb_enabled:
        background_tasks.append(asyncio.create_task(sb_expiry_run()))

    yield

    for task in background_tasks:
        task.cancel()
        try:
            await task
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


app = FastAPI(title="MNQ Multi-Strategy Bot", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(sb_webhook_router)
app.include_router(state_router)
