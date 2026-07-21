"""REST connector tests using httpx.MockTransport."""

import asyncio

import httpx
import pytest

from eiye_db.connectors.base import ConnectorError
from eiye_db.connectors.rest import RestConnector

OPENAPI = {
    "paths": {
        "/users": {
            "get": {"parameters": [{"name": "limit", "schema": {"type": "integer"}}]},
            "post": {},
        },
        "/internal": {"post": {}},
    }
}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/openapi.json":
        return httpx.Response(200, json=OPENAPI)
    if request.url.path == "/users":
        return httpx.Response(200, json=[{"id": 1, "email": "a@b.co"}, {"id": 2}])
    if request.url.path == "/single":
        return httpx.Response(200, json={"ok": True})
    if request.url.path == "/":
        return httpx.Response(200, text="root")
    return httpx.Response(404)


@pytest.fixture
def conn():
    return RestConnector({"base_url": "http://test.local"}, transport=httpx.MockTransport(handler))


def test_test_connection(conn):
    asyncio.run(conn.test_connection())


def test_discover_openapi_get_only(conn):
    tables = asyncio.run(conn.discover_schema())
    assert tables == [{"name": "/users", "fields": [{"name": "limit", "type": "integer"}]}]


def test_query_list(conn):
    rows = asyncio.run(conn.query({"path": "/users"}, limit=1))
    assert rows == [{"id": 1, "email": "a@b.co"}]


def test_query_object_wrapped(conn):
    rows = asyncio.run(conn.query({"path": "/single"}, limit=10))
    assert rows == [{"ok": True}]


def test_query_404_raises(conn):
    with pytest.raises(ConnectorError, match="404"):
        asyncio.run(conn.query({"path": "/missing"}, limit=10))


def test_missing_base_url():
    conn = RestConnector({})
    with pytest.raises(ConnectorError, match="base_url"):
        asyncio.run(conn.test_connection())
