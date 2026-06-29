# WNID-P3-01 MCP Tools/Resources/Prompts Read Path Report

> Date: 2026-06-25
>
> Task: `WNID-P3-01`
>
> Evidence type: native Go test + Docker runtime + live service + live API +
> live browser + prompt blocker evidence
>
> Scope: WeKnora native MCP service tools/resources/prompts read path through
> PA intelligent dialogue; no MCP tool execution PASS and no WNFC conclusion
> rewrite.

## Result

`WNID-P3-01` is complete for the MCP tools/resources read path. PA now has a
safe local MCP service, configured through the confirmed PA native MCP mutation
path, and the live native confirmed test returns one real tool and one real
resource. The `#/dialogue` page exposes MCP read-path status as a first-class
intelligent dialogue surface.

Prompt read parity remains blocked by a native API gap:
`native_mcp_prompt_api_missing`. That blocker is carried forward separately and
is not counted as MCP tool/resource read or execution PASS.

Task state: `complete` for tools/resources read path; prompt API blocker
recorded for follow-up.

## Implemented Product Surface

Changed PA files:

- `backend/scripts/safe_local_mcp_server.py`;
- `backend/scripts/configure_safe_local_mcp.py`;
- `frontend/src/pages/DialoguePage.tsx`;
- `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_read_path.py`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_READ_PATH_WNID_P3_01.md`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`.

Changed native/runtime files:

- `internal/handler/mcp_service.go`;
- `internal/handler/mcp_service_ssrf.go`;
- `internal/handler/mcp_service_ssrf_test.go`;
- `docker-compose.yml`.

The dialogue page now exposes:

- `MCP Read Path` status panel;
- native MCP service count and source;
- tools/resources read-path status;
- prompt blocker reason;
- approval status;
- tool execution blocker reason.

## Native Source Audit

Native WeKnora source audit confirmed:

- `internal/handler/mcp_service.go` exposes
  `GET /api/v1/mcp-services/{id}/tools`;
- `internal/handler/mcp_service.go` exposes
  `GET /api/v1/mcp-services/{id}/resources`;
- `internal/application/service/mcp_service.go` implements `GetMCPServiceTools`
  and `GetMCPServiceResources` through the MCP client manager;
- `internal/types/mcp.go` defines `MCPTool`, `MCPResource`, and
  `MCPTestResult`;
- `client/mcp_service.go` includes client methods for service test, tool list,
  and resource list;
- native approval routes exist for tool approval list/set/resolve, but actual
  tool execution remains `WNID-P3-02`;
- no native MCP prompt list/read route, type, or client method was found.

## Controlled Native Exception

The first live attempt found that WeKnora's normal SSRF protection rejects
local/private MCP URLs. Direct database insertion was rejected as unsafe because
it would bypass the product security control.

The implemented native exception is narrow:

- `WEKNORA_MCP_SSRF_ALLOWLIST` accepts exact full MCP URLs only;
- the exception is used only by MCP service create/update URL validation;
- other outbound URL surfaces still use the existing global SSRF policy;
- no wildcard, host-wide, credential, file, shell, or raw environment access is
  introduced.

Runtime value used for validation:

```text
WEKNORA_MCP_SSRF_ALLOWLIST=http://host.docker.internal:8765/mcp
```

The safe local MCP service exposes only:

- tool: `ping`;
- resource: `pa://safe-mcp/health`.

It performs no file, shell, network, credential, environment, database, or
private endpoint access.

## Live Validation

Native focused test:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -w /workspace golang:1.26.0 go test ./internal/handler -run 'TestValidateMCPServiceURLForSSRF|TestNormalizeMCPAllowlistURL' -count=1
```

Result:

```text
ok  	github.com/Tencent/WeKnora/internal/handler	0.252s
```

Docker runtime validation:

```bash
WEKNORA_MCP_SSRF_ALLOWLIST=http://host.docker.internal:8765/mcp docker compose up -d --no-deps --build app
curl -fsS http://127.0.0.1:8080/health
docker exec WeKnora-app sh -lc 'printf "%s" "$WEKNORA_MCP_SSRF_ALLOWLIST"'
```

Runtime evidence:

```text
{"status":"ok"}
http://host.docker.internal:8765/mcp
```

Safe local MCP configuration:

```bash
backend/.venv/bin/python backend/scripts/configure_safe_local_mcp.py
```

Live service evidence:

```text
PA safe local MCP configured
- action: create
- service: PA Safe Local MCP
- transport: http-streamable
- enabled: true
- live_test: success=true tools=1 resources=1
- mutation_path: PA BFF confirmed native MCP mutation
```

P3-01 checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_mcp_read_path.py
```

Live evidence:

```text
WeKnora native intelligent dialogue MCP read path
- decision: PASS
- task: WNID-P3-01
- evidence_type: live_api + live_browser + live_service + blocker
- api: services=1 selected=PA Safe Local MCP detail=live confirmed_test=live success=true tools=1 resources=1 approval=live
- prompts: blocked reason=native_mcp_prompt_api_missing carried_forward=true
- browser: route=dialogue mcp_read_path=visible markers=8 hidden_advanced_panel=false
```

The checker starts temporary PA backend/frontend services, calls
`/api/mcp/native/overview`, reads service detail, performs the confirmation
gated native MCP test, verifies the prompt API blocker, and opens `#/dialogue`
in headless Chrome to prove the MCP read-path panel is visible without opening
a hidden advanced panel.

## Blockers And Follow-Up

Remaining blocker:

- Native MCP prompt API is missing:
  `native_mcp_prompt_api_missing`.

Follow-up:

- `WNID-P3-02` can now use `PA Safe Local MCP` and its `ping` tool for
  approval-gated execution or denial evidence.
- `WNID-P3-03` should decide MCP prompt parity: either add a minimal native MCP
  prompt list/read API if the underlying MCP client supports prompts, or record
  an explicit product decision that prompts are out of scope for the safe local
  MCP service.

## Remaining WNID Boundaries

- `WNID-P3-02` must still prove approval-gated MCP tool execution or denial
  with PA audit/history.
- `WNID-P4-*` must still prove Web Search provider setup and AgentQA Web Search
  references.
- No MCP execution PASS is claimed from service visibility or tools/resources
  read success.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No MCP tool execution, Web Search, or final WNID PASS is claimed.
- No `.env`, database, log, upload, `node_modules`, `dist`, screenshot, raw
  provider payload, raw tool output, or credential was staged.
- `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` was not touched.
