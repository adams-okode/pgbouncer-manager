"""Integration tests for tenant CRUD and pool endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import get_service
from app.main import app
from app.services.pgbouncer import PgBouncerService


@pytest.fixture
def client(tmp_path):
    settings = Settings(config_dir=tmp_path, auth_scheme="scram-sha-256")
    svc = PgBouncerService(settings)
    app.dependency_overrides[get_service] = lambda: svc
    with TestClient(app) as test_client:
        yield test_client, svc
    app.dependency_overrides.clear()


def _add(client, **overrides):
    payload = {
        "id": "t1",
        "host": "db.example.com",
        "port": 5432,
        "db_name": "appdb",
        "user": "svc",
        "password": "secret",
        "pool_size": 15,
    }
    payload.update(overrides)
    return client.post("/api/tenants", json=payload)


def test_add_tenant_hashes_credential(client):
    test_client, svc = client
    resp = _add(test_client)
    assert resp.status_code == 201
    assert resp.json()["id"] == "t1"

    users = svc.read_userlist()
    assert "svc" in users
    # Stored as a SCRAM verifier, never the plaintext.
    assert users["svc"].startswith("SCRAM-SHA-256$")
    assert "secret" not in users["svc"]

    dbs = svc.read_databases()
    assert dbs["t1"]["host"] == "db.example.com"
    assert dbs["t1"]["dbname"] == "appdb"


def test_list_tenants(client):
    test_client, _ = client
    _add(test_client)
    resp = test_client.get("/api/tenants")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1 and body[0]["id"] == "t1"


def test_duplicate_add_conflicts(client):
    test_client, _ = client
    _add(test_client)
    assert _add(test_client).status_code == 409


def test_invalid_tenant_id_rejected(client):
    test_client, _ = client
    assert _add(test_client, id="bad id!").status_code == 422


def test_get_missing_tenant_404(client):
    test_client, _ = client
    assert test_client.get("/api/tenants/nope").status_code == 404


def test_patch_pool_size_keeps_credential(client):
    test_client, svc = client
    _add(test_client)
    before = svc.read_userlist()["svc"]

    resp = test_client.patch("/api/tenants/t1", json={"pool_size": 42})
    assert resp.status_code == 200
    assert resp.json()["pool_size"] == 42
    assert svc.read_databases()["t1"]["pool_size"] == "42"
    assert svc.read_userlist()["svc"] == before  # unchanged


def test_patch_password_rehashes(client):
    test_client, svc = client
    _add(test_client)
    before = svc.read_userlist()["svc"]

    resp = test_client.patch("/api/tenants/t1", json={"password": "newsecret"})
    assert resp.status_code == 200
    after = svc.read_userlist()["svc"]
    assert after != before
    assert after.startswith("SCRAM-SHA-256$")


def test_delete_removes_tenant_and_user(client):
    test_client, svc = client
    _add(test_client)
    resp = test_client.delete("/api/tenants/t1")
    assert resp.status_code == 200
    assert svc.read_databases() == {}
    assert "svc" not in svc.read_userlist()


def test_delete_missing_404(client):
    test_client, _ = client
    assert test_client.delete("/api/tenants/nope").status_code == 404


def test_delete_keeps_user_shared_by_another_tenant(client):
    test_client, svc = client
    _add(test_client, id="t1")
    _add(test_client, id="t2")  # same user "svc"
    test_client.delete("/api/tenants/t1")
    # svc still referenced by t2, so its credential must remain.
    assert "svc" in svc.read_userlist()
    assert "t2" in svc.read_databases()


# --- pools endpoints with a fake service --------------------------------------


class FakeService:
    def __init__(self, rows, reload_message="reloaded"):
        self._rows = rows
        self._reload_message = reload_message

    def run_psql(self, query):
        return self._rows

    def reload(self):
        return self._reload_message


def test_pools_status_maps_columns():
    rows = [
        {
            "database": "app",
            "user": "svc",
            "pool_mode": "transaction",
            "cl_active": "10",
            "cl_waiting": "2",
            "sv_idle": "5",
            "maxwait": "0",
        }
    ]
    app.dependency_overrides[get_service] = lambda: FakeService(rows)
    with TestClient(app) as test_client:
        resp = test_client.get("/api/pools/status")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    pool = resp.json()["pools"][0]
    assert pool == {
        "database": "app",
        "user": "svc",
        "pool_mode": "transaction",
        "active": 10,
        "waiting": 2,
        "idle": 5,
        "max_wait": 0,
    }


def test_reload_endpoint():
    app.dependency_overrides[get_service] = lambda: FakeService([], "sent SIGHUP")
    with TestClient(app) as test_client:
        resp = test_client.post("/api/pools/reload")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json() == {"status": "success", "message": "sent SIGHUP"}
