# eiye_db — Project Goals

## Vision

**eiye_db** is a semantic surface that helps organizations become AI-ready by providing safe, governed, and comprehensive access to all their data sources through a single orchestration layer. Organizations struggle with three core problems: discovering what data they have, connecting agents to it safely, and governing access at scale. eiye_db solves all three.

## Core Problem Statement

Organizations accumulate data across dozens of systems — databases, file stores, cloud services, email, CRM/ERP, repositories, logs, MCP servers, web APIs — but when they try to make this data available to AI agents, they face:

1. **Data Discovery Gap** — No unified view of what data sources exist, their schemas, and their structure
2. **Unsafe Agent Connection** — Agents either get no access (gaps → hallucination) or too much access (risk → breach)
3. **Governance Fragmentation** — Access control, PII handling, and audit trails are scattered across systems

## Mission

Build a composable, extensible framework that:
- Maps every data source an organization owns into a unified semantic surface
- Exposes that surface through natural language (orchestration agent), REST API, MCP servers, and programmatic interfaces
- Enforces PII detection/detraction, access control, and auditability at every query
- Scales from single-org deployments to multi-tenant SaaS

## Strategic Positioning

eiye_db sits at the intersection of three market trends:

| Trend | eiye_db's Response |
|-------|-------------------|
| AI agents need reliable data access | Semantic surface eliminates gaps that cause hallucination |
| Enterprises demand governance | Built-in PII, ABAC, audit — not bolted on later |
| MCP protocol adoption accelerates | Native MCP server exposure for agentic ecosystems |

## Architecture Goals

### 1. Extensible Data Source Registry

Support composable modules for every data source type an organization might use:

- **Databases**: PostgreSQL, MySQL, MongoDB, SQLite, Redis, Elasticsearch
- **File Systems**: Local filesystems, S3-compatible object stores, Google Drive, SharePoint
- **Cloud Storage**: AWS S3, Google Cloud Storage, Azure Blob
- **APIs**: REST endpoints, GraphQL schemas, SOAP services
- **Email**: IMAP/SMTP, Microsoft Exchange
- **Calendars**: Google Calendar, Microsoft 365 Calendar
- **CRM/ERP**: Salesforce, HubSpot, SAP, Oracle ERP
- **Repositories**: Git (GitHub, GitLab, Bitbucket)
- **Logs**: ELK stack, Splunk, CloudWatch
- **MCP Servers**: Native MCP server discovery and integration
- **Web Search**: Integrated search across public and private indexes
- **Document Formats**: CSV, Excel, Word, PDF, Markdown, JSON, XML

Each module is independently pluggable. Adding a new source type requires only implementing the connector interface.

### 2. Semantic Surface Layer

The semantic surface maps raw data sources into a unified representation:

- **Schema Discovery**: Automatic schema inference for each connected source
- **Structure Mapping**: Knowledge graph representation of relationships between data sources
- **Parameter Catalog**: Documented parameters, filters, and query patterns for each source
- **Type Normalization**: Cross-source type mapping (e.g., "customer_id" in SQL → "customerId" in API)

### 3. Orchestration Agent (Conductor)

A separate microservice using [strands-agents](https://github.com/strands-agents) that:

- Manages multi-turn conversations with context persistence across data sources
- Maintains awareness of all connected data sources and their capabilities
- Translates natural language queries into source-specific operations
- Caches results using proxy queries (cache hit → return; cache miss → pull from source)
- Persists conversation context for continuity across sessions

### 4. PII Detection & Detraction Engine

Built-in, extensible PII handling:

- **Detection**: Regex-based + spaCy NER + configurable custom patterns
- **Detraction**: Automatic anonymization/redaction of detected PII
- **Configurable**: Thresholds, pattern lists, and anonymization strategies per-source
- **Risk Scoring**: Per-query risk assessment with configurable action thresholds
- **Extensible**: Plugin architecture for custom PII types and detection rules

### 5. Access Control

Multi-threat model support:

- **ABAC (Attribute-Based)**: Primary access control for enterprise deployments
- **RBAC (Role-Based)**: For SMB/simple deployments
- **Hybrid**: Both ABAC and RBAC with fallback logic
- **API Key-based**: Current implementation, with stubs for OAuth2, mTLS, SAML
- **Tenant Isolation**: Multi-tenant support for SaaS deployment

### 6. Caching & Proxy Layer

Intelligent data caching:

- **Proxy Queries**: All queries route through cache layer first
- **Cache Hit**: Return cached result (sub-millisecond)
- **Cache Miss**: Pull from source, cache result, return to caller
- **Configurable TTL**: Per-source TTL policies
- **Backend Options**: Redis (production), in-memory (dev/test), file-based (offline)

### 7. MCP Server Exposure

Native MCP server for agentic ecosystems:

- Exposes all connected data sources as MCP tools
- Standardized tool definitions with schema documentation
- Supports both stdio and SSE transport modes
- Enables any MCP-compatible agent to query the semantic surface

### 8. REST API (FastAPI)

Programmatic access via REST:

- Full CRUD for datasource management
- Query execution endpoints
- PII detection/anonymization endpoints
- Access control policy management
- Health and status monitoring
- Audit log retrieval

### 9. Frontend UI (React)

Configuration, monitoring, and deployment interface:

- **Datasource Configuration**: Add, edit, test connections visually
- **Semantic Surface Explorer**: Browse discovered schemas and relationships
- **PII Dashboard**: View detected PII, risk scores, anonymization results
- **Access Control Manager**: Configure ABAC/RBAC policies
- **Monitoring Panel**: Real-time query metrics, cache hit rates, error rates
- **Deployment Configurator**: Switch between SaaS, single-org, and on-prem modes

## Deployment Goals

### Tier 1: Single Organization (SMB)

- **Target**: Organizations with up to 25 data sources
- **Mode**: Single-tenant, self-hosted or managed
- **Access Control**: API key-based with RBAC stubs
- **Pricing**: Usage-surface based (per datasource, per query volume)
- **Deployment**: Docker Compose, single binary

### Tier 2: Multi-Tenant SaaS

- **Target**: Organizations managing dozens of data sources across teams
- **Mode**: Multi-tenant with tenant isolation
- **Access Control**: Full ABAC with policy engine
- **Pricing**: Per-tenant + per-datasource + volume tiers
- **Deployment**: Kubernetes, auto-scaling

### Tier 3: Enterprise On-Premise

- **Target**: Regulated industries (finance, healthcare, government)
- **Mode**: Fully isolated, air-gapped capable
- **Access Control**: ABAC + RBAC hybrid with custom policy integration
- **Pricing**: Enterprise license + support contract
- **Deployment**: Custom infrastructure, dedicated instances

## Commercial Strategy

### Open-Core Model

| Component | License | Notes |
|-----------|---------|-------|
| Core semantic surface | OSS (Apache-2.0) | Foundation layer |
| Data source connectors | OSS | All standard connectors |
| PII engine | OSS | Detection + anonymization |
| ABAC engine | OSS | Policy engine |
| Orchestration agent | OSS | strands-agents integration |
| Frontend UI | OSS | React configuration panel |
| Advanced analytics | Commercial | Cross-source intelligence |
| Enterprise SSO | Commercial | SAML, OAuth2, LDAP |
| Audit & compliance | Commercial | SOC2, HIPAA, GDPR reports |
| Multi-tenant orchestration | Commercial | SaaS management plane |

### Pricing Tiers (Usage-Surface Based)

| Tier | Datasources | Queries/mo | Price | Target |
|------|-------------|------------|-------|--------|
| Free | Up to 5 | 1,000 | $0 | Evaluation |
| Starter | Up to 15 | 25,000 | $99/mo | Small teams |
| Pro | Up to 50 | 250,000 | $499/mo | Growing orgs |
| Business | Up to 150 | 1M | $1,999/mo | Mid-market |
| Enterprise | Unlimited | Custom | Custom | Large orgs |

### Try-and-Buy SaaS Path

- Free tier with 5 datasources and 1,000 queries/month
- In-app upgrade prompts when limits approached
- One-click migration to paid tiers
- No data lock-in — export all configuration

## Competitive Landscape

| Competitor | Strength | eiye_db Advantage |
|-----------|----------|-------------------|
| Data catalogs (Collibra, Alation) | Enterprise metadata management | Agent-native, not just cataloging |
| MCP tool servers | Standardized agent interfaces | Full semantic surface, not just tools |
| ETL platforms (Fivetran, Airbyte) | Data pipeline automation | Real-time query surface, not batch |
| API gateways (Kong, Apigee) | API management | Agent-aware, PII-governed access |
| OpenPlanter (internal) | Entity resolution, investigation | eiye_db is the data layer; OpenPlanter is a consumer |

## Integration with OpenPlanter Ecosystem

eiye_db generalizes **Pathway B** ("MCP-toolbox → OpenPlanter: Structured Data Access") from `OpenPlanter/strategic_integration_plan_v2.md` into a standalone product, inverting the dependency: OpenPlanter becomes a consumer of eiye_db rather than the hub. All integrations below are **planned**, not built:

```
CopyDrive → eiye_db (Semantic Surface) → ai-ministry / AutoResearchClaw
                              ↕
                      OpenPlanter Engine (embedded)
                              ↕
                    MCP Server Exposure
```

- **OpenPlanter's entity resolution logic** (name normalization + matching strategies from `OpenPlanter/scripts/entity_resolution.py`) will be extracted, generalized, and embedded in eiye_db as the cross-source linking layer — note: OpenPlanter has no packaged engine today; extraction is Phase 2 work
- **CopyDrive** feeds Google Drive documents into the semantic surface
- **MCP-toolbox** provides database connectivity primitives
- **first-principles-memory** provides persistent memory for the orchestration agent
- **strands-agents** powers the natural language conductor

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Data source types supported | 20+ | Connector registry count |
| Schema discovery accuracy | >95% | Manual audit of discovered schemas |
| PII detection recall | >98% | Benchmark against labeled datasets |
| Cache hit rate | >70% | Query metrics dashboard |
| Agent query success rate | >90% | Orchestration agent error tracking |
| Time to first datasource | <5 min | Configuration wizard benchmark |
| Multi-tenant isolation | Verified | Security audit results |

## Non-Goals (Explicitly Out of Scope)

- **Data transformation/ETL** — eiye_db exposes data; it doesn't transform pipelines
- **Data warehouse** — Not a storage layer; queries flow through to sources
- **Business intelligence dashboards** — That's a downstream consumer concern
- **Email marketing** — Email connector is for access, not campaigns
- **Hardware design** — Separate track (RJ/NewEternal)

## Next Steps (High-Level)

1. Complete Tier 1 datasource connectors (PostgreSQL, MongoDB, S3, Git, REST)
2. Build semantic surface schema discovery engine
3. Implement orchestration agent with strands-agents integration
4. Develop React frontend for configuration and monitoring
5. Add PII detection benchmarks and validation suite
6. Create deployment templates (Docker Compose, Helm chart)
7. Write integration tests across all connector types
8. Build MCP server tool definitions for all sources
9. Implement ABAC policy engine with test cases
10. Prepare SaaS multi-tenant architecture
