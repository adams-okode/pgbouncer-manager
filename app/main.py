"""PgBouncer Manager - FastAPI backend for managing PgBouncer tenants."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import pools, tenants

logger = logging.getLogger("pgbouncer_manager")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle."""
    _configure_logging()
    settings = get_settings()
    logger.info(
        "starting pgbouncer-manager config_dir=%s auth_scheme=%s",
        settings.config_dir, settings.auth_scheme,
    )
    yield
    logger.info("shutting down pgbouncer-manager")


app = FastAPI(title="PgBouncer Manager", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router)
app.include_router(pools.router)


@app.get("/")
def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"service": "pgbouncer-manager", "status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=True)
