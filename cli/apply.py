"""``pgbouncer-manager apply`` -- reconcile a tenants.yaml against the API.

The Kubernetes half of this project is declarative: you describe the databases
you want and the operator makes it so. This is the same idea for the
Compose/bare-metal half, over the same schema (:mod:`app.spec`), so a
``tenants.yaml`` and a set of ``PgBouncerDatabase`` resources describe a
deployment identically and one can become the other.

Passwords are sent on create, and on update only with ``--rotate-credentials``.
That is deliberate: the API stores a salted SCRAM verifier and cannot report
whether it matches a given password, so re-sending one on every apply would
re-hash it, rewrite userlist.txt with a fresh salt, and reload PgBouncer every
single run.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.spec import DatabaseSpec, TenantSet

# Tenant fields the API can report back, and so the ones a diff can compare.
_COMPARABLE = ("host", "port", "db_name", "user", "pool_size", "pool_mode")


class ApplyError(RuntimeError):
    """Raised when a tenants file cannot be applied."""


def load_tenant_set(path: Path) -> TenantSet:
    """Parse and validate a tenants.yaml (or .json) file."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ApplyError(
            "apply needs PyYAML: pip install pgbouncer-manager"
        ) from exc

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ApplyError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ApplyError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ApplyError(f"{path} must contain a mapping with a 'databases' key")
    try:
        return TenantSet.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError
        raise ApplyError(f"{path} is not a valid tenant set:\n{exc}") from exc


def _desired_payload(spec: DatabaseSpec) -> dict[str, Any]:
    """The comparable half of a tenant, as the API reports it."""
    return {
        "host": spec.host,
        "port": spec.port,
        "db_name": spec.dbname or "postgres",
        "user": spec.user or "postgres",
        "pool_size": spec.pool_size if spec.pool_size is not None else 15,
        "pool_mode": spec.pool_mode,
    }


def diff(spec: DatabaseSpec, current: dict[str, Any]) -> dict[str, Any]:
    """Fields that differ between desired and current. Empty means in sync."""
    desired = _desired_payload(spec)
    return {
        field: desired[field]
        for field in _COMPARABLE
        if desired[field] != current.get(field)
    }


def plan(
    tenants: TenantSet, current: list[dict[str, Any]], *, prune: bool
) -> tuple[list[DatabaseSpec], list[tuple[DatabaseSpec, dict[str, Any]]], list[str]]:
    """Split desired vs current state into (create, update, delete)."""
    by_id = {item["id"]: item for item in current}
    to_create: list[DatabaseSpec] = []
    to_update: list[tuple[DatabaseSpec, dict[str, Any]]] = []

    for spec in tenants.databases:
        existing = by_id.get(spec.name)
        if existing is None:
            to_create.append(spec)
            continue
        changes = diff(spec, existing)
        if changes:
            to_update.append((spec, changes))

    desired_names = {spec.name for spec in tenants.databases}
    to_delete = (
        sorted(name for name in by_id if name not in desired_names) if prune else []
    )
    return to_create, to_update, to_delete


def apply(
    tenants: TenantSet,
    request: Callable[..., Any],
    *,
    prune: bool = False,
    dry_run: bool = False,
    rotate_credentials: bool = False,
    out: Any = sys.stdout,
) -> int:
    """Reconcile ``tenants`` through ``request``. Returns a process exit code."""
    current = request("GET", "/tenants") or []
    to_create, to_update, to_delete = plan(tenants, current, prune=prune)

    if not (to_create or to_update or to_delete):
        print("Already up to date.", file=out)
        return 0

    for spec in to_create:
        password = _password_for(spec, required=True)
        print(f"+ create {spec.name}", file=out)
        if not dry_run:
            request("POST", "/tenants", spec.to_api_payload(password))

    for spec, changes in to_update:
        summary = ", ".join(f"{k}={v!r}" for k, v in sorted(changes.items()))
        if rotate_credentials and spec.password is not None:
            changes = {**changes, "password": _password_for(spec, required=True)}
            summary += ", password=<rotated>"
        print(f"~ update {spec.name}: {summary}", file=out)
        if not dry_run:
            request("PATCH", f"/tenants/{spec.name}", changes)

    for name in to_delete:
        print(f"- delete {name}", file=out)
        if not dry_run:
            request("DELETE", f"/tenants/{name}")

    if dry_run:
        print("\nDry run: nothing was changed.", file=out)
    return 0


def _password_for(spec: DatabaseSpec, *, required: bool) -> str:
    if spec.password is None:
        if required:
            raise ApplyError(
                f"database {spec.name!r} needs a password: add a `password:` "
                "with value, env, or file"
            )
        return ""
    try:
        return spec.password.resolve_locally()
    except ValueError as exc:
        raise ApplyError(f"database {spec.name!r}: {exc}") from exc


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "apply",
        help="Reconcile tenants from a declarative YAML file",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-f", "--file", required=True, type=Path, help="Path to tenants.yaml"
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete tenants that are not in the file (destructive)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan without applying it"
    )
    parser.add_argument(
        "--rotate-credentials",
        action="store_true",
        help=(
            "Also re-send passwords for tenants that already exist. Off by "
            "default because it re-hashes with a fresh salt every run"
        ),
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Skip the PgBouncer reload after applying",
    )
