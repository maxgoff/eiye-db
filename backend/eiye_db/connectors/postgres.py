"""PostgreSQL connector. Queries run inside read-only transactions."""

from typing import Any

import asyncpg

from eiye_db.connectors.base import Connector, ConnectorError

_SCHEMA_SQL = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position
"""

_PK_SQL = """
SELECT kcu.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public'
"""


def rows_to_tables(columns: list[tuple], pks: set[tuple]) -> list[dict[str, Any]]:
    """Group (table, column, type) rows into the connector schema shape."""
    tables: dict[str, list[dict[str, Any]]] = {}
    for table, column, dtype in columns:
        tables.setdefault(table, []).append(
            {"name": column, "type": dtype, "is_primary_key": (table, column) in pks}
        )
    return [{"name": name, "fields": fields} for name, fields in tables.items()]


class PostgresConnector(Connector):
    def _dsn(self) -> str:
        dsn = self.config.get("dsn")
        if not dsn:
            raise ConnectorError("postgres config requires 'dsn'")
        return dsn

    async def _connect(self):
        try:
            return await asyncpg.connect(self._dsn(), timeout=10)
        except (OSError, asyncpg.PostgresError, ValueError) as e:
            raise ConnectorError(f"connection failed: {e}") from e

    async def test_connection(self) -> None:
        conn = await self._connect()
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()

    async def discover_schema(self) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            columns = [tuple(r) for r in await conn.fetch(_SCHEMA_SQL)]
            pks = {tuple(r) for r in await conn.fetch(_PK_SQL)}
        except asyncpg.PostgresError as e:
            raise ConnectorError(f"schema discovery failed: {e}") from e
        finally:
            await conn.close()
        return rows_to_tables(columns, pks)

    async def query(self, request: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        sql = request.get("sql")
        if not sql:
            raise ConnectorError("postgres query requires 'sql'")
        # Bound the scan server-side so `limit` caps memory, not just the
        # returned slice (fetch() otherwise materializes the whole result set).
        bounded = f"SELECT * FROM ({sql.rstrip().rstrip(';')}) _eiye_q LIMIT $1"
        conn = await self._connect()
        try:
            # readonly transaction makes writes fail server-side regardless of the SQL text
            async with conn.transaction(readonly=True):
                records = await conn.fetch(bounded, limit)
        except asyncpg.PostgresError as e:
            raise ConnectorError(f"query failed: {e}") from e
        finally:
            await conn.close()
        return [dict(r) for r in records]
