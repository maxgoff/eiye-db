"""Filesystem connector: CSV and text files under a configured root."""

import csv
from pathlib import Path
from typing import Any

from eiye_db.connectors.base import Connector, ConnectorError

_TEXT_SUFFIXES = {".txt", ".md", ".log", ".json"}
_MAX_FILES = 1000
_SAMPLE_ROWS = 20


def infer_type(values: list[str]) -> str:
    non_empty = [v for v in values if v != ""]
    if not non_empty:
        return "string"
    try:
        for v in non_empty:
            int(v)
        return "integer"
    except ValueError:
        pass
    try:
        for v in non_empty:
            float(v)
        return "number"
    except ValueError:
        return "string"


class FilesystemConnector(Connector):
    def _root(self) -> Path:
        root = self.config.get("root")
        if not root:
            raise ConnectorError("filesystem config requires 'root'")
        return Path(root).resolve()

    def _resolve(self, rel_path: str) -> Path:
        root = self._root()
        target = (root / rel_path).resolve()
        if root != target and root not in target.parents:
            raise ConnectorError(f"path escapes datasource root: {rel_path}")
        return target

    async def test_connection(self) -> None:
        root = self._root()
        if not root.is_dir():
            raise ConnectorError(f"root is not a directory: {root}")

    async def discover_schema(self) -> list[dict[str, Any]]:
        root = self._root()
        if not root.is_dir():
            raise ConnectorError(f"root is not a directory: {root}")
        tables = []
        count = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            count += 1
            if count > _MAX_FILES:
                break
            rel = str(path.relative_to(root))
            if path.suffix.lower() == ".csv":
                tables.append({"name": rel, "fields": self._csv_fields(path)})
            elif path.suffix.lower() in _TEXT_SUFFIXES:
                tables.append({"name": rel, "fields": [{"name": "content", "type": "text"}]})
        return tables

    def _csv_fields(self, path: Path) -> list[dict[str, Any]]:
        try:
            with path.open(newline="", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return []
                samples: list[list[str]] = [[] for _ in header]
                for i, row in enumerate(reader):
                    if i >= _SAMPLE_ROWS:
                        break
                    for col, value in enumerate(row[: len(header)]):
                        samples[col].append(value)
            return [{"name": h, "type": infer_type(samples[i])} for i, h in enumerate(header)]
        except OSError as e:
            raise ConnectorError(f"cannot read {path.name}: {e}") from e

    async def query(self, request: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        rel_path = request.get("path")
        if not rel_path:
            raise ConnectorError("filesystem query requires 'path'")
        target = self._resolve(rel_path)
        if not target.is_file():
            raise ConnectorError(f"no such file: {rel_path}")
        try:
            if target.suffix.lower() == ".csv":
                with target.open(newline="", errors="replace") as f:
                    # restkey keeps overflow cells from ragged rows under a
                    # string key instead of None (which breaks JSON serialization).
                    reader = csv.DictReader(f, restkey="_extra")
                    return [row for _, row in zip(range(limit), reader)]
            return [{"content": target.read_text(errors="replace")[:100_000]}]
        except OSError as e:
            raise ConnectorError(f"cannot read {rel_path}: {e}") from e
