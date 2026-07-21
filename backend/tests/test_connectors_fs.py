"""Filesystem connector tests."""

import asyncio

import pytest

from eiye_db.connectors.base import ConnectorError
from eiye_db.connectors.filesystem import FilesystemConnector, infer_type


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "people.csv").write_text(
        "name,age,score\nAlice,30,91.5\nBob,25,88.0\n"
    )
    (tmp_path / "notes.md").write_text("# Notes\nemail: x@y.com\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "empty.csv").write_text("")
    return tmp_path


def test_infer_type():
    assert infer_type(["1", "2"]) == "integer"
    assert infer_type(["1.5", "2"]) == "number"
    assert infer_type(["a", "1"]) == "string"
    assert infer_type([]) == "string"


def test_discover(data_dir):
    conn = FilesystemConnector({"root": str(data_dir)})
    tables = asyncio.run(conn.discover_schema())
    by_name = {t["name"]: t for t in tables}
    assert by_name["people.csv"]["fields"] == [
        {"name": "name", "type": "string"},
        {"name": "age", "type": "integer"},
        {"name": "score", "type": "number"},
    ]
    assert by_name["notes.md"]["fields"] == [{"name": "content", "type": "text"}]
    assert by_name["sub/empty.csv"]["fields"] == []


def test_query_csv(data_dir):
    conn = FilesystemConnector({"root": str(data_dir)})
    rows = asyncio.run(conn.query({"path": "people.csv"}, limit=1))
    assert rows == [{"name": "Alice", "age": "30", "score": "91.5"}]


def test_query_text(data_dir):
    conn = FilesystemConnector({"root": str(data_dir)})
    rows = asyncio.run(conn.query({"path": "notes.md"}, limit=10))
    assert "x@y.com" in rows[0]["content"]


def test_path_traversal_blocked(data_dir):
    conn = FilesystemConnector({"root": str(data_dir)})
    with pytest.raises(ConnectorError, match="escapes"):
        asyncio.run(conn.query({"path": "../../etc/passwd"}, limit=10))


def test_missing_root_rejected(tmp_path):
    conn = FilesystemConnector({"root": str(tmp_path / "nope")})
    with pytest.raises(ConnectorError):
        asyncio.run(conn.test_connection())


def test_missing_file_rejected(data_dir):
    conn = FilesystemConnector({"root": str(data_dir)})
    with pytest.raises(ConnectorError, match="no such file"):
        asyncio.run(conn.query({"path": "ghost.csv"}, limit=10))
