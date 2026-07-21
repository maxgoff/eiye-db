#!/usr/bin/env python
"""Point eiye_db at one of your datasources and see a governed, PII-redacted query.

Registers a datasource, discovers its schema, runs one read-only query through the
full governance chain (connector -> PII redaction -> audit), and prints the command
to connect a real agent over MCP. Everything runs in-process against a local SQLite
metadata store -- no server or port required for this walkthrough.

Examples:
  quickstart.py --name notes --type filesystem  --root ~/Documents/exports
  quickstart.py --name warehouse --type postgresql --dsn postgresql://user:pass@host/db
  quickstart.py --name api --type rest_api --url https://api.example.com

Run it via scripts/quickstart.sh, which sets up the venv + editable install for you.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"

try:
    from eiye_db import audit, db, registry, service
    from eiye_db.connectors import ConnectorError
    from eiye_db.models import DataSourceCreate
except ModuleNotFoundError:
    sys.exit(
        "eiye_db is not importable. Run via scripts/quickstart.sh, or set up the venv:\n"
        f"  cd {BACKEND} && python -m venv .venv && .venv/bin/pip install -e .\n"
        "then run this script with that interpreter (.venv/bin/python)."
    )

KEY_ID = "quickstart"


def build_config(args: argparse.Namespace) -> dict:
    if args.type == "filesystem":
        if not args.root:
            sys.exit("--root is required for --type filesystem")
        return {"root": str(Path(args.root).expanduser().resolve())}
    if args.type == "postgresql":
        if not args.dsn:
            sys.exit("--dsn is required for --type postgresql")
        return {"dsn": args.dsn}
    if args.type == "rest_api":
        if not args.url:
            sys.exit("--url is required for --type rest_api")
        return {"base_url": args.url}
    sys.exit(f"unsupported type: {args.type}")


def sample_request(dtype: str, table: str) -> dict:
    """A reasonable read-only query for the first discovered table."""
    if dtype == "postgresql":
        return {"sql": f"SELECT * FROM {table}"}
    # filesystem + rest_api both address by the table name (a relative path / endpoint).
    return {"path": table}


def register(name: str, dtype: str, config: dict):
    for ds in registry.list_all():
        if ds.name == name:
            print(f"→ reusing existing datasource '{name}' ({ds.id})")
            return ds
    ds = registry.create(DataSourceCreate(name=name, type=dtype, config=config))
    audit.record("create", "datasource", ds.id, KEY_ID, ds.id)
    print(f"→ registered '{name}' ({ds.id})")
    return ds


async def walkthrough(ds, args) -> None:
    print("\n[1/3] Testing the connection…")
    try:
        await service.test_connection(ds.id, KEY_ID)
        print("      ✓ connected")
    except ConnectorError as e:
        sys.exit(f"      ✗ connection failed: {e}")

    print("\n[2/3] Discovering the schema…")
    schema = await service.discover_schema(ds.id, KEY_ID)
    tables = schema["tables"]
    if not tables:
        print("      (no readable tables found — for a filesystem source, point --root at a")
        print("       directory containing CSV/text/PDF/XLSX files)")
        return
    for t in tables[:20]:
        fields = t.get("fields") or []
        if fields and fields[0].get("name") == "content":
            print(f"      • {t['name']}  [text/content]")
        else:
            cols = ", ".join(f["name"] for f in fields[:10])
            more = "" if len(fields) <= 10 else f" (+{len(fields) - 10} more)"
            print(f"      • {t['name']}  [{len(fields)} cols: {cols}{more}]")
    if len(tables) > 20:
        print(f"      … and {len(tables) - 20} more")

    request = json.loads(args.request) if args.request else sample_request(args.type, tables[0]["name"])
    print(f"\n[3/3] Governed query  →  {json.dumps(request)}  (limit {args.limit})")
    try:
        res = (await service.run_query(ds.id, request, args.limit, KEY_ID)).model_dump()
    except ConnectorError as e:
        print(f"      ✗ query failed: {e}")
        print("      Craft your own with --request '<json>' (e.g. '{\"sql\": \"SELECT ...\"}').")
        return

    print(f"      rows: {res['row_count']}   PII redacted: {res['pii_filtered']}   "
          f"redactions: {res['pii_counts'] or '{}'}")
    for row in res["rows"][:3]:
        text = json.dumps(row, ensure_ascii=False)
        print("      " + (text if len(text) <= 200 else text[:200] + " …"))
    print("\n      ^ emails/phones/etc. come back as [REDACTED:*]. Enable name/location")
    print("        redaction with:  pip install -e \".[ner]\" && python -m spacy download en_core_web_sm")
    print("        then set EIYE_PII_NER_ENABLED=true.")


def print_connect(db_url: str) -> None:
    py = sys.executable
    print("\n" + "─" * 68)
    print("Connect a real agent over MCP (same governance chain):\n")
    print(f"  claude mcp add eiye-db --scope local \\\n"
          f"    --env EIYE_DATABASE_URL={db_url} \\\n"
          f"    -- {py} -m eiye_db.mcp_server\n")
    print("  claude mcp list         # expect: eiye-db … ✓ Connected")
    print("  claude -p \"List eiye-db datasources, get the first one's schema, then query it.\"")
    print("\nView metrics/audit over REST (optional):\n")
    print(f"  EIYE_DATABASE_URL={db_url} {py} -m eiye_db.main   # then GET /api/v1/metrics")
    print("─" * 68)


def main() -> None:
    p = argparse.ArgumentParser(description="eiye_db quickstart", formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="a label for this datasource")
    p.add_argument("--type", required=True, choices=["filesystem", "postgresql", "rest_api"])
    p.add_argument("--root", help="filesystem: directory to expose (read-only)")
    p.add_argument("--dsn", help="postgresql: connection string")
    p.add_argument("--url", help="rest_api: base URL")
    p.add_argument("--limit", type=int, default=5, help="max rows for the sample query (default 5)")
    p.add_argument("--request", help="override the sample query with a JSON request object")
    p.add_argument("--db", help="metadata store URL (default: sqlite at backend/eiye.db)")
    args = p.parse_args()

    db_url = args.db or f"sqlite:///{BACKEND / 'eiye.db'}"
    db.configure(db_url)

    config = build_config(args)
    ds = register(args.name, args.type, config)
    asyncio.run(walkthrough(ds, args))
    print_connect(db_url)


if __name__ == "__main__":
    main()
