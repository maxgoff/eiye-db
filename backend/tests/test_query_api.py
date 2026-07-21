"""End-to-end governed query flow: register → test → discover → query → audit."""

import pytest


@pytest.fixture
def fs_source(client, tmp_path):
    (tmp_path / "customers.csv").write_text(
        "name,email,phone\n"
        "Alice,alice@example.com,617-555-1234\n"
        "Bob,bob@corp.io,415-555-9876\n"
    )
    resp = client.post(
        "/api/v1/datasources",
        json={"name": "crm-files", "type": "filesystem", "config": {"root": str(tmp_path)}},
    )
    return resp.json()


def test_full_flow(client, fs_source):
    ds_id = fs_source["id"]

    tested = client.post(f"/api/v1/datasources/{ds_id}/test")
    assert tested.status_code == 200
    assert tested.json()["status"] == "connected"
    assert tested.json()["last_connected"] is not None

    discovered = client.post(f"/api/v1/datasources/{ds_id}/discover")
    assert discovered.status_code == 200
    assert discovered.json()["tables"][0]["name"] == "customers.csv"

    schema = client.get(f"/api/v1/surface/schema/{ds_id}")
    assert schema.status_code == 200
    assert schema.json()["tables"] == discovered.json()["tables"]

    sources = client.get("/api/v1/surface/sources").json()
    assert sources[0]["tables"] == 1

    result = client.post(
        "/api/v1/query",
        json={"datasource_id": ds_id, "request": {"path": "customers.csv"}},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["row_count"] == 2
    assert body["pii_filtered"] is True
    assert body["rows"][0]["email"] == "[REDACTED:email]"
    assert body["rows"][0]["phone"] == "[REDACTED:phone]"
    assert body["rows"][0]["name"] == "Alice"
    assert body["pii_counts"] == {"email": 2, "phone": 2}

    actions = [e["action"] for e in client.get("/api/v1/audit").json()]
    assert actions[0] == "query"
    assert "discover_schema" in actions
    assert "test_connection" in actions
    assert "create" in actions


def test_include_pii_in_dev_mode(client, fs_source):
    result = client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "customers.csv"}, "include_pii": True},
    )
    assert result.json()["rows"][0]["email"] == "alice@example.com"
    assert result.json()["pii_filtered"] is False


def test_query_limit(client, fs_source):
    result = client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "customers.csv"}, "limit": 1},
    )
    assert result.json()["row_count"] == 1


def test_query_unknown_source_404(client):
    resp = client.post("/api/v1/query", json={"datasource_id": "nope", "request": {}})
    assert resp.status_code == 404


def test_query_bad_request_502(client, fs_source):
    resp = client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "ghost.csv"}},
    )
    assert resp.status_code == 502
    audit_top = client.get("/api/v1/audit").json()[0]
    assert audit_top["action"] == "query"
    assert audit_top["success"] is False


def test_schema_before_discovery_404(client, fs_source):
    assert client.get(f"/api/v1/surface/schema/{fs_source['id']}").status_code == 404


def test_ragged_csv_row_does_not_crash(client, tmp_path):
    (tmp_path / "ragged.csv").write_text("a,b\n1,2,3,4\n")
    ds = client.post(
        "/api/v1/datasources",
        json={"name": "ragged", "type": "filesystem", "config": {"root": str(tmp_path)}},
    ).json()
    resp = client.post(
        "/api/v1/query", json={"datasource_id": ds["id"], "request": {"path": "ragged.csv"}}
    )
    assert resp.status_code == 200
    assert resp.json()["rows"][0]["_extra"] == ["3", "4"]


def test_query_request_pii_redacted_in_audit(client, fs_source):
    # failure path: the requested filename carries an email; it must not be
    # persisted to the audit trail verbatim
    client.post(
        "/api/v1/query",
        json={"datasource_id": fs_source["id"], "request": {"path": "leak-alice@example.com.csv"}},
    )
    top = client.get("/api/v1/audit").json()[0]
    assert top["success"] is False
    assert "alice@example.com" not in top["details"]["request"]["path"]
    assert "[REDACTED:email]" in top["details"]["request"]["path"]
