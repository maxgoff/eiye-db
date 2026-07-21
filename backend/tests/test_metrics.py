"""Market-test metrics endpoint tests."""

import pytest


@pytest.fixture
def fs_source(client, tmp_path):
    (tmp_path / "people.csv").write_text(
        "name,email,phone\nAlice,alice@example.com,617-555-1234\nBob,bob@corp.io,415-555-9876\n"
    )
    return client.post(
        "/api/v1/datasources",
        json={"name": "people", "type": "filesystem", "config": {"root": str(tmp_path)}},
    ).json()


def test_empty_metrics(client):
    m = client.get("/api/v1/metrics").json()
    assert m["datasources"] == 0
    assert m["queries"]["total"] == 0
    assert m["queries"]["success_rate"] is None
    assert m["pii_redactions"]["total"] == 0
    assert m["first_datasource_at"] is None


def test_metrics_reflect_flow(client, fs_source):
    client.post(f"/api/v1/datasources/{fs_source['id']}/discover")
    client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "people.csv"}},
    )

    m = client.get("/api/v1/metrics").json()
    assert m["datasources"] == 1
    assert m["actions"]["create"] == 1
    assert m["actions"]["query"] == 1
    assert m["queries"] == {"total": 1, "succeeded": 1, "failed": 0, "success_rate": 1.0}
    # two rows, each with an email + phone redacted
    assert m["pii_redactions"]["by_type"] == {"email": 2, "phone": 2}
    assert m["pii_redactions"]["total"] == 4
    assert m["first_datasource_at"] is not None
    assert m["first_successful_query_at"] is not None
    assert m["last_activity_at"] is not None


def test_failed_query_counted(client, fs_source):
    client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "ghost.csv"}},
    )
    m = client.get("/api/v1/metrics").json()
    assert m["queries"] == {"total": 1, "succeeded": 0, "failed": 1, "success_rate": 0.0}
    assert m["first_successful_query_at"] is None


def test_metrics_admin_gated(client, monkeypatch):
    from eiye_db.config import settings

    monkeypatch.setattr(settings, "api_key", "secret")
    monkeypatch.setattr(settings, "admin_api_key", "root-secret")
    assert client.get("/api/v1/metrics", headers={"X-API-Key": "secret"}).status_code == 403
    assert client.get("/api/v1/metrics", headers={"X-API-Key": "root-secret"}).status_code == 200
