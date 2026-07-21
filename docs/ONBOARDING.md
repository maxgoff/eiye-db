# Onboarding — get up to speed fast

This file is the durable, in-repo orientation for any agent or engineer picking
up eiye_db cold. It captures the non-obvious operational facts that reading the
code alone won't give you. Read this, then `GOALS.md` (vision), `TODO.md`
(status), and the git log (`git log --stat`).

## What this is

A **semantic surface** that lets AI agents safely query an organization's data
sources. See `GOALS.md` for the full vision. What is actually **built** is a
narrower first product — the **Governed MCP Gateway** wedge:

> register a datasource → discover its schema → run a governed, read-only query
> → PII is redacted → the access is audited. Exposed over both a REST API and a
> stdio MCP server so any MCP-compatible agent (Claude Code/Desktop, Cursor)
> gets the datasource as tools.

The breadth in `GOALS.md`/`TODO.md` (more connectors, ABAC, Redis cache, React
UI, spaCy/NER, multi-tenancy, rate limiting) is a **deliberately deferred
post-wedge backlog**, gated on market feedback — not missing work. Do not treat
those as bugs.

## Strategy context (why the plan looks the way it does)

`TODO.md` originally had a breadth-first 10-phase plan. It was deliberately
replaced (commit `01531d7`) with the vertical W1–W7 wedge so there's one
end-to-end demoable path to market-test before building breadth. W1–W6 are done;
the one open W7 item is **choosing market-test metrics** (time-to-first-
datasource, queries/session, PII-hit rate) — a product decision, not code.

## Where things are

```
backend/eiye_db/
  main.py          FastAPI app (/health, /api/v1/status), lifespan configures the DB
  config.py        pydantic-settings, EIYE_ env prefix
  models.py        pydantic domain models (StrEnum, Literal-typed closed sets)
  db.py            SQLite metadata store (SQLAlchemy 2.x): datasources + audit_logs
  registry.py      datasource CRUD over the store
  service.py       ** the governance chain — shared by REST and MCP **
  security.py      API-key auth (dev mode when unset; admin key gates raw PII)
  audit.py         append-only audit trail
  pii.py           regex PII detection + recursive redaction
  connectors/      base.py + postgres.py, filesystem.py, rest.py, factory in __init__
  api.py           REST routes (/api/v1/...)
  mcp_server.py    stdio MCP server (FastMCP) — 3 tools, same service layer
backend/tests/     pytest suite (72 tests); conftest gives fresh DB + TestClient per test
examples/demo_data/  demo CSVs used by the README quickstart
.github/workflows/ci.yml  pytest + ruff on a 3.11/3.12 matrix
```

## Run and test

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                       # 72 pass, 2 skipped (live-PG, see below)
ruff check .                    # CI gates on this — keep it clean
uvicorn eiye_db.main:app --reload
python -m eiye_db.mcp_server     # the stdio MCP server
```

The README has the verified 5-minute quickstart (register demo CSVs → query →
see redaction + audit → connect an MCP client). Requires Python **3.11+**
(uses `StrEnum`, `X | Y` unions, `asyncio.timeout`).

## Load-bearing invariants — do not break these

This is a **security/governance product**. Three guarantees must hold on *every*
query path (REST and MCP). A gap in any is high-severity:

1. **Read-only.** Postgres runs inside a `readonly=True` transaction *and* wraps
   user SQL in a bounding subquery; filesystem is root-scoped + traversal-safe;
   REST is GET-only.
2. **PII redaction.** `pii.redact_structure` redacts keys **and** values **and**
   numeric scalars. `include_pii=True` is REST-admin-only; the **MCP path always
   redacts** (no opt-out). The query *request* is also redacted before it's
   audited (SQL predicates can contain PII).
3. **Audit trail.** Every create/test/discover/query is recorded, including
   failures. `GET /api/v1/audit` is admin-gated.

Both REST and MCP go through `service.py` precisely so these can't diverge. If
you add a connector or an interface, route it through `service.py`.

## Gotchas that cost time

- **`FastMCP`, not `MCPServer`.** The installed `mcp` SDK exposes
  `from mcp.server.fastmcp import FastMCP`. Newer docs show a renamed
  `MCPServer` — that import fails on the pinned version.
- **Shared registry across processes.** The API and the MCP server share the
  SQLite store via `EIYE_DATABASE_URL` (default `sqlite:///./eiye.db`, relative
  to cwd). MCP hosts spawn the server from an arbitrary cwd, so set an
  **absolute** path for both. See README.
- **Live-PG tests are gated** behind `EIYE_TEST_PG_DSN`; they skip without it.
- **`httpx`/starlette TestClient deprecation warning** is benign (it suggests a
  likely-typosquat `httpx2`; we intentionally did not install it).

## History you can't see from the code

eiye_db was scaffolded inside `../OpenPlanter` on 2026-07-20. Load-bearing facts:

- **Do not run `OpenPlanter/generate_eiye*.py`.** Those scripts would overwrite
  this repo with 39 files of never-executed, buggy generated code (import-time
  errors, unwired connectors, `eval()`). This backend was written fresh,
  test-first. Mine the generators for *design intent* only.
- The canonical clean `GOALS.md`/`TODO.md` came from `OpenPlanter/eiye_db/`; the
  originals here were shell-heredoc-mangled and restored (commit `8f43834`).
- OpenPlanter has **no packaged entity-resolution engine** — GOALS.md's claim
  that it's "embedded" is aspirational (Phase-2 extraction of ~150–200 lines).

## Working discipline (how this repo has been developed)

Every phase was **adversarially reviewed** (a find→verify multi-agent pass) and
the confirmed findings fixed with regression tests before moving on — that's how
the real PII-leak holes were caught (commit `b11baf8`). Continue this: after a
substantive change, review and verify, don't just ship.

## Fastest path back to context after a reboot

1. Read this file, then `git log --stat -8`.
2. `cd backend && source .venv/bin/activate && pytest -q` — green suite = the
   invariants above still hold.
3. `TODO.md` shows what's done (W1–W7) and the one open decision.
