"""Typed view of the ``PgBouncerPooler`` spec.

The CRD's OpenAPI schema (shipped with the Helm chart) is what the API server
validates against; this model is what the operator reasons with. Both exist
because the API server can reject a malformed shape but cannot express rules
like "these ini keys are reserved".
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.spec import PasswordRef


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class ImageSpec(_Model):
    repository: str
    tag: str = ""
    pull_policy: str = "IfNotPresent"

    @property
    def ref(self) -> str:
        return f"{self.repository}:{self.tag}" if self.tag else self.repository


class ServiceSpec(_Model):
    type: str = "ClusterIP"
    annotations: dict[str, str] = Field(default_factory=dict)


class ReloadSpec(_Model):
    """How a config change reaches the running PgBouncer.

    ``sighup`` is the default because it is the only option that does not drop
    established client connections: a sidecar watches the mounted config and
    signals PgBouncer in-place, so adding tenant 101 leaves the other 100
    undisturbed. ``rollout`` re-creates the pods instead, which is simpler to
    reason about but interrupts every session, and is offered for clusters
    where a shared process namespace is not acceptable.
    """

    strategy: Literal["sighup", "rollout"] = "sighup"
    interval_seconds: int = Field(default=10, ge=1, le=3600)


class TLSSpec(_Model):
    """Client-facing TLS. ``secretName`` must hold ``tls.crt`` and ``tls.key``."""

    secret_name: str
    # PgBouncer's client_tls_sslmode. "require" makes TLS mandatory for clients.
    mode: str = "require"


class SecurityDefaults(_Model):
    run_as_user: int = 1100
    run_as_group: int = 1100
    fs_group: int = 1100


class PoolerSpec(_Model):
    """``spec`` of a PgBouncerPooler."""

    image: ImageSpec
    # The operator's own image, reused as the reload sidecar. It already ships
    # the psql client and the reload logic, so there is no third image to pin.
    manager_image: ImageSpec | None = None

    replicas: int = Field(default=2, ge=0)
    listen_port: int = Field(default=6432, ge=1, le=65535)

    # PgBouncer's client-authentication method.
    auth_type: str = "scram-sha-256"
    # How this operator hashes passwords into userlist.txt. Kept separate from
    # auth_type: they usually match, but md5 clients against a scram userlist
    # is a real (if unhappy) configuration.
    auth_scheme: Literal["scram-sha-256", "md5", "plain"] = "scram-sha-256"
    admin_users: list[str] = Field(default_factory=lambda: ["pgbouncer"])
    # Credential for those admin users. Without it, nothing outside the pooler
    # pod can reach the admin console under a real auth_type, which is what
    # SHOW POOLS / SHOW STATS need. The reload sidecar does not use it -- it
    # signals the process directly -- so this is only required when something
    # off-pod (the manager UI) queries the console.
    admin_password: PasswordRef | None = None

    # Free-form [pgbouncer] section options. Reserved keys are rejected during
    # reconcile rather than here, so the failure surfaces on the resource.
    settings: dict[str, str] = Field(default_factory=dict)

    # Which PgBouncerDatabase resources belong to this pooler. Empty selector
    # means "every database in the namespace that does not name a different
    # pooler", which is the behaviour a single-pooler namespace wants.
    database_selector: dict[str, str] = Field(default_factory=dict)

    # Server-connection ceiling per target Postgres, keyed "host:port". Feeds
    # the same capacity arithmetic the API exposes at /api/capacity.
    capacity_limits: dict[str, int] = Field(default_factory=dict)

    manage_deployment: bool = True
    service: ServiceSpec = Field(default_factory=ServiceSpec)
    reload: ReloadSpec = Field(default_factory=ReloadSpec)
    tls: TLSSpec | None = None
    security: SecurityDefaults = Field(default_factory=SecurityDefaults)

    resources: dict[str, Any] = Field(default_factory=dict)
    node_selector: dict[str, str] = Field(default_factory=dict)
    tolerations: list[dict[str, Any]] = Field(default_factory=list)
    affinity: dict[str, Any] = Field(default_factory=dict)
    topology_spread_constraints: list[dict[str, Any]] = Field(default_factory=list)
    pod_annotations: dict[str, str] = Field(default_factory=dict)
    pod_labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("settings", mode="before")
    @classmethod
    def _stringify_settings(cls, value: Any) -> Any:
        """YAML gives ``max_client_conn: 1000`` as an int; ini values are text.

        Booleans become ``1``/``0`` because that is what PgBouncer parses --
        never Python's ``True``, which it would reject.
        """
        if not isinstance(value, dict):
            return value
        out: dict[str, str] = {}
        for key, item in value.items():
            if isinstance(item, bool):
                out[key] = "1" if item else "0"
            else:
                out[key] = str(item)
        return out
