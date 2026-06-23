# WeKnora Native Web Search Management Live Report

> Task: `WNX-P2-03`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P2-03` is PASS for safe live-partial web search management readiness.

PA now exposes a `wnx-p2-03` web search management overview backed by WeKnora
native provider APIs. The current live tenant has no configured web search
providers, so saved-provider detail, provider connection tests, and actual
AgentQA web-search readiness remain explicitly unconfigured/backlog in this
run. PA does not expose API keys, provider parameters, provider endpoints,
raw search results, raw provider payloads, credential forms, provider CRUD, or
raw credential tests.

## Native Audit

| Area | Source | Result |
| --- | --- | --- |
| Routes | `internal/router/router.go` | Provider catalog/list/detail are Viewer+; raw test, saved-provider test, CRUD, and credential subresource are Admin+. |
| Handler | `internal/handler/web_search_provider.go` | Saved-provider test performs a real external search with stored credentials; raw test accepts unsaved credential-bearing parameters. |
| Credentials | `internal/handler/web_search_provider_credentials.go` | Credentials are written through a dedicated subresource and only configured state is returned. |
| DTO | `internal/handler/dto/web_search_provider.go` | API key values are omitted, but engine/base/proxy URL and extra config can be returned by native DTO; PA strips these fields. |
| Runtime | `internal/application/service/web_search.go` | AgentQA/workflow search resolves provider configuration and performs external requests; readiness cannot be claimed from provider catalog alone. |

## PA Surfaces

| Surface | PA endpoint | Live result |
| --- | --- | --- |
| Overview | `/api/web-search/native/overview` | `status=partial`, `provider_types.status=live`, `provider_types.count=7`, `configured_providers.count=0`, `provider_test.status=backlog`. |
| Provider detail | `/api/web-search/native/providers/{provider_id}` | Implemented as a sanitized read path; not exercised live because no provider is configured. |
| Provider test | `/api/web-search/native/providers/{provider_id}/test` | Confirmation-gated and not executed in this live run because no provider is configured. |
| AgentQA readiness | `/api/web-search/native/overview` | `agentqa_dependency.status=optional_unconfigured`; PA does not claim AgentQA web-search readiness. |
| Capability Center | `/api/native/status`, `/#/capabilities` | Web search group renders `provider_test_status`, `provider_read_status`, and `agentqa_dependency_status`. |

## Validation

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_web_search_management.py --browser
```

Result:

```text
WeKnora native web search management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- provider_types: status=live count=7
- configured_providers: status=live count=0 ready=0
- provider_read: backlog detail=not_configured
- provider_test: overview=backlog blocked_path=backlog confirmed_path=not_requested
- agentqa_dependency: optional_unconfigured
- mutations: backlog
- browser: Capability Center rendered web search management readiness
```

## Evidence Boundary

Live evidence:

- PA reached WeKnora native provider type catalog and configured-provider list.
- Capability Center rendered the current-run web search management summary from
  `/api/native/status`.
- Response masking excludes credential values, provider parameters, endpoints,
  raw provider payloads, raw search results, and raw test errors.

Backlog evidence:

- The tenant has no configured web search provider, so saved-provider detail and
  test cannot be counted as live PASS in this run.
- Provider create/update/delete, credential forms, raw credential tests, raw web
  search debugging, and PA-owned search orchestration remain backlog until a
  separate approval, audit, and rollback design is accepted.

Blocked evidence:

- No native runtime blocker was observed for provider type/list readiness.
- No external web search provider test was run without explicit operator
  confirmation.

## Coverage

Web search moves from `read-only` to `live-partial`:

```text
10.25 / 15 = 68.3%
```

The increase is only `+0.25`; this report does not claim full provider
management or AgentQA web-search readiness because no provider is configured
and external tests/mutations remain confirmation-gated or backlog.
