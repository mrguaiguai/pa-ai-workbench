# WNFC-P2-03 MCP Approval-Gated Tool Execution Scope Report

Task: WNFC-P2-03
Date: 2026-06-24
Decision: REMOVED FROM CURRENT WNFC SCOPE
Evidence type: excluded evidence plus historical blocked evidence

## Scope

The user explicitly removed MCP service execution from the current WNFC 100%
scope on 2026-06-24 and said it should be iterated later.

This task is therefore marked `[b]`, not `[x]`. No MCP tool execution PASS is
claimed, and no mock MCP tool, fake endpoint, fixture tool list, or no-op
execution was used as completion evidence.

The previous WNFC-P2-03 requirement is preserved as historical context: at
least one low-risk real MCP tool would need to execute with:

- explicit human confirmation/approval;
- bounded execution timeout;
- native/PA audit or history evidence;
- masked output with no raw credentials, raw endpoint details, or provider
  payload leakage.

## Native Source Audit

Native WeKnora has MCP tool execution primitives:

- `internal/mcp/client.go`
  - `CallTool(ctx, name, args)` calls MCP `tools/call`.
- `internal/agent/tools/mcp_tool.go`
  - Wraps native MCP tools as Agent tools.
  - Calls the approval gate before `CallTool` when the tool approval policy
    requires approval.
  - Re-derives execution timeout after approval so the actual MCP tool call has
    a fresh bounded execution window.
  - Prefixes MCP output as untrusted data and redacts image payloads.
- `internal/agent/approval/gate.go`
  - Emits `tool_approval_required`.
  - Waits for approval, rejection, timeout, or cancellation.
  - Emits `tool_approval_resolved`.
- `internal/handler/mcp_service.go`
  - `PUT /api/v1/mcp-services/{id}/tool-approvals/{tool_name}` sets tool
    approval policy.
  - `POST /api/v1/agent/tool-approvals/{pending_id}` resolves a pending
    approval.
- `internal/handler/session/agent_stream_handler.go`
  - Persists `tool_approval_required` and `tool_approval_resolved` stream
    events for replay/history.

Native WeKnora does not expose a direct PA-safe endpoint such as
`POST /api/v1/mcp-services/{id}/tools/{tool}/execute`. The existing execution
path is inside the Agent loop and requires a real listed MCP tool, an Agent tool
call, and a pending approval event.

## Current Runtime Blocker

WNFC-P2-02 already proved the current MCP service cannot supply real
tools/resources/prompts evidence. P2-03 revalidated the tool-execution-specific
impact:

- PA can read native MCP service list/detail.
- PA can read approval policy metadata.
- The confirmation-gated native MCP test reaches the configured service but
  fails initialization.
- The current service exposes `tools=0`, so there is no low-risk real MCP tool
  available for execution.

Therefore a PA execution workflow would be fake unless a real initialized MCP
service with at least one safe tool is supplied, or native/runtime configuration
is fixed. This remains a future-iteration requirement, not a current WNFC final
readiness blocker.

## Prior PA Changes

Changed files:

- `backend/app/services/mcp_service.py`
  - Adds an explicit `tool_execution` blocked surface to MCP overview/detail
    and confirmed-test responses.
- `backend/app/services/native_status_service.py`
  - Adds `tool_execution_status` and `tool_execution_count` to the MCP native
    status summary.
- `backend/scripts/check_weknora_native_mcp_tool_execution.py`
  - Adds current-run blocker smoke.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to WNFC report inventory.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_mcp_tool_execution.py
```

Current-run output:

```text
WeKnora native MCP approval-gated tool execution
- decision: BLOCKED
- evidence_type: blocked evidence plus live api
- services: status=live count=1 approval=live
- confirmed_test: status=partial success=false tools=0
- tool_execution: blocked reason=no_live_mcp_tool_available
- current_service_blocker: Initialization failed: failed to initialize: transport error: server returned 4xx for initialize POST, likely a legacy SSE server
```

## Future Iteration Inputs

If MCP approval-gated tool execution is brought back into scope later, provide
or fix:

- A real reachable MCP service configured with the transport expected by the
  native WeKnora MCP client.
- At least one low-risk tool that can be listed by native
  `/api/v1/mcp-services/{id}/tools`.
- A deterministic invocation prompt or native execution path that triggers that
  low-risk tool.
- Approval policy set for that tool, followed by a real pending approval event,
  explicit approval, successful tool result, timeout evidence, and replayable
  history/audit evidence through PA.

No mock MCP tool, fake endpoint, fixture tool list, or no-op execution can count
as PASS in that later iteration.

## Status Impact

WNFC-P2-03 is `[b]` removed from the current WNFC 100% scope.

MCP service tools/resources/prompts list/read and approval-gated tool execution
are deferred for later iteration. The current scoped MCP requirement is limited
to the already-completed P2-01 CRUD/credential/status slice, so aggregate WNFC
score is now `13.00 / 14 = 92.9%`.
