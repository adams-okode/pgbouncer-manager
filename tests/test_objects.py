"""The security posture of generated objects, asserted rather than reviewed."""

import pytest

from controller.objects import (
    build_deployment,
    build_pod_disruption_budget,
    build_secret,
    build_service,
)
from controller.spec import PoolerSpec


def pooler(**overrides):
    spec = {
        "image": {"repository": "pgbouncer", "tag": "test"},
        "managerImage": {"repository": "manager", "tag": "test"},
    }
    spec.update(overrides)
    return PoolerSpec.model_validate(spec)


def containers(deployment):
    return {c["name"]: c for c in deployment["spec"]["template"]["spec"]["containers"]}


def test_every_container_drops_privileges():
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    for container in containers(deployment).values():
        ctx = container["securityContext"]
        assert ctx["allowPrivilegeEscalation"] is False
        assert ctx["readOnlyRootFilesystem"] is True
        assert ctx["runAsNonRoot"] is True
        assert ctx["capabilities"]["drop"] == ["ALL"]
        assert ctx["seccompProfile"]["type"] == "RuntimeDefault"


def test_pooler_pod_gets_no_service_account_token():
    """PgBouncer never calls the Kubernetes API; a mounted token would only be
    a credential sitting behind the thing clients connect to."""
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    assert deployment["spec"]["template"]["spec"]["automountServiceAccountToken"] is False


def test_config_is_mounted_group_readable_not_world_readable():
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    volumes = {v["name"]: v for v in deployment["spec"]["template"]["spec"]["volumes"]}
    assert volumes["config"]["secret"]["defaultMode"] == 0o440


def test_config_mount_uses_no_subpath():
    """A subPath mount is copied once and never refreshed, which would freeze
    the config at pod start and make every later reconcile invisible."""
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    for container in containers(deployment).values():
        for mount in container.get("volumeMounts", []):
            assert "subPath" not in mount


def test_sighup_strategy_adds_a_sidecar_and_shares_the_process_namespace():
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    assert "reloader" in containers(deployment)
    assert deployment["spec"]["template"]["spec"]["shareProcessNamespace"] is True


def test_sighup_strategy_keeps_the_checksum_off_the_pod_template():
    """Putting it there would restart every pod on every tenant change -
    exactly the disruption sighup exists to avoid."""
    deployment = build_deployment("main", "data", pooler(), config_checksum="abc")
    annotations = deployment["spec"]["template"]["metadata"]["annotations"]
    assert not any("config-checksum" in key for key in annotations)


def test_rollout_strategy_puts_the_checksum_on_the_pod_template():
    deployment = build_deployment(
        "main", "data", pooler(reload={"strategy": "rollout"}), config_checksum="abc"
    )
    annotations = deployment["spec"]["template"]["metadata"]["annotations"]
    assert "abc" in annotations.values()
    assert "reloader" not in containers(deployment)
    assert "shareProcessNamespace" not in deployment["spec"]["template"]["spec"]


def test_sighup_without_a_manager_image_is_refused():
    spec = PoolerSpec.model_validate({"image": {"repository": "pgbouncer"}})
    with pytest.raises(ValueError, match="managerImage"):
        build_deployment("main", "data", spec, config_checksum="abc")


def test_tls_secret_is_mounted_when_configured():
    deployment = build_deployment(
        "main", "data", pooler(tls={"secretName": "pooler-tls"}), config_checksum="abc"
    )
    volumes = {v["name"]: v for v in deployment["spec"]["template"]["spec"]["volumes"]}
    assert volumes["tls"]["secret"]["secretName"] == "pooler-tls"


def test_pdb_is_skipped_for_a_single_replica():
    """A PDB over one pod blocks node drains instead of protecting anything."""
    assert build_pod_disruption_budget("main", "data", pooler(replicas=1)) is None
    assert build_pod_disruption_budget("main", "data", pooler(replicas=2)) is not None


def test_service_targets_the_named_port():
    service = build_service("main", "data", pooler(listenPort=7432))
    assert service["spec"]["ports"][0]["port"] == 7432
    assert service["spec"]["ports"][0]["targetPort"] == "pgbouncer"


def test_secret_carries_all_three_config_files():
    """One Secret, not a ConfigMap plus a Secret: the kubelet swaps a volume
    atomically, so PgBouncer never sees a new databases.ini beside a stale
    userlist.txt."""
    secret = build_secret("main", "data", {"a.ini": "x"})
    assert secret["stringData"] == {"a.ini": "x"}
    assert secret["type"] == "Opaque"
