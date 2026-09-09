"""Tests for the operator's pure reconciliation.

These are the behaviours that decide whether the operator settles or thrashes,
and whether a namespace user can talk it into an insecure config.
"""

import pytest

from app import auth
from app.spec import DatabaseSpec
from controller.reconcile import (
    DatabaseInput,
    ReconcileError,
    build_config,
    build_userlist,
)
from controller.spec import PoolerSpec


def pooler(**overrides):
    spec = {"image": {"repository": "pgbouncer", "tag": "test"}}
    spec.update(overrides)
    return PoolerSpec.model_validate(spec)


def db(name, password="pw", **overrides):
    spec = {"name": name, "host": "db1", "user": name, "poolSize": 20}
    spec.update(overrides)
    return DatabaseInput(name, DatabaseSpec.model_validate(spec), password)


# --- idempotence ------------------------------------------------------------
def test_reconcile_is_idempotent_across_passes():
    """The single most important property: an unchanged spec produces
    unchanged bytes, so PgBouncer is not reloaded on a timer forever."""
    spec = pooler()
    databases = [db("acme"), db("globex")]

    first = build_config(spec, databases)
    second = build_config(spec, databases, existing_userlist=first.users)

    assert second.checksum == first.checksum
    assert second.files == first.files


def test_changed_password_produces_a_new_verifier():
    spec = pooler()
    first = build_config(spec, [db("acme", password="old")])
    second = build_config(
        spec, [db("acme", password="new")], existing_userlist=first.users
    )

    assert second.checksum != first.checksum
    assert auth.verify_password("new", "acme", second.users["acme"])


def test_changing_auth_scheme_rehashes_even_though_the_password_matches():
    """An md5 entry verifies against the right password, so a naive
    'does it verify?' check would never migrate it to scram."""
    md5_pooler = pooler(authScheme="md5")
    md5_config = build_config(md5_pooler, [db("acme")])
    assert md5_config.users["acme"].startswith("md5")

    scram = build_config(
        pooler(authScheme="scram-sha-256"),
        [db("acme")],
        existing_userlist=md5_config.users,
    )
    assert scram.users["acme"].startswith("SCRAM-SHA-256$")


def test_output_is_order_independent():
    """Input order must not change the rendered config.

    Compared on content rather than checksum: freshly hashed SCRAM verifiers
    carry a random salt, so two independent renders of the same password
    legitimately differ in bytes. What must not differ is the entry order.
    """
    spec = pooler()
    forward = build_config(spec, [db("acme"), db("globex")])
    reverse = build_config(spec, [db("globex"), db("acme")])

    assert forward.files["databases.ini"] == reverse.files["databases.ini"]
    assert list(forward.users) == list(reverse.users)


# --- credential edge cases --------------------------------------------------
def test_conflicting_passwords_for_one_user_are_reported_not_silently_merged():
    """userlist.txt is keyed by username, so two passwords cannot both win."""
    config = build_config(
        pooler(),
        [
            DatabaseInput("a", DatabaseSpec(name="a", host="h", user="shared"), "pw1"),
            DatabaseInput("b", DatabaseSpec(name="b", host="h", user="shared"), "pw2"),
        ],
    )
    assert any("credential conflict" in w for w in config.warnings)
    assert "b" in config.skipped_databases
    assert "b" not in config.parts
    assert auth.verify_password("pw1", "shared", config.users["shared"])


def test_conflict_resolution_does_not_depend_on_input_order():
    """The same database must win on every replica and every restart."""
    inputs = [
        DatabaseInput("a", DatabaseSpec(name="a", host="h", user="shared"), "pw1"),
        DatabaseInput("b", DatabaseSpec(name="b", host="h", user="shared"), "pw2"),
    ]
    forward = build_config(pooler(), inputs)
    reverse = build_config(pooler(), list(reversed(inputs)))

    assert forward.files["databases.ini"] == reverse.files["databases.ini"]
    assert list(forward.skipped_databases) == list(reverse.skipped_databases) == ["b"]
    assert auth.verify_password("pw1", "shared", forward.users["shared"])
    assert auth.verify_password("pw1", "shared", reverse.users["shared"])


def test_database_without_a_password_is_skipped_with_a_reason():
    config = build_config(pooler(), [DatabaseInput("a", DatabaseSpec(name="a", host="h", user="u"), None)])
    assert config.skipped_databases["a"] == "no password available"
    assert "a" not in config.parts


def test_admin_credential_is_added_for_the_admin_console():
    config = build_config(pooler(), [db("acme")], admin_password="adminpw")
    assert auth.verify_password("adminpw", "pgbouncer", config.users["pgbouncer"])


def test_admin_credential_is_also_reused_when_unchanged():
    spec = pooler()
    first = build_config(spec, [db("acme")], admin_password="adminpw")
    second = build_config(
        spec, [db("acme")], existing_userlist=first.users, admin_password="adminpw"
    )
    assert second.checksum == first.checksum


# --- config safety ----------------------------------------------------------
@pytest.mark.parametrize("key", ["auth_file", "auth_type", "admin_users", "auth_query"])
def test_reserved_ini_options_cannot_be_overridden(key):
    """Allowing these would let whoever edits a pooler disable authentication
    for every database behind it."""
    with pytest.raises(ReconcileError, match="operator-managed"):
        build_config(pooler(settings={key: "anything"}), [])


def test_trust_auth_type_is_warned_about():
    config = build_config(pooler(authType="trust"), [db("acme")])
    assert any("without proving who they are" in w for w in config.warnings)


def test_missing_server_tls_is_warned_about():
    config = build_config(pooler(), [db("acme")])
    assert any("server_tls_sslmode" in w for w in config.warnings)


def test_configured_server_tls_clears_the_warning():
    config = build_config(
        pooler(settings={"server_tls_sslmode": "verify-full"}), [db("acme")]
    )
    assert not any("server_tls_sslmode" in w for w in config.warnings)


def test_unbounded_pool_is_flagged():
    """No forced user means one pool per connecting user, so poolSize stops
    being a ceiling -- the same gotcha the API's capacity report surfaces."""
    config = build_config(
        pooler(), [DatabaseInput("shared", DatabaseSpec(name="shared", host="h"), None)]
    )
    assert any("unbounded" in w for w in config.warnings)


def test_invalid_database_name_is_skipped_rather_than_corrupting_the_file():
    config = build_config(
        pooler(), [DatabaseInput("bad", DatabaseSpec(name="bad name", host="h"), None)]
    )
    assert "bad name" in config.skipped_databases
    assert "bad name" not in config.files["databases.ini"]


# --- rendered content -------------------------------------------------------
def test_rendered_ini_points_at_the_operator_managed_paths():
    config = build_config(pooler(), [db("acme")])
    ini = config.files["pgbouncer.ini"]
    assert "auth_file = /etc/pgbouncer/userlist.txt" in ini
    assert "%include /etc/pgbouncer/databases.ini" in ini
    assert "unix_socket_dir = /tmp/pgbouncer" in ini


def test_tls_paths_are_rendered_when_tls_is_configured():
    config = build_config(pooler(tls={"secretName": "pooler-tls"}), [db("acme")])
    ini = config.files["pgbouncer.ini"]
    assert "client_tls_sslmode = require" in ini
    assert "client_tls_cert_file = /etc/pgbouncer/tls/tls.crt" in ini


# --- capacity ---------------------------------------------------------------
def test_capacity_sums_pool_sizes_against_the_same_target():
    """Pools are keyed on entry name plus forced user, not on the target
    dbname, so two tenants on one Postgres each get their own pool."""
    config = build_config(
        pooler(),
        [db("acme", poolSize=120), db("globex", poolSize=100)],
    )
    (target,) = config.capacity({"db1:5432": 200})
    assert target.declared_total == 220
    assert target.status == "oversubscribed"
    # 200 minus the 3 connections Postgres reserves for superusers.
    assert target.headroom == 197 - 220


def test_capacity_is_unknown_without_a_declared_limit():
    config = build_config(pooler(), [db("acme")])
    (target,) = config.capacity({})
    assert target.status == "unknown"
    assert target.max_connections is None


def test_userlist_omits_databases_with_no_forced_user():
    users, _, _ = build_userlist(
        [DatabaseInput("s", DatabaseSpec(name="s", host="h"), "pw")],
        auth_scheme="scram-sha-256",
    )
    assert users == {}
