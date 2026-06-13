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
import subprocess
import tempfile
from pathlib import Path

from app import auth
from app.config import Settings

logger = logging.getLogger("pgbouncer_manager.service")

# Tenant ids land directly in an ini key, so constrain them tightly.
_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,63}$")
_ROW_COUNT_RE = re.compile(r"^\(\d+ rows?\)$")


class PgBouncerError(RuntimeError):
    """Raised when a PgBouncer operation fails."""


def validate_tenant_id(tenant_id: str) -> str:
    """Validate a tenant id before it is written to a config file."""
    if not _TENANT_ID_RE.match(tenant_id):
        raise ValueError(
            "Tenant id must be 1-63 chars of letters, digits, '_', '.', or '-'"
        )
    return tenant_id


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
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


def serialize_db_config(parts: dict[str, str]) -> str:
    """Serialize a parsed db config dict back into a single line."""
    return " ".join(f"{key}={value}" for key, value in parts.items())


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
        lines = ["[databases]"]
        for tenant_id, parts in databases.items():
            lines.append(f"{tenant_id} = {serialize_db_config(parts)}")
        _atomic_write(self.settings.databases_path, "\n".join(lines) + "\n")

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
        lines = ["; userlist.txt -- managed by pgbouncer-manager"]
        for user, secret in users.items():
            lines.append(f'"{user}" "{secret}"')
        _atomic_write(self.settings.userlist_path, "\n".join(lines) + "\n")

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
