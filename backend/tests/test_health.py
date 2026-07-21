"""Health and status endpoint tests."""

from fastapi.testclient import TestClient

from eiye_db import __version__
from eiye_db.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_status():
    resp = client.get("/api/v1/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "eiye_db"
    assert body["version"] == __version__


def test_unknown_route_404():
    assert client.get("/api/v1/nope").status_code == 404
