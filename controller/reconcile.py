"""Desired state, computed as pure functions.

Nothing here talks to the API server. Every function takes resolved inputs and
returns either file content or a plain object dict, which keeps the interesting
decisions -- credential churn, capacity, config injection, the reload strategy
-- testable without a cluster. :mod:`controller.handlers` is the thin, impure
layer that fetches inputs and applies the results.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app import auth
from app.services import render
from app.services.pgbouncer import TargetCapacity, compute_capacity, validate_tenant_id
from app.spec import DatabaseSpec
from controller import api
from controller.spec import PoolerSpec

# Options the operator derives from dedicated spec fields. Letting a free-form
# `settings` map override them is not a merge conflict, it is a privilege
# escalation: whoever can edit a pooler could point auth_file at an empty file
# or downgrade auth_type to trust, and every database behind the pooler would
# accept unauthenticated clients.
RESERVED_INI_KEYS = frozenset(
    {
        "auth_file",
        "auth_type",
        "auth_hba_file",
        "auth_query",
        "admin_users",
        "listen_addr",
        "listen_port",
        "unix_socket_dir",
        "client_tls_cert_file",
        "client_tls_key_file",
        "client_tls_sslmode",
        "logfile",
        "pidfile",
    }
)

# Applied unless the pooler overrides them. These are conventional PgBouncer
# defaults, not opinions of this operator, with one exception noted below.
DEFAULT_SETTINGS: dict[str, str] = {
    "pool_mode": "transaction",
    "max_client_conn": "1000",
    "default_pool_size": "20",
    # Clients (notably JDBC and some ORMs) send startup parameters PgBouncer
    # does not track; without this they fail to connect in transaction mode.
    "ignore_startup_parameters": "extra_float_digits",
}

TLS_DIR = f"{api.CONFIG_DIR}/tls"
# Anything at or above this counts as encrypted-in-transit to the backend.
_SAFE_SERVER_TLS_MODES = frozenset({"require", "verify-ca", "verify-full"})


class ReconcileError(Exception):
    """Desired state cannot be computed. Surfaces as a Degraded condition."""


@dataclass(frozen=True)
class DatabaseInput:
    """One PgBouncerDatabase resource with its password already resolved.

    Resolution happens in the handler, because it means reading a Secret. By
    the time state reaches this module the plaintext is either present or
    known-absent, and the reason it is absent has already been reported.
    """

    resource_name: str
    spec: DatabaseSpec
    password: str | None = None


@dataclass(frozen=True)
class RenderedConfig:
    files: dict[str, str]
    checksum: str
    users: dict[str, str]
    parts: dict[str, dict[str, str]]
    warnings: list[str] = field(default_factory=list)
    ready_databases: list[str] = field(default_factory=list)
    skipped_databases: dict[str, str] = field(default_factory=dict)

    def capacity(self, limits: Mapping[str, int]) -> list[TargetCapacity]:
        """Capacity verdicts for this config, using the API's own arithmetic."""
        return compute_capacity(self.parts, capacity_limits=limits)


def _matches_scheme(stored: str, scheme: str) -> bool:
    """True when ``stored`` is in the format ``scheme`` produces.

    Needed so that flipping a pooler from md5 to scram-sha-256 actually
    re-hashes. Without it the old md5 entry still verifies against the correct
    password, the entry looks up to date, and the migration silently never
    happens.
    """
    if scheme == "scram-sha-256":
        return stored.startswith("SCRAM-SHA-256$")
    if scheme == "md5":
        return stored.startswith("md5")
    return not stored.startswith(("SCRAM-SHA-256$", "md5"))


def build_userlist(
    databases: Sequence[DatabaseInput],
    *,
    auth_scheme: str,
    existing: Mapping[str, str] | None = None,
    scram_iterations: int = 4096,
    admin_users: Sequence[str] = (),
    admin_password: str | None = None,
) -> tuple[dict[str, str], list[str], dict[str, str]]:
    """Resolve username -> stored credential.

    Returns the userlist, human-readable warnings, and the databases that could
    not contribute a credential (name -> reason).

    An existing entry that already matches the desired password is reused
    verbatim. That is the difference between an operator that settles and one
    that reloads PgBouncer forever: SCRAM verifiers are randomly salted, so
    re-hashing an unchanged password yields different bytes on every pass and
    every pass then looks like a change.
    """
    existing = existing or {}
    users: dict[str, str] = {}
    plaintext_by_user: dict[str, str] = {}
    warnings: list[str] = []
    skipped: dict[str, str] = {}

    # Sorted so that a credential conflict resolves the same way on every
    # replica and every restart, rather than by dict iteration luck.
    for db in sorted(databases, key=lambda d: d.spec.name):
        spec = db.spec
        if not spec.user:
            continue
        if db.password is None:
            skipped[spec.name] = "no password available"
            continue

        claimed = plaintext_by_user.get(spec.user)
        if claimed is not None and claimed != db.password:
            # userlist.txt is keyed by username alone, so two databases forcing
            # the same user cannot hold two passwords. Report it instead of
            # letting the last writer win invisibly.
            warnings.append(
                f"credential conflict: databases share user {spec.user!r} with "
                f"different passwords; {spec.name!r} was ignored"
            )
            skipped[spec.name] = f"credential conflict on user {spec.user!r}"
            continue
        plaintext_by_user[spec.user] = db.password

        prior = existing.get(spec.user)
        if (
            prior
            and _matches_scheme(prior, auth_scheme)
            and auth.verify_password(db.password, spec.user, prior)
        ):
            users[spec.user] = prior
        else:
            users[spec.user] = auth.hash_password(
                db.password,
                spec.user,
                scheme=auth_scheme,
                iterations=scram_iterations,
            )

    # Admin users last: an admin credential is the pooler's own, and must not
    # be silently displaced by a database that happens to force the same name.
    for admin in admin_users:
        if admin_password is None:
            continue
        if admin in users:
            warnings.append(
                f"admin user {admin!r} is also a database's forced user; the "
                "admin credential takes precedence"
            )
        prior = existing.get(admin)
        if (
            prior
            and _matches_scheme(prior, auth_scheme)
            and auth.verify_password(admin_password, admin, prior)
        ):
            users[admin] = prior
        else:
            users[admin] = auth.hash_password(
                admin_password, admin, scheme=auth_scheme, iterations=scram_iterations
            )

    return dict(sorted(users.items())), warnings, skipped


def build_pgbouncer_ini(pooler: PoolerSpec) -> tuple[str, list[str]]:
    """Render the ``[pgbouncer]`` section, refusing reserved overrides."""
    clashes = sorted(RESERVED_INI_KEYS & set(pooler.settings))
    if clashes:
        raise ReconcileError(
            "spec.settings may not set operator-managed options "
            f"({', '.join(clashes)}); use the dedicated spec fields instead"
        )

    settings: dict[str, str] = {
        "listen_addr": "0.0.0.0",
        "listen_port": str(pooler.listen_port),
        "unix_socket_dir": api.SOCKET_DIR,
        "auth_type": pooler.auth_type,
        "auth_file": f"{api.CONFIG_DIR}/{api.USERLIST_TXT}",
        "admin_users": ",".join(pooler.admin_users),
        **DEFAULT_SETTINGS,
        **pooler.settings,
    }
    if pooler.tls is not None:
        settings["client_tls_sslmode"] = pooler.tls.mode
        settings["client_tls_cert_file"] = f"{TLS_DIR}/tls.crt"
        settings["client_tls_key_file"] = f"{TLS_DIR}/tls.key"

    warnings: list[str] = []
    if pooler.auth_type in {"trust", "any"}:
        warnings.append(
            f"auth_type is {pooler.auth_type!r}: clients reach every pooled "
            "database without proving who they are"
        )
    if settings.get("server_tls_sslmode") not in _SAFE_SERVER_TLS_MODES:
        warnings.append(
            "server_tls_sslmode is not require/verify-ca/verify-full: traffic "
            "from the pooler to Postgres may be unencrypted"
        )
    if pooler.tls is None:
        warnings.append(
            "no spec.tls: client connections to the pooler are unencrypted"
        )

    text = render.render_pgbouncer_ini(
        settings, include=f"{api.CONFIG_DIR}/{api.DATABASES_INI}"
    )
    return text, warnings


def build_config(
    pooler: PoolerSpec,
    databases: Sequence[DatabaseInput],
    *,
    existing_userlist: Mapping[str, str] | None = None,
    admin_password: str | None = None,
) -> RenderedConfig:
    """Render all three config files for one pooler."""
    pgbouncer_ini, warnings = build_pgbouncer_ini(pooler)

    users, user_warnings, skipped = build_userlist(
        databases,
        auth_scheme=pooler.auth_scheme,
        existing=existing_userlist,
        admin_users=pooler.admin_users if admin_password else (),
        admin_password=admin_password,
    )
    warnings.extend(user_warnings)

    parts: dict[str, dict[str, str]] = {}
    for db in sorted(databases, key=lambda d: d.spec.name):
        if db.spec.name in skipped:
            continue
        try:
            validate_tenant_id(db.spec.name)
        except ValueError as exc:
            skipped[db.spec.name] = str(exc)
            continue
        if db.spec.is_unbounded:
            warnings.append(
                f"database {db.spec.name!r} forces no user: PgBouncer opens one "
                "pool per connecting user, so its connection ceiling is unbounded"
            )
        parts[db.spec.name] = db.spec.to_parts()

    files = {
        api.PGBOUNCER_INI: pgbouncer_ini,
        api.DATABASES_INI: render.render_databases_ini(parts),
        api.USERLIST_TXT: render.render_userlist(users),
    }
    return RenderedConfig(
        files=files,
        checksum=checksum(files),
        users=users,
        parts=parts,
        warnings=warnings,
        ready_databases=sorted(parts),
        skipped_databases=skipped,
    )


def checksum(files: Mapping[str, str]) -> str:
    """Stable digest of rendered config, used to detect real changes.

    Only the content is hashed, in filename order, so an unrelated re-render
    that produces identical bytes does not look like a change.
    """
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[name].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
