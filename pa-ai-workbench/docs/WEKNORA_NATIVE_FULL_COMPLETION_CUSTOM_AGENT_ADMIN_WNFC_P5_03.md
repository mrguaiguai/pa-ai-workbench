# WNFC-P5-03 Custom Agent Admin Residual Evidence

Task: `WNFC-P5-03: Custom Agent admin residual closure`

Decision: `[x]` complete

Evidence type: live API/browser plus audit proof

## Scope

WNFC-P5-03 closes the residual custom Agent admin backlog without changing
WeKnora Go code. PA now exposes confirmation-gated native custom Agent
create/update/copy/delete through the PA BFF, records every mutation in
`NativeMutationAudit`, and renders the Agent admin readiness surface in the
Analysis page.

Web Search remains explicitly out of scope and disabled in the PA mutation
payload sanitizer.

## Native Source Audit

Native WeKnora already exposes the required API surface:

- `internal/router/router.go`
  - `POST /api/v1/agents` is Contributor+.
  - `PUT /api/v1/agents/:id` is `OwnedAgentOrAdmin`.
  - `DELETE /api/v1/agents/:id` is `OwnedAgentOrAdmin`.
  - `POST /api/v1/agents/:id/copy` is Contributor+ and the copied Agent is
    owned by the caller.
- `internal/handler/custom_agent.go`
  - `CreateAgent`, `UpdateAgent`, `DeleteAgent`, and `CopyAgent` return native
    live responses and reject invalid targets.
- `internal/application/service/custom_agent.go`
  - create/update/delete enforce tenant context, built-in Agent protections,
    and creator ownership.
  - copy creates a new non-built-in custom Agent with copied config and caller
    ownership.
- `internal/types/custom_agent.go`
  - `CustomAgentConfig` contains the runtime config fields PA passes through;
    PA forces `web_search_enabled=false` for WNFC.

No controlled native exception lane was needed, so no Go test was added for
this task.

## PA Changes

- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds native custom Agent get/create/update/copy/delete adapter methods.
  - Sanitizes mutation payloads and forces `web_search_enabled=false`.
- `backend/app/services/native_agent_service.py`
  - Adds `CONFIRM_NATIVE_AGENT_MUTATION`.
  - Adds PA BFF create/update/copy/delete service functions.
  - Requires confirm_token before mutation.
  - Records `NativeMutationAudit` with capability `custom_agent`.
  - Marks catalog surfaces `copy`, `mutations`, and ownership as live.
- `backend/app/api/analysis.py`
  - Adds `/api/analysis/native-agents` create endpoint.
  - Adds `/api/analysis/native-agents/{agent_id}` update/delete endpoints.
  - Adds `/api/analysis/native-agents/{agent_id}/copy`.
- `frontend/src/api/client.ts`
  - Adds native custom Agent mutation client helpers and response types.
- `frontend/src/pages/AnalysisPage.tsx`
  - Shows Agent copy/mutation/ownership surfaces in the native Agent panel.
- `backend/scripts/check_weknora_native_custom_agent_admin.py`
  - Adds the live P5-03 API/browser/audit smoke.
- `backend/scripts/check_weknora_native_agentqa_workflow.py`
  - Updates the older AgentQA smoke to expect copy/mutation surfaces as live.

## Live Smoke Evidence

Command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_custom_agent_admin.py --browser
```

Output:

```text
WeKnora native custom Agent admin residual closure
- decision: PASS
- evidence_type: live api/browser plus audit proof
- custom_agent_admin: create=live update=live copy=live delete=live
- ownership: native OwnedAgentOrAdmin/copy-owned-by-caller path verified
- audit: custom_agent mutations succeeded
- browser: Analysis page rendered Agent admin surface status
- output: sanitized
```

The smoke first proves a wrong confirm token blocks create, then creates an
isolated temporary custom Agent, updates it, copies it, deletes both custom
Agents, and verifies `/api/native-audit/events?capability=custom_agent` contains
the expected succeeded mutation events without exposing raw confirm tokens.

## Verification

Python compile:

```text
backend/.venv/bin/python -m py_compile knowledge_engine/backends/weknora_api_backend.py backend/app/services/native_agent_service.py backend/app/api/analysis.py backend/scripts/check_weknora_native_custom_agent_admin.py backend/scripts/check_weknora_native_agentqa_workflow.py
```

Result: passed.

Live API/browser smoke:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_custom_agent_admin.py --browser
```

Result: passed.

Additional validation results are recorded in the task closeout after running
the WNFC acceptance checker, frontend typecheck, `git diff --check`, and the
sensitive scan.

## Status

`WNFC-P5-03` is `[x]` complete.

AgentQA/custom Agent remains `live-full`. This residual closure does not raise
the aggregate score because that capability group was already scored
`live-full`. The aggregate WNFC score remains `12.00 / 14 = 85.7%` until a
score-moving blocked group is closed.
