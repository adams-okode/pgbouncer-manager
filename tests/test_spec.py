"""The declarative schema shared by the CRD, tenants.yaml, and apply."""

import pytest
from pydantic import ValidationError

from app.spec import DatabaseSpec, TenantSet


def test_accepts_both_camel_and_snake_case():
    """The CRD speaks camelCase and Python speaks snake_case; one schema has
    to answer to both or the two surfaces drift apart."""
    camel = DatabaseSpec.model_validate({"name": "a", "host": "h", "poolSize": 20})
    snake = DatabaseSpec.model_validate({"name": "a", "host": "h", "pool_size": 20})
    assert camel.pool_size == snake.pool_size == 20


def test_to_parts_renders_databases_ini_keys():
    spec = DatabaseSpec.model_validate(
        {"name": "a", "host": "h", "dbname": "d", "user": "u",
         "poolSize": 20, "reservePoolSize": 5, "poolMode": "transaction"}
    )
    assert spec.to_parts() == {
        "host": "h", "port": "5432", "dbname": "d", "user": "u",
        "pool_size": "20", "reserve_pool": "5", "pool_mode": "transaction",
    }


def test_entry_without_a_user_is_unbounded():
    assert DatabaseSpec(name="a", host="h").is_unbounded is True
    assert DatabaseSpec(name="a", host="h", user="u").is_unbounded is False


def test_unknown_pool_mode_is_rejected():
    with pytest.raises(ValidationError, match="poolMode"):
        DatabaseSpec.model_validate({"name": "a", "host": "h", "poolMode": "pooled"})


def test_password_without_a_user_is_rejected():
    """userlist.txt is keyed by username, so a password with no user has
    nowhere to go."""
    with pytest.raises(ValidationError, match="requires a user"):
        DatabaseSpec.model_validate(
            {"name": "a", "host": "h", "password": {"value": "x"}}
        )


def test_password_needs_exactly_one_source():
    with pytest.raises(ValidationError, match="exactly one"):
        DatabaseSpec.model_validate(
            {"name": "a", "host": "h", "user": "u",
             "password": {"value": "x", "env": "Y"}}
        )


def test_typo_in_a_field_name_is_rejected_not_ignored():
    with pytest.raises(ValidationError):
        DatabaseSpec.model_validate({"name": "a", "host": "h", "poolsize": 20})


def test_defaults_are_merged_into_every_database():
    """The reason a hundred-tenant file stays readable."""
    tenants = TenantSet.model_validate(
        {
            "defaults": {"host": "db1", "poolSize": 20, "poolMode": "transaction"},
            "databases": [
                {"name": "acme", "user": "acme"},
                {"name": "globex", "user": "globex", "poolSize": 40},
            ],
        }
    )
    acme, globex = tenants.databases
    assert (acme.host, acme.pool_size) == ("db1", 20)
    assert (globex.host, globex.pool_size) == ("db1", 40)


def test_duplicate_names_are_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        TenantSet.model_validate(
            {"databases": [{"name": "a", "host": "h"}, {"name": "a", "host": "h2"}]}
        )


def test_password_resolves_from_the_environment(monkeypatch):
    monkeypatch.setenv("ACME_PW", "s3cret")
    spec = DatabaseSpec.model_validate(
        {"name": "a", "host": "h", "user": "u", "password": {"env": "ACME_PW"}}
    )
    assert spec.password.resolve_locally() == "s3cret"


def test_password_resolves_from_a_file_without_the_trailing_newline(tmp_path):
    path = tmp_path / "pw"
    path.write_text("s3cret\n")
    spec = DatabaseSpec.model_validate(
        {"name": "a", "host": "h", "user": "u", "password": {"file": str(path)}}
    )
    assert spec.password.resolve_locally() == "s3cret"


def test_secret_key_ref_cannot_be_resolved_outside_the_cluster():
    spec = DatabaseSpec.model_validate(
        {"name": "a", "host": "h", "user": "u",
         "password": {"secretKeyRef": {"name": "s"}}}
    )
    with pytest.raises(ValueError, match="only be resolved inside Kubernetes"):
        spec.password.resolve_locally()
