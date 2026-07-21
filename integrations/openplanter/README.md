# OpenPlanter ↔ eiye_db bridge

A REST bridge that lets the [OpenPlanter](https://github.com/ShinMegamiBoson/OpenPlanter)
agent consume eiye_db's governed data surface as three agent tools. It exists to
**dogfood the wedge with a local, non-Claude agent** — proof that the governance
layer (read-only, PII redaction, audit) is provider-agnostic.

This directory holds the integration as a **patch owned by eiye_db**, not a fork.
OpenPlanter is a separate upstream repo we don't control, so we keep our changes
here (provenance + reproducibility) and leave OpenPlanter pristine.

## What the patch adds

`eiye-bridge.patch` — 4 files, 151 insertions, 0 deletions, no new dependencies
(stdlib `urllib` only):

| File | Change |
|------|--------|
| `agent/tool_defs.py` | +3 tool schemas: `eiye_db_list_datasources`, `eiye_db_get_schema`, `eiye_db_query` |
| `agent/tools.py` | `_eiye_request` helper + 3 handler methods on `WorkspaceTools` |
| `agent/engine.py` | +3 dispatch branches in `_apply_tool_call` |
| `tests/test_tool_defs.py` | tool-inventory assertion updated (+3 names) |

Design notes:
- The bridge **never sends `include_pii`**, so eiye_db always redacts and audits.
- `eiye_db_query`'s `request` arg is a **JSON object encoded as a string** (e.g.
  `'{"path": "customers.csv"}'`). OpenPlanter feeds schemas to both OpenAI strict
  mode (which forbids free-form objects) and Anthropic, so a string is the only
  cross-provider-safe shape. Small local models are unreliable at producing this
  double-encoded arg — prefer Claude or a large tool-tuned model (qwen2.5-coder
  32B, llama3.3 70B). eiye_db's *native MCP* `query_datasource` takes a real
  object and has no such constraint.

## Config (env, read by the handlers)

| Var | Default | Purpose |
|-----|---------|---------|
| `EIYE_DB_URL` | `http://localhost:8000/api/v1` | eiye_db REST base URL |
| `EIYE_DB_API_KEY` | _(unset)_ | optional `X-API-Key` (unset = open dev mode) |

## Apply

```sh
git clone https://github.com/ShinMegamiBoson/OpenPlanter.git
cd OpenPlanter
git apply /path/to/eiye_db/integrations/openplanter/eiye-bridge.patch
python -m pytest tests/test_tool_defs.py -q     # 20 passed
```

## Run the dogfood

```sh
# 1. start eiye_db and register a datasource with PII (see examples/demo_data)
# 2. drive it with a local model through OpenPlanter:
ollama serve && ollama pull qwen2.5-coder
python -m agent --provider ollama --model qwen2.5-coder --reasoning-effort none \
  --task "List eiye_db datasources, get the schema of the first, then query it."
# or with Claude (OpenPlanter's default backend), set ANTHROPIC_API_KEY and:
python -m agent --provider anthropic --model claude-opus-4-6 --task "...same..."
```

## When you *don't* need this bridge

To dogfood the **actual product surface (MCP)** with Claude Code, skip OpenPlanter
entirely — eiye_db ships a stdio MCP server. See the repo README's MCP section:
`claude mcp add eiye-db -- .../.venv/bin/python -m eiye_db.mcp_server`, then
`claude -p "..."`. Same governance chain, no bridge, no fork.

## Regenerating the patch

The bridge lives in the working tree at `../OpenPlanter`. To refresh after edits:

```sh
git -C ../OpenPlanter diff \
  agent/tools.py agent/tool_defs.py agent/engine.py tests/test_tool_defs.py \
  > integrations/openplanter/eiye-bridge.patch
```

Patch anchors are additive (inserted before `list_artifacts` / the `Unknown
action type` fallback), so it can bit-rot if upstream refactors those spots —
`git apply --check` against a fresh clone before demoing.
