# WNID-P4-02 AgentQA Web Search Run

> Date: 2026-06-26
>
> Task: `WNID-P4-02`
>
> Evidence type: native Go test + Docker runtime + live API + live browser + citation/history
>
> Decision: PASS

## Scope

This task proves Web Search as a native AgentQA capability in PA. It completes
the answer-side requirement left open by `WNID-P4-01`: a saved native provider
is not enough; native AgentQA must call `web_search` and PA must persist
traceable web references as citations/history.

## Native Source Audit

| Native surface | Evidence |
| --- | --- |
| AgentQA request | `internal/handler/session/qa.go` routes AgentQA to ReACT mode only when custom Agent `agent_mode` is `smart-reasoning`. |
| Runtime config | `internal/application/service/session_agent_qa.go` enables Web Search only when both custom Agent config and request set `web_search_enabled=true`; provider id falls back to the tenant default when absent. |
| Tool registration | `internal/application/service/agent_service.go` registers `web_search` and `web_fetch` when Web Search is enabled and passes the provider id into the native tool. |
| Web Search result shape | `internal/agent/tools/web_search.go` returns structured `results` with title, URL, snippet, provider source, rank, and optional published time. |
| Reference gap fixed | `internal/agent/act.go` now extracts native `web_search` tool results into `SearchResult` references with `source_type=web_search`, URL metadata, rank, title, and snippet. |

## PA Changes

| PA surface | Status | Notes |
| --- | --- | --- |
| Adapter | complete | `WeKnoraApiBackend` maps native Web Search references to `Evidence(source_type=web_search)` with stable `web_search:<hash>` evidence ids and URL metadata. |
| Citation validation | complete | Real citations now accept `web_search` only when a URL locator is present. |
| AgentQA runtime | complete | PA runtime/output/message metadata expose `web_reference_count`, `web_providers`, and a compact web evidence summary. |
| Dialogue UI | complete | AgentQA submits the request-side `web_search_enabled` flag and Tool Trace renders `web_references` plus `web_providers`. |
| Checker | complete | `backend/scripts/check_weknora_native_intelligent_dialogue_web_search_agentqa.py` creates a temporary smart-reasoning Agent, enables DuckDuckGo through the confirmed strategy path, runs live AgentQA, validates citations/history, opens `#/dialogue`, and deletes the temporary Agent. |

## Live Evidence

Native validation:

```text
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -w /workspace golang:1.26.0 gofmt -w internal/agent/act.go internal/agent/act_references_test.go
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -v /private/tmp/pa-go-mod-cache:/go/pkg/mod -w /workspace golang:1.26.0 go test ./internal/agent -run 'TestExtractKnowledgeReferencesFromToolResult|TestExtractWikiReferencesFromToolResult|TestExtractWebSearchReferencesFromToolResult|TestAppendUniqueKnowledgeReferences' -count=1
docker compose build app
docker compose up -d --no-deps app
```

Native Go test output:

```text
ok  	github.com/Tencent/WeKnora/internal/agent	0.248s
```

PA validation:

```text
backend/.venv/bin/python -m py_compile backend/app/services/native_agent_service.py backend/app/services/generation_service.py backend/app/schemas.py knowledge_engine/backends/weknora_api_backend.py backend/scripts/check_weknora_native_intelligent_dialogue_web_search_agentqa.py
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/.bin/tsc --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/.bin/vite build
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_web_search_agentqa.py
```

Checker output:

```text
WeKnora native intelligent dialogue AgentQA Web Search
- decision: PASS
- task: WNID-P4-02
- evidence_type: native_go_test + live_api + live_browser + citation_history
- api: agent_id=b44a855c-a4ce-4d09-bea7-13292bc5c8c4 tool=web_search provider=duckduckgo tool_call=16 tool_result=6 web_refs=25 citations=25 history=1
- references: source_type=web_search url_count=7
- browser: route=dialogue web_search_agentqa=visible markers=7 hidden_advanced_panel=false
```

The checker:

- reused the configured no-credential `duckduckgo` native provider and proved
  the saved-provider test succeeds;
- created a temporary native custom Agent through PA confirmation/audit path;
- set `agent_mode=smart-reasoning`, `allowed_tools=["web_search"]`,
  `web_search_enabled=true`, and the DuckDuckGo provider id;
- ran PA `/api/analysis/native-agentqa` with `web_search_enabled=true`;
- required a real native `web_search` tool name, tool call/result events,
  Web Search references, saved `web_search` citations, URL locators, and PA
  history;
- opened `#/dialogue` in headless Chrome and proved the AgentQA Web Search
  trace markers are visible outside any hidden advanced panel;
- deleted the temporary Agent after validation.

## Current Truth

`WNID-P4-02` is complete. WNID Web Search now has both provider setup evidence
and live native AgentQA answer/reference evidence. The next open WNID task is
`WNID-P5-01` for Wiki Mode Agent workflow.
