# WNFC-P2-02 MCP Tools, Resources, and Prompts Scope Report

Task: WNFC-P2-02
Date: 2026-06-24
Decision: REMOVED FROM CURRENT WNFC SCOPE
Evidence type: excluded evidence plus historical blocked evidence
Current WNFC score: 13.00 / 14 = 92.9%

## Scope

The user explicitly removed MCP service tools/resources/prompts list/read from
the current WNFC 100% scope on 2026-06-24 and said it should be iterated later.

This task is therefore marked `[b]`, not `[x]`. No MCP tool/resource/prompt PASS
is claimed, and no mock MCP service, demo endpoint, fixture tool list, or
fabricated prompt surface was used as completion evidence.

The previous blocker evidence is preserved as historical context:

- Native WeKnora exposes tools and resources routes, but no native MCP prompts
  list/read route or prompt type/client interface was found.
- The currently configured MCP service is visible through PA/native service
  list/detail, but the confirmation-gated connection test does not initialize
  successfully, so it does not provide real tool/resource list evidence.

## Native Source Audit

Native MCP routes found:

- `GET /api/v1/mcp-services/{id}/tools`
- `GET /api/v1/mcp-services/{id}/resources`

Native service/client support found:

- `mcpServiceService.GetMCPServiceTools`
- `mcpServiceService.GetMCPServiceResources`
- `client.ListTools`
- `client.ListResources`

Native prompts support not found:

- No `GET /api/v1/mcp-services/{id}/prompts` route.
- No `MCPPrompt` type.
- No `ListPrompts` or prompt read method in the native MCP service interface.

Because prompts were part of the original WNFC-P2-02 surface, this remains a
native API gap for any future MCP service iteration.

## Prior PA Changes

Changed files:

- `backend/app/services/mcp_service.py`
  - Adds an explicit `prompts` surface with `status=blocked` and
    `reason=native_mcp_prompt_api_missing`.
  - Keeps tools/resources behind the existing confirmation-gated external probe
    boundary.
  - Preserves a sanitized failed test `reason` so runtime blockers can be
    diagnosed without leaking raw endpoint or credential fields.
- `backend/app/services/native_status_service.py`
  - Adds `prompts_status` and `prompts_count` to the MCP status summary.
- `knowledge_engine/backends/weknora_api_backend.py`
  - Preserves a sanitized native MCP test failure reason.
- `backend/scripts/check_weknora_native_mcp_resources_tools_prompts.py`
  - Adds current-run blocker smoke.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_mcp_resources_tools_prompts.py
```

Current-run output:

```text
WeKnora native MCP tools/resources/prompts
- decision: BLOCKED
- evidence_type: blocked evidence plus live api
- services: status=live count=1 detail=live
- confirmed_test: status=partial success=false tools=0 resources=0
- prompts: blocked reason=native_mcp_prompt_api_missing
- current_service_blocker: Initialization failed: failed to initialize: transport error: server returned 4xx for initialize POST, likely a legacy SSE server
```

## Diagnosis

The current blocker is not a PA-only mapping issue:

- PA can read the native MCP service list/detail.
- PA can call the confirmation-gated native test path.
- Native test reaches the configured service but initialization fails before
  real tools/resources can be listed.
- Native WeKnora lacks the required prompt route/interface entirely.

The likely required next inputs/changes are:

- A real reachable MCP service configured with the correct transport for the
  native client, returning non-empty or at least successfully listed
  tools/resources. The current service still fails initialization with
  `server returned 4xx for initialize POST, likely a legacy SSE server`, so PA
  needs either the correct streamable HTTP endpoint or an explicit update to
  configure the service as legacy SSE where appropriate.
- A native prompt list/read API, or a documented native-equivalent prompt
  surface. Adding this would be a controlled native exception and would require
  Go tests plus PA live API evidence before WNFC-P2-02 can close.

## Future Iteration Inputs

If MCP service tools/resources/prompts are brought back into scope later,
provide one of these paths:

1. A real MCP service endpoint that WeKnora can reach locally, with transport
   type (`http-streamable` or `sse`), service name, and whether credentials are
   needed. The service must initialize successfully and expose at least one
   readable tool or resource. Put any secret value in an ignored local env/config
   file, not in chat or Git.
2. If the current configured service is the intended service, confirm the
   correct transport and endpoint shape for it. The live error indicates a
   likely streamable-HTTP-vs-legacy-SSE mismatch.
3. Decide whether MCP prompts are mandatory for the later PA product scope. If
   yes, WNFC-P2-02 needs a native WeKnora prompt list/read API contract before
   PASS. If no, keep prompts outside that future scope too.

## Status Impact

WNFC-P2-02 is `[b]` removed from the current WNFC 100% scope.

MCP remains `live-partial`; aggregate WNFC score is current
`13.00 / 14 = 92.9%` after `WNFC-P2-03` was also removed from scope.

`WNFC-P2-03` remains a separate in-scope MCP tool-execution blocker until the
user explicitly removes it or a real low-risk MCP tool becomes available.
