"""Kubernetes objects owned by a PgBouncerPooler, as plain dicts.

Also pure. The handler adds owner references and applies these; nothing here
needs a cluster, so the security posture below is asserted by unit tests rather
than by reading YAML in a review.
"""

from __future__ import annotations

from typing import Any

from controller import api
from controller.reconcile import TLS_DIR
from controller.spec import PoolerSpec

CONFIG_VOLUME = "config"
SOCKET_VOLUME = "run"
TLS_VOLUME = "tls"

# Rendered config is mounted read-only and group-readable, never world-readable:
# userlist.txt holds credential verifiers, which are offline-crackable against a
# weak password even though they are not plaintext.
CONFIG_FILE_MODE = 0o440


def _container_security_context(spec: PoolerSpec) -> dict[str, Any]:
    return {
        "allowPrivilegeEscalation": False,
        "privileged": False,
        "readOnlyRootFilesystem": True,
        "runAsNonRoot": True,
        "runAsUser": spec.security.run_as_user,
        "runAsGroup": spec.security.run_as_group,
        "capabilities": {"drop": ["ALL"]},
        "seccompProfile": {"type": "RuntimeDefault"},
    }


def _pod_security_context(spec: PoolerSpec) -> dict[str, Any]:
    return {
        "runAsNonRoot": True,
        "runAsUser": spec.security.run_as_user,
        "runAsGroup": spec.security.run_as_group,
        # fsGroup is what makes the 0440 Secret mount readable by the
        # unprivileged PgBouncer user at all.
        "fsGroup": spec.security.fs_group,
        "seccompProfile": {"type": "RuntimeDefault"},
    }


def config_secret_name(pooler_name: str) -> str:
    return f"{pooler_name}-pgbouncer-config"


def build_secret(
    pooler_name: str, namespace: str, files: dict[str, str]
) -> dict[str, Any]:
    """The Secret holding pgbouncer.ini, databases.ini and userlist.txt.

    All three live in one Secret rather than splitting the non-secret ini into
    a ConfigMap. Two reasons: a single volume avoids nesting one mount inside
    another to assemble ``/etc/pgbouncer``, and the kubelet swaps a volume's
    contents atomically, so PgBouncer never observes a new databases.ini
    alongside a stale userlist.txt.
    """
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": config_secret_name(pooler_name),
            "namespace": namespace,
            "labels": api.common_labels(pooler_name, "config"),
        },
        "type": "Opaque",
        "stringData": dict(files),
    }


def build_service(
    pooler_name: str, namespace: str, spec: PoolerSpec
) -> dict[str, Any]:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": pooler_name,
            "namespace": namespace,
            "labels": api.common_labels(pooler_name, "pooler"),
            "annotations": dict(spec.service.annotations),
        },
        "spec": {
            "type": spec.service.type,
            "selector": api.selector_labels(pooler_name),
            "ports": [
                {
                    "name": "pgbouncer",
                    "port": spec.listen_port,
                    "targetPort": "pgbouncer",
                    "protocol": "TCP",
                }
            ],
        },
    }


def _volumes(pooler_name: str, spec: PoolerSpec) -> list[dict[str, Any]]:
    volumes: list[dict[str, Any]] = [
        {
            "name": CONFIG_VOLUME,
            "secret": {
                "secretName": config_secret_name(pooler_name),
                "defaultMode": CONFIG_FILE_MODE,
            },
        },
        # The root filesystem is read-only, so PgBouncer's unix socket needs a
        # writable directory. The reload sidecar shares it.
        {"name": SOCKET_VOLUME, "emptyDir": {}},
    ]
    if spec.tls is not None:
        volumes.append(
            {
                "name": TLS_VOLUME,
                "secret": {
                    "secretName": spec.tls.secret_name,
                    "defaultMode": CONFIG_FILE_MODE,
                },
            }
        )
    return volumes


def _config_mounts(spec: PoolerSpec) -> list[dict[str, Any]]:
    # Deliberately no subPath: a subPath mount is a one-time copy that the
    # kubelet never refreshes, which would freeze the config at pod start and
    # make every later reconcile invisible to PgBouncer.
    mounts: list[dict[str, Any]] = [
        {"name": CONFIG_VOLUME, "mountPath": api.CONFIG_DIR, "readOnly": True},
        {"name": SOCKET_VOLUME, "mountPath": api.SOCKET_DIR},
    ]
    if spec.tls is not None:
        mounts.append({"name": TLS_VOLUME, "mountPath": TLS_DIR, "readOnly": True})
    return mounts


def build_deployment(
    pooler_name: str,
    namespace: str,
    spec: PoolerSpec,
    *,
    config_checksum: str,
) -> dict[str, Any]:
    """The PgBouncer Deployment, plus a reload sidecar under the sighup strategy."""
    sighup = spec.reload.strategy == "sighup"
    if sighup and spec.manager_image is None:
        raise ValueError(
            "reload.strategy=sighup needs spec.managerImage for the reload sidecar"
        )

    annotations = dict(spec.pod_annotations)
    if not sighup:
        # Only the rollout strategy wants the checksum on the pod template.
        # Under sighup this annotation would be actively harmful: changing it
        # restarts every pod, which is exactly the disruption sighup avoids.
        annotations[api.ANNOTATION_CONFIG_CHECKSUM] = config_checksum

    containers: list[dict[str, Any]] = [
        {
            "name": "pgbouncer",
            "image": spec.image.ref,
            "imagePullPolicy": spec.image.pull_policy,
            # The config is fully rendered, so bypass whatever entrypoint the
            # base image uses to template one of its own.
            "command": ["pgbouncer", f"{api.CONFIG_DIR}/{api.PGBOUNCER_INI}"],
            "ports": [{"name": "pgbouncer", "containerPort": spec.listen_port}],
            "volumeMounts": _config_mounts(spec),
            "securityContext": _container_security_context(spec),
            "resources": dict(spec.resources),
            "readinessProbe": {
                "tcpSocket": {"port": "pgbouncer"},
                "initialDelaySeconds": 2,
                "periodSeconds": 5,
                "timeoutSeconds": 3,
            },
            "livenessProbe": {
                "tcpSocket": {"port": "pgbouncer"},
                "initialDelaySeconds": 10,
                "periodSeconds": 20,
                "timeoutSeconds": 5,
                "failureThreshold": 3,
            },
        }
    ]

    if sighup:
        assert spec.manager_image is not None  # guarded above
        containers.append(
            {
                "name": "reloader",
                "image": spec.manager_image.ref,
                "imagePullPolicy": spec.manager_image.pull_policy,
                "command": ["python", "-m", "controller.reloader"],
                "env": [
                    {"name": "PGBM_WATCH_DIR", "value": api.CONFIG_DIR},
                    {
                        "name": "PGBM_RELOAD_INTERVAL",
                        "value": str(spec.reload.interval_seconds),
                    },
                ],
                "volumeMounts": [
                    {
                        "name": CONFIG_VOLUME,
                        "mountPath": api.CONFIG_DIR,
                        "readOnly": True,
                    }
                ],
                "securityContext": _container_security_context(spec),
                "resources": {
                    "requests": {"cpu": "10m", "memory": "32Mi"},
                    "limits": {"memory": "64Mi"},
                },
            }
        )

    pod_spec: dict[str, Any] = {
        "containers": containers,
        "volumes": _volumes(pooler_name, spec),
        "securityContext": _pod_security_context(spec),
        # PgBouncer never calls the Kubernetes API; mounting a token would only
        # hand a credential to whatever reaches the pooler.
        "automountServiceAccountToken": False,
        # Long-lived pooled connections deserve a chance to drain.
        "terminationGracePeriodSeconds": 60,
    }
    if sighup:
        # How the sidecar finds and signals the PgBouncer process. Scoped to
        # this pod, whose two containers are already one trust domain.
        pod_spec["shareProcessNamespace"] = True
    if spec.node_selector:
        pod_spec["nodeSelector"] = dict(spec.node_selector)
    if spec.tolerations:
        pod_spec["tolerations"] = list(spec.tolerations)
    if spec.affinity:
        pod_spec["affinity"] = dict(spec.affinity)
    if spec.topology_spread_constraints:
        pod_spec["topologySpreadConstraints"] = list(spec.topology_spread_constraints)

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": pooler_name,
            "namespace": namespace,
            "labels": api.common_labels(pooler_name, "pooler"),
        },
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": api.selector_labels(pooler_name)},
            "template": {
                "metadata": {
                    "labels": {
                        **api.common_labels(pooler_name, "pooler"),
                        **spec.pod_labels,
                    },
                    "annotations": annotations,
                },
                "spec": pod_spec,
            },
        },
    }


def build_pod_disruption_budget(
    pooler_name: str, namespace: str, spec: PoolerSpec
) -> dict[str, Any] | None:
    """Keep one pooler replica up during voluntary disruption.

    Returns None below two replicas: a PDB over a single pod blocks node
    drains outright rather than protecting anything.
    """
    if spec.replicas < 2:
        return None
    return {
        "apiVersion": "policy/v1",
        "kind": "PodDisruptionBudget",
        "metadata": {
            "name": pooler_name,
            "namespace": namespace,
            "labels": api.common_labels(pooler_name, "pooler"),
        },
        "spec": {
            "minAvailable": 1,
            "selector": {"matchLabels": api.selector_labels(pooler_name)},
        },
    }
