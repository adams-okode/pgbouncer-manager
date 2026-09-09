"""The declarative shape of a set of PgBouncer databases.

This is deliberately one schema serving three surfaces:

* ``spec`` of a ``PgBouncerDatabase`` custom resource,
* an entry in a ``tenants.yaml`` fed to ``pgbouncer-manager apply``,
* the payload the API already accepts, via :meth:`DatabaseSpec.to_api_payload`.

Keeping them identical is the point. Someone who has declared a pooler on
Docker Compose should be able to move the same YAML to Kubernetes and have it
mean the same thing, which is only true if there is a single definition of what
a "database" is. Field names are snake_case in Python and accepted in either
snake_case or the camelCase that Kubernetes conventions expect.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

# databases.ini options this schema models explicitly. Anything else goes
# through `options`, which is validated by the renderer rather than here.
_INT_OPTIONS = (
    ("pool_size", "pool_size"),
    ("reserve_pool_size", "reserve_pool"),
    ("max_db_connections", "max_db_connections"),
    ("max_db_client_connections", "max_db_client_connections"),
)


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class PasswordRef(_Model):
    """Where the plaintext password for a database's forced user comes from.

    Exactly one source must be set. ``value`` is accepted for local testing and
    ``secret_key_ref`` is the Kubernetes path; ``env`` and ``file`` exist so a
    Compose deployment can keep the plaintext out of the YAML it commits.
    """

    value: str | None = None
    env: str | None = None
    file: str | None = None
    secret_key_ref: SecretKeyRef | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> PasswordRef:
        set_fields = [
            name
            for name in ("value", "env", "file", "secret_key_ref")
            if getattr(self, name) is not None
        ]
        if len(set_fields) != 1:
            raise ValueError(
                "password must set exactly one of value, env, file, secretKeyRef; "
                f"got {sorted(set_fields) or 'none'}"
            )
        return self

    def resolve_locally(self) -> str:
        """Read the password from this process's env or filesystem.

        Raises for ``secret_key_ref``, which only the operator can resolve --
        that indirection exists precisely so the plaintext never has to be
        readable by whoever writes the manifest.
        """
        if self.value is not None:
            return self.value
        if self.env is not None:
            try:
                return os.environ[self.env]
            except KeyError as exc:
                raise ValueError(
                    f"password env var {self.env!r} is not set"
                ) from exc
        if self.file is not None:
            try:
                # Trailing newlines are near-universal in mounted secret files
                # and are almost never part of the password.
                return Path(self.file).read_text(encoding="utf-8").rstrip("\r\n")
            except OSError as exc:
                raise ValueError(f"cannot read password file {self.file!r}: {exc}") from exc
        raise ValueError(
            "secretKeyRef can only be resolved inside Kubernetes; "
            "use env or file outside the cluster"
        )


class SecretKeyRef(_Model):
    """A key in a Kubernetes Secret in the same namespace."""

    name: str
    key: str = "password"


class DatabaseSpec(_Model):
    """One ``databases.ini`` entry."""

    name: str
    host: str
    port: int = Field(default=5432, ge=1, le=65535)
    dbname: str | None = None
    # No forced user means PgBouncer opens one pool *per connecting user*, so
    # the entry's real connection ceiling is unbounded. Allowed, but callers
    # are expected to surface it (see PgBouncerService.capacity_by_target).
    user: str | None = None
    password: PasswordRef | None = None
    pool_size: int | None = Field(default=None, ge=0)
    pool_mode: str | None = None
    reserve_pool_size: int | None = Field(default=None, ge=0)
    max_db_connections: int | None = Field(default=None, ge=0)
    max_db_client_connections: int | None = Field(default=None, ge=0)
    # Escape hatch for databases.ini options this schema does not name.
    options: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _pool_mode_is_known(self) -> DatabaseSpec:
        if self.pool_mode is not None and self.pool_mode not in {
            "session",
            "transaction",
            "statement",
        }:
            raise ValueError(
                "poolMode must be one of session, transaction, statement"
            )
        if self.password is not None and self.user is None:
            raise ValueError("password requires a user: it is stored per-user in userlist.txt")
        return self

    @property
    def is_unbounded(self) -> bool:
        """True when this entry has no forced user (one pool per client user)."""
        return not self.user

    def to_parts(self) -> dict[str, str]:
        """Render to the ordered key/value parts of a databases.ini line."""
        parts: dict[str, str] = {"host": self.host, "port": str(self.port)}
        if self.dbname:
            parts["dbname"] = self.dbname
        if self.user:
            parts["user"] = self.user
        for attr, ini_key in _INT_OPTIONS:
            value = getattr(self, attr)
            if value is not None:
                parts[ini_key] = str(value)
        if self.pool_mode:
            parts["pool_mode"] = self.pool_mode
        parts.update(self.options)
        return parts

    def to_api_payload(self, password: str) -> dict[str, Any]:
        """Render to the body ``POST /api/tenants`` expects."""
        return {
            "id": self.name,
            "host": self.host,
            "port": self.port,
            "db_name": self.dbname or "postgres",
            "user": self.user or "postgres",
            "password": password,
            "pool_size": self.pool_size if self.pool_size is not None else 15,
            "pool_mode": self.pool_mode,
        }


class TenantSet(_Model):
    """A whole ``tenants.yaml`` file: defaults plus a list of databases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        # Tolerate apiVersion/kind so the same document can carry the header
        # a Kubernetes user expects without it meaning anything here.
        extra="ignore",
    )

    defaults: dict[str, Any] = Field(default_factory=dict)
    databases: list[DatabaseSpec] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data: Any) -> Any:
        """Fold ``defaults`` into each database before per-item validation.

        Defaults are the whole reason this file scales: a hundred tenants on
        one Postgres differ only by name and dbname, and repeating host, port
        and poolSize a hundred times is how they drift apart.
        """
        if not isinstance(data, dict):
            return data
        defaults = data.get("defaults") or {}
        if not defaults:
            return data
        merged = []
        for entry in data.get("databases") or []:
            if isinstance(entry, dict):
                merged.append({**defaults, **entry})
            else:
                merged.append(entry)
        return {**data, "databases": merged}

    @model_validator(mode="after")
    def _names_are_unique(self) -> TenantSet:
        seen: set[str] = set()
        for db in self.databases:
            if db.name in seen:
                raise ValueError(f"duplicate database name: {db.name!r}")
            seen.add(db.name)
        return self


PasswordRef.model_rebuild()
