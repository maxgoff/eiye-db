"""Query/discovery orchestration shared by the REST API and the MCP server.

Every path through here enforces the governance chain:
connector (read-only) → PII redaction → audit trail.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder

from eiye_db import audit, pii, registry
from eiye_db.connectors import ConnectorError, get_connector
from eiye_db.models import ConnectionStatus, DataSource, SourceQueryResponse

QUERY_TIMEOUT_SECONDS = 30


class NotFoundError(Exception):
    pass


def _get_or_raise(datasource_id: str) -> DataSource:
    ds = registry.get(datasource_id)
    if ds is None:
        raise NotFoundError(f"datasource not found: {datasource_id}")
    return ds


async def test_connection(datasource_id: str, key_id: str) -> DataSource:
    ds = _get_or_raise(datasource_id)
    connector = get_connector(ds.type, ds.config)
    try:
        await connector.test_connection()
    except ConnectorError:
        registry.set_status(ds.id, ConnectionStatus.ERROR)
        audit.record("test_connection", "datasource", ds.id, key_id, ds.id, success=False)
        raise
    finally:
        await connector.close()
    registry.set_status(ds.id, ConnectionStatus.CONNECTED, connected=True)
    audit.record("test_connection", "datasource", ds.id, key_id, ds.id)
    return registry.get(ds.id)


async def discover_schema(datasource_id: str, key_id: str) -> dict[str, Any]:
    ds = _get_or_raise(datasource_id)
    connector = get_connector(ds.type, ds.config)
    try:
        tables = await connector.discover_schema()
    except ConnectorError:
        audit.record("discover_schema", "datasource", ds.id, key_id, ds.id, success=False)
        raise
    finally:
        await connector.close()
    schema = {
        "datasource_id": ds.id,
        "tables": tables,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }
    registry.set_schema(ds.id, schema)
    audit.record("discover_schema", "datasource", ds.id, key_id, ds.id, details={"tables": len(tables)})
    return schema


async def run_query(
    datasource_id: str,
    request: dict[str, Any],
    limit: int,
    key_id: str,
    include_pii: bool = False,
) -> SourceQueryResponse:
    ds = _get_or_raise(datasource_id)
    connector = get_connector(ds.type, ds.config)
    # Query text (SQL predicates, REST params) can itself contain PII — redact
    # before it is persisted to the audit trail.
    safe_request = pii.redact_structure(request)[0]
    start = time.monotonic()
    try:
        async with asyncio.timeout(QUERY_TIMEOUT_SECONDS):
            rows = await connector.query(request, limit)
    except (ConnectorError, TimeoutError):
        audit.record("query", "datasource", ds.id, key_id, ds.id, details={"request": safe_request}, success=False)
        raise
    finally:
        await connector.close()

    rows = jsonable_encoder(rows)
    pii_counts: dict[str, int] = {}
    if not include_pii:
        rows, pii_counts = pii.redact_structure(rows)

    # Build the response before auditing success so a serialization failure
    # is recorded as a failure, not a phantom success.
    response = SourceQueryResponse(
        datasource_id=ds.id,
        rows=rows,
        row_count=len(rows),
        pii_filtered=not include_pii,
        pii_counts=pii_counts,
        execution_time_ms=(time.monotonic() - start) * 1000,
    )
    audit.record(
        "query",
        "datasource",
        ds.id,
        key_id,
        ds.id,
        details={
            "request": safe_request,
            "rows": len(rows),
            "pii_redactions": sum(pii_counts.values()),
            "include_pii": include_pii,
        },
    )
    return response
