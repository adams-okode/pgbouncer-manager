"""Tests for the declarative `apply` path used on Compose and bare metal."""

import pytest

from app.spec import TenantSet
from cli import apply as apply_cmd


def tenant_set(*databases, defaults=None):
    return TenantSet.model_validate(
        {"defaults": defaults or {}, "databases": list(databases)}
    )


class FakeApi:
    """Records calls and answers GET /tenants from a fixed list."""

    def __init__(self, current=()):
        self.current = list(current)
        self.calls = []

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path == "/tenants":
            return self.current
        return {}


def test_creates_missing_tenants():
    api = FakeApi()
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "user": "acme",
                    "password": {"value": "pw"}}),
        api,
    )
    method, path, payload = api.calls[1]
    assert (method, path) == ("POST", "/tenants")
    assert payload["id"] == "acme"
    assert payload["password"] == "pw"


def test_updates_only_the_fields_that_differ():
    api = FakeApi(
        [{"id": "acme", "host": "db1", "port": 5432, "db_name": "acme",
          "user": "acme", "pool_size": 20, "pool_mode": None}]
    )
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "dbname": "acme", "user": "acme",
                    "poolSize": 40, "password": {"value": "pw"}}),
        api,
    )
    method, path, payload = api.calls[1]
    assert (method, path) == ("PATCH", "/tenants/acme")
    assert payload == {"pool_size": 40}


def test_an_unchanged_file_makes_no_write_calls():
    """Re-applying must be a no-op, or every run reloads PgBouncer."""
    api = FakeApi(
        [{"id": "acme", "host": "db1", "port": 5432, "db_name": "acme",
          "user": "acme", "pool_size": 20, "pool_mode": None}]
    )
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "dbname": "acme", "user": "acme",
                    "poolSize": 20, "password": {"value": "pw"}}),
        api,
    )
    assert [c[0] for c in api.calls] == ["GET"]


def test_password_is_not_resent_on_update_by_default():
    """The API stores a salted verifier it cannot compare, so re-sending a
    password would re-hash it and reload PgBouncer on every run."""
    api = FakeApi(
        [{"id": "acme", "host": "db1", "port": 5432, "db_name": "acme",
          "user": "acme", "pool_size": 20, "pool_mode": None}]
    )
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "dbname": "acme", "user": "acme",
                    "poolSize": 40, "password": {"value": "pw"}}),
        api,
    )
    assert "password" not in api.calls[1][2]


def test_rotate_credentials_resends_the_password():
    api = FakeApi(
        [{"id": "acme", "host": "db1", "port": 5432, "db_name": "acme",
          "user": "acme", "pool_size": 20, "pool_mode": None}]
    )
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "dbname": "acme", "user": "acme",
                    "poolSize": 40, "password": {"value": "new"}}),
        api,
        rotate_credentials=True,
    )
    assert api.calls[1][2]["password"] == "new"


def test_prune_is_off_by_default():
    api = FakeApi([{"id": "stale", "host": "h", "port": 5432, "db_name": "d",
                    "user": "u", "pool_size": 20, "pool_mode": None}])
    apply_cmd.apply(tenant_set(), api)
    assert [c[0] for c in api.calls] == ["GET"]


def test_prune_deletes_tenants_absent_from_the_file():
    api = FakeApi([{"id": "stale", "host": "h", "port": 5432, "db_name": "d",
                    "user": "u", "pool_size": 20, "pool_mode": None}])
    apply_cmd.apply(tenant_set(), api, prune=True)
    assert ("DELETE", "/tenants/stale", None) in api.calls


def test_dry_run_writes_nothing():
    api = FakeApi()
    apply_cmd.apply(
        tenant_set({"name": "acme", "host": "db1", "user": "acme",
                    "password": {"value": "pw"}}),
        api,
        dry_run=True,
    )
    assert [c[0] for c in api.calls] == ["GET"]


def test_missing_password_on_create_is_a_clear_error():
    api = FakeApi()
    with pytest.raises(apply_cmd.ApplyError, match="needs a password"):
        apply_cmd.apply(tenant_set({"name": "acme", "host": "db1", "user": "acme"}), api)


def test_loads_a_tenants_file_with_defaults(tmp_path):
    path = tmp_path / "tenants.yaml"
    path.write_text(
        """
defaults:
  host: db-primary.internal
  poolSize: 20
databases:
  - name: acme
    user: acme
    password:
      env: ACME_PW
  - name: globex
    user: globex
    poolSize: 40
    password:
      env: GLOBEX_PW
"""
    )
    tenants = apply_cmd.load_tenant_set(path)
    assert [d.name for d in tenants.databases] == ["acme", "globex"]
    assert tenants.databases[0].pool_size == 20
    assert tenants.databases[1].pool_size == 40
    assert tenants.databases[0].host == "db-primary.internal"


def test_invalid_tenants_file_reports_the_field(tmp_path):
    path = tmp_path / "tenants.yaml"
    path.write_text("databases:\n  - name: acme\n    poolMode: pooled\n    host: h\n")
    with pytest.raises(apply_cmd.ApplyError, match="poolMode"):
        apply_cmd.load_tenant_set(path)


def test_password_from_env_is_resolved_at_apply_time(tmp_path, monkeypatch):
    monkeypatch.setenv("ACME_PW", "s3cret")
    path = tmp_path / "tenants.yaml"
    path.write_text(
        "databases:\n  - name: acme\n    host: db1\n    user: acme\n"
        "    password:\n      env: ACME_PW\n"
    )
    api = FakeApi()
    apply_cmd.apply(apply_cmd.load_tenant_set(path), api)
    assert api.calls[1][2]["password"] == "s3cret"
