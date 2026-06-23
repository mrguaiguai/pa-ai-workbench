# PA WeKnora Native Expansion Internal Production Spec

> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Stage: Native Expansion / internal production
>
> Previous stage source: `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`

## 1. Stage Positioning

This stage starts from the current `weknora-first-mvp` branch. The WeKnora-first
stage has already finished most `WF-P0` to `WF-P2` read-only or live visibility
slices: document/RAG status, native AgentQA entry, Wiki browse/search/read,
MCP visibility, web search visibility, vector store visibility, frontend status
strip, report safety, and backlog decisions for risky mutations.

The next stage is not another visibility pass. Its goal is to make PA usable as
an internal production knowledge workbench for a small team: real workflows,
real WeKnora native capability coverage, truthful status, recoverable services,
history/citation continuity, and final acceptance reports.

## 2. Goals And Non-Goals

### Goals

- Reach at least **80%** coverage over eligible WeKnora native capability groups
  by the scoring rules in Section 5.
- Make PA's basic daily workflows truly usable: choose knowledge bases, ingest
  documents, inspect indexing/chunks, run RAG/knowledge-chat, use AgentQA/custom
  Agent entry points, browse Wiki, review history, and inspect citations.
- Keep PA's product value intact: frontend shell, business database, task
  history, citation/evidence layer, reports, status surfaces, deployment
  runbook, and professional workflow entry points.
- Route general platform capability through WeKnora native APIs/modules first:
  knowledge base, document parsing/indexing, chunk, retrieval, Wiki, AgentQA,
  custom Agent, MCP, web search, vector store, model/config, parser, data
  source, FAQ/tag/favorite/skill where available.
- Ship internal production evidence: live API validation, browser validation,
  report-safety checks, coverage ledger, risk/backlog list, and handoff prompt.

### Non-Goals

- Do not build a complete SaaS multi-tenant product in this stage.
- Do not rewrite WeKnora's native admin console inside PA when a jump link,
  read-only status, or small safe adapter is enough.
- Do not self-implement general RAG, general Wiki, general Agent orchestration,
  chunking, parser, embedding, vector store, MCP, or web search if WeKnora has a
  native path.
- Do not treat mock evidence, fixture-only evidence, static UI, old reports,
  cached browser state, or hidden fallbacks as PASS.
- Do not print or commit `.env` values, API keys, service tokens, private
  endpoints, raw uploaded bodies, local databases, logs, caches, provider
  payloads, screenshots, `uploads`, `node_modules`, or `dist`.
- Do not make WeKnora auth/tenant/org/IM/WeKnoraCloud the PA internal
  production mainline. These can be status, jump, blocked, or backlog items.

## 3. Modular PA Product Architecture

### 3.1 PA Frontend Shell

PA owns the user-facing workbench: home, library, RAG debug, intelligent
analysis, Wiki, history, capability center, and configuration center.

Responsibilities:

- Navigation, page composition, loading/error/blocked/backlog states.
- Product wording, professional templates, task entry points, and operator flow.
- Citation display, evidence locators, history review, and report access.
- Native jump links when full PA management UI is out of scope.

Forbidden:

- Do not show fake green states for unconfigured native services.
- Do not hide fallback/mock/partial state.
- Do not expose raw credential values or provider payloads.

### 3.2 PA Backend BFF

PA backend is a BFF layer. It exposes PA semantic APIs instead of naked WeKnora
responses.

Responsibilities:

- Normalize WeKnora native responses into PA status, history, citation, and
  workflow contracts.
- Add trace id, timeout, retry class, safe error messages, and source labels.
- Mask credentials and private config.
- Persist PA business records and snapshots that are needed for audit/history.

Forbidden:

- Do not persist WeKnora chunks/vectors as PA-owned truth.
- Do not expose raw upstream errors if they can contain credentials or payloads.
- Do not bypass the native adapter for new WeKnora capability.

### 3.3 WeKnora Native Adapter

All native integrations must pass through a shared adapter/client layer.

Responsibilities:

- Centralize base URL, token presence, workspace, knowledge base, timeout,
  retries, trace id, response normalization, and error classification.
- Provide typed/safe helper methods for knowledge base, document, chunk, RAG,
  knowledge-chat, AgentQA, custom Agent, Wiki, MCP, web search, vector store,
  model/config, parser, data source, FAQ/tag/favorite/skill.
- Keep secret-bearing config out of logs, reports, frontend payloads, and PA DB.

Forbidden:

- Do not add one-off HTTP calls directly in page handlers when an adapter method
  should exist.
- Do not normalize evidence in frontend-only code.

### 3.4 PA Business DB

PA stores business state, not WeKnora platform internals.

PA may store:

- `Document`, `Conversation`, `GenerationTask`, `GeneratedOutput`, `Citation`.
- `WikiPage`/`WikiCitation` or native Wiki reference snapshots needed by PA.
- Active workspace/knowledge-base selection snapshot.
- Workflow run state, report metadata, and safe validation summaries.

PA must not store:

- WeKnora authoritative chunks/vectors.
- Raw embeddings.
- Raw provider requests/responses.
- Credential values, API keys, service tokens, private endpoints, or `.env`
  values.

### 3.5 Evidence/Citation Layer

PA's citation layer is a core product asset and must survive every native
integration.

Allowed citation sources:

- Traceable `document_chunk` with native document/chunk ids.
- Traceable `wiki_page` with native page ids and readable locator.
- Traceable AgentQA/native Agent references only when the native response
  exposes enough source identity to audit the answer.

Not evidence:

- MCP status, web-search provider status, vector-store status, model/provider
  status, parser readiness, config availability, native jump link, or general
  health check.
- Agent answer text without traceable references.

### 3.6 Validation/Ops Layer

This layer protects internal production truthfulness.

Responsibilities:

- Live smoke runners, browser matrix, report safety, coverage ledger, service
  runbook, LaunchAgents checks, blocked/backlog recording, and handoff prompt.
- Separate live evidence, fixture evidence, mock evidence, cached evidence,
  partial evidence, blocked evidence, and backlog evidence in every report.

### 3.7 PA-native Professional Workflow Layer

PA keeps professional templates and workflow entry points. During this stage,
the layer should package native WeKnora capabilities instead of deepening a
separate general Agent/RAG/Wiki stack.

Default stance:

- Preserve policy/case/QA entry points and historical outputs.
- Freeze deeper PA-native general orchestration unless the user explicitly
  scopes a narrow professional workflow slice.
- Treat professional workflow output as internal production only when it has
  live WeKnora evidence and PA citation/history persistence.

## 4. Stage Progress Protocol

This spec is the source of truth for `WNX-*` work.

Status markers:

```text
[ ] Not started
[~] Partial committed slice; not enough for final PASS
[x] Completed with required evidence
[!] Blocked by real runtime/API/config/safety gap
[b] Backlog/deferred by stage scope
```

Execution loop:

1. Work in `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench`.
2. Read this spec.
3. Read `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md` for prior state.
4. Read `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md` when it exists.
5. Read `.github/skills/pa-weknora-native-expansion/SKILL.md` and the outer
   `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md`
   when available.
6. Run `git status -sb` and `git log --oneline -5`.
7. Execute exactly one `WNX-*` id per run.
8. Before editing, state task id, task classification, planned files,
   validation method, and expected PASS evidence type.
9. For native capability tasks, inspect WeKnora routes/handlers/services/types
   before PA code changes.
10. Validate through API/smoke/browser/service checks as required.
11. Update task status only after validation or a real blocked/backlog decision.
12. Stage only current-task files with explicit paths.

## 5. Coverage Ledger Rules

The coverage ledger must use this scoring model:

| State | Score | Meaning |
| --- | ---: | --- |
| `live-full` | 1.0 | Real PA path calls real WeKnora native capability and satisfies the PA contract, including history/citation/status when applicable. |
| `live-partial` | 0.5 | Real native call works, but PA contract is incomplete, such as missing citation, no mutation UI, or partial workflow coverage. |
| `read-only` | 0.25 | PA can safely inspect native status/list/catalog, but cannot execute the user workflow. |
| `blocked` | 0 | A real API/config/runtime/safety gap prevents completion. |
| `backlog` | 0 | Deferred by stage scope or risk. |
| `unsafe-for-pa` | 0 | Not suitable for PA exposure without a separate safety design. |

Coverage target:

```text
sum(capability_group_score) / count(eligible_capability_groups) >= 80%
```

The ledger must list all eligible groups, current state, target state,
validation method, evidence link/report, risk, and next action.

Baseline capability groups for this stage:

| Group | Current stage signal | Target | Notes |
| --- | --- | --- | --- |
| System health/status/deployment | live/read-only | `live-full` | PA should recover backend, frontend, WeKnora, model, embedding, vector, parser. |
| Workspace/knowledge-base management | live-partial/read-only | `live-full` | Active KB selection plus safe KB CRUD where native API supports it. |
| Document lifecycle | live-partial | `live-full` | File/url/manual ingestion, status, delete/reparse/cancel where safe. |
| Chunk management | read-only/live-partial | `live-partial` or `live-full` | Preview first; dangerous mutation needs confirmation. |
| Knowledge-search/RAG | live-full/live-partial | `live-full` | Preserve current-run evidence and citation mapping. |
| Knowledge-chat/session chat | backlog | `live-full` | Add real PA conversation/history path. |
| AgentQA/custom Agent | live-partial | `live-full` or explicit citation blocker | Answer/history is not enough if references are missing. |
| Native Wiki | live-partial/read-only | `live-full` for safe flows | Mutations need confirmation and rollback story. |
| MCP | read-only | `live-partial` or `live-full` | Credential/mutation safety decides scope. |
| Web search | read-only | `live-partial` or `live-full` | Provider readiness plus AgentQA readiness. |
| Vector store | live-partial | `live-partial` or `live-full` | No raw secret/config exposure. |
| Model/embedding/rerank/parser | partial status | `live-partial` or `live-full` | Remote checks and test calls must be sanitized. |
| Data sources/connectors | backlog | `live-partial` | Start with safe validate/resources/sync status. |
| FAQ/tags/favorites/skills | backlog | `live-partial` | Workbench polish and knowledge organization. |
| History/citation/product shell | PA-owned live | `live-full` | Must integrate every native workflow output. |

Excluded or limited groups:

- Full SaaS auth/tenant/org/IM/WeKnoraCloud: status, jump, blocked, or backlog
  only unless explicitly reprioritized.
- Raw platform observability/admin mutation: backlog unless it has a safe PA
  use case and confirmation flow.

## 6. Task Board

| ID | Priority | Capability slice | Status | Required evidence |
| --- | --- | --- | --- | --- |
| WNX-0-01 | Governance | New native expansion spec + skill | [x] | Spec/skill created, skill frontmatter validates, diff/sensitive scans pass. |
| WNX-0-02 | Governance | Architecture blueprint and module boundaries | [x] | `docs/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md` with PA/WeKnora/DB/adapter/evidence/ops boundaries. |
| WNX-0-03 | Governance | Coverage ledger and 80% scoring baseline | [x] | `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md` with current/target states and scoring. |
| WNX-P0-01 | P0 | Unified WeKnora native client | [x] | Adapter has shared config/error/timeout/retry/trace/normalization and smoke validation. |
| WNX-P0-02 | P0 | Internal config/status center backend | [x] | PA API exposes masked native config/status for core platform areas. |
| WNX-P0-03 | P0 | Capability center frontend shell | [x] | Browser-validated capability center shows coverage, gaps, blocked/backlog, jump links. |
| WNX-P0-04 | P0 | Live acceptance harness | [x] | Checker/smoke runner verifies live evidence, report safety, coverage score, browser matrix hooks. |
| WNX-P0-05 | P0 | Internal deployment readiness | [x] | Service/runbook validation proves recoverable backend/frontend/WeKnora/model/embedding/vector/parser. |
| WNX-P1-01 | P1 | Knowledge base management | [x] | PA can list/read/create/update/delete/pin/tag active KBs or record safe blockers. |
| WNX-P1-02 | P1 | Document lifecycle | [x] | File/url/manual ingestion, status spans, preview/download, delete/reparse/cancel/chunks as safe live flows. |
| WNX-P1-03 | P1 | Chunk management | [x] | Chunk list/read/update/toggle/delete/questions mapped with confirmation/backlog rules. |
| WNX-P1-04 | P1 | Native RAG + knowledge-chat | [x] | Search and knowledge-chat run through native APIs with PA history/citation/current-run evidence. |
| WNX-P1-05 | P1 | AgentQA + custom Agent workflow | [x] | Native AgentQA/custom Agent enters PA intelligent analysis/history; citation blocker stays explicit if needed. |
| WNX-P1-06 | P1 | Wiki full native workflow | [x] | Pages/search/create/update/delete/index/log/graph/stats/lint/issues safe flows integrated. |
| WNX-P1-07 | P1 | History and citation unification | [x] | All native workflows persist PA history and valid citation locators or fail closed. |
| WNX-P2-01 | P2 | Model/embedding/rerank/parser config | [x] | Masked status plus remote/model/embedding/rerank/parser checks without secret leakage. |
| WNX-P2-02 | P2 | MCP service management | [x] | Safe live-partial MCP list/read/test controls; no configured service in live run; credentials/mutations/tool execution remain backlog. |
| WNX-P2-03 | P2 | Web search provider management | [x] | Safe live-partial provider type/list/read/test controls; no configured provider in live run; credentials/mutations/raw search remain backlog. |
| WNX-P2-04 | P2 | Vector store management | [x] | Safe live-partial vector store type/list/detail/test controls and KB binding visibility without raw config/secret leakage. |
| WNX-P2-05 | P2 | Data source connector management | [ ] | Connector validate/resources/sync/pause/resume/logs with dangerous mutation backlog as needed. |
| WNX-P2-06 | P2 | FAQ, tags, favorites, skills | [ ] | Native FAQ/tags/favorites/skill list integrated as workbench organization primitives. |
| WNX-P3-01 | P3 | Six-page product workflow browser matrix | [ ] | Home, library, RAG, analysis, Wiki, history, capability center pass desktop/mobile browser checks. |
| WNX-P3-02 | P3 | Internal production report | [ ] | `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_PASS_REPORT.md` with coverage/live/browser/config/risk/backlog. |
| WNX-P3-03 | P3 | Deployment handoff prompt/runbook | [ ] | New-chat prompt and deployment runbook explain continuation from git log/spec/reports. |

## 7. Progress Log

| Date | Task id | Status | Evidence | Commit / branch | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-06-22 | WNX-0-01 | [x] | `governance artifact`: native expansion spec and skill added; validation includes skill frontmatter, diff check, sensitive scan, and keyword checks. | this commit on `weknora-first-mvp` | No product code changed and no new live capability PASS is claimed. |
| 2026-06-22 | WNX-0-02 | [x] | `audit/map`: architecture blueprint added with PA Frontend Shell, PA Backend BFF, WeKnora Native Adapter, PA Business DB, Evidence/Citation Layer, Validation/Ops Layer, and PA-native Professional Workflow Layer boundaries; validation includes diff check, keyword checks, and sensitive scan. | this commit on `weknora-first-mvp` | No product code changed and no new live capability PASS is claimed; the blueprint maps later `WNX-P0`, `WNX-P1`, and `WNX-P2` development landing zones. |
| 2026-06-22 | WNX-0-03 | [x] | `audit/map`: coverage ledger added with 15 eligible capability groups, current baseline `5.50 / 15 = 36.7%`, minimum target `12.00 / 15 = 80.0%`, evidence links, risks, and next `WNX-*` actions; validation includes diff check, keyword checks, and sensitive scan. | this commit on `weknora-first-mvp` | No product code changed and no new live capability PASS is claimed; future tasks must refresh live WNX evidence before final internal production PASS. |
| 2026-06-23 | WNX-P0-01 | [x] | `live evidence` + `fixture evidence`: `WeKnoraNativeClient` added; MCP and vector-store native live smokes pass through PA; fixture contract proves health/MCP/vector paths share `backend.client.request_json`, status metadata is visible, and error redaction remains stable. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_CLIENT_REPORT.md`; unsafe MCP/vector mutations remain backlog for their own WNX tasks. |
| 2026-06-23 | WNX-P0-02 | [x] | `live API evidence`: `/api/native/status` added as a masked PA BFF status center with 15 capability groups, unified `configured/masked/status/source_endpoint/next_action` fields, live MCP/web/vector/model status, and backlog markers for unimplemented/high-risk platform areas. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_STATUS_CENTER_REPORT.md`; this task does not upgrade coverage score or convert read-only visibility into workflow PASS. |
| 2026-06-23 | WNX-P0-03 | [x] | `live browser evidence backed by live API response`: capability center route loads `/api/native/status`, renders 15 live capability groups, shows `live=7`, `partial=5`, `blocked=0`, `backlog=3`, and passes desktop/mobile Chrome DOM checks without horizontal overflow or suspicious secret-like text. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_CAPABILITY_CENTER_BROWSER_REPORT.md`; this task adds truthful frontend visibility only and does not upgrade backlog/read-only groups to workflow PASS. |
| 2026-06-23 | WNX-P0-04 | [x] | `checker execution evidence`: stage harness added with self-test, static report/spec/ledger validation, Phase 5 report-safety self-test reuse, browser hook checks, coverage math checks (`5.50/15 = 36.7%`, target `12.00/15 = 80.0%`), and optional live `/api/native/status` validation showing `groups=15 live=7 partial=5 blocked=0 backlog=3`. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_EXPANSION_ACCEPTANCE_HARNESS_REPORT.md`; this guardrail does not upgrade any capability score or create workflow PASS by itself. |
| 2026-06-23 | WNX-P0-05 | [x] | `live service/status evidence`: deployment readiness checker validates recovery scripts/runbook and starts temporary backend/frontend; `/health`, `/api/status`, `/api/model/status`, `/api/native/status`, and frontend HTML all pass with WeKnora connected, KB mapping validated, non-mock chat/embedding, and vector/model/parser group live. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_REPORT.md`; coverage ledger updates system health/status/deployment to `live-full` and current score to `6.00 / 15 = 40.0%`; cloud deployment and deeper parser management remain later scope. |
| 2026-06-23 | WNX-P1-01 | [x] | `live API/browser evidence`: PA BFF `/api/knowledge-bases/native/overview` and `/api/knowledge-bases/native/active` list/read native KBs, save a PA active-selection snapshot, expose safe tag status, and Chrome headless verifies the Library KB selector DOM. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_KB_MANAGEMENT_LIVE_REPORT.md`; coverage ledger updates workspace/knowledge-base management to `live-full` and current score to `6.50 / 15 = 43.3%`; destructive create/update/delete and pin/tag write flows remain backlog until confirmation/audit trail exists. |
| 2026-06-23 | WNX-P1-02 | [x] | `live API/browser evidence`: PA BFF file upload reached indexed through WeKnora, URL and manual ingestion returned native ids, chunks/spans/preview/download were live, reparse/delete submitted native lifecycle actions, cancel stayed a safe terminal-state control, and Chrome headless verified Library lifecycle UI. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_DOCUMENT_LIFECYCLE_LIVE_REPORT.md`; coverage ledger updates document lifecycle to `live-full` and current score to `7.00 / 15 = 46.7%`; destructive chunk mutation remains `WNX-P1-03`. |
| 2026-06-23 | WNX-P1-03 | [x] | `live API/browser evidence`: PA BFF validates native chunk list/by-id, toggles enabled state, deletes a temporary smoke chunk with confirmation, records audit events, and Chrome headless verifies the Library chunk detail workflow. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_CHUNK_MANAGEMENT_LIVE_REPORT.md`; coverage ledger updates chunk management to `live-full` and current score to `7.75 / 15 = 51.7%`; content rewrite, generated-question delete PASS, and search-by-chunk remain backlog. |
| 2026-06-23 | WNX-P1-04 | [x] | `live API/browser evidence`: PA RAG debug returns current-run native search evidence, PA BFF runs native WeKnora knowledge-chat, persists conversation/history/output/citations, and Chrome headless verifies the RAG page knowledge-chat workflow. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_RAG_KNOWLEDGE_CHAT_LIVE_REPORT.md`; coverage ledger updates knowledge-chat/session chat to `live-full` and current score to `8.75 / 15 = 58.3%`; full cross-workflow history/citation unification remains `WNX-P1-07`. |
| 2026-06-23 | WNX-P1-05 | [x] | `live API/browser evidence`: PA BFF lists native custom Agents/type presets/placeholders/suggested questions safely, runs native `/api/v1/agent-chat/{session_id}`, persists PA conversation/history/output, and Chrome headless verifies the Analysis page native AgentQA workflow. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_AGENTQA_CUSTOM_AGENT_LIVE_REPORT.md`; coverage score remains `8.75 / 15 = 58.3%` because native AgentQA emitted zero traceable references in the live run, so PA records `CITATION_BLOCKED` instead of fabricating citations; Agent copy/update/delete remain backlog. |
| 2026-06-23 | WNX-P1-06 | [x] | `live API/browser evidence`: PA BFF exposes native Wiki pages/search/read/create/update/delete/index/log/graph/stats/lint/issues, smoke creates/updates/soft-deletes a temporary native Wiki page, and Chrome headless verifies the Wiki page Native workflow panel and confirmation controls. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_WIKI_WORKFLOW_LIVE_REPORT.md`; coverage ledger updates Native Wiki to `live-full` and current score to `9.25 / 15 = 61.7%`; global rebuild-links/auto-fix stay confirmation-gated and cross-workflow citation unification remains `WNX-P1-07`. |
| 2026-06-23 | WNX-P1-07 | [x] | `live API/browser evidence`: PA history now exposes traceable citation counts, citation-blocked state, and native workflow filters; live smoke verifies native knowledge-chat saved 2 locatable citations while native AgentQA fails closed as `citation_blocked=true`, and Chrome headless verifies the History page evidence states. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md`; coverage ledger updates History/citation/product shell to `live-full` and current score to `9.75 / 15 = 65.0%`; AgentQA/custom Agent remains `live-partial` until native references are traceable. |
| 2026-06-23 | WNX-P2-01 | [x] | `live API/browser evidence`: PA BFF `/api/model/native/overview` reads native model providers, model catalog, parser engines, storage engine status, and PA chat/embedding runtime as masked statuses; Chrome headless verifies the Capability Center model/config readiness card. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_MODEL_CONFIG_LIVE_REPORT.md`; coverage score remains `9.75 / 15 = 65.0%` because this group target is `live-partial`; remote model/embedding/rerank/parser/storage active tests stay `blocked_admin_only` until an operator confirmation and secret-handling design exists. |
| 2026-06-23 | WNX-P2-02 | [x] | `live API/browser evidence`: PA BFF `/api/mcp/native/overview` reaches native MCP service list with `services.status=live`, `services.count=0`, exposes sanitized service detail/test endpoints, and Chrome headless verifies Capability Center MCP management status including `safe_test_status`. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_MCP_MANAGEMENT_LIVE_REPORT.md`; coverage ledger updates MCP to `live-partial` and current score to `10.00 / 15 = 66.7%`; no configured service exists for live external test/tool/resource probes, and credentials, service CRUD, approval mutation, and tool execution remain backlog. |
| 2026-06-23 | WNX-P2-03 | [x] | `live API/browser evidence`: PA BFF `/api/web-search/native/overview` reaches native provider type catalog and configured-provider list with `provider_types.count=7`, `configured_providers.count=0`, exposes sanitized provider detail/test endpoints, and Chrome headless verifies Capability Center web search management status including `provider_test_status`. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_WEB_SEARCH_MANAGEMENT_LIVE_REPORT.md`; coverage ledger updates Web search to `live-partial` and current score to `10.25 / 15 = 68.3%`; no configured provider exists for live external test or AgentQA web-search readiness, and credentials, provider CRUD, raw tests/search, and PA-owned orchestration remain backlog. |
| 2026-06-23 | WNX-P2-04 | [x] | `live API/browser evidence`: PA BFF `/api/vector-stores/native/overview` reaches native vector-store type/list APIs, reads one configured env store through a safe-index detail path, verifies active KB binding and embedding readiness, and Chrome headless verifies Capability Center vector-store management status including `store_test_status`. | this commit on `weknora-first-mvp` | Dedicated report: `docs/WEKNORA_NATIVE_VECTOR_STORE_MANAGEMENT_LIVE_REPORT.md`; coverage ledger updates Vector store to `live-partial` and current score to `10.50 / 15 = 70.0%`; confirmed external vector-store test was not requested, and CRUD, raw config/test, KB rebind, and PA-owned vector administration remain backlog. |

## 8. Task Cards

### WNX-0-01: New native expansion spec + skill

- Goal: create the next-stage spec and skill so future work is modular,
  WeKnora-native-first, evidence-driven, and internal-production-oriented.
- Scope: add this spec, repo-local skill, outer workspace skill, and a
  next-stage pointer in the previous sprint spec.
- Inputs: current `weknora-first-mvp` state, previous five-day sprint spec,
  previous sprint skill, skill-creator rules, Phase 3/4/5 validation habits.
- Output report: this spec and both `SKILL.md` files.
- Editable files: `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md`,
  `.github/skills/pa-weknora-native-expansion/SKILL.md`,
  `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md`,
  and a small next-stage entry in `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.
- Forbidden: product code, runtime config, `.env`, database, logs, caches,
  uploads, screenshots, and broad staging.
- Acceptance: both skills pass quick validation; `git diff --check` passes;
  sensitive scan finds no secret assignments/private keys; required keywords
  are present in this spec.
- Recommended validation: run the commands in Section 10.
- PASS evidence: governance artifact validation only; no live evidence claim.
- Blocked/backlog: mark `[!]` if the outer `.agents` path cannot be written
  after approval; mark `[b]` only if the user drops the outer skill requirement.
- Status source: Section 6 row `WNX-0-01`.

### WNX-0-02: Architecture blueprint and module boundaries

- Goal: turn Section 3 into a more operational architecture blueprint with
  module ownership, request flow, DB ownership, adapter contracts, and frontend
  page responsibilities.
- Scope: document PA/WeKnora/frontend/BFF/adapter/DB/evidence/ops/professional
  boundaries, including a diagram and file map.
- Inputs: this spec, old product spec, current backend/frontend structure,
  WeKnora native routes, PA model definitions, current reports.
- Output report: `docs/WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md`.
- Editable files: that architecture doc and this spec status/progress rows.
- Forbidden: code changes, endpoint invention, or claiming implementation from
  architecture alone.
- Acceptance: doc names core modules, existing files, desired adapter modules,
  data boundaries, allowed citation sources, and unsafe areas.
- Recommended validation: `rg` for each architecture layer, `git diff --check`.
- PASS evidence: audit/design evidence, not live capability evidence.
- Blocked/backlog: mark `[!]` if the codebase layout cannot be inspected.
- Status source: Section 6 row `WNX-0-02`.

### WNX-0-03: Coverage ledger and 80% scoring baseline

- Goal: create the stage coverage ledger and make the 80% rule executable by
  future agents.
- Scope: enumerate eligible capability groups, current state, target state,
  score, evidence source, report links, blockers, and owner.
- Inputs: Section 5, prior WF reports, live status endpoints, current frontend
  pages, WeKnora native capability map.
- Output report: `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md`.
- Editable files: the ledger doc and this spec status/progress rows.
- Forbidden: inflating scores from read-only visibility, mock evidence, cached
  reports, static UI, or unverified inference.
- Acceptance: total score formula is shown, current baseline is computed, target
  score is explained, and each group has a next WNX task id.
- Recommended validation: `rg -n "live-full|live-partial|read-only|80%"`.
- PASS evidence: ledger/audit evidence; no new live capability PASS unless
  validated separately by a capability task.
- Blocked/backlog: mark `[!]` if prior reports are missing or contradictory.
- Status source: Section 6 row `WNX-0-03`.

### WNX-P0-01: Unified WeKnora native client

- Goal: make all native integrations use one PA adapter/client contract.
- Scope: centralize base URL, token/config presence, workspace, KB, timeout,
  retry class, trace id, response normalization, safe errors, and status labels.
- Inputs: WeKnora router/handler/service/types, existing
  `knowledge_engine/backends/weknora_api_backend.py`, PA backend API/service
  files, current native visibility adapters.
- Output report: client design notes and smoke output, either in a dedicated
  report or coverage ledger row.
- Editable files: adapter/client modules, related backend API/service files,
  tests/smokes, this spec status/progress rows.
- Forbidden: direct new one-off HTTP calls outside the adapter; logging secrets;
  frontend-only normalization of native evidence.
- Acceptance: at least two existing native capability paths use the shared
  client, error responses are sanitized, and trace/status metadata is visible.
- Recommended validation: backend smoke against real WeKnora plus unit/fixture
  tests for redaction/error normalization.
- PASS evidence: live API evidence for shared-client paths plus fixture evidence
  only for redaction branches.
- Blocked/backlog: mark `[!]` if real WeKnora is unavailable; keep noncritical
  native areas as backlog until the client contract is stable.
- Status source: Section 6 row `WNX-P0-01`.

### WNX-P0-02: Internal config/status center backend

- Goal: expose one PA backend status surface for native platform readiness.
- Scope: workspace, KB, models, embedding, rerank, parser, vector store, MCP,
  web search, data source, FAQ/tags/favorites/skills where native APIs exist.
- Inputs: unified client, existing `/health`, `/api/status`,
  `/api/model/status`, native visibility endpoints, WeKnora config/status APIs.
- Output report: config/status center API report with masked fields.
- Editable files: backend API/service/schema files, smoke scripts, reports,
  this spec status/progress rows.
- Forbidden: raw credential values, raw provider payloads, private endpoints,
  local `.env` values, or treating configured-but-untested as live-full.
- Acceptance: PA API returns `configured`, `masked`, `live/partial/blocked`,
  source endpoint, and next action for each capability group.
- Recommended validation: curl/API smoke against live backend and WeKnora,
  sensitive scan over output report.
- PASS evidence: live API evidence; unavailable groups must be blocked/backlog.
- Blocked/backlog: mark `[!]` for runtime/config/API failure; mark `[b]` for
  unsupported platform areas outside PA internal production scope.
- Status source: Section 6 row `WNX-P0-02`.

### WNX-P0-03: Capability center frontend shell

- Goal: give operators a real capability center/config center in PA.
- Scope: coverage summary, capability group status, config gaps, blocked/backlog
  reasons, safe native jump links, validation report links, and no fake green
  states.
- Inputs: config/status center backend, coverage ledger, existing frontend
  shell/navigation/status components.
- Output report: browser validation report for capability center.
- Editable files: frontend pages/components/routes/styles, backend route only if
  a small BFF shape adjustment is needed, report, this spec rows.
- Forbidden: static status cards, hidden fallback, mock data as healthy state,
  secret display, or marketing landing-page behavior.
- Acceptance: desktop and mobile browser checks show real statuses, partial and
  blocked states remain visible, and text does not overflow.
- Recommended validation: frontend build/type check plus browser validation.
- PASS evidence: live browser evidence backed by live API response.
- Blocked/backlog: mark `[!]` if backend status API is unavailable; mark `[b]`
  for risky mutation UI deferred to native admin jump links.
- Status source: Section 6 row `WNX-P0-03`.

### WNX-P0-04: Live acceptance harness

- Goal: create one stage checker that guards internal production PASS claims.
- Scope: live evidence checks, report safety, coverage score, browser matrix
  hooks, blocked/backlog consistency, and status/spec progress sanity.
- Inputs: existing Phase 3/4/5 checkers, report safety scripts, prior browser
  matrix, coverage ledger.
- Output report: checker script output and stage validation report.
- Editable files: scripts/tests/reports/docs needed for the harness, this spec
  rows.
- Forbidden: marking PASS from fixture-only output, stale reports, cached files,
  or static HTML.
- Acceptance: checker fails on mock evidence, missing evidence classification,
  leaked secret-shaped assignments, or coverage below target unless explicitly
  in progress.
- Recommended validation: run checker against current reports and a small
  negative fixture if safe.
- PASS evidence: checker execution evidence; live capability PASS still belongs
  to each capability task.
- Blocked/backlog: mark `[!]` if current reports cannot be parsed safely.
- Status source: Section 6 row `WNX-P0-04`.

### WNX-P0-05: Internal deployment readiness

- Goal: prove the internal production stack can be stopped, started, checked,
  and recovered.
- Scope: backend, frontend, WeKnora service reachability, model, embedding,
  vector store, parser, LaunchAgents/service scripts, runbook, status endpoints.
- Inputs: existing local service scripts, LaunchAgents docs, `/health`,
  `/api/status`, `/api/model/status`, native config/status center.
- Output report: deployment readiness/runbook update.
- Editable files: runbook docs, service scripts only if needed, validation
  scripts, this spec rows.
- Forbidden: committing logs, pid files, local DBs, `.env`, caches, screenshots,
  or service output containing secrets.
- Acceptance: documented commands recover services and status endpoints return
  truthful state; unavailable dependencies are blocked with next steps.
- Recommended validation: service/status smoke, without printing secret-bearing
  environment.
- PASS evidence: live service/status evidence.
- Blocked/backlog: mark `[!]` for missing runtime dependencies; mark `[b]` for
  cloud deployment beyond internal local production scope.
- Status source: Section 6 row `WNX-P0-05`.

### WNX-P1-01: Knowledge base management

- Goal: make PA manage active WeKnora knowledge bases enough for internal use.
- Scope: list/read/create/update/delete/pin/tags where native APIs support safe
  operations; active KB selection and multi-KB status.
- Inputs: WeKnora KB routes/services/types, unified client, PA status/config
  center, library UI.
- Output report: KB management live report.
- Editable files: adapter, backend BFF, PA DB selection snapshot, frontend
  library/config pages, tests/reports, this spec rows.
- Forbidden: deleting or mutating production KB without confirmation flow;
  storing secrets; hiding selected-KB fallback.
- Acceptance: list/read and active selection are live; mutation flows either
  pass with confirmation and audit trail or are explicit backlog.
- Recommended validation: API smoke and browser workflow for selection.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for missing native APIs/config; mark `[b]` for
  unsafe destructive actions.
- Status source: Section 6 row `WNX-P1-01`.

### WNX-P1-02: Document lifecycle

- Goal: make documents move through WeKnora native ingestion/indexing with PA
  product status and recovery controls.
- Scope: file/url/manual ingestion, status stages/spans, preview/download,
  delete/reparse/cancel where safe, and chunk preview link.
- Inputs: native document/knowledge APIs, PA document models/services, library
  page, upload components, current live document/RAG reports.
- Output report: document lifecycle live report.
- Editable files: adapter, backend document APIs/services/models if needed,
  frontend library/upload/status, tests/reports, this spec rows.
- Forbidden: local PA parser/chunker/vector path as completion for WeKnora docs;
  raw file body in reports; unsafe delete without confirmation.
- Acceptance: at least one sanitized document goes through live native ingestion
  and status; lifecycle controls reflect real native state.
- Recommended validation: live upload/status/chunk smoke plus browser workflow.
- PASS evidence: live API/browser evidence; fixture is acceptable only as input
  processed by the live system.
- Blocked/backlog: mark `[!]` if indexing/runtime fails; mark `[b]` for risky
  actions lacking safe native support.
- Status source: Section 6 row `WNX-P1-02`.

### WNX-P1-03: Chunk management

- Goal: expose safe chunk inspection and selected safe chunk operations.
- Scope: chunk list/by-id, update, toggle, delete, generated questions, and
  search-by-chunk if native APIs support it.
- Inputs: native chunk routes/services/types, document lifecycle path, citation
  contract, frontend library/detail view.
- Output report: chunk management validation report.
- Editable files: adapter, backend chunk BFF, frontend chunk panels, tests/
  reports, this spec rows.
- Forbidden: dangerous mutation without confirmation; treating chunk status as
  citation unless tied to a real answer/evidence.
- Acceptance: chunk preview is live; mutations either pass with confirmation and
  audit trail or remain backlog.
- Recommended validation: API smoke and browser chunk detail workflow.
- PASS evidence: live API/browser evidence for safe operations.
- Blocked/backlog: mark `[!]` for native API gaps; mark `[b]` for destructive
  operations lacking safety design.
- Status source: Section 6 row `WNX-P1-03`.

### WNX-P1-04: Native RAG + knowledge-chat

- Goal: unify PA RAG debug and user knowledge-chat around WeKnora native APIs.
- Scope: knowledge-search, knowledge-chat/session chat, current-run isolation,
  conversation history, citation mapping, source scope, and error/status labels.
- Inputs: current RAG adapter, WeKnora search/chat routes, PA history models,
  citation contract, RAG debug page.
- Output report: RAG and knowledge-chat live report.
- Editable files: adapter, backend RAG/chat APIs, history/citation persistence,
  frontend RAG/debug/chat pages, tests/reports, this spec rows.
- Forbidden: mock model/embedding, stale current-run evidence, hidden fallback,
  old cached answers as PASS.
- Acceptance: search and chat both work through live WeKnora and persist PA
  history/citation when references exist.
- Recommended validation: live API matrix plus browser workflow.
- PASS evidence: live evidence with source, source_type, evidence_id, native ids,
  and current-run guard.
- Blocked/backlog: mark `[!]` if model/embedding/chat runtime blocks; mark `[b]`
  for advanced ranking UI beyond internal use.
- Status source: Section 6 row `WNX-P1-04`.

### WNX-P1-05: AgentQA + custom Agent workflow

- Goal: make WeKnora native AgentQA/custom Agent usable from PA intelligent
  analysis and history.
- Scope: native agent list/type presets/placeholders/suggested questions/copy,
  AgentQA run, history persistence, citation/reference mapping, blocker display.
- Inputs: WeKnora AgentQA/custom Agent routes/services/types, current PA
  AgentQA visibility, intelligent analysis page, history/citation layers.
- Output report: AgentQA/custom Agent live report.
- Editable files: adapter, backend agent APIs/services, frontend intelligent
  analysis/history pages, tests/reports, this spec rows.
- Forbidden: PA-native general agent reimplementation; claiming citation PASS
  if native response lacks traceable references; raw prompts/provider payloads.
- Acceptance: at least one native AgentQA/custom Agent path runs live and stores
  output; citation is PASS only with traceable native references, otherwise an
  explicit blocker is preserved.
- Recommended validation: live API smoke plus browser analysis workflow.
- PASS evidence: live API/browser evidence; citation PASS requires traceable
  references.
- Blocked/backlog: mark `[!]` for citation/reference gaps or model runtime
  failure; mark `[b]` for advanced agent builder UI.
- Status source: Section 6 row `WNX-P1-05`.

### WNX-P1-06: Wiki full native workflow

- Goal: make PA's Wiki page a real native Wiki workspace, not only a status
  mirror.
- Scope: pages list/read/search/create/update/delete, index/log, graph, stats,
  lint, issues; confirmation for mutations; backlog for auto-fix/rebuild-links
  until safe.
- Inputs: native Wiki routes/services/types, current Wiki overview API, PA Wiki
  models/citations, frontend Wiki page.
- Output report: Wiki workflow live report.
- Editable files: adapter, backend Wiki APIs/services, frontend Wiki page,
  history/citation integration, tests/reports, this spec rows.
- Forbidden: destructive Wiki mutation without confirmation; pretending lint
  status is citation evidence; static Wiki samples as PASS.
- Acceptance: browse/search/read and at least one safe mutation or explicit
  mutation backlog are validated; citation locator works for Wiki-derived
  answers.
- Recommended validation: live API and browser Wiki workflow.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for native API/runtime gaps; mark `[b]` for
  auto-fix/rebuild/issue mutation without safety design.
- Status source: Section 6 row `WNX-P1-06`.

### WNX-P1-07: History and citation unification

- Goal: make every native workflow produce consistent PA history and evidence
  behavior.
- Scope: RAG, knowledge-chat, AgentQA, custom Agent, Wiki, document/chunk-driven
  outputs, generated reports, and filters.
- Inputs: PA models, citation contract, existing history page, all native
  workflow reports.
- Output report: history/citation unification report.
- Editable files: backend models/services/API, frontend history/citation
  components, migrations if required, tests/reports, this spec rows.
- Forbidden: fabricating evidence for status/config capabilities; lossy citation
  migration; hiding missing citation blockers.
- Acceptance: each output type is either persisted with valid locator or
  fails closed with visible blocker; history filters can distinguish sources.
- Recommended validation: API smoke plus browser history workflow.
- PASS evidence: live or current-run API/browser evidence for native outputs.
- Blocked/backlog: mark `[!]` if native references are insufficient; mark `[b]`
  for advanced analytics beyond internal production.
- Status source: Section 6 row `WNX-P1-07`.

### WNX-P2-01: Model/embedding/rerank/parser config

- Goal: expose native model and parsing readiness for operators without secrets.
- Scope: model/provider catalog, credential status, remote checks, embedding
  test, rerank check, parser engine/storage status.
- Inputs: WeKnora model/init/system/parser routes, PA model status endpoint,
  config center backend/frontend.
- Output report: model/config validation report.
- Editable files: adapter, backend config APIs, frontend capability/config
  center, tests/reports, this spec rows.
- Forbidden: credential values, provider payloads, `.env` values, raw private
  endpoint output.
- Acceptance: PA shows masked/configured/live/blocked status and a safe test
  result for each applicable runtime.
- Recommended validation: live API smoke and sensitive scan.
- PASS evidence: live API evidence; masked status is not enough for live-full
  unless a test call succeeds.
- Blocked/backlog: mark `[!]` for runtime/config gaps; mark `[b]` for provider
  admin features better left to WeKnora native console.
- Status source: Section 6 row `WNX-P2-01`.

### WNX-P2-02: MCP service management

- Goal: make MCP services visible and safely manageable where appropriate.
- Scope: service CRUD/test, tools, resources, approvals, and safe jump links.
- Inputs: WeKnora MCP routes/services/types, current MCP visibility report,
  config/capability center.
- Output report: MCP management report.
- Editable files: adapter, backend MCP BFF, frontend config/capability center,
  tests/reports, this spec rows.
- Forbidden: exposing credential values; executing tools without approval;
  storing provider/tool payloads in reports.
- Acceptance: list/read/test live where configured; create/update/delete and
  tool execution either pass with approval model or remain backlog.
- Recommended validation: live API smoke and browser status workflow.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for unavailable native MCP runtime; mark `[b]` for
  unsafe execution/mutation.
- Status source: Section 6 row `WNX-P2-02`.

### WNX-P2-03: Web search provider management

- Goal: manage web search readiness for native AgentQA/workflows.
- Scope: provider types/list/create/update/delete/test and AgentQA web-search
  readiness.
- Inputs: WeKnora web search routes/services/types, current visibility report,
  AgentQA workflow.
- Output report: web search management report.
- Editable files: adapter, backend web-search BFF, frontend config/capability
  center, tests/reports, this spec rows.
- Forbidden: raw API keys, provider payloads, secret-bearing test output, or
  claiming AgentQA web search readiness from provider catalog alone.
- Acceptance: configured provider status/test is live or explicitly blocked;
  AgentQA readiness reflects actual provider availability.
- Recommended validation: live API smoke and browser status workflow.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for missing credentials/runtime; mark `[b]` for
  provider admin mutation without safe native credential endpoint.
- Status source: Section 6 row `WNX-P2-03`.

### WNX-P2-04: Vector store management

- Goal: make vector-store readiness and KB binding visible and manageable.
- Scope: vector store types/list/create/update/delete/test, active KB binding,
  embedding readiness, and safe jump links.
- Inputs: WeKnora vector store routes/services/types, current vector visibility
  report, KB management, embedding status.
- Output report: vector store management report.
- Editable files: adapter, backend vector BFF, frontend config/capability center,
  tests/reports, this spec rows.
- Forbidden: raw DSNs/config/secrets, raw vector data, direct PA vector admin
  that conflicts with WeKnora as source of truth.
- Acceptance: list/read/binding/test are live or blocked with next action;
  mutations require safe native config flow and confirmation.
- Recommended validation: live API smoke and browser status workflow.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for unavailable test/config endpoint; mark `[b]`
  for destructive store mutation.
- Status source: Section 6 row `WNX-P2-04`.

### WNX-P2-05: Data source connector management

- Goal: add safe connector visibility and sync controls for knowledge ingestion.
- Scope: connector types/list/create/update/validate/resources/sync/pause/
  resume/logs; start with safe read/sync.
- Inputs: WeKnora data source routes/services/types, document lifecycle, config
  center.
- Output report: data source connector report.
- Editable files: adapter, backend data-source BFF, frontend config/library
  pages, tests/reports, this spec rows.
- Forbidden: storing connector credentials, printing sync logs with secrets,
  unsafe destructive mutation.
- Acceptance: connector type/status/resource validation is live; sync controls
  are live only if safe and auditable.
- Recommended validation: live API smoke with sanitized connector or read-only
  native status if no connector is configured.
- PASS evidence: live API/browser evidence; read-only catalog is at most
  `read-only` coverage.
- Blocked/backlog: mark `[!]` for missing native API/config; mark `[b]` for
  credential-heavy connector setup.
- Status source: Section 6 row `WNX-P2-05`.

### WNX-P2-06: FAQ, tags, favorites, skills

- Goal: complete PA as a usable knowledge workbench with organization features.
- Scope: FAQ CRUD/search/import progress, KB tags, user favorites, native skill
  list, and safe status indicators.
- Inputs: WeKnora FAQ/tag/favorite/skill routes/services/types, PA library/Wiki/
  history pages.
- Output report: workbench organization report.
- Editable files: adapter, backend BFF, frontend library/config/history pages,
  tests/reports, this spec rows.
- Forbidden: large custom taxonomy system if native tags/favorites exist;
  fixture-only organization samples as PASS.
- Acceptance: at least one organization feature works live through native API
  and appears in PA UX without breaking history/citation.
- Recommended validation: live API smoke and browser workflow.
- PASS evidence: live API/browser evidence.
- Blocked/backlog: mark `[!]` for missing native route/config; mark `[b]` for
  low-value admin polish beyond internal production.
- Status source: Section 6 row `WNX-P2-06`.

### WNX-P3-01: Six-page product workflow browser matrix

- Goal: prove PA's internal production UI is coherent across core pages.
- Scope: home, library, RAG debug, intelligent analysis, Wiki, history,
  capability/config center; desktop and mobile viewport checks.
- Inputs: all completed WNX reports, current frontend build, live backend.
- Output report: browser matrix report.
- Editable files: frontend polish only if validation finds issues, report, this
  spec rows.
- Forbidden: hiding blockers, fake demo data, disabling visible partial states,
  or accepting text overflow/overlap.
- Acceptance: every page loads real backend status, shows truthful capability
  state, has no incoherent overlap, and does not claim unverified PASS.
- Recommended validation: browser automation plus build/type check.
- PASS evidence: live browser evidence.
- Blocked/backlog: mark `[!]` for runtime/browser failures; mark `[b]` for
  optional pages outside internal production.
- Status source: Section 6 row `WNX-P3-01`.

### WNX-P3-02: Internal production report

- Goal: produce the final internal production acceptance report.
- Scope: coverage score, live API evidence, browser evidence, config/deployment
  readiness, history/citation coverage, risks, blockers, backlog, and next
  release path.
- Inputs: coverage ledger, all WNX reports, browser matrix, deployment runbook,
  report safety output.
- Output report: `docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_PASS_REPORT.md`.
- Editable files: final report, this spec rows, coverage ledger if evidence
  changes.
- Forbidden: using mock evidence, cached evidence, old reports, fixture-only
  evidence, static UI, or unverified inference as final PASS.
- Acceptance: report clearly separates live evidence, fixture evidence, mock
  evidence, cached evidence, partial evidence, blocked evidence, and backlog
  evidence; score is computed and justified.
- Recommended validation: report safety checker, coverage checker, `git diff
  --check`, sensitive scan.
- PASS evidence: current live reports and checker output.
- Blocked/backlog: mark `[!]` if coverage or required live validations are below
  internal production threshold.
- Status source: Section 6 row `WNX-P3-02`.

### WNX-P3-03: Deployment handoff prompt/runbook

- Goal: make the next conversation or operator able to continue safely.
- Scope: new-chat prompt, branch/status summary, service runbook, validation
  commands, known blockers/backlog, and how to read git log/spec/reports.
- Inputs: final report, deployment readiness report, this spec, coverage ledger.
- Output report: handoff prompt/runbook section or dedicated doc.
- Editable files: docs/runbook/handoff prompt, this spec rows.
- Forbidden: secrets, local-only raw logs, `.env` values, private endpoints,
  or broad claims not backed by reports.
- Acceptance: prompt tells a new Codex instance to trust `git log --oneline`,
  this spec, the coverage ledger, and pass reports; runbook can recover local
  internal production services.
- Recommended validation: `rg` for required pointers, sensitive scan, diff check.
- PASS evidence: documentation validation plus service/status evidence if the
  runbook includes commands.
- Blocked/backlog: mark `[!]` if required final reports are not available.
- Status source: Section 6 row `WNX-P3-03`.

## 9. Evidence Classification Rules

| Evidence type | Definition | Can count as capability PASS |
| --- | --- | --- |
| live evidence | Current real PA backend/frontend calling real WeKnora and real non-mock runtime where needed | Yes |
| fixture evidence | Sanitized test input processed through the live system | Only as supporting evidence |
| mock evidence | Mock backend/model/embedding/API, static sample, fake response, or UI-only demo | No |
| cached evidence | Old report, stale browser state, previous run output, old evidence id | No unless rerun live and labeled current |
| partial evidence | Real call proves only part of the user-facing contract | No final PASS; mark partial or blocked |
| blocked evidence | Real gap in API/config/runtime/safety prevents completion | No PASS; mark `[!]` |
| backlog evidence | Intentional deferral with reason and next step | No PASS; mark `[b]` |

`live evidence`, `fixture evidence`, `mock evidence`, and `cached evidence`
must be explicitly separated in every stage report.

## 10. Validation Commands For WNX-0-01

Run from `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench` unless noted.

```bash
git status -sb
git diff --check
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/.github/skills/pa-weknora-native-expansion
rg -n "BEGIN (RSA|OPENSSH|PRIVATE) KEY|[A-Za-z0-9_]*(API_KEY|SERVICE_TOKEN|PASSWORD|SECRET|AUTHORIZATION)[A-Za-z0-9_]*\\s*=" docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md .github/skills/pa-weknora-native-expansion/SKILL.md /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md
rg -n "WNX-P0-01|WNX-P3-02|80%|coverage ledger|internal production|live evidence|mock evidence" docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md
git status -sb
```

The sensitive scan command is expected to return no matches. It is acceptable
for docs to mention generic phrases such as API keys or service tokens as
rules, but not as assignments or real values.

## 11. Safety And Commit Rules

- Keep `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` untouched and unstaged.
- Use explicit staging paths for the current task only.
- Do not use broad staging such as `git add docs`.
- Do not push unless the user explicitly asks.
- Do not merge into `main`.
- Do not delete existing branches.
- When a task is code-bearing, validate before spec status updates.
- When validation cannot run, record `[!]` or `[b]`; do not mark `[x]` from
  inference.

## 12. Next Suggested Execution Order

1. `WNX-0-02`: architecture blueprint.
2. `WNX-0-03`: coverage ledger and scoring baseline.
3. `WNX-P0-01`: unified native client.
4. `WNX-P0-02`: backend config/status center.
5. `WNX-P0-03`: frontend capability/config center.
6. `WNX-P0-04`: live acceptance harness.
7. `WNX-P0-05`: internal deployment readiness.
8. `WNX-P1-*`: core user workflows, one workflow per run.
9. `WNX-P2-*`: native platform configuration, only after P0 is stable.
10. `WNX-P3-*`: browser matrix, final report, and handoff.
