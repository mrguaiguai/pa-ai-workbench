---
name: pa-weknora-native-intelligent-dialogue
description: "Use this skill for PA AI Workbench WeKnora Native Intelligent Dialogue work in /Users/mac/Downloads/WeKnora-main/pa-ai-workbench, especially WNID-* tasks that connect WeKnora README Intelligent Conversation capabilities: ReACT AgentQA, quick Q&A, Wiki Mode, built-in tools, MCP tools, Web Search, online prompt/retrieval strategy, multi-turn context, suggested questions, citations, audit/history, browser validation, and no mock/demo PASS."
---

# PA WeKnora Native Intelligent Dialogue

Use this skill for every `WNID-*` task in the WeKnora Native Intelligent
Dialogue stage. This is a post-WNFC stage: do not rewrite WNFC completion, but
do reopen Web Search and MCP tool execution as hard WNID final gates.

Default cwd:

```text
/Users/mac/Downloads/WeKnora-main/pa-ai-workbench
```

## Source Of Truth

At the start of each task:

1. Read `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`.
2. Read `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`.
3. Read `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md`.
4. Read `.github/skills/pa-weknora-native-intelligent-dialogue/SKILL.md`.
5. Read `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-intelligent-dialogue/SKILL.md` when available.
6. Run `git status -sb` and `git log --oneline -5`.

If repo-local and outer skills diverge, obey the stricter rule and repair the
divergence in a governance task.

## Task Binding

- Execute exactly one `WNID-*` task id per run.
- If the user names a task id, use that id.
- If the user says continue, choose the earliest unfinished WNID task in this
  order: `WNID-0`, `WNID-P1`, `WNID-P2`, `WNID-P3`, `WNID-P4`, `WNID-P5`,
  `WNID-P6`, `WNID-P7`, `WNID-P8`.
- Do not substitute WNX/WNFC task ids for WNID work.
- Do not remove Web Search or MCP tool execution from final WNID scope unless
  the user explicitly changes the WNID goal.

## Classify Before Editing

Before modifying files, state in Chinese:

1. Task id.
2. Task type:
   - WeKnora native Agent capability接入
   - PA BFF/business DB/history/citation/audit
   - PA intelligent dialogue product shell
   - MCP/Web Search credential/approval/security foundation
   - validation/ops/deployment
   - native-source patch/runtime validation
3. Planned files.
4. Validation method.
5. Expected PASS evidence type: live API, live browser, live service, native Go
   test, Docker runtime, audit/map, blocked.

## Native Source First

For native capability tasks, inspect WeKnora sources before PA code changes:

- README Intelligent Conversation table: `README.md`.
- Session chat and AgentQA: `internal/handler/session/qa.go`,
  `internal/application/service/session_agent_qa.go`,
  `internal/application/service/agent_service.go`,
  `internal/handler/session/agent_stream_handler.go`,
  `internal/types/session.go`, `internal/types/agent.go`.
- Custom Agent config and suggested questions:
  `internal/handler/custom_agent.go`,
  `internal/application/service/custom_agent.go`,
  `internal/types/custom_agent.go`, `client/agent_manage.go`.
- MCP: `internal/handler/mcp_service.go`,
  `internal/application/service/mcp_service.go`,
  `internal/application/service/mcp_tool_approval_service.go`,
  `internal/types/mcp.go`.
- Web Search: `internal/handler/web_search*.go`,
  `internal/application/service/web_search*.go`,
  `internal/types/web_search_provider.go`.
- Wiki: `internal/handler/wiki_page.go`,
  `internal/application/service/wiki_*.go`,
  `internal/types/wiki_page.go`, and native Wiki tool paths found by `rg`.
- Knowledge/RAG: `internal/handler/knowledge*.go`,
  `internal/application/service/knowledge*.go`,
  `internal/application/service/chat_pipeline/*`,
  `internal/types/retrieval_config.go`.

Then inspect PA adapter/product files such as:

- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/api/*`
- `backend/app/services/*`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `frontend/src/pages/*`
- `frontend/src/api/client.ts`
- `backend/scripts/check_weknora_*`

Do not build a PA-owned replacement for WeKnora Agent, RAG, Wiki, MCP, Web
Search, prompt, retrieval, or tool orchestration when native support exists.

## Hard Gates

WNID final PASS must prove:

- Web Search is configured/tested or has an exact user-action blocker. Final
  PASS requires a live native AgentQA run with `web_search_enabled=true` and
  traceable web references.
- MCP execution is configured/tested or has an exact user-action blocker. Final
  PASS requires at least one safe MCP tool list/read plus approval-gated
  execution or denial with PA audit/history evidence.
- Online conversation strategy covers native prompt/context templates, tools,
  MCP selection, Web Search, web fetch, multi-turn context, history turns,
  retrieval thresholds, rerank thresholds, and suggested prompts.
- Suggested questions come from the native agent endpoint and can launch a live
  dialogue run.

Never mark complete from status/catalog visibility alone.

## Source Modification Principle

Use `PA-first + controlled native exception lane`.

- `PA-first`: when WeKnora already exposes the route, field, event, reference,
  config, provider, or execution path, change PA adapter/BFF/history/citation/
  audit/UI only.
- `native exception`: when WeKnora lacks a required event/reference/config/tool
  execution/safe API, make the smallest native Go change and prove it with
  focused native tests, Docker runtime validation when needed, and PA live
  API/browser evidence.
- `blocked`: when the gap is a missing provider key, MCP service, OAuth scope,
  workspace, account, permission, approval, or sample data, stop the affected
  path and ask for the exact missing item.

## Evidence Rules

- Document/Wiki citations must be locatable through PA.
- Web Search evidence needs provider identity plus URL/title/snippet/rank or an
  equivalent native reference shape.
- MCP evidence needs service, tool, approval policy, approval/denial result,
  execution summary, timeout/error class, audit id, and history visibility.
- Built-in tool events prove tool use, not factual citation by themselves.
- Keep live, partial, blocked, fixture, mock, cached, and stale evidence
  separate in every report.

Never count these as PASS:

- mock provider/model/MCP/web-search output
- fixture-only proof
- old reports or cached browser state
- static UI/demo pages
- hidden fallback
- answer text without traceable references when citation is required

## Credential And Safety Rules

- Show only masked/configured/status/test summaries.
- Never print or commit `.env` values, API keys, service tokens, passwords,
  private endpoints, private key blocks, raw uploaded bodies, raw web pages,
  raw prompts, local DB contents, logs, caches, provider payloads, raw vectors,
  or raw connector config.
- Use confirmation tokens for strategy mutations, external provider tests, MCP
  tool execution, Web Search credential changes, Wiki mutations, and destructive
  operations.
- Record PA audit/history entries for mutations and external executions.

## Validation

- Backend tasks require live PA/WeKnora API or service smoke, or a recorded
  blocker.
- Frontend tasks require browser validation.
- Native Go changes require focused native tests and Docker runtime validation
  when running WeKnora behavior must change.
- Credential/provider/config tasks require masked-output checks and sensitive
  scans.
- Final completion requires a WNID acceptance harness and desktop/mobile
  browser matrix proving all README Intelligent Conversation rows through PA.

## Staging And Output

- Stage only current-task files with explicit paths.
- Do not stage `.env`, databases, logs, caches, uploads, `node_modules`,
  `dist`, screenshots, raw provider payloads, or unrelated reports.
- Keep `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md` unchanged unless explicitly
  scoped.
- Keep `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` untouched and unstaged
  unless explicitly scoped.
- Do not push or merge unless explicitly asked.

End each task with changed files, validation results, evidence type, risks,
blockers or missing API requests, and the next useful `WNID-*` task.
