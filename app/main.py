"""PgBouncer Manager - FastAPI backend for managing PgBouncer tenants."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.routes import capacity, pools, tenants

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
        "starting pgbouncer-manager config_dir=%s auth_scheme=%s read_only=%s",
        settings.config_dir, settings.auth_scheme, settings.read_only,
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
app.include_router(capacity.router)


@app.get("/api/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    """Health check endpoint.

    Also advertises ``read_only`` so the UI can hide controls that this
    instance would reject, rather than offering edits that 409.
    """
    return {
        "service": "pgbouncer-manager",
        "status": "ok",
        "read_only": settings.read_only,
    }


def _mount_ui(application: FastAPI) -> None:
    """Serve the compiled SPA at the root, if it was bundled into this build.

    Must run after the API routers: those routes are matched first, and this
    mount is the catch-all for everything else.
    """
    settings = get_settings()
    if not settings.ui_is_available:
        return
    application.mount(
        "/", StaticFiles(directory=settings.ui_dir, html=True), name="ui"
    )
    logger.warning(
        "serving bundled web UI at / -- the API ships without authentication, "
        "so put this behind an authenticating proxy before exposing the port"
    )


_mount_ui(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=True)
