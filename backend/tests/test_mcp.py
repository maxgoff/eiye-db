"""MCP server tool tests — exercise the tool functions against the service layer."""

import asyncio

import pytest

from eiye_db import registry
from eiye_db.mcp_server import get_schema, list_datasources, mcp, query_datasource
from eiye_db.models import DataSourceCreate, DataSourceType


@pytest.fixture
def fs_source(tmp_path):
    (tmp_path / "leads.csv").write_text("company,contact\nAcme,ceo@acme.com\n")
    return registry.create(
        DataSourceCreate(name="leads", type=DataSourceType.FILE_SYSTEM, config={"root": str(tmp_path)})
    )


def test_tools_registered():
    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"list_datasources", "get_schema", "query_datasource"} <= tool_names


def test_list_datasources(fs_source):
    listed = list_datasources()
    assert listed[0]["name"] == "leads"
    assert listed[0]["schema_discovered"] is False


def test_get_schema_discovers_live(fs_source):
    schema = asyncio.run(get_schema(fs_source.id))
    assert schema["tables"][0]["name"] == "leads.csv"
    assert list_datasources()[0]["schema_discovered"] is True


def test_query_redacts_pii(fs_source):
    result = asyncio.run(query_datasource(fs_source.id, {"path": "leads.csv"}))
    assert result["rows"][0]["contact"] == "[REDACTED:email]"
    assert result["rows"][0]["company"] == "Acme"
    assert result["pii_filtered"] is True


def test_query_is_audited(fs_source, client):
    asyncio.run(query_datasource(fs_source.id, {"path": "leads.csv"}))
    entries = client.get("/api/v1/audit").json()
    assert entries[0]["action"] == "query"
    assert entries[0]["api_key_id"] == "mcp-stdio"
