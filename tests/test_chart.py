"""The Helm chart and the operator must agree on the resource schema.

`helm template` renders custom resources; the operator parses them. Nothing
else in CI connects those two, so a values key renamed on one side and not the
other would otherwise only surface in a real cluster.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from app.spec import DatabaseSpec
from controller.reconcile import DatabaseInput, build_config
from controller.spec import PoolerSpec

CHART = Path(__file__).resolve().parent.parent / "charts" / "pgbouncer-manager"

pytestmark = pytest.mark.skipif(
    shutil.which("helm") is None, reason="helm is not installed"
)

VALUES = {
    "manager": {"enabled": True},
    "networkPolicy": {"enabled": True},
    "pooler": {
        "tls": {"enabled": True, "secretName": "pooler-tls"},
        "adminPasswordSecret": {"name": "pgbouncer-admin", "key": "password"},
        "capacityLimits": {"db-primary.internal:5432": 200},
    },
    "databaseDefaults": {
        "host": "db-primary.internal",
        "port": 5432,
        "poolSize": 20,
        "poolMode": "transaction",
    },
    "databases": [
        {
            "name": "acme",
            "dbname": "acme_production",
            "user": "acme",
            "password": {"secretKeyRef": {"name": "acme-db"}},
        },
        {
            "name": "globex",
            "dbname": "globex_production",
            "user": "globex",
            "poolSize": 40,
            "password": {"secretKeyRef": {"name": "globex-db", "key": "pgpassword"}},
        },
    ],
}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    values_file = tmp_path_factory.mktemp("chart") / "values.yaml"
    values_file.write_text(json.dumps(VALUES))
    out = subprocess.run(
        ["helm", "template", "test", str(CHART), "-f", str(values_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    return [doc for doc in yaml.safe_load_all(out.stdout) if doc]


def _of_kind(docs, kind):
    return [d for d in docs if d.get("kind") == kind]


def test_chart_renders_every_expected_kind(rendered):
    kinds = {d["kind"] for d in rendered}
    assert {
        "CustomResourceDefinition",
        "ServiceAccount",
        "ClusterRole",
        "ClusterRoleBinding",
        "Deployment",
        "Service",
        "NetworkPolicy",
        "PgBouncerPooler",
        "PgBouncerDatabase",
    } <= kinds


def test_rendered_pooler_parses_as_the_operator_reads_it(rendered):
    (pooler,) = _of_kind(rendered, "PgBouncerPooler")
    spec = PoolerSpec.model_validate(pooler["spec"])
    assert spec.tls is not None and spec.tls.secret_name == "pooler-tls"
    assert spec.admin_password is not None
    assert spec.capacity_limits == {"db-primary.internal:5432": 200}
    assert spec.reload.strategy == "sighup"


def test_rendered_databases_parse_and_inherit_defaults(rendered):
    databases = {
        d["metadata"]["name"]: DatabaseSpec.model_validate(
            {k: v for k, v in d["spec"].items() if k != "poolerRef"}
        )
        for d in _of_kind(rendered, "PgBouncerDatabase")
    }
    assert databases["acme"].host == "db-primary.internal"
    assert databases["acme"].pool_size == 20
    # An explicit value must win over the default.
    assert databases["globex"].pool_size == 40
    assert databases["globex"].password.secret_key_ref.key == "pgpassword"


def test_chart_output_renders_valid_pgbouncer_config(rendered):
    """The end-to-end contract: values -> custom resources -> config files."""
    (pooler,) = _of_kind(rendered, "PgBouncerPooler")
    inputs = [
        DatabaseInput(
            d["metadata"]["name"],
            DatabaseSpec.model_validate(
                {k: v for k, v in d["spec"].items() if k != "poolerRef"}
            ),
            "password-from-secret",
        )
        for d in _of_kind(rendered, "PgBouncerDatabase")
    ]
    config = build_config(PoolerSpec.model_validate(pooler["spec"]), inputs)

    assert "acme = host=db-primary.internal port=5432 dbname=acme_production" in (
        config.files["databases.ini"]
    )
    assert "client_tls_sslmode = require" in config.files["pgbouncer.ini"]
    # 20 + 40 against a 200-connection target is well inside budget.
    (target,) = config.capacity(PoolerSpec.model_validate(pooler["spec"]).capacity_limits)
    assert target.status == "ok"


def test_manager_is_deployed_read_only(rendered):
    """Under the operator the custom resources own the config, so a writable
    manager would accept edits its next reconcile silently reverts."""
    manager = next(
        d for d in _of_kind(rendered, "Deployment") if d["metadata"]["name"].endswith("-manager")
    )
    env = {
        e["name"]: e.get("value")
        for e in manager["spec"]["template"]["spec"]["containers"][0]["env"]
    }
    assert env["READ_ONLY"] == "true"


def test_operator_rbac_cannot_enumerate_secrets(rendered):
    """It reads password Secrets by name. Granting list or watch would let a
    stolen operator token dump every secret in the cluster."""
    (role,) = _of_kind(rendered, "ClusterRole")
    secret_rules = [
        rule for rule in role["rules"] if "secrets" in rule.get("resources", [])
    ]
    assert secret_rules
    for rule in secret_rules:
        assert "list" not in rule["verbs"]
        assert "watch" not in rule["verbs"]


def test_crds_survive_uninstall(rendered):
    """Deleting the CRDs would cascade-delete every tenant definition."""
    for crd in _of_kind(rendered, "CustomResourceDefinition"):
        assert crd["metadata"]["annotations"]["helm.sh/resource-policy"] == "keep"


def test_chart_lints():
    subprocess.run(["helm", "lint", str(CHART)], check=True, capture_output=True)
