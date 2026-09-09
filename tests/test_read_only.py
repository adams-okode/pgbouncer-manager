"""Read-only mode: the API must refuse writes another controller would revert."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.deps import get_service
from app.main import app
from app.services.pgbouncer import PgBouncerService


@pytest.fixture
def read_only_client(tmp_path):
    settings = Settings(config_dir=tmp_path, read_only=True)
    app.dependency_overrides[get_service] = lambda: PgBouncerService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed(tmp_path):
    (tmp_path / "databases.ini").write_text("[databases]\nt1 = host=h user=u\n")


def test_reads_still_work(read_only_client, tmp_path):
    _seed(tmp_path)
    assert read_only_client.get("/api/tenants").status_code == 200


def test_create_is_refused(read_only_client):
    resp = read_only_client.post(
        "/api/tenants",
        json={"id": "t1", "host": "h", "password": "p"},
    )
    assert resp.status_code == 409
    assert "read-only" in resp.json()["detail"]


def test_update_is_refused(read_only_client, tmp_path):
    _seed(tmp_path)
    assert read_only_client.patch("/api/tenants/t1", json={"pool_size": 5}).status_code == 409


def test_delete_is_refused(read_only_client, tmp_path):
    _seed(tmp_path)
    assert read_only_client.delete("/api/tenants/t1").status_code == 409


def test_refusal_happens_before_any_write(read_only_client, tmp_path):
    """A 409 must not leave a half-applied change behind."""
    _seed(tmp_path)
    before = (tmp_path / "databases.ini").read_text()
    read_only_client.delete("/api/tenants/t1")
    assert (tmp_path / "databases.ini").read_text() == before


def test_health_advertises_the_mode(read_only_client):
    assert read_only_client.get("/api/health").json()["read_only"] is True


def test_writes_are_allowed_by_default(tmp_path):
    settings = Settings(config_dir=tmp_path)
    app.dependency_overrides[get_service] = lambda: PgBouncerService(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        resp = client.post(
            "/api/tenants",
            json={"id": "t1", "host": "h", "user": "u", "password": "p"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 201
