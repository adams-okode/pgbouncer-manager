"""kopf handlers: fetch inputs, call the pure reconciler, apply the results.

Deliberately thin. Anything that decides *what* the cluster should contain
lives in :mod:`controller.reconcile` and :mod:`controller.objects`; this module
only decides *when* to compute it and how to report the outcome.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import kopf
from pydantic import ValidationError

from app.spec import DatabaseSpec, PasswordRef
from controller import api, kube
from controller.objects import (
    build_deployment,
    build_pod_disruption_budget,
    build_secret,
    build_service,
    config_secret_name,
)
from controller.reconcile import DatabaseInput, ReconcileError, build_config
from controller.spec import PoolerSpec

logger = logging.getLogger("pgbouncer_manager.operator")

# How often to re-render even without a watched event. This is what picks up a
# password rotated inside a referenced Secret: the operator holds `get` on
# Secrets but deliberately not `list`/`watch`, so it cannot be told about the
# change and must look. Trading a slower rotation for a much smaller blast
# radius if the operator's credentials leak.
RESYNC_SECONDS = float(os.environ.get("PGBM_RESYNC_SECONDS", "120"))

_USERLIST_LINE_RE = re.compile(r'^\s*"([^"]+)"\s+"(.+)"\s*$')


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_: Any) -> None:
    settings.posting.level = logging.INFO
    # Keep bookkeeping in annotations under this operator's own group so it
    # cannot collide with another controller's.
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(
        prefix=api.GROUP
    )
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix=api.GROUP, key="last-handled"
    )
    settings.watching.server_timeout = 600
    kube.init()


# --- resolution helpers -----------------------------------------------------
def _database_spec(resource: dict[str, Any]) -> DatabaseSpec:
    """Parse a PgBouncerDatabase into the shared DatabaseSpec.

    ``spec.name`` defaults to the resource name so the common case needs no
    duplication, while still allowing a databases.ini entry name that differs
    from the Kubernetes object name.
    """
    spec = dict(resource.get("spec") or {})
    spec.pop("poolerRef", None)
    spec.setdefault("name", resource["metadata"]["name"])
    return DatabaseSpec.model_validate(spec)


def _resolve_password(namespace: str, ref: PasswordRef | None) -> tuple[str | None, str]:
    """Return (password, reason-if-missing) for one database."""
    if ref is None:
        return None, "no password configured"
    if ref.secret_key_ref is not None:
        data = kube.get_secret(namespace, ref.secret_key_ref.name)
        if data is None:
            return None, f"secret {ref.secret_key_ref.name!r} not found"
        value = data.get(ref.secret_key_ref.key)
        if value is None:
            return None, (
                f"secret {ref.secret_key_ref.name!r} has no key "
                f"{ref.secret_key_ref.key!r}"
            )
        # Mounted and kubectl-created secrets very often carry a trailing
        # newline that was never part of the password.
        return value.rstrip("\r\n"), ""
    if ref.value is not None:
        return ref.value, ""
    return None, "password source is not resolvable inside the cluster (use secretKeyRef)"


def _selector_matches(selector: dict[str, str], labels: dict[str, str]) -> bool:
    return all(labels.get(key) == value for key, value in selector.items())


def _owns(pooler_name: str, selector: dict[str, str], database: dict[str, Any]) -> bool:
    """Whether ``database`` belongs to the pooler named ``pooler_name``.

    An explicit ``spec.poolerRef`` always wins. Otherwise the pooler's
    ``databaseSelector`` decides, and an empty selector claims every database
    that has not named a different pooler -- the behaviour a namespace with a
    single pooler wants without any labelling ceremony.
    """
    ref = (database.get("spec") or {}).get("poolerRef") or {}
    if ref.get("name"):
        return bool(ref["name"] == pooler_name)
    labels = (database.get("metadata") or {}).get("labels") or {}
    return _selector_matches(selector, labels)


def _collect(namespace: str, pooler_name: str, selector: dict[str, str]) -> list[dict[str, Any]]:
    return [
        db
        for db in kube.list_custom(namespace, api.DATABASE_PLURAL)
        if _owns(pooler_name, selector, db)
    ]


def _owner_reference(pooler_body: dict[str, Any]) -> dict[str, Any] | None:
    """Owner reference pointing at the pooler, built explicitly.

    Not ``kopf.adopt``: that adopts into whatever resource is currently being
    handled, and these objects are also rendered from a PgBouncerDatabase
    handler. A Secret owned by one tenant's resource would be garbage-collected
    the moment that tenant was deleted, taking the whole pooler's config with
    it.
    """
    meta = pooler_body.get("metadata") or {}
    uid = meta.get("uid")
    if not uid:
        return None
    return {
        "apiVersion": api.API_VERSION,
        "kind": api.POOLER_KIND,
        "name": meta["name"],
        "uid": uid,
        "controller": True,
        "blockOwnerDeletion": True,
    }


def _adopt(obj: dict[str, Any], owner: dict[str, Any] | None) -> dict[str, Any]:
    if owner is not None:
        obj.setdefault("metadata", {})["ownerReferences"] = [owner]
    return obj


def _existing_userlist(namespace: str, pooler_name: str) -> dict[str, str]:
    """Parse the userlist already deployed, so unchanged entries are reused."""
    data = kube.get_secret(namespace, config_secret_name(pooler_name))
    if not data:
        return {}
    users: dict[str, str] = {}
    for raw in (data.get(api.USERLIST_TXT) or "").splitlines():
        match = _USERLIST_LINE_RE.match(raw)
        if match:
            users[match.group(1)] = match.group(2)
    return users


# --- the reconcile ----------------------------------------------------------
def reconcile_pooler(name: str, namespace: str, body: dict[str, Any]) -> dict[str, Any]:
    """Render and apply everything one pooler owns. Returns its status patch."""
    try:
        pooler = PoolerSpec.model_validate(body.get("spec") or {})
    except ValidationError as exc:
        raise kopf.PermanentError(f"invalid PgBouncerPooler spec: {exc}") from exc

    inputs: list[DatabaseInput] = []
    db_status: dict[str, tuple[bool, str]] = {}
    for resource in _collect(namespace, name, pooler.database_selector):
        db_name = resource["metadata"]["name"]
        try:
            spec = _database_spec(resource)
        except ValidationError as exc:
            db_status[db_name] = (False, f"invalid spec: {exc.errors()[0]['msg']}")
            continue
        password, reason = _resolve_password(namespace, spec.password)
        if password is None and spec.user:
            db_status[db_name] = (False, reason)
            continue
        db_status[db_name] = (True, "")
        inputs.append(DatabaseInput(db_name, spec, password))

    admin_password, admin_reason = (
        _resolve_password(namespace, pooler.admin_password)
        if pooler.admin_password is not None
        else (None, "")
    )
    if pooler.admin_password is not None and admin_password is None:
        logger.warning("pooler %s/%s admin credential: %s", namespace, name, admin_reason)

    try:
        rendered = build_config(
            pooler,
            inputs,
            existing_userlist=_existing_userlist(namespace, name),
            admin_password=admin_password,
        )
    except ReconcileError as exc:
        raise kopf.PermanentError(str(exc)) from exc

    owner = _owner_reference(body)
    kube.apply(_adopt(build_secret(name, namespace, rendered.files), owner))

    if pooler.manage_deployment:
        for obj in (
            build_deployment(name, namespace, pooler, config_checksum=rendered.checksum),
            build_service(name, namespace, pooler),
            build_pod_disruption_budget(name, namespace, pooler),
        ):
            if obj is None:
                continue
            kube.apply(_adopt(obj, owner))

    # Report per-database readiness on the databases themselves, so `kubectl
    # get pgbouncerdatabase` explains a tenant that silently did not appear.
    for db_name, (ok, reason) in db_status.items():
        skipped = rendered.skipped_databases.get(db_name)
        ready = ok and skipped is None
        kube.patch_status(
            namespace,
            api.DATABASE_PLURAL,
            db_name,
            {
                "pooler": name,
                "ready": ready,
                "message": reason or skipped or "",
                "conditions": [
                    api.condition(
                        "Ready",
                        ready,
                        "Configured" if ready else "NotConfigured",
                        reason or skipped or "included in the pooler config",
                    )
                ],
            },
        )

    targets = [
        {
            "host": t.host,
            "port": t.port,
            "databases": t.tenants,
            "declaredTotal": t.declared_total,
            "reserveTotal": t.reserve_total,
            "worstCaseTotal": t.worst_case_total,
            "maxConnections": t.max_connections,
            "headroom": t.headroom,
            "utilization": t.utilization,
            "status": t.status,
            "unboundedPools": t.unbounded_pools,
        }
        for t in rendered.capacity(pooler.capacity_limits)
    ]
    oversubscribed = [
        str(t["host"]) for t in targets if t["status"] == "oversubscribed"
    ]

    conditions = [
        api.condition(
            "Ready",
            not rendered.skipped_databases,
            "Reconciled" if not rendered.skipped_databases else "PartiallyReconciled",
            f"{len(rendered.ready_databases)} database(s) configured"
            + (
                f"; skipped: {', '.join(sorted(rendered.skipped_databases))}"
                if rendered.skipped_databases
                else ""
            ),
            observed_generation=body.get("metadata", {}).get("generation"),
        ),
        api.condition(
            "CapacitySafe",
            not oversubscribed,
            "WithinBudget" if not oversubscribed else "Oversubscribed",
            "pool sizes exceed max_connections on: " + ", ".join(oversubscribed)
            if oversubscribed
            else "declared pool sizes fit the configured connection budget",
        ),
    ]

    return {
        "observedGeneration": body.get("metadata", {}).get("generation"),
        "configSecret": config_secret_name(name),
        "configChecksum": rendered.checksum,
        "databases": len(rendered.ready_databases),
        "skippedDatabases": sorted(rendered.skipped_databases),
        "targets": targets,
        "warnings": rendered.warnings,
        "conditions": conditions,
    }


# --- watches ----------------------------------------------------------------
def _located(name: str | None, namespace: str | None) -> tuple[str, str]:
    """Narrow kopf's optional name/namespace for a namespaced resource.

    Both are always present for the namespaced kinds this operator watches;
    the optionality in kopf's signature covers cluster-scoped ones.
    """
    if not name or not namespace:
        raise kopf.PermanentError("handler invoked without a name and namespace")
    return name, namespace


@kopf.on.create(api.GROUP, api.VERSION, api.POOLER_PLURAL)
@kopf.on.update(api.GROUP, api.VERSION, api.POOLER_PLURAL)
@kopf.on.resume(api.GROUP, api.VERSION, api.POOLER_PLURAL)
def pooler_changed(
    *,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    patch: kopf.Patch,
    **_: Any,
) -> None:
    pooler_name, ns = _located(name, namespace)
    patch.status.update(reconcile_pooler(pooler_name, ns, dict(body)))


@kopf.timer(
    api.GROUP,
    api.VERSION,
    api.POOLER_PLURAL,
    interval=RESYNC_SECONDS,
    # Do not fight an in-progress change; resync is a backstop, not the path.
    idle=RESYNC_SECONDS,
)
def pooler_resync(
    *,
    name: str | None,
    namespace: str | None,
    body: kopf.Body,
    patch: kopf.Patch,
    **_: Any,
) -> None:
    """Catch changes no watch reports -- notably a rotated password Secret."""
    pooler_name, ns = _located(name, namespace)
    patch.status.update(reconcile_pooler(pooler_name, ns, dict(body)))


@kopf.on.create(api.GROUP, api.VERSION, api.DATABASE_PLURAL)
@kopf.on.update(api.GROUP, api.VERSION, api.DATABASE_PLURAL)
@kopf.on.delete(api.GROUP, api.VERSION, api.DATABASE_PLURAL, optional=True)
def database_changed(
    *, name: str | None, namespace: str | None, body: kopf.Body, **_: Any
) -> None:
    """Re-render every pooler that claims this database.

    On delete the resource is already gone from the listing by the time this
    runs, so the same code path removes it from the rendered config.
    """
    database_name, namespace = _located(name, namespace)
    resource = dict(body)
    for pooler in kube.list_custom(namespace, api.POOLER_PLURAL):
        pooler_name = pooler["metadata"]["name"]
        try:
            selector = PoolerSpec.model_validate(
                pooler.get("spec") or {}
            ).database_selector
        except ValidationError:
            continue
        if not _owns(pooler_name, selector, resource):
            continue
        status = reconcile_pooler(pooler_name, namespace, pooler)
        kube.patch_status(namespace, api.POOLER_PLURAL, pooler_name, status)
        logger.info(
            "database %s/%s triggered reconcile of pooler %s",
            namespace, database_name, pooler_name,
        )
