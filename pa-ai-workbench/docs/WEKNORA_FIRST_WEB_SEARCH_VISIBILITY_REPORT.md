# WeKnora-First Web Search Visibility Report

> Task: `WF-P2-02`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live PA API + live WeKnora native read-only web search visibility.

## Scope

`WF-P2-02` exposes read-only WeKnora native web search provider readiness in
PA. PA does not implement provider CRUD, credential forms, connection tests,
raw web search debugging, or independent PA-owned web search orchestration in
this task.

The intended PA surface is truthful status:

- list supported native web search provider types
- count configured tenant providers when safe
- label AgentQA web search as optional, unavailable, or backlog
- keep credential and mutation surfaces blocked/backlog
- avoid leaking API keys, base URLs, proxy URLs, engine IDs, extra config,
  provider credentials, raw provider payloads, local paths, or endpoints

## Native Source Audit

| Area | Source | Finding |
| --- | --- | --- |
| Route registration | `internal/router/router.go` | `GET /api/v1/web-search/providers`, `GET /api/v1/web-search-providers/types`, `GET /api/v1/web-search-providers`, and `GET /api/v1/web-search-providers/:id` are Viewer+ read-only routes. Provider CRUD, credentials, and tests are Admin+. |
| Provider type catalog | `internal/handler/web_search.go`, `internal/handler/web_search_provider.go`, `internal/types/web_search_provider.go` | Provider type metadata lists supported provider families and requirements. PA surfaces only type/count/readiness flags. |
| Configured provider DTO | `internal/handler/dto/web_search_provider.go` | The native DTO omits API key values but can expose non-secret parameters such as base/proxy URL, engine ID, extra config, and credential field names. PA strips those fields. |
| Runtime service | `internal/application/service/web_search.go` | Actual search and RAG compression use provider credentials and external calls. PA does not call search/test flows in this task. |
| AgentQA relation | `internal/application/service/session_knowledge_qa.go`, `internal/application/service/session_agent_qa.go` | Web search is enabled by request/agent config and provider selection; this task does not prove that web search is required for AgentQA. |

## PA API Shape

New endpoint:

```text
GET /api/web-search/native/overview?limit=5
```

Response categories:

- `status`: `live`, `blocked`, or `backlog`
- `provider_types`: live supported provider catalog count and safe type flags
- `configured_providers`: live configured-provider count, default count, and credential-configured count
- `agentqa_dependency`: `optional`, `optional_unconfigured`, `blocked`, or `backlog`
- `mutations`: backlog list for provider CRUD, credentials, connection tests, raw search debugging, and PA-owned orchestration

Frontend status strip now reads the endpoint and shows a `Web search` chip plus
provider type/configured-provider counts.

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_web_search_visibility_live.py
```

Sanitized output:

```text
WeKnora web search visibility smoke passed (live)
- PA endpoint: /api/web-search/native/overview
- overview status: live
- provider types status/count: live/7
- configured providers status/count/default: live/0/0
- credentials configured count: 0
- AgentQA web search status: optional_unconfigured
- mutations status: backlog
- sanitized response: True
```

Browser validation:

- The shared PA status strip loads `/api/web-search/native/overview`.
- The `Web search` chip renders the live web search status.
- Details include web search provider type count, configured-provider count,
  and AgentQA dependency status.

## Evidence Classification

| Status | Meaning in this task |
| --- | --- |
| live | Used for PA `/api/web-search/native/overview`, provider type catalog, and configured-provider list. |
| optional_unconfigured | AgentQA exposes web search controls, but the current tenant has no configured provider. |
| blocked | Would apply if read-only provider catalog or provider list could not be queried safely. Not observed. |
| backlog | Provider CRUD, credential forms, connection tests, raw search debugging, and PA-owned web search orchestration remain backlog by design. |

## Safety Boundary

PA does not expose these web search fields:

- API key
- credential field names
- provider parameters
- base URL
- proxy URL
- engine ID
- extra config
- provider docs URL
- raw provider payloads
- connection-test responses

The report and smoke output also avoid private endpoints, service tokens, local
database paths, logs, caches, and raw secrets.

## PASS Statement

`WF-P2-02` passes for read-only native web search provider visibility. PA can
now show supported provider catalog readiness and configured-provider count, and
it truthfully labels AgentQA web search as optional but unconfigured in the
current tenant.

Credential management, provider mutation, connection tests, raw web search
debugging, and PA-owned web search orchestration remain explicit backlog.
