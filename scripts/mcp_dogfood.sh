#!/usr/bin/env bash
# Dogfood eiye_db's governed MCP surface with Claude Code headless (claude -p).
# Claude drives the tools: list_datasources -> get_schema -> query_datasource,
# and receives PII-redacted rows through the same governance chain as REST.
# Then prints the metrics the run produced.
set -euo pipefail

# --- config ---------------------------------------------------------------
REPO="/Users/maxgoff/eiye_db"
BACKEND="$REPO/backend"
VENV_PY="$BACKEND/.venv/bin/python"
DB_URL="sqlite:///$BACKEND/eiye.db"          # sqlite:/// + /abs -> sqlite:////abs
DEMO_ROOT="$REPO/examples/demo_data"
TOOLS=(mcp__eiye-db__list_datasources mcp__eiye-db__get_schema mcp__eiye-db__query_datasource)
PROMPT='Using the eiye-db MCP server: call list_datasources, then call get_schema on the id of the first datasource, then call query_datasource on that datasource with request={"path":"customers.csv"} and limit 5. Report the datasource list, the schema tables, and the returned rows.'

# --- preflight ------------------------------------------------------------
command -v claude >/dev/null || { echo "✗ claude CLI not on PATH"; exit 1; }
[ -x "$VENV_PY" ] || { echo "✗ venv python missing: $VENV_PY"; echo "  fix: cd $BACKEND && python3 -m venv .venv && .venv/bin/pip install -e ."; exit 1; }

echo "→ ensuring a demo datasource exists in $BACKEND/eiye.db …"
EIYE_DATABASE_URL="$DB_URL" DEMO_ROOT="$DEMO_ROOT" "$VENV_PY" - <<'PY'
import os
from eiye_db import db, registry, audit
from eiye_db.models import DataSourceCreate
db.configure()
if not any(d.name == "demo-customers" for d in registry.list_all()):
    ds = registry.create(DataSourceCreate(
        name="demo-customers", type="filesystem",
        config={"root": os.environ["DEMO_ROOT"]}))
    audit.record("create", "datasource", ds.id, "seed", ds.id)
    print("  seeded", ds.id)
else:
    print("  already present")
PY

echo "→ checking eiye-db MCP server is connected …"
if ! claude mcp list 2>&1 | grep -q 'eiye-db.*Connected'; then
  echo "✗ eiye-db MCP server not connected. Register it with:"
  echo "  claude mcp add eiye-db --scope local --env EIYE_DATABASE_URL=$DB_URL -- $VENV_PY -m eiye_db.mcp_server"
  exit 1
fi
echo "✓ eiye-db connected"

# --- run the agent --------------------------------------------------------
echo
echo "=== claude -p (Claude chooses and calls the MCP tools) ==="
claude -p "$PROMPT" --allowedTools "${TOOLS[@]}"

# --- show the metrics the run produced (REST-only endpoint) ---------------
echo
echo "=== GET /api/v1/metrics ==="
if ! curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  EIYE_DATABASE_URL="$DB_URL" "$VENV_PY" -m eiye_db.main >/tmp/eiye_metrics_server.log 2>&1 &
  SRV=$!
  trap 'kill "$SRV" 2>/dev/null || true' EXIT
  for _ in $(seq 1 30); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; sleep 0.2; done
fi
curl -s http://localhost:8000/api/v1/metrics | python3 -m json.tool \
  || echo "(metrics fetch failed; see /tmp/eiye_metrics_server.log)"
