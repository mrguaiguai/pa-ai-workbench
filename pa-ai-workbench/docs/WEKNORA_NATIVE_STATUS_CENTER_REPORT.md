# WeKnora Native Status Center Report

Task: `WNX-P0-02`

Date: 2026-06-23

Branch: `weknora-first-mvp`

## Decision

`PASS`

Evidence type: `live API evidence`.

This task adds a masked PA backend BFF status center at:

```text
/api/native/status
```

The status center aggregates current PA and WeKnora readiness into one safe
shape for the future capability/config center UI. It does not claim new
workflow coverage for backlog or mutation-heavy native platform areas.

## Implemented Contract

The new status center returns:

- `schema_version: wnx-p0-02`
- `source: pa_backend_bff`
- `evidence_type: live_api`
- top-level `configured` and `masked`
- masked config booleans for WeKnora, chat model, and embedding
- 15 capability groups matching the coverage ledger
- per-group `status`, `configured`, `masked`, `source_endpoint`,
  `native_endpoint`, `next_action`, and sanitized summary

No raw base URL, token, password, private endpoint, provider payload,
connection string, logs, local database path, chunks, vectors, or `.env` values
are returned.

## Live Smoke Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_native_status_center_live.py
```

Result:

- `PASS`
- PA endpoint: `/api/native/status`
- overview status: `partial`
- group count: `15`
- live groups: `7`
- partial groups: `5`
- blocked/backlog groups: `3`
- MCP/web/vector: `live/live/live`
- model status: `live`
- masked response: `True`

The top-level status is `partial` because the status center truthfully keeps
unimplemented or high-risk areas as `backlog`, rather than treating route
existence as capability PASS.

## Capability Group Summary

| Group | Status-center stance | Evidence boundary |
| --- | --- | --- |
| System health/status/deployment | Live status surface, deployment recovery still later. | `WNX-P0-05` owns recoverability. |
| Workspace/knowledge-base | Validated through existing status mapping. | KB management workflow remains `WNX-P1-01`. |
| Document lifecycle | Partial baseline. | Full workflow remains `WNX-P1-02`. |
| Chunk management | Partial/read path baseline. | Mutations remain `WNX-P1-03`. |
| Knowledge-search/RAG | Live baseline from existing native adapter path. | Knowledge-chat remains separate in `WNX-P1-04`. |
| Knowledge-chat/session chat | Backlog. | PA path not integrated yet. |
| AgentQA/custom Agent | Live after `WNX-P3-08`. | Current live AgentQA Wiki references are traceable and saved as PA citations. |
| Native Wiki | Partial. | Read-only surfaces exist; mutations remain backlog. |
| MCP | Live read-only status. | CRUD, credentials, tool execution, approval mutation remain `WNX-P2-02`. |
| Web search | Live read-only status. | Provider CRUD/test and credential flow remain `WNX-P2-03`. |
| Vector store | Live read-only status. | CRUD/test/rebind/raw config remain `WNX-P2-04`. |
| Model/embedding/rerank/parser | Live PA model/embedding readiness; native catalog/parser work remains backlog. | `WNX-P2-01` owns catalog/parser/rerank checks. |
| Data sources/connectors | Backlog. | Safe validate/resources/sync status remains `WNX-P2-05`. |
| FAQ/tags/favorites/skills | Backlog. | Workbench organization primitives remain `WNX-P2-06`. |
| History/citation/product shell | Partial. | Cross-workflow unification remains `WNX-P1-07`. |

## Safety Notes

- The API intentionally summarizes existing MCP/web/vector overviews instead of
  embedding raw items or provider payloads.
- `api_key_configured` and other configured flags are booleans only.
- `source_endpoint` and `native_endpoint` are route templates, not private
  deployment URLs.
- This report does not update the coverage score. It gives `WNX-P0-03` one
  backend contract to render truthfully and gives `WNX-P0-04` one API to check.

## Follow-Up Landing Zones

- `WNX-P0-03`: build the frontend capability center from `/api/native/status`.
- `WNX-P0-04`: add checker coverage for schema, evidence classification, and
  secret-safety of status center output.
- `WNX-P2-01`: expand live native model catalog, parser, and rerank readiness.
- `WNX-P2-05` and `WNX-P2-06`: replace backlog entries with sanitized live
  connector and organization-primitive status when scoped.
