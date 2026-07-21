"""API-key authentication tests."""

import pytest

from eiye_db.config import settings


@pytest.fixture
def locked(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    monkeypatch.setattr(settings, "admin_api_key", "root-secret")


def test_dev_mode_open(client):
    assert client.get("/api/v1/datasources").status_code == 200


def test_missing_key_401(client, locked):
    assert client.get("/api/v1/datasources").status_code == 401


def test_wrong_key_401(client, locked):
    assert client.get("/api/v1/datasources", headers={"X-API-Key": "wrong"}).status_code == 401


def test_valid_key_ok(client, locked):
    assert client.get("/api/v1/datasources", headers={"X-API-Key": "secret"}).status_code == 200


def test_admin_key_ok(client, locked):
    assert client.get("/api/v1/datasources", headers={"X-API-Key": "root-secret"}).status_code == 200


def test_health_needs_no_key(client, locked):
    assert client.get("/health").status_code == 200


def test_audit_denied_for_primary_key(client, locked):
    assert client.get("/api/v1/audit", headers={"X-API-Key": "secret"}).status_code == 403


def test_audit_allowed_for_admin_key(client, locked):
    assert client.get("/api/v1/audit", headers={"X-API-Key": "root-secret"}).status_code == 200


def test_include_pii_denied_for_primary_key(client, locked, tmp_path):
    (tmp_path / "d.csv").write_text("a\n1\n")
    ds = client.post(
        "/api/v1/datasources",
        json={"name": "d", "type": "filesystem", "config": {"root": str(tmp_path)}},
        headers={"X-API-Key": "secret"},
    ).json()
    resp = client.post(
        "/api/v1/query",
        json={"datasource_id": ds["id"], "request": {"path": "d.csv"}, "include_pii": True},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 403
