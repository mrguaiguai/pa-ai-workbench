# WeKnora Native Client Report

Task: `WNX-P0-01`

Date: 2026-06-23

Branch: `weknora-first-mvp`

## Decision

`PASS`

Evidence type:

- `live evidence`: current PA backend calls real WeKnora through existing native
  visibility endpoints.
- `fixture evidence`: local HTTP fixture proves shared-client routing, status
  metadata, retry/error behavior, and redaction branches.

## Implemented Contract

`knowledge_engine/backends/weknora_api_backend.py` now has an explicit
`WeKnoraNativeClient` used by `WeKnoraApiBackend`.

The shared client owns:

- base URL and service token presence checks without exposing values;
- timeout and retry settings;
- JSON, multipart, and SSE request entrypoints;
- auth header application;
- per-request trace id logging through the existing WeKnora adapter logger;
- response JSON parsing;
- typed `WeKnoraUnavailableError` mapping;
- sanitized error messages and log excerpts;
- a safe `native_client_status()` shape with `schema_version: wnx-p0-01`.

`WeKnoraApiBackend` keeps the public PA adapter methods stable while delegating
the low-level request calls to `backend.client`.

## Shared Paths Proved By Fixture

`backend/scripts/smoke_weknora_native_client_contract.py` proves these existing
native adapter methods use the same `request_json` contract:

| Existing PA adapter method | WeKnora path class | Evidence |
| --- | --- | --- |
| `health()` | `/health` | Fixture call counted through `backend.client.request_json`. |
| `list_mcp_services()` | `/api/v1/mcp-services` | Fixture call counted through `backend.client.request_json`. |
| `list_vector_store_types()` | `/api/v1/vector-stores/types` | Fixture call counted through `backend.client.request_json`. |

The same delegation path is also used by document lifecycle, chunk listing,
native search, Wiki, AgentQA session creation, web search provider visibility,
MCP visibility, and vector store visibility because those methods call the same
`_request_json`, `_request_multipart_json`, or `_request_sse_json` adapter
entrypoints.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_mcp_visibility_live.py
```

Result:

- `PASS`
- PA endpoint: `/api/mcp/native/overview`
- overview status: `live`
- services status/count/enabled: `live/0/0`
- tools status/count: `backlog/0`
- resources status/count: `backlog/0`
- approval status/count/required: `backlog/0/0`
- mutations status: `backlog`
- sanitized response: `True`

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_vector_store_visibility_live.py
```

Result:

- `PASS`
- PA endpoint: `/api/vector-stores/native/overview`
- overview status: `live`
- store types status/count: `live/7`
- stores status/count/env/user: `live/1/1/0`
- KB binding status/source/engine: `available/env/postgres`
- embedding status/provider/mock: `live/openai_compatible/False`
- mutations status: `backlog`
- sanitized response: `True`

## Fixture Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_native_client_contract.py
```

Result:

- `PASS`
- client: `WeKnoraNativeClient`
- shared paths:
  - `/health`
  - `/api/v1/mcp-services`
  - `/api/v1/vector-stores/types`
- status schema: `wnx-p0-01`
- trace metadata declared: `True`
- client status hides service token and base URL value
- public error hides service token
- auth error retry flag remains stable

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_adapter_errors_m2.py
```

Result:

- `PASS`
- 401/403 auth errors remain typed and non-retryable.
- 404 remains typed as not-found and non-retryable.
- 429 and 5xx remain retryable.
- timeout and network errors remain retryable.
- invalid JSON remains a response mapping error without retry.
- fixture token remains redacted from error strings.

## Safety Notes

- No `.env` values, service tokens, provider payloads, connection strings,
  vectors, chunks, logs, uploads, databases, screenshots, or private keys are
  written by this report.
- `native_client_status()` exposes booleans and policy metadata only; it does
  not expose base URL, token, workspace id, or KB id values.
- MCP execution/mutation, vector-store mutation/test, and other unsafe platform
  operations remain backlog until covered by explicit WNX tasks and confirmation
  rules.

## Follow-Up Landing Zones

- `WNX-P0-02` can reuse `native_client_status()` for the internal config/status
  center.
- `WNX-P1-02` can build document lifecycle status/spans/chunks on the shared
  timeout/retry/error contract.
- `WNX-P1-04` and `WNX-P1-05` can use the same request/SSE contract for native
  RAG, knowledge-chat, AgentQA, and custom Agent workflows.
- `WNX-P2-02`, `WNX-P2-03`, and `WNX-P2-04` should keep using this client
  rather than creating capability-specific HTTP helpers.
