"""Pure rendering of the three PgBouncer config files.

These functions take desired state and return file *content*. They touch no
disk and no cluster, which is what lets the same code back three very different
callers:

* :class:`~app.services.pgbouncer.PgBouncerService`, which writes the result to
  a shared volume (the Docker Compose / bare-metal model),
* the Kubernetes operator, which packs the result into a Secret,
* ``apply``, which diffs the result against what is already deployed.

Values are validated rather than trusted. A ``databases.ini`` entry is a
space-separated ``key=value`` connect string and ``pgbouncer.ini`` is
newline-separated ``key = value``, so a value containing whitespace or a
newline does not merely produce a malformed file -- it injects an adjacent
directive. Under the operator that input arrives from whoever can create a
custom resource in the namespace, and an injected ``auth_type = trust`` would
silently disable authentication for the whole pooler.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

# PgBouncer's own option names: lowercase words and underscores.
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# Connect-string values are delimited by whitespace, so they may not contain any.
_DB_VALUE_RE = re.compile(r"^[^\s\x00-\x1f]+$")
# ini values run to end of line: anything but a newline or other control char.
_INI_VALUE_RE = re.compile(r"^[^\n\r\x00-\x08\x0b\x0c\x0e-\x1f]*$")

DATABASES_HEADER = "; databases.ini -- managed by pgbouncer-manager"
USERLIST_HEADER = "; userlist.txt -- managed by pgbouncer-manager"


class ConfigValueError(ValueError):
    """Raised when a config key or value would corrupt the rendered file."""


def _check_key(key: str, *, where: str) -> str:
    if not _KEY_RE.match(key):
        raise ConfigValueError(f"invalid {where} option name: {key!r}")
    return key


def _check_db_value(key: str, value: str) -> str:
    if not _DB_VALUE_RE.match(value):
        raise ConfigValueError(
            f"invalid value for databases.ini option {key!r}: "
            "values may not be empty or contain whitespace"
        )
    return value


def _check_ini_value(key: str, value: str) -> str:
    if not _INI_VALUE_RE.match(value):
        raise ConfigValueError(
            f"invalid value for pgbouncer.ini option {key!r}: "
            "values may not span lines"
        )
    return value


def serialize_db_config(parts: Mapping[str, str]) -> str:
    """Serialize one tenant's parsed key/value config into a connect string."""
    return " ".join(
        f"{_check_key(key, where='databases.ini')}={_check_db_value(key, value)}"
        for key, value in parts.items()
    )


def render_databases_ini(databases: Mapping[str, Mapping[str, str]]) -> str:
    """Render the ``[databases]`` section from tenant id -> config parts."""
    lines = ["[databases]"]
    for tenant_id, parts in databases.items():
        lines.append(f"{tenant_id} = {serialize_db_config(parts)}")
    return "\n".join(lines) + "\n"


def render_userlist(users: Mapping[str, str]) -> str:
    """Render ``userlist.txt`` from username -> already-hashed credential.

    Credentials are written verbatim; hashing is the caller's job (see
    :mod:`app.auth`). A quote in either field would break the line format that
    :meth:`PgBouncerService.read_userlist` parses back, so reject it.
    """
    lines = [USERLIST_HEADER]
    for user, secret in users.items():
        if '"' in user or "\n" in user:
            raise ConfigValueError(f"invalid username for userlist.txt: {user!r}")
        if '"' in secret or "\n" in secret:
            raise ConfigValueError(f"invalid credential for user {user!r}")
        lines.append(f'"{user}" "{secret}"')
    return "\n".join(lines) + "\n"


def render_pgbouncer_ini(
    settings: Mapping[str, str],
    *,
    include: str | None = None,
) -> str:
    """Render a ``[pgbouncer]`` section, optionally with an ``%include``.

    ``include`` points at the file holding the ``[databases]`` section. It is
    kept separate so that a config change to one does not require rewriting the
    other, and so PgBouncer's ``RELOAD`` picks up tenant changes on their own.
    """
    lines = ["; pgbouncer.ini -- managed by pgbouncer-manager", "[pgbouncer]"]
    for key, value in settings.items():
        _check_key(key, where="pgbouncer.ini")
        lines.append(f"{key} = {_check_ini_value(key, value)}")
    if include:
        _check_ini_value("%include", include)
        lines.extend(["", f"%include {include}"])
    return "\n".join(lines) + "\n"
