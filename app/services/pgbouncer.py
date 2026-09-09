"""Service layer encapsulating all PgBouncer side effects.

Keeping subprocess calls and file IO here (instead of scattered across routes)
makes the HTTP layer thin and the behaviour testable. The two config files this
manages are:

* ``databases.ini`` -- one ``name = key=value ...`` line per tenant.
* ``userlist.txt`` -- ``"user" "hashed-credential"`` lines.

Writes are atomic (temp file in the same directory + ``os.replace``) so a crash
mid-write can never leave PgBouncer with a half-written config.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import stat
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app import auth
from app.config import Settings
from app.services.render import (
    render_databases_ini,
    render_userlist,
    serialize_db_config,
)

logger = logging.getLogger("pgbouncer_manager.service")

# Re-exported: callers have imported these from this module since before the
# rendering was split out into app.services.render.
__all__ = [
    "PgBouncerError",
    "PgBouncerService",
    "TargetCapacity",
    "compute_capacity",
    "parse_db_config",
    "serialize_db_config",
    "validate_tenant_id",
]

# Tenant ids land directly in an ini key, so constrain them tightly.
_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,63}$")
_ROW_COUNT_RE = re.compile(r"^\(\d+ rows?\)$")


class PgBouncerError(RuntimeError):
    """Raised when a PgBouncer operation fails."""


@dataclass(frozen=True)
class TargetCapacity:
    """Server-connection budget for one target Postgres (``host:port``).

    Every ``databases.ini`` entry is its own PgBouncer pool -- a pool is keyed
    on the entry name and the forced user, not on the target database -- so
    ``pool_size`` values across entries add up rather than overlap.
    """

    host: str
    port: int
    tenants: list[str] = field(default_factory=list)
    declared_total: int = 0
    reserve_total: int = 0
    worst_case_total: int = 0
    current_connections: int | None = None
    max_connections: int | None = None
    headroom: int | None = None
    utilization: float | None = None
    status: str = "unknown"
    source: str = "databases.ini"
    # Entries with no forced user get one pool *per connecting user*, so their
    # true ceiling is a multiple of pool_size that config alone cannot reveal.
    unbounded_pools: list[str] = field(default_factory=list)


@dataclass
class _Bucket:
    """Running totals for one target while capacity is being accumulated."""

    tenants: list[str] = field(default_factory=list)
    declared: int = 0
    reserve: int = 0
    current: int | None = None
    unbounded: list[str] = field(default_factory=list)


def _as_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _field_int(row: dict[str, str], *names: str) -> int | None:
    """First parseable integer among ``names``, tolerating column renames."""
    for name in names:
        parsed = _as_int(row.get(name))
        if parsed is not None:
            return parsed
    return None


def validate_tenant_id(tenant_id: str) -> str:
    """Validate a tenant id before it is written to a config file."""
    if not _TENANT_ID_RE.match(tenant_id):
        raise ValueError(
            "Tenant id must be 1-63 chars of letters, digits, '_', '.', or '-'"
        )
    return tenant_id


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temp file + rename).

    ``mkstemp`` creates the temp file 0600. PgBouncer reads these files as its
    own (often non-root) user, so an unreadable 0600 file would break it after
    the first rewrite. We therefore preserve the mode of an existing file (so
    operators can lock perms down, e.g. 0640 with a shared group) and default
    new files to 0644.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        mode = 0o644
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        # Best-effort cleanup of the temp file on any failure.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def parse_db_config(config: str) -> dict[str, str]:
    """Parse the right-hand side of a databases.ini line into an ordered dict."""
    parts: dict[str, str] = {}
    for token in config.split():
        if "=" in token:
            key, value = token.split("=", 1)
            parts[key] = value
    return parts


def compute_capacity(
    databases: Mapping[str, Mapping[str, str]],
    *,
    live: Mapping[str, Mapping[str, str]] | None = None,
    assumed_pool_size: int = 20,
    capacity_limits: Mapping[str, int] | None = None,
    superuser_reserved_connections: int = 3,
    tight_ratio: float = 0.8,
) -> list[TargetCapacity]:
    """Summarise committed server connections per target ``host:port``.

    Pure: it takes parsed config in and gives verdicts out, touching no files
    and no admin console. That is what lets the Kubernetes operator report the
    same numbers on a PgBouncerPooler's status as the API reports at
    ``/api/capacity``, from custom resources rather than from a databases.ini,
    without either side re-deriving the arithmetic.

    ``live`` is the admin console's view of effective settings, keyed by
    database name. It refines the declared config where available and is
    simply absent when PgBouncer is unreachable.
    """
    live = live or {}
    limits = capacity_limits or {}

    grouped: dict[tuple[str, int], _Bucket] = {}
    for tenant_id, parts in sorted(databases.items()):
        host = parts.get("host", "")
        port = _as_int(parts.get("port")) or 5432
        row = dict(live.get(tenant_id, {}))

        pool_size = _field_int(row, "pool_size")
        if pool_size is None:
            pool_size = _as_int(parts.get("pool_size"))
        if pool_size is None:
            pool_size = assumed_pool_size
        # Column name differs across PgBouncer versions.
        reserve = _field_int(row, "reserve_pool", "reserve_pool_size")
        if reserve is None:
            reserve = _as_int(parts.get("reserve_pool")) or 0
        current = _field_int(row, "current_connections")

        bucket = grouped.setdefault((host, port), _Bucket())
        bucket.tenants.append(tenant_id)
        bucket.declared += pool_size
        bucket.reserve += reserve
        if current is not None:
            bucket.current = current if bucket.current is None else bucket.current + current
        if not parts.get("user"):
            bucket.unbounded.append(tenant_id)

    return [
        _to_capacity(
            host,
            port,
            bucket,
            from_console=bool(live),
            limit=limits.get(f"{host}:{port}"),
            superuser_reserved_connections=superuser_reserved_connections,
            tight_ratio=tight_ratio,
        )
        for (host, port), bucket in sorted(grouped.items())
    ]


def _to_capacity(
    host: str,
    port: int,
    bucket: _Bucket,
    *,
    from_console: bool,
    limit: int | None,
    superuser_reserved_connections: int,
    tight_ratio: float,
) -> TargetCapacity:
    worst_case = bucket.declared + bucket.reserve

    headroom: int | None = None
    utilization: float | None = None
    status = "unknown"
    if limit is not None:
        usable = max(limit - superuser_reserved_connections, 0)
        headroom = usable - worst_case
        utilization = round(worst_case / usable, 4) if usable else None
        if headroom < 0:
            status = "oversubscribed"
        elif utilization is not None and utilization >= tight_ratio:
            status = "tight"
        else:
            status = "ok"

    return TargetCapacity(
        host=host,
        port=port,
        tenants=list(bucket.tenants),
        declared_total=bucket.declared,
        reserve_total=bucket.reserve,
        worst_case_total=worst_case,
        current_connections=bucket.current,
        max_connections=limit,
        headroom=headroom,
        utilization=utilization,
        status=status,
        source="pgbouncer" if from_console else "databases.ini",
        unbounded_pools=list(bucket.unbounded),
    )


class PgBouncerService:
    """All PgBouncer file and process interactions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # --- databases.ini ------------------------------------------------------
    def read_databases(self) -> dict[str, dict[str, str]]:
        """Return mapping of tenant id -> parsed key/value config."""
        result: dict[str, dict[str, str]] = {}
        try:
            text = self.settings.databases_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return result
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith((";", "#", "[")):
                continue
            if "=" not in line:
                continue
            tenant_id, config = line.split("=", 1)
            result[tenant_id.strip()] = parse_db_config(config.strip())
        return result

    def write_databases(self, databases: dict[str, dict[str, str]]) -> None:
        _atomic_write(self.settings.databases_path, render_databases_ini(databases))

    # --- userlist.txt -------------------------------------------------------
    def read_userlist(self) -> dict[str, str]:
        users: dict[str, str] = {}
        try:
            text = self.settings.userlist_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return users
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith((";", "#")):
                continue
            match = re.match(r'"([^"]+)"\s+"(.+)"\s*$', line)
            if match:
                users[match.group(1)] = match.group(2)
        return users

    def write_userlist(self, users: dict[str, str]) -> None:
        _atomic_write(self.settings.userlist_path, render_userlist(users))

    # --- credentials --------------------------------------------------------
    def hash_credential(self, password: str, username: str) -> str:
        if auth.is_already_hashed(password):
            return password
        return auth.hash_password(
            password,
            username,
            scheme=self.settings.auth_scheme,
            iterations=self.settings.scram_iterations,
        )

    # --- psql admin console -------------------------------------------------
    def run_psql(self, query: str) -> list[dict[str, str]]:
        """Run a SHOW query against the admin console and return parsed rows.

        Uses unaligned output with a tab field separator so values are parsed
        by column *name* rather than by fragile positional ``split()`` logic.
        """
        s = self.settings
        cmd = [
            s.psql_bin,
            "-h", s.admin_host,
            "-p", str(s.admin_port),
            "-U", s.admin_user,
            "-d", s.admin_db,
            "-A",                # unaligned output
            "-F", "\t",          # tab-separated fields
            "-P", "pager=off",
            "-c", query,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=s.query_timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise PgBouncerError("PgBouncer admin query timed out") from exc
        except FileNotFoundError as exc:
            raise PgBouncerError(f"{s.psql_bin!r} executable not found") from exc

        if result.returncode != 0:
            raise PgBouncerError(result.stderr.strip() or "psql command failed")
        return self._parse_tabular(result.stdout)

    @staticmethod
    def _parse_tabular(stdout: str) -> list[dict[str, str]]:
        lines = [
            ln for ln in stdout.splitlines()
            if ln.strip() and not _ROW_COUNT_RE.match(ln.strip())
        ]
        if not lines:
            return []
        header = lines[0].split("\t")
        rows: list[dict[str, str]] = []
        for line in lines[1:]:
            values = line.split("\t")
            if len(values) != len(header):
                # Skip malformed rows rather than mis-aligning columns.
                continue
            rows.append(dict(zip(header, values, strict=True)))
        return rows

    # --- capacity -----------------------------------------------------------
    def _show_databases(self) -> dict[str, dict[str, str]]:
        """Effective per-database settings from the admin console, keyed by name.

        Returns ``{}`` when PgBouncer is unreachable so capacity reporting can
        fall back to the declared config instead of failing outright.
        """
        try:
            rows = self.run_psql("SHOW DATABASES;")
        except PgBouncerError as exc:
            logger.info("capacity: admin console unavailable (%s); using databases.ini", exc)
            return {}
        return {row["name"]: row for row in rows if row.get("name")}

    def capacity_by_target(self, *, effective: bool = True) -> list[TargetCapacity]:
        """Summarise committed server connections per target ``host:port``."""
        s = self.settings
        return compute_capacity(
            self.read_databases(),
            live=self._show_databases() if effective else {},
            assumed_pool_size=s.assumed_pool_size,
            capacity_limits=s.capacity_limits,
            superuser_reserved_connections=s.superuser_reserved_connections,
            tight_ratio=s.capacity_tight_ratio,
        )

    # --- reload -------------------------------------------------------------
    def reload(self) -> str:
        """Reload PgBouncer. Returns a human-readable status message."""
        s = self.settings
        if s.reload_containers:
            cmd = [s.docker_bin, "kill", "--signal=HUP", *s.reload_containers]
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=s.reload_timeout, check=False,
                )
            except FileNotFoundError as exc:
                raise PgBouncerError(f"{s.docker_bin!r} executable not found") from exc
            except subprocess.TimeoutExpired as exc:
                raise PgBouncerError("Reload (docker kill) timed out") from exc
            if result.returncode != 0:
                raise PgBouncerError(result.stderr.strip() or "docker kill failed")
            return f"Sent SIGHUP to: {', '.join(s.reload_containers)}"

        # No containers configured: reload via the admin console.
        self.run_psql("RELOAD;")
        return "Reloaded via admin console (RELOAD)"
