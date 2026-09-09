"""Thin wrapper over the Kubernetes client.

Isolated from :mod:`controller.handlers` so the handlers read as reconcile
logic rather than as client plumbing, and so tests can substitute a fake.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from kubernetes import client, config
from kubernetes.dynamic import DynamicClient
from kubernetes.dynamic.exceptions import NotFoundError, ResourceNotFoundError

from controller import api

logger = logging.getLogger("pgbouncer_manager.operator")

FIELD_MANAGER = "pgbouncer-manager-operator"

_client: DynamicClient | None = None


def init() -> DynamicClient:
    """Load cluster credentials once, in-cluster or from a kubeconfig."""
    global _client
    if _client is not None:
        return _client
    try:
        config.load_incluster_config()
        logger.info("using in-cluster Kubernetes credentials")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("using kubeconfig credentials")
    _client = DynamicClient(client.ApiClient())
    return _client


def dyn() -> DynamicClient:
    return _client if _client is not None else init()


def apply(obj: dict[str, Any]) -> dict[str, Any]:
    """Server-side apply an object, taking ownership of the fields it sets.

    Server-side apply rather than create-or-patch because it converges: a
    field this operator stops setting is removed from the live object instead
    of lingering, so switching reload strategy actually drops the sidecar.
    ``force_conflicts`` claims fields another manager has touched -- for
    objects the operator owns outright, a conflict means drift to correct.
    """
    resource = dyn().resources.get(
        api_version=obj["apiVersion"], kind=obj["kind"]
    )
    return resource.server_side_apply(
        body=obj,
        name=obj["metadata"]["name"],
        namespace=obj["metadata"].get("namespace"),
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    ).to_dict()


def get_secret(namespace: str, name: str) -> dict[str, str] | None:
    """Return a Secret's decoded string data, or None when it does not exist."""
    try:
        resource = dyn().resources.get(api_version="v1", kind="Secret")
        found = resource.get(name=name, namespace=namespace).to_dict()
    except (NotFoundError, ResourceNotFoundError):
        return None
    except client.ApiException as exc:
        if exc.status == 404:
            return None
        raise
    data = found.get("data") or {}
    decoded: dict[str, str] = {}
    for key, value in data.items():
        try:
            decoded[key] = base64.b64decode(value).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            # A binary value cannot be a password or a config file; skip it
            # rather than failing the whole reconcile.
            logger.warning("secret %s/%s key %r is not valid UTF-8", namespace, name, key)
    return decoded


def list_custom(namespace: str, plural: str) -> list[dict[str, Any]]:
    """List one of this operator's custom resources in a namespace."""
    try:
        resource = dyn().resources.get(api_version=api.API_VERSION, plural=plural)
    except ResourceNotFoundError:
        return []
    return [item.to_dict() for item in resource.get(namespace=namespace).items]


def get_custom(namespace: str, plural: str, name: str) -> dict[str, Any] | None:
    try:
        resource = dyn().resources.get(api_version=api.API_VERSION, plural=plural)
        return resource.get(name=name, namespace=namespace).to_dict()
    except (NotFoundError, ResourceNotFoundError):
        return None


def patch_status(
    namespace: str, plural: str, name: str, status: dict[str, Any]
) -> None:
    """Merge-patch a custom resource's status subresource."""
    try:
        resource = dyn().resources.get(api_version=api.API_VERSION, plural=plural)
        resource.patch(
            name=name,
            namespace=namespace,
            body={"status": status},
            content_type="application/merge-patch+json",
            subresource="status",
        )
    except (NotFoundError, ResourceNotFoundError):
        # The resource went away mid-reconcile; nothing to report on.
        return
