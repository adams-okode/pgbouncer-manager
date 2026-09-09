"""FastAPI dependency providers."""

from __future__ import annotations

from fastapi import Depends, HTTPException

from app.config import Settings, get_settings
from app.services.pgbouncer import PgBouncerService


def get_service() -> PgBouncerService:
    """Provide a PgBouncerService bound to the current settings."""
    settings: Settings = get_settings()
    return PgBouncerService(settings)


def require_writable(settings: Settings = Depends(get_settings)) -> None:
    """Reject config-mutating requests when this instance does not own the files.

    409 rather than 403: nothing is wrong with the caller's credentials, the
    resource is simply not writable through this door.
    """
    if settings.read_only:
        raise HTTPException(
            status_code=409,
            detail=(
                "This instance is read-only (READ_ONLY=true): another controller "
                "owns databases.ini and userlist.txt. Change the PgBouncerDatabase "
                "resource or tenants.yaml instead."
            ),
        )
