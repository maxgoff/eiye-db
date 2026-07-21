"""REST API connector. GET-only; discovers schema from OpenAPI when available."""

from typing import Any

import httpx

from eiye_db.connectors.base import Connector, ConnectorError


class RestConnector(Connector):
    def __init__(self, config: dict[str, Any], transport: httpx.AsyncBaseTransport | None = None):
        super().__init__(config)
        self._transport = transport

    def _base_url(self) -> str:
        base_url = self.config.get("base_url")
        if not base_url:
            raise ConnectorError("rest_api config requires 'base_url'")
        return base_url.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url(),
            headers=self.config.get("headers", {}),
            timeout=15,
            transport=self._transport,
        )

    async def test_connection(self) -> None:
        try:
            async with self._client() as client:
                resp = await client.get("/")
        except httpx.HTTPError as e:
            raise ConnectorError(f"connection failed: {e}") from e
        if resp.status_code >= 500:
            raise ConnectorError(f"server error: HTTP {resp.status_code}")

    async def discover_schema(self) -> list[dict[str, Any]]:
        try:
            async with self._client() as client:
                resp = await client.get("/openapi.json")
        except httpx.HTTPError as e:
            raise ConnectorError(f"discovery failed: {e}") from e
        if resp.status_code != 200:
            return []
        try:
            spec = resp.json()
        except ValueError:
            return []
        tables = []
        for path, methods in spec.get("paths", {}).items():
            get_op = methods.get("get")
            if get_op is None:
                continue
            fields = [
                {"name": p.get("name", ""), "type": p.get("schema", {}).get("type", "string")}
                for p in get_op.get("parameters", [])
            ]
            tables.append({"name": path, "fields": fields})
        return tables

    async def query(self, request: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        path = request.get("path")
        if not path:
            raise ConnectorError("rest_api query requires 'path'")
        try:
            async with self._client() as client:
                resp = await client.get(path, params=request.get("params"))
        except httpx.HTTPError as e:
            raise ConnectorError(f"query failed: {e}") from e
        if resp.status_code >= 400:
            raise ConnectorError(f"HTTP {resp.status_code} from {path}")
        try:
            data = resp.json()
        except ValueError:
            return [{"content": resp.text[:100_000]}]
        if isinstance(data, list):
            return [d if isinstance(d, dict) else {"value": d} for d in data[:limit]]
        return [data]
