"""Tests for the handler helpers that decide ownership and membership.

These are the pure parts of the otherwise cluster-bound handler module.
"""

from controller import api
from controller.handlers import (
    _adopt,
    _database_spec,
    _owner_reference,
    _owns,
)


def pooler_body(name="main", uid="uid-1"):
    return {"metadata": {"name": name, "namespace": "data", "uid": uid}}


def database(name="acme", labels=None, pooler_ref=None, spec=None):
    body = {
        "metadata": {"name": name, "namespace": "data", "labels": labels or {}},
        "spec": dict(spec or {"host": "db1"}),
    }
    if pooler_ref:
        body["spec"]["poolerRef"] = {"name": pooler_ref}
    return body


# --- ownership --------------------------------------------------------------
def test_owner_reference_points_at_the_pooler():
    """Not at whichever resource happened to trigger the reconcile.

    These objects are rendered from PgBouncerDatabase handlers too, so an
    owner reference taken from the triggering resource would let deleting one
    tenant garbage-collect the whole pooler's config Secret.
    """
    ref = _owner_reference(pooler_body())
    assert ref == {
        "apiVersion": api.API_VERSION,
        "kind": api.POOLER_KIND,
        "name": "main",
        "uid": "uid-1",
        "controller": True,
        "blockOwnerDeletion": True,
    }


def test_owner_reference_is_omitted_without_a_uid():
    assert _owner_reference({"metadata": {"name": "main"}}) is None


def test_adopt_sets_the_reference_on_the_object():
    obj = _adopt({"metadata": {"name": "x"}}, _owner_reference(pooler_body()))
    assert obj["metadata"]["ownerReferences"][0]["name"] == "main"


def test_adopt_without_an_owner_leaves_the_object_alone():
    obj = _adopt({"metadata": {"name": "x"}}, None)
    assert "ownerReferences" not in obj["metadata"]


# --- membership -------------------------------------------------------------
def test_explicit_pooler_ref_wins_over_the_selector():
    db = database(pooler_ref="other", labels={"pooler": "main"})
    assert _owns("main", {"pooler": "main"}, db) is False
    assert _owns("other", {}, db) is True


def test_empty_selector_claims_unassigned_databases():
    """The behaviour a single-pooler namespace wants without labelling."""
    assert _owns("main", {}, database()) is True


def test_selector_must_match_every_label():
    db = database(labels={"pooler": "main"})
    assert _owns("main", {"pooler": "main"}, db) is True
    assert _owns("main", {"pooler": "main", "tier": "gold"}, db) is False


def test_selector_does_not_claim_a_database_bound_elsewhere():
    db = database(pooler_ref="other", labels={"pooler": "main"})
    assert _owns("main", {}, db) is False


# --- spec parsing -----------------------------------------------------------
def test_entry_name_defaults_to_the_resource_name():
    assert _database_spec(database(name="acme")).name == "acme"


def test_explicit_spec_name_overrides_the_resource_name():
    db = database(name="acme-prod-pooler", spec={"host": "db1", "name": "acme"})
    assert _database_spec(db).name == "acme"


def test_pooler_ref_is_not_part_of_the_database_spec():
    """It addresses the pooler; it is not a databases.ini option."""
    spec = _database_spec(database(pooler_ref="main"))
    assert "poolerRef" not in spec.to_parts()
