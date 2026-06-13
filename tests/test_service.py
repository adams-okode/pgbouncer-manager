"""Tests for the PgBouncer service layer."""

import os
import stat

import pytest

from app.config import Settings
from app.services.pgbouncer import (
    PgBouncerService,
    parse_db_config,
    serialize_db_config,
    validate_tenant_id,
)


def make_service(tmp_path) -> PgBouncerService:
    return PgBouncerService(Settings(config_dir=tmp_path, auth_scheme="md5"))


def test_parse_and_serialize_roundtrip():
    parts = parse_db_config("host=db port=5432 dbname=app user=svc pool_size=20")
    assert parts == {
        "host": "db",
        "port": "5432",
        "dbname": "app",
        "user": "svc",
        "pool_size": "20",
    }
    # Serialization preserves insertion order.
    assert serialize_db_config(parts) == "host=db port=5432 dbname=app user=svc pool_size=20"


def test_databases_roundtrip_and_header(tmp_path):
    svc = make_service(tmp_path)
    svc.write_databases({"t1": {"host": "h", "port": "5432", "user": "u"}})
    text = svc.settings.databases_path.read_text()
    assert text.startswith("[databases]")
    assert 't1 = host=h port=5432 user=u' in text
    assert svc.read_databases() == {"t1": {"host": "h", "port": "5432", "user": "u"}}


def test_userlist_roundtrip(tmp_path):
    svc = make_service(tmp_path)
    svc.write_userlist({"alice": "md5abc", "bob": "SCRAM-SHA-256$4096:x$y:z"})
    assert svc.read_userlist() == {"alice": "md5abc", "bob": "SCRAM-SHA-256$4096:x$y:z"}


def test_read_missing_files_returns_empty(tmp_path):
    svc = make_service(tmp_path)
    assert svc.read_databases() == {}
    assert svc.read_userlist() == {}


def test_atomic_write_leaves_no_tempfiles(tmp_path):
    svc = make_service(tmp_path)
    svc.write_databases({"t1": {"host": "h"}})
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_new_config_files_are_readable(tmp_path):
    # PgBouncer reads these as its own user, so new files must not be 0600.
    svc = make_service(tmp_path)
    svc.write_databases({"t1": {"host": "h"}})
    mode = stat.S_IMODE(svc.settings.databases_path.stat().st_mode)
    assert mode == 0o644


def test_existing_file_mode_is_preserved(tmp_path):
    svc = make_service(tmp_path)
    svc.write_databases({"t1": {"host": "h"}})
    os.chmod(svc.settings.databases_path, 0o640)
    svc.write_databases({"t1": {"host": "h2"}})  # rewrite
    mode = stat.S_IMODE(svc.settings.databases_path.stat().st_mode)
    assert mode == 0o640  # operator-set perms survive rewrites


def test_hash_credential_passthrough_when_already_hashed(tmp_path):
    svc = make_service(tmp_path)
    already = "md5deadbeef"
    assert svc.hash_credential(already, "u") == already
    fresh = svc.hash_credential("plain", "u")
    assert fresh.startswith("md5")


def test_parse_tabular():
    stdout = "database\tuser\tcl_active\tcl_waiting\tsv_idle\tmaxwait\tpool_mode\n" \
        "app\tsvc\t10\t2\t5\t0\ttransaction\n" \
        "(1 row)"
    rows = PgBouncerService._parse_tabular(stdout)
    assert rows == [
        {
            "database": "app",
            "user": "svc",
            "cl_active": "10",
            "cl_waiting": "2",
            "sv_idle": "5",
            "maxwait": "0",
            "pool_mode": "transaction",
        }
    ]


def test_parse_tabular_empty():
    assert PgBouncerService._parse_tabular("") == []


@pytest.mark.parametrize("bad", ["", "a b", "with/slash", "x" * 64, "semi;colon"])
def test_validate_tenant_id_rejects(bad):
    with pytest.raises(ValueError):
        validate_tenant_id(bad)


@pytest.mark.parametrize("good", ["t1", "tenant_1", "a.b-c", "X" * 63])
def test_validate_tenant_id_accepts(good):
    assert validate_tenant_id(good) == good
