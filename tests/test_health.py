"""Smoke tests for the API health endpoint and the bundled UI mount."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import _mount_ui, app

client = TestClient(app)


def test_health_check():
    """Health endpoint returns a healthy status payload."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "pgbouncer-manager"
    assert body["status"] == "ok"


def _built_ui(tmp_path):
    (tmp_path / "index.html").write_text("<html>ui</html>")
    return tmp_path


def test_ui_unavailable_when_not_built(tmp_path):
    """A source checkout has no compiled SPA, so the mount must stay off."""
    assert Settings(serve_ui=True, ui_dir=tmp_path / "absent").ui_is_available is False


def test_ui_unavailable_when_disabled(tmp_path):
    """SERVE_UI=false keeps the service API-only even with the SPA present."""
    assert Settings(serve_ui=False, ui_dir=_built_ui(tmp_path)).ui_is_available is False


def test_ui_available_when_built_and_enabled(tmp_path):
    assert Settings(serve_ui=True, ui_dir=_built_ui(tmp_path)).ui_is_available is True


def test_mount_serves_index_at_root(tmp_path, monkeypatch):
    """When mounted, / returns the SPA shell rather than a JSON payload."""
    settings = Settings(serve_ui=True, ui_dir=_built_ui(tmp_path))
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = FastAPI()
    _mount_ui(application)

    response = TestClient(application).get("/")
    assert response.status_code == 200
    assert "<html>ui</html>" in response.text


def test_no_mount_leaves_root_unrouted(tmp_path, monkeypatch):
    settings = Settings(serve_ui=False, ui_dir=_built_ui(tmp_path))
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = FastAPI()
    _mount_ui(application)

    assert TestClient(application).get("/").status_code == 404
