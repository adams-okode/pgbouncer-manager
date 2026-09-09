"""Group/version/kind constants and status-condition helpers."""

from __future__ import annotations

import datetime as _dt
from typing import Any

# adams-okode.github.io is the project's own GitHub Pages domain, so the API
# group is one the project actually controls rather than a squatted example.com.
GROUP = "pgbouncer.adams-okode.github.io"
VERSION = "v1alpha1"
API_VERSION = f"{GROUP}/{VERSION}"

POOLER_KIND = "PgBouncerPooler"
POOLER_PLURAL = "pgbouncerpoolers"
DATABASE_KIND = "PgBouncerDatabase"
DATABASE_PLURAL = "pgbouncerdatabases"

# Labels stamped on every object the operator owns.
LABEL_MANAGED_BY = "app.kubernetes.io/managed-by"
LABEL_NAME = "app.kubernetes.io/name"
LABEL_INSTANCE = "app.kubernetes.io/instance"
LABEL_COMPONENT = "app.kubernetes.io/component"
MANAGED_BY = "pgbouncer-manager-operator"

# Where config lands inside the PgBouncer container.
CONFIG_DIR = "/etc/pgbouncer"
PGBOUNCER_INI = "pgbouncer.ini"
DATABASES_INI = "databases.ini"
USERLIST_TXT = "userlist.txt"
# PgBouncer needs a writable directory for its unix socket, and the pod runs
# with a read-only root filesystem, so this is an emptyDir shared with the
# reload sidecar.
SOCKET_DIR = "/tmp/pgbouncer"

ANNOTATION_CONFIG_CHECKSUM = f"{GROUP}/config-checksum"


def now() -> str:
    """RFC3339 timestamp, as Kubernetes conditions expect."""
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def condition(
    type_: str,
    status: bool,
    reason: str,
    message: str = "",
    *,
    observed_generation: int | None = None,
) -> dict[str, Any]:
    """Build one entry for a ``status.conditions`` list."""
    cond: dict[str, Any] = {
        "type": type_,
        "status": "True" if status else "False",
        "reason": reason,
        "message": message[:32768],
        "lastTransitionTime": now(),
    }
    if observed_generation is not None:
        cond["observedGeneration"] = observed_generation
    return cond


def selector_labels(pooler_name: str) -> dict[str, str]:
    """Labels identifying the PgBouncer pods of one pooler."""
    return {
        LABEL_NAME: "pgbouncer",
        LABEL_INSTANCE: pooler_name,
    }


def common_labels(pooler_name: str, component: str) -> dict[str, str]:
    return {
        **selector_labels(pooler_name),
        LABEL_COMPONENT: component,
        LABEL_MANAGED_BY: MANAGED_BY,
    }
