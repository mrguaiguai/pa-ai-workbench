# WNID-P3-03 MCP Prompt Parity Report

> Date: 2026-06-25
>
> Task: `WNID-P3-03`
>
> Evidence type: native Go test + Docker runtime + live service + live API +
> live browser
>
> Scope: native MCP prompt list/read parity through PA intelligent dialogue.
> This resolves the prior `native_mcp_prompt_api_missing` blocker. It does not
> claim Web Search PASS, final WNID PASS, or any WNFC conclusion change.

## Result

`WNID-P3-03` is complete. The underlying `mark3labs/mcp-go` client already
supports `prompts/list` and `prompts/get`, so the blocker was a missing
WeKnora route/service/client wrapper rather than an MCP protocol limitation.

The native patch adds prompt list/read support, the safe local MCP server now
exposes one static prompt, and PA exposes confirmed prompt read through the
intelligent dialogue MCP panel.

Task state: `complete`.

## Implemented Product Surface

Changed native/runtime files:

- `internal/mcp/client.go`;
- `internal/mcp/client_prompt_test.go`;
- `internal/types/mcp.go`;
- `internal/types/interfaces/mcp_service.go`;
- `internal/application/service/mcp_service.go`;
- `internal/handler/mcp_service.go`;
- `internal/router/router.go`.

Changed PA files:

- `knowledge_engine/backends/weknora_api_backend.py`;
- `backend/app/api/mcp.py`;
- `backend/app/services/mcp_service.py`;
- `backend/scripts/safe_local_mcp_server.py`;
- `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_prompt_parity.py`;
- `frontend/src/api/client.ts`;
- `frontend/src/pages/DialoguePage.tsx`;
- `frontend/src/styles.css`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_PROMPT_PARITY_WNID_P3_03.md`;
- `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`.

Native routes added:

```text
GET /api/v1/mcp-services/{id}/prompts
POST /api/v1/mcp-services/{id}/prompts/{prompt_name}/read
```

PA route added:

```text
POST /api/mcp/native/services/{service_id}/prompts/{prompt_name}/read
```

The PA route requires the existing safe MCP probe confirmation token:

```text
TEST_NATIVE_MCP_SERVICE
```

## Native Source Audit

Native audit confirmed:

- `internal/mcp/types.go` already declared `PromptsCapability`;
- `mark3labs/mcp-go@v0.52.0` exposes `Client.ListPrompts` and
  `Client.GetPrompt`;
- WeKnora's `MCPClient` interface, `mcpServiceService`, handler, router, and
  public `types.MCPTestResult` did not expose prompts before this task;
- the safe local MCP server previously exposed only one tool and one resource,
  so it could not provide live prompt parity evidence.

## Safety Contract

Prompt read is treated as confirmed external MCP probing, not a mutation:

- PA requires `TEST_NATIVE_MCP_SERVICE`;
- prompt arguments must be a JSON object;
- native prompt arguments are string-only before calling `prompts/get`;
- native output returns sanitized role/content type/text summary only;
- image/audio/resource payloads are summarized by content type and MIME type;
- raw binary data, embedded resources, headers, credentials, URLs, input
  schemas, and service config are not returned by PA evidence.

The safe local MCP prompt is:

```text
pa-safe-summary
```

It is static and performs no file, shell, network, credential, environment,
database, or private endpoint access.

## Live Validation

Native focused test:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -v /private/tmp/pa-go-mod-cache:/go/pkg/mod -w /workspace golang:1.26.0 go test ./internal/mcp ./internal/application/service ./internal/handler -run 'TestSafeMCPPromptMessageRedactsBinaryContent|TestTruncateMCPPromptText|TestSafeMCPToolOutputRedactsBinaryContent|TestTruncateMCPExecutionText|TestValidateMCPServiceURLForSSRF|TestNormalizeMCPAllowlistURL' -count=1
```

Result:

```text
ok  	github.com/Tencent/WeKnora/internal/mcp	1.713s
ok  	github.com/Tencent/WeKnora/internal/application/service	0.333s
ok  	github.com/Tencent/WeKnora/internal/handler	0.332s
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

P3-03 checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_mcp_prompt_parity.py
```

Live evidence:

```text
WeKnora native intelligent dialogue MCP prompt parity
- decision: PASS
- task: WNID-P3-03
- evidence_type: native_go_test + Docker runtime + live_service + live_api + live_browser
- api: service=PA Safe Local MCP prompts=1 selected_prompt=pa-safe-summary prompt_read=live messages=1
- blocker: native_mcp_prompt_api_missing resolved=true
- browser: route=dialogue mcp_prompt_parity=visible markers=8 hidden_advanced_panel=false
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
dist/assets/index-e70a6d15.css
dist/assets/index-aaaeb375.js
built in 838ms
```

## Remaining WNID Boundaries

- `WNID-P4-01` and `WNID-P4-02` remain open for Web Search provider setup and
  native AgentQA Web Search reference proof.
- `WNID-P5-01` remains open for Wiki Mode Agent workflow.
- `WNID-P6-01`, `WNID-P7-01`, `WNID-P8-01`, and `WNID-P8-02` remain open.
- Final WNID PASS remains blocked until all remaining WNID hard gates complete
  with current-run evidence.

## Non-Changes

- No WNFC spec or completion conclusion changed.
- No `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` change was made.
- No Web Search or final WNID PASS is claimed.
- No `.env`, database, log, upload, `node_modules`, `dist`, screenshot, raw
  provider payload, raw prompt payload, raw MCP binary/resource body, or
  credential was staged.
