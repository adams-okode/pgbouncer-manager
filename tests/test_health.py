"""Smoke tests for the PgBouncer Manager API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_check():
    """Root endpoint returns a healthy status payload."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "pgbouncer-manager"
    assert body["status"] == "ok"
