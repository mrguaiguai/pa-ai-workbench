# WNID-P3-02 MCP Approval-Gated Tool Execution Report

> Date: 2026-06-25
>
> Task: `WNID-P3-02`
>
> Evidence type: native Go test + Docker runtime + live service + live API +
> live browser + PA audit/history
>
> Scope: approval-gated execution or denial of one safe native MCP tool through
> PA intelligent dialogue. This does not claim MCP prompt parity, Web Search
> PASS, final WNID PASS, or any WNFC conclusion change.

## Result

`WNID-P3-02` is complete. PA now exposes a confirmation-gated MCP tool
execution path for the configured safe native MCP service. The live checker
sets native approval policy for the `ping` tool, proves one rejected execution,
then proves one approved execution through WeKnora's native MCP client. Both
paths record `NativeMutationAudit` entries and PA history outputs.

Task state: `complete`.

## Implemented Product Surface

Changed native/runtime files:

- `internal/types/mcp.go`;
- `internal/types/interfaces/mcp_service.go`;
- `internal/application/service/mcp_service.go`;
- `internal/application/service/mcp_service_execution_test.go`;
- `internal/handler/mcp_service.go`;
- `internal/router/router.go`.

Changed PA files:

- `knowledge_engine/backends/weknora_api_backend.py`;
- `backend/app/api/mcp.py`;
- `backend/app/services/mcp_service.py`;
- `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_tool_execution.py`;
- `frontend/src/api/client.ts`;
- `frontend/src/pages/DialoguePage.tsx`;
- `frontend/src/styles.css`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_TOOL_EXECUTION_WNID_P3_02.md`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`.

The dialogue page now exposes an MCP execution panel with:

- selected safe MCP service;
- rejected `ping` execution path;
- approved `ping` execution path;
- approval decision;
- execution status;
- PA history output id;
- PA audit status.

## Native Source Audit

Native WeKnora source audit confirmed before the native exception:

- `internal/mcp/client.go` already implements `CallTool`;
- `internal/application/service/mcp_tool_approval_service.go` already stores
  per-service, per-tool approval policy;
- `internal/handler/mcp_service.go` already exposes approval list/set routes;
- `internal/handler/session/agent_tool_handler.go` and
  `internal/agent/tools/mcp_tool.go` already support native agent pending
  approval resolution;
- no public MCP service route existed for direct, deterministic execution of a
  known safe MCP tool from PA.

## Controlled Native Exception

The native patch adds the smallest direct execution surface needed by WNID:

```text
POST /api/v1/mcp-services/{id}/tools/{tool_name}/execute
```

The new service method:

- validates the MCP service id and tool name;
- accepts only JSON-object arguments;
- checks native MCP tool approval policy via `MCPToolApprovalService`;
- returns a successful denial when approval is required and PA sends
  `approval_decision=reject`;
- executes the tool only when either approval is not required or PA sends
  `approval_decision=approve`;
- calls the existing native MCP client `CallTool`;
- returns only sanitized output, summary counts, and status fields.

This path is intentionally separate from the Agent pending-card approval flow.
It uses the same native approval policy store but gives PA a deterministic
execution contract for the safe local MCP tool evidence required by WNID.

## PA Confirmation, Audit, And History

PA exposes:

```text
PUT /api/mcp/native/services/{service_id}/tool-approvals/{tool_name}
POST /api/mcp/native/services/{service_id}/tools/{tool_name}/execute
```

Both routes require the fixed confirmation token:

```text
EXECUTE_NATIVE_MCP_TOOL
```

PA records:

- operation `weknora_mcp_tool_approval_set` for approval policy changes;
- operation `weknora_mcp_tool_execute` for rejected and approved executions;
- request summaries containing service id, tool name, argument keys, and
  approval decision only;
- generated history outputs with task type `native_mcp_tool_execution`.

No raw credential, header, service config, binary MCP payload, private endpoint,
or raw tool schema is returned by the checker.

## Live Validation

Native focused test:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -w /workspace golang:1.26.0 go test ./internal/application/service ./internal/handler -run 'TestSafeMCPToolOutputRedactsBinaryContent|TestTruncateMCPExecutionText|TestValidateMCPServiceURLForSSRF|TestNormalizeMCPAllowlistURL' -count=1
```

Result:

```text
ok  	github.com/Tencent/WeKnora/internal/application/service	0.277s
ok  	github.com/Tencent/WeKnora/internal/handler	0.276s
```

Docker runtime validation:

```bash
WEKNORA_MCP_SSRF_ALLOWLIST=http://host.docker.internal:8765/mcp docker compose up -d --no-deps --build app
curl -fsS http://127.0.0.1:8080/health
docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:8.10.1 -fsS http://host.docker.internal:8765/mcp
```

Runtime evidence:

```text
{"status":"ok"}
{"status":"ok","server":{"name":"pa-safe-local-mcp","version":"1.0.0"}}
```

P3-02 checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_mcp_tool_execution.py
```

Live evidence:

```text
WeKnora native intelligent dialogue MCP tool execution
- decision: PASS
- task: WNID-P3-02
- evidence_type: live_service + live_api + live_browser + audit_history + native_go_test
- api: service=PA Safe Local MCP tool=ping approval_policy=live reject=rejected approve=executed approval_required=true audits=2 history=2
- history: reject_output=out_c2b30c895f2d approve_output=out_6cb9d544bfb6 task_type=native_mcp_tool_execution
- browser: route=dialogue mcp_tool_execution=visible markers=8 hidden_advanced_panel=false
```

Frontend validation:

```bash
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/lib/tsc.js -p tsconfig.json --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
```

Result:

```text
vite v4.5.14 building for production...
1591 modules transformed.
dist/index.html
dist/assets/index-184d2bbf.css
dist/assets/index-788a39e5.js
built in 717ms
```

## Remaining WNID Boundaries

- `WNID-P3-03` remains open for MCP prompt parity. Current blocker is
  `native_mcp_prompt_api_missing`.
- `WNID-P4-01` and `WNID-P4-02` remain open for Web Search provider setup and
  native AgentQA Web Search reference proof.
- `WNID-P8-02` final PASS remains blocked until all remaining WNID hard gates
  complete with current-run evidence.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` change was made.
- No Web Search, MCP prompt parity, or final WNID PASS is claimed.
- No `.env`, database, log, upload, `node_modules`, `dist`, screenshot, raw
  provider payload, raw MCP binary output, or credential was staged.
