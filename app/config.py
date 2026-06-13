"""Application configuration via pydantic-settings.

All values can be overridden with environment variables (case-insensitive) or a
local ``.env`` file. Settings are read at runtime through :func:`get_settings`
so the process environment is honoured even when it is set after import.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the PgBouncer Manager service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- PgBouncer config files ---------------------------------------------
    # ``CONFIG_DIR`` is kept un-prefixed for backwards compatibility.
    config_dir: Path = Path("/etc/pgbouncer")
    databases_file: str = "databases.ini"
    userlist_file: str = "userlist.txt"

    # --- Admin console (psql) -----------------------------------------------
    admin_host: str = "localhost"
    admin_port: int = 6432
    admin_user: str = "pgbouncer"
    admin_db: str = "pgbouncer"
    psql_bin: str = "psql"
    query_timeout: int = 10

    # --- Reload strategy ----------------------------------------------------
    # Docker container names to send SIGHUP to. When empty, the service falls
    # back to issuing ``RELOAD;`` over the admin console.
    reload_containers: list[str] = []
    docker_bin: str = "docker"
    reload_timeout: int = 30

    # --- Credential hashing -------------------------------------------------
    # One of: "scram-sha-256", "md5", "plain".
    auth_scheme: str = "scram-sha-256"
    scram_iterations: int = 4096

    # --- API / CORS ---------------------------------------------------------
    cors_origins: list[str] = ["*"]

    @property
    def databases_path(self) -> Path:
        return self.config_dir / self.databases_file

    @property
    def userlist_path(self) -> Path:
        return self.config_dir / self.userlist_file

    @field_validator("auth_scheme")
    @classmethod
    def _validate_auth_scheme(cls, value: str) -> str:
        allowed = {"scram-sha-256", "md5", "plain"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"auth_scheme must be one of {sorted(allowed)}")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
