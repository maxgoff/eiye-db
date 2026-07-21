# eiye_db — TODO

**Strategy (decided 2026-07-20):** build vertically to a market-testable **Governed MCP Gateway** — one end-to-end path (register datasource → discover schema → governed query → MCP exposure) with three connectors covering distinct data shapes — then let market feedback drive breadth. The original 10-phase breadth-first plan is condensed under "Post-wedge backlog" and is gated on what the market test tells us.

**The wedge product:** any MCP-compatible agent (Claude Desktop/Code, Cursor, etc.) connects to eiye_db and gets governed access to an org's datasources: schema discovery, read-only queries, always-on PII redaction, API-key auth, and a full audit trail. No custom UI needed — the MCP client *is* the UI.

## Wedge: Governed MCP Gateway (market-testable)

### W0: Backend Core — DONE (M1)
- [x] Project scaffolding (FastAPI, pyproject.toml, requirements.txt)
- [x] Configuration management (pydantic-settings, `EIYE_` env prefix)
- [x] Core data models (DataSourceType, ConnectionStatus, PIIResult, etc.)
- [x] Health check endpoint (`/health`, `/api/v1/status`)

### W1: Datasource Registry & Persistence
- [x] SQLAlchemy + SQLite metadata store (datasources, audit log tables)
- [x] Registry CRUD: `POST/GET/PUT/DELETE /api/v1/datasources`
- [x] `POST /api/v1/datasources/{id}/test` — connection test, updates status

### W2: Connector Interface + Three Connectors
- [x] Async connector interface (`test_connection`, `discover_schema`, `query`)
- [x] PostgreSQL connector (asyncpg; queries run in read-only transactions)
- [x] Filesystem/CSV connector (root-scoped, path-traversal-safe, CSV schema inference)
- [x] REST API connector (GET-only, OpenAPI discovery when available)

### W3: PII Filtering (baseline)
- [x] Regex pattern library (email, phone, SSN, credit card w/ Luhn, IPv4)
- [x] Recursive redaction over arbitrary query results
- [x] `include_pii` honored only for the admin API key

### W4: Governance
- [x] API-key auth middleware (unset key = open dev mode)
- [x] Read-only enforcement per connector (PG read-only txn, REST GET-only, FS read-only)
- [x] Audit trail persisted for every query/discovery + `GET /api/v1/audit`

### W5: Query Path & Surface API
- [x] `POST /api/v1/query` — source-scoped query → connector → PII filter → audit
- [x] `POST /api/v1/datasources/{id}/discover` — schema discovery, persisted
- [x] `GET /api/v1/surface/sources`, `GET /api/v1/surface/schema/{id}`

### W6: MCP Server
- [x] stdio MCP server: `list_datasources`, `get_schema`, `query_datasource` tools
- [x] PII redaction + audit enforced on the MCP path (same service layer as REST)
- [x] Claude Desktop/Code connection instructions

### W7: Ship It
- [x] GitHub Actions CI (pytest on push/PR)
- [x] README 5-minute quickstart: register a CSV dir → query via curl → connect Claude via MCP
- [x] Demo dataset (`examples/demo_data/`) + walkthrough
- [x] Decide + instrument market-test metrics — `GET /api/v1/metrics` (admin-gated),
      derived from the audit trail: datasources, action counts, query success rate,
      PII redactions by type, first-datasource / first-successful-query timestamps

## Post-wedge backlog (market feedback gates these)

- **Connectors, breadth**: MySQL, MongoDB, SQLite, S3, Google Drive, IMAP/Exchange, GitHub/GitLab, Salesforce/HubSpot, SAP/Oracle, Snowflake/BigQuery, Splunk/CloudWatch, LDAP
- **Semantic surface**: cross-source relationship detection, knowledge graph, type normalization, parameter catalog; entity-resolution extraction from OpenPlanter (`scripts/entity_resolution.py` → generalized linking layer)
- **Orchestration agent ("Conductor")**: strands-agents, NL → multi-source query planning, first-principles-memory context persistence, unified `QueryRequest` NL interface
- **PII, advanced**: spaCy NER / presidio, custom pattern config, anonymization strategies (hashing, tokenization), benchmark suite
- **Access control**: ABAC policy engine, RBAC fallback, per-source key allowlists, OAuth2/mTLS, tenant isolation
- **Caching**: Redis/memory/file proxy layer, per-source TTL, invalidation
- **MCP, advanced**: SSE transport, MCP-to-MCP bridging, tool composition
- **Frontend (React)**: connection wizard, surface explorer, PII dashboard, policy manager, monitoring
- **Ops**: Alembic migrations (once registry schema stabilizes), loguru structured logging, Docker/Helm, Prometheus/Grafana
- **Commercial**: multi-tenant SaaS, metering/billing (Stripe), pricing pages, landing page, demo environment

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1: Core | Backend scaffolding + config + models | ✅ done |
| M2: Wedge | Governed MCP Gateway (W1–W7), market-testable | in progress |
| M3+: | Gated on market-test results | pending |
