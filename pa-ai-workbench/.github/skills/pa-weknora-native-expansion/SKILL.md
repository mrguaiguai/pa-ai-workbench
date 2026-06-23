---
name: pa-weknora-native-expansion
description: Use this skill for PA AI Workbench WeKnora Native Expansion internal production work in /Users/mac/Downloads/WeKnora-main/pa-ai-workbench, especially WNX-* tasks that connect WeKnora native knowledge base, document, chunk, RAG, knowledge-chat, AgentQA, custom Agent, Wiki, MCP, web search, vector store, model/config, data source, citation, status, frontend, deployment, live validation, or internal production acceptance.
---

# PA WeKnora Native Expansion

Use this skill for every `WNX-*` task in the Native Expansion internal production
stage.

Default cwd:

```text
/Users/mac/Downloads/WeKnora-main/pa-ai-workbench
```

## Source Of Truth

At the start of each task:

1. Read `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md`.
2. Read `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md` for prior stage state.
3. Read `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md` if it exists.
4. Read `.github/skills/pa-weknora-native-expansion/SKILL.md`.
5. Read `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md` when available.
6. Run `git status -sb` and `git log --oneline -5`.

If the repo-local and outer skills diverge, obey the stricter rule and repair
the divergence in a governance task.

## Task Binding

- Execute exactly one `WNX-*` task id per run.
- If the user names a task id, use that id.
- If the user gives a broad "continue" request, choose the earliest unfinished
  task in this order: `WNX-0`, `WNX-P0`, `WNX-P1`, `WNX-P2`, `WNX-P3`.
- Split oversized work into a new explicit task card instead of silently doing
  several slices.
- Update spec status only after validation or a real blocked/backlog decision.

## Classify Before Editing

Before modifying files, state in Chinese:

1. Task id.
2. Task type:
   - WeKnora native capability接入
   - PA product shell
   - PA BFF/business DB/history/citation
   - validation/ops/deployment
   - PA-native professional workflow freeze/backlog
3. Planned files.
4. Validation method.
5. Expected PASS evidence type: live API, live browser, live service, audit/map,
   blocked, or backlog.

## WeKnora Native Source Search

For native capability tasks, inspect WeKnora sources before PA code changes:

- Routes: `internal/router/router.go`
- Knowledge/KB/document/chunk/search: `internal/handler/knowledge*.go`,
  `internal/application/service/knowledge*.go`,
  `internal/application/service/knowledgebase_search*.go`,
  `internal/types/search.go`, `internal/types/retriever.go`
- Session chat/AgentQA/custom Agent: `internal/handler/session/qa.go`,
  `internal/application/service/session_agent_qa.go`,
  `internal/handler/custom_agent.go`,
  `internal/application/service/custom_agent.go`
- Wiki: `internal/handler/wiki_page.go`,
  `internal/application/service/wiki_*.go`, `internal/types/wiki_page.go`
- MCP: `internal/handler/mcp_service.go`,
  `internal/application/service/mcp_service.go`
- Web search: `internal/handler/web_search*.go`,
  `internal/application/service/web_search*.go`
- Vector store: `internal/handler/vectorstore.go`,
  `internal/application/service/vectorstore*.go`, `internal/types/vectorstore.go`
- Model/init/parser/system/config: relevant `internal/handler/*`,
  `internal/application/service/*`, and `internal/types/*` files found by `rg`
- Data source/FAQ/tag/favorite/skill: relevant handler/service/type files found
  by `rg`

Then inspect PA adapter/product files such as:

- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/api/*`
- `backend/app/services/*`
- `backend/app/models.py`
- `agent/orchestrator.py`
- `agent/tools/registry.py`
- `frontend/src/pages/*`

Do not build a PA-owned general RAG, Wiki, Agent, parser, embedding, vector
store, MCP, or web-search subsystem when WeKnora has a native path.

## PASS And Coverage Rules

Use the stage coverage states:

- `live-full`: real PA path plus real WeKnora native capability satisfies the PA
  contract.
- `live-partial`: real native call works but citation/history/mutation/workflow
  contract is incomplete.
- `read-only`: PA can inspect native status/catalog/list only.
- `blocked`: real runtime/API/config/safety gap.
- `backlog`: intentionally deferred.
- `unsafe-for-pa`: not safe to expose without a separate design.

The stage target is at least 80% eligible native capability coverage. Do not
inflate coverage from visibility alone.

Never count these as PASS:

- mock backend/model/embedding/API
- fixture-only proof
- old reports or cached browser state
- static UI/demo pages
- hidden fallback
- Agent answer text without traceable native references when citation is part
  of the contract

If live capability is unavailable, mark `[!]` or `[b]` with cause and next step.

## Credential And Data Safety

For config, credential, provider, MCP, web search, vector store, data source, or
model tasks:

- Show only masked/configured/status/test results.
- Never print or commit `.env` values, API keys, service tokens, passwords,
  private endpoints, private key blocks, raw uploaded bodies, local DB contents,
  logs, caches, raw prompts, provider payloads, or raw vector data.
- Do not store WeKnora authoritative chunks/vectors or secrets in PA business
  DB.

## Validation

- Backend tasks require API or smoke validation against live PA/WeKnora, or a
  recorded blocker.
- Frontend tasks require browser validation for affected pages.
- Deployment tasks require service/status/runbook validation.
- Report/spec tasks require `git diff --check`, relevant `rg` checks, sensitive
  scan, and skill validation when skills are touched.
- Keep live evidence, fixture evidence, mock evidence, cached evidence, partial
  evidence, blocked evidence, and backlog evidence separate in reports.

## Staging And Output

- Stage only current-task files with explicit paths.
- Do not stage `.env`, databases, logs, caches, uploads, `node_modules`, `dist`,
  screenshots, or unrelated reports.
- Keep `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` unstaged unless the user
  explicitly changes scope.
- Do not push or merge to `main` unless explicitly asked.

End each task with changed files, validation results, evidence type, risks, and
the next useful WNX task.
