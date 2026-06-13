"""FastAPI dependency providers."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.services.pgbouncer import PgBouncerService


def get_service() -> PgBouncerService:
    """Provide a PgBouncerService bound to the current settings."""
    settings: Settings = get_settings()
    return PgBouncerService(settings)
