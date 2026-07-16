---
name: pa-weknora-first-sprint
description: Use this skill for PA AI Workbench five-day WeKnora-first sprint work in repository root, especially when connecting WeKnora native RAG, document, Wiki, AgentQA, custom Agent, MCP, web search, vector store, citation, status, frontend, live validation, or sprint report tasks.
---

# PA WeKnora-First Sprint

Use this skill for every task in the five-day WeKnora-first sprint.

Every sprint task must run under exactly one `WF-*` task id from
`docs/archive/weknora-first/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`. If the requested work does not fit an
existing id, first clarify or add the smallest governance/task-card slice; do
not perform unnumbered sprint work.

Default to the repository root:

```text
repository root
```

## Sprint Progress Source

Treat the sprint spec as the progress source of truth, like the earlier phase specs.

At the start of every sprint task:

1. Read `docs/archive/weknora-first/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.
2. Read `docs/archive/weknora-first/PA_EXISTING_WORK_REVIEW_FOR_WEKNORA_FIRST.md` when the task depends on prior PA work.
3. Run `git status -sb` and `git log --oneline -5` in `repository root`.
4. Use the task board in the sprint spec to choose work:
   - user-specified `WF-*` id wins;
   - otherwise choose the earliest unfinished P0 task;
   - do not move to P1 while P0 is unfinished unless the user explicitly reprioritizes;
   - treat P2 as backlog unless the user scopes a narrow read-only/jump slice.
5. Execute only that one `WF-*` id. Split oversized work into a new explicit
   task card instead of silently completing multiple slices.

At the end of a task:

- Update the task board and progress log in `docs/archive/weknora-first/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md` only after validation or a real blocked/backlog decision.
- Mark `[x]` only for live PASS evidence, except audit/map tasks whose acceptance criteria explicitly says no live PASS is claimed.
- Mark `[!]` when real WeKnora/API/model/config/runtime conditions block completion, with cause and next step.
- Mark `[b]` for conscious backlog/deferred scope.
- Use `[~]` only for a useful partial slice that is committed but not enough for final PASS.
- Commit only current-task files when a task is complete; keep unrelated dirty or untracked files untouched.
- Never update the spec status to `[x]` before the task's declared validation
  has passed. If validation cannot run, record `[!]` or `[b]` with the cause and
  next step.

## First Decision

Before changing files, classify the requested slice as exactly one primary type:

| Type | Meaning | Default action |
| --- | --- | --- |
| WeKnora native capability接入 | PA should consume an existing WeKnora API/module for general RAG, document, Wiki, AgentQA, custom Agent, MCP, web search, or vector store behavior | Search WeKnora routes/services/types first, then build the thinnest PA adapter. |
| PA 产品壳 | PA owns navigation, UX, state display, history, citation rendering, task records, reports, or workflow templates | Preserve PA experience and keep state truthful. |
| PA-native 专业编排 | PA-specific policy/case/professional Agent logic | Freeze or backlog during this sprint unless the user explicitly scopes one narrow professional workflow task. |

Do not start by self-implementing a general RAG, Wiki, Agent, parser, chunker, embedding, or vector-store subsystem if WeKnora already has a native path.

## Per-Task Guardrail

Handle one clear capability slice per run, such as:

- RAG retrieval/debug
- AgentQA
- Wiki browse/search/read
- Wiki publish/index status
- document upload/status/chunks
- knowledge base selection
- citation/evidence mapping
- frontend status integration
- report safety or live validation

Before editing, state in Chinese:

1. `WF-*` task id.
2. Task classification: WeKnora native capability接入, PA产品壳, or PA-native专业编排冻结/backlog.
3. Planned files to edit.
4. Validation command/API/browser check.
5. PASS evidence type expected, such as live API, live browser, audit/map, blocked, or backlog.

Do not edit files until this declaration has been given. If live evidence is
required but unavailable, do not create mock data to pass the task; classify the
result as blocked or backlog.

## WeKnora-First Source Search

For native capability tasks, inspect relevant WeKnora sources before PA code changes:

- Routes: `platform/weknora/internal/router/router.go`
- Knowledge/document: `platform/weknora/internal/handler/knowledge.go`, `platform/weknora/internal/application/service/knowledge*.go`
- Search/RAG: `platform/weknora/internal/application/service/knowledgebase_search*.go`, `platform/weknora/internal/types/search.go`, `platform/weknora/internal/types/retriever.go`
- AgentQA/custom Agent: `platform/weknora/internal/handler/session/qa.go`, `platform/weknora/internal/application/service/session_agent_qa.go`, `platform/weknora/internal/handler/custom_agent.go`, `platform/weknora/internal/application/service/custom_agent.go`
- Wiki: `platform/weknora/internal/handler/wiki_page.go`, `platform/weknora/internal/application/service/wiki_*.go`, `platform/weknora/internal/types/wiki_page.go`
- MCP: `platform/weknora/internal/handler/mcp_service.go`, `platform/weknora/internal/application/service/mcp_service.go`
- Web search: `platform/weknora/internal/handler/web_search*.go`, `platform/weknora/internal/application/service/web_search*.go`
- Vector store: `platform/weknora/internal/handler/vectorstore.go`, `platform/weknora/internal/application/service/vectorstore*.go`, `platform/weknora/internal/types/vectorstore.go`

Then inspect PA adapter/product files as needed:

- `packages/knowledge-engine/knowledge_engine/factory.py`
- `packages/knowledge-engine/knowledge_engine/backends/weknora_api_backend.py`
- `apps/pa-api/app/api/*`
- `apps/pa-api/app/services/*`
- `packages/agent-runtime/agent/orchestrator.py`
- `packages/agent-runtime/agent/tools/registry.py`
- `apps/pa-web/src/pages/*`

## PASS Rules

PASS requires live evidence:

- Real PA backend/frontend or real PA backend API.
- Real WeKnora native API/module.
- Real non-mock model and embedding when the slice depends on them.
- Traceable evidence fields: `source`, `source_type`, `evidence_id`, and native ids such as `chunk_id`, `external_doc_id`, or `wiki_page_id`.
- Report or validation output that distinguishes live, fixture, mock, cached, partial, blocked, and backlog evidence.

Do not count these as PASS:

- mock backend
- mock model or mock embedding
- fixture-only proof
- static UI or demo page
- old cache or old report
- hidden fallback
- partial native response without citation/status contract

If live capability is not available, mark it `blocked` or `backlog` with cause and next step. Do not replace it with mock to make the task green.

## Spec Status Gate

The sprint spec is updated after evidence, not before it:

- For `[x]`, run the task's declared validation first and confirm the PASS
  evidence type matches the task card.
- For `[!]`, record the real runtime/API/model/config/source blocker and the
  next action needed to unblock it.
- For `[b]`, record why the slice is intentionally deferred and what smaller
  read-only or jump slice could be done later.
- For `[~]`, commit only a useful partial slice and make clear why it is not
  enough for PASS.
- Never use historical Phase 3/4/5 reports, cached browser state, fixture-only
  output, or static UI as current sprint PASS.

## Frontend And Backend Validation

For frontend tasks:

- Run a build/type check when feasible.
- Use browser validation for affected pages.
- Confirm visible status reflects real, mock, fallback, partial, blocked, or backlog truthfully.
- Do not hide fallback/mock/partial state to make a card look healthy.

For backend tasks:

- Validate through API calls or smoke scripts.
- Use `apps/pa-api/.venv/bin/python` for PA scripts when available.
- Keep `/health`, `/api/status`, and `/api/model/status` separate because WeKnora connectivity, chat model readiness, and embedding readiness can differ.

If a task touches both frontend and backend, run both validation categories or
record the exact blocker. A frontend task cannot be completed from build output
alone when the changed page needs live status/citation behavior. A backend task
cannot be completed from documentation alone unless its task card explicitly
says it is an audit/map task.

## Safety Rules

Never print, write into docs, or commit secrets:

- `.env` values
- API keys
- service tokens
- passwords
- private endpoints
- uploaded file bodies
- local database contents
- logs
- caches
- provider payloads

Never commit `.env`, local databases, logs, caches, uploads, `node_modules`, `dist`, screenshots, or generated runtime files.

Use precise staging paths. Do not use broad staging such as `git add docs` during this sprint if unrelated untracked docs exist.

Before committing:

- Run `git status -sb`.
- Stage only current-task paths with explicit filenames.
- Confirm unrelated dirty/untracked files remain unstaged, especially local
  reports outside the current task.
- Do not commit local databases, run logs, caches, uploads, `node_modules`,
  `dist`, screenshots, `.env`, API keys, private keys, service tokens, or real
  provider payloads.
- Do not push unless the user explicitly asks.

## Scope Reduction Rule

If a WeKnora capability is too large, do the smallest real integration slice first:

- read-only status before full admin mutation
- PA jump link to WeKnora native admin before rebuilding admin UI
- one KB/document/wiki/agent path before broad management
- one live smoke before a large matrix

Record remaining work as backlog with a concrete next step.

## Required Task Output

Each completed task should summarize:

- changed files
- validation commands and results
- live evidence or blocked/backlog reason
- risks found
- next optimization suggestion

Keep the summary concise and do not include secrets or raw private data.
