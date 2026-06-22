# WeKnora-First 5-Day Sprint Spec

> Date: 2026-06-22
>
> Sprint branch: `weknora-first-mvp`
>
> Frozen baseline branch: `pa-native-baseline-20260622`
>
> Stable mainline: `main`

## 1. Stage Goal And Non-Goals

### Goal

Within five days, connect as many WeKnora native capabilities as possible into PA while preserving PA's product shell, history, citation/evidence quality, status surfaces, and professional workflow entry points.

The sprint principle is WeKnora-first:

- Use WeKnora native APIs/modules for general knowledge base, document ingestion, RAG retrieval, Wiki, AgentQA, custom Agent, MCP, web search, and vector-store capabilities.
- Let PA implement only the product adapter, UX, navigation, history, task records, citation mapping, reporting, and domain workflow packaging.
- Count a capability as PASS only after it works through real PA + real WeKnora + real non-mock model/embedding runtime.

### Non-Goals

- Do not deepen PA-native general RAG, general Wiki, or general Agent orchestration when WeKnora has a native path.
- Do not build mock-only features, static demo pages, fixture-only completion, or UI green states that hide fallback/partial status.
- Do not merge sprint work into `main` during the five-day sprint.
- Do not submit `.env`, API keys, service tokens, local databases, logs, uploads, caches, `node_modules`, `dist`, screenshots, raw chunks, raw prompts, or provider payloads.

## 2. Branch Strategy

| Branch | Purpose | Rule |
| --- | --- | --- |
| `pa-native-baseline-20260622` | Freeze current PA-native product version for later PA-native Agent design | Create from current baseline and push. Do not develop sprint work here. |
| `weknora-first-mvp` | Five-day WeKnora-first sprint branch | All stage 0 docs and sprint work land here. |
| `main` | Stable mainline | Do not make large WeKnora-first changes or merge sprint back during this stage. |

Current baseline commit for both new branches: `36ea9ca chore: add PA local service scripts`.

## 3. Stage 0 Review Conclusions

The review in `docs/PA_EXISTING_WORK_REVIEW_FOR_WEKNORA_FIRST.md` determines the sprint ordering:

- Preserve PA frontend experience, citation/evidence standards, task history, real-test reports, homepage runtime checks, local service scripts, and PA/WeKnora storage separation.
- Migrate or thin PA-owned general RAG/Wiki/Agent behavior toward WeKnora native APIs.
- Freeze PA-native professional Agent work, including deeper policy/case orchestration, for later product design after the WeKnora-first MVP.
- Treat `mock`, `extracted`, fixture-only, old-cache, and historical evidence as development aids only.

## 4. Sprint Task Board And Progress Protocol

This spec is the sprint source of truth. Future agents must use this section the same way previous phase specs used their task tables: read it first, choose one unfinished task, validate the task, then update the status only after the evidence is real enough for that status.

Status markers:

```text
[ ] Not started
[~] In progress or partial evidence exists
[x] Completed with the required evidence
[!] Blocked by real runtime/API/config gap
[b] Backlog/deferred by sprint scope
```

Task execution format:

```text
Read docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md
-> Read docs/PA_EXISTING_WORK_REVIEW_FOR_WEKNORA_FIRST.md
-> Read .github/skills/pa-weknora-first-sprint/SKILL.md
-> Read outer .agents/skills/pa-weknora-first-sprint/SKILL.md when available
-> Run git status -sb and git log --oneline -5
-> Locate one unfinished task id
-> Before editing, state task id, classification, planned files, validation, and PASS evidence type
-> Inspect WeKnora native source/API first for native capability tasks
-> Implement the smallest real slice
-> Run backend API validation and/or browser validation as required
-> Update this task board and progress log only after validation or a real blocked/backlog decision
-> Run safety checks
-> Commit only current-task files when a code/docs task is complete
```

Task selection rules:

1. Every sprint execution must be tied to exactly one `WF-*` id.
2. If the user names a `WF-*` id, execute that id.
3. If the user says "continue" or gives a broad request, choose the earliest unfinished P0 task.
4. Do not move to P1 while P0 has unfinished tasks unless the user explicitly reprioritizes.
5. Treat P2 as backlog unless P0/P1 are stable or the user explicitly scopes a P2 read-only/jump slice.
6. Treat P3 as future/post-sprint scope unless a `WF-P3-*` row and full task card are explicitly added.
7. Execute one task id per run; split oversized work instead of silently completing multiple slices.
8. Do not mark `[x]` from mock, fixture-only, cached, old report, hidden fallback, or inference-only evidence.
9. If live validation cannot run, mark `[!]` with cause and next step, or `[b]` if the task is consciously deferred.

### 4.1 Task Status Overview

| ID | Priority | Capability slice | Status | Required status evidence |
| --- | --- | --- | --- | --- |
| WF-0 | Stage 0 | Existing-work review, branches, sprint spec, sprint skill | [x] | Review/spec committed on `weknora-first-mvp`; skill validates in workspace. |
| WF-P0-01 | P0 | WeKnora native capability map | [x] | Source/routes inspected and gap table documented; no live PASS claimed. |
| WF-P0-02 | P0 | Knowledge base and document native path | [x] | Live PA document service uploaded to WeKnora, persisted native id, reached indexed, and read native chunks. |
| WF-P0-03 | P0 | RAG debug native alignment | [x] | Live PA RAG debug path called native WeKnora search and returned traceable evidence/rank/trace metadata. |
| WF-P0-04 | P0 | Truthful status and report gates | [x] | Live API/browser status surfaces expose real/native/mock/fallback/partial/blocked/backlog; report checker gates unsafe PASS evidence. |
| WF-P0-05 | P0 | Evidence/citation contract preservation | [x] | Native integrations preserve `source`, `source_type`, `evidence_id`, native ids, and locator fields. |
| WF-P1-01 | P1 | WeKnora native AgentQA/custom Agent | [x] | PA calls native AgentQA/custom Agent and stores answer/history with citation mapping or explicit citation blocker. |
| WF-P1-02 | P1 | Native Wiki browse/search/index/graph/lint | [x] | PA reads native Wiki browse/search/read/index/stats/graph/lint/issues with honest backlog labels for mutations. |
| WF-P1-03 | P1 | Knowledge base selection and mapping | [ ] | Active workspace/KB mapping is visible and validated through real config/API state. |
| WF-P1-04 | P1 | Frontend integration polish | [ ] | Browser validation covers the six PA pages and visible WeKnora-first states. |
| WF-P2-01 | P2 | MCP service visibility | [b] | Backlog unless a read-only status/jump slice is explicitly scoped. |
| WF-P2-02 | P2 | Web search provider visibility | [b] | Backlog unless AgentQA depends on visible provider readiness. |
| WF-P2-03 | P2 | Vector store management visibility | [b] | Backlog unless read-only readiness or native-admin jump is scoped. |
| WF-P2-04 | P2 | Advanced Wiki maintenance | [b] | Backlog until core Wiki browse/search/read is stable. |

### 4.2 Progress Log

| Date | Task id | Status | Evidence | Commit / branch | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-06-22 | WF-0 | [x] | Existing-work review and sprint spec added; `pa-native-baseline-20260622` and `weknora-first-mvp` created; skill frontmatter validated; diff and sensitive-value scans passed. | `bb3dc59` on `weknora-first-mvp` | Skill lives at outer workspace `.agents/skills/pa-weknora-first-sprint`; the nested PA repo does not own that path. |
| 2026-06-22 | WF-P0-01 | [x] | `audit/map`: WeKnora native routes/services/types and PA adapter/product surfaces inspected; `docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md` added; no live capability PASS claimed. | this commit on `weknora-first-mvp` | P0 follow-up order and exact file touch plan documented for `WF-P0-02` through `WF-P0-05`; P2 MCP/web search/vector store admin remains backlog by default. |
| 2026-06-22 | WF-P0-02 | [x] | `live`: PA document service uploaded a sanitized file to WeKnora, persisted `external_doc_id=e3fa4420-c083-4a2d-b47e-a3c540e6f3fb`, reached `indexed`, and read 1 native chunk; fixture smoke proves PA-local parser/chunker/vector path is avoided for WeKnora docs. | this commit on `weknora-first-mvp` | Report: `docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md`; evidence is not fixture-only and does not print keys, provider payloads, or raw document body. |
| 2026-06-22 | WF-P0-03 | [x] | `live`: PA RAG debug retrieved WeKnora evidence for `external_doc_id=257afb30-83f8-4f32-ba4e-a216d319a7fd` with `source=weknora_api`, `source_type=document_chunk`, `evidence_id=document_chunk:7caecfe8-619e-44e2-930d-814fb3e29fb7`, rank/native rank, and trace stages. | this commit on `weknora-first-mvp` | Report: `docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md`; fixture smokes only guard redaction/validation and are not the PASS evidence. |
| 2026-06-22 | WF-P0-04 | [x] | `live API/browser`: temporary current-worktree backend exposed `weknora_first_status_gates`; homepage showed live/mock/partial/blocked/backlog and fixture-only PASS rejection; checker self-test and report scan passed. | this commit on `weknora-first-mvp` | Report: `docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md`; port 8000 service config was not modified, and validation used temporary localhost ports 8017/5177. |
| 2026-06-22 | WF-P0-05 | [x] | `audit/map + focused smoke`: `docs/WEKNORA_FIRST_CITATION_CONTRACT.md` defines required fields, per-source mapping, metadata allowlist, fail-closed behavior, locator expectations, and blocked/backlog rules; citation smoke preserved document/Wiki evidence ids, persisted 2 citations, located 2 citations, and passed 3 fail-closed checks. | this commit on `weknora-first-mvp` | No live path or frontend rendering code changed; prior P0 live reports remain supporting context, and fixture smoke is not counted as standalone live capability PASS. |
| 2026-06-22 | WF-P1-01 | [x] | `live API + explicit citation blocker`: PA adapter called native `/api/v1/agent-chat/{session_id}` with `builtin-wiki-researcher`, stored a completed PA output, saw event types `agent_query,answer,complete,tool_call,tool_result`, and recorded `native_reference_count=0`, `saved_citations=0`, `CITATION_BLOCKED`. | this commit on `weknora-first-mvp` | Report: `docs/WEKNORA_FIRST_AGENTQA_LIVE_REPORT.md`; answer/history adapter slice is PASS, while citation mapping is blocked because native AgentQA emitted no traceable `references` event. |
| 2026-06-22 | WF-P1-02 | [x] | `live PA API + live native Wiki`: PA `/api/wiki/native/overview` called WeKnora native Wiki pages/search/read/index/stats/graph/lint/issues; live counts were pages `5/355`, search `5`, index `5/15`, stats total pages `355`, graph nodes `5`, lint issues `2261`, issue list `0`, and read traceability was true. | this commit on `weknora-first-mvp` | Report: `docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md`; native Wiki mutations such as rebuild-links, auto-fix, and issue status updates remain explicit backlog. |

### 4.3 Status Update Rules

- Update `Status` in the task board and add a progress-log row when a task reaches `[x]`, `[!]`, or `[b]`.
- Use `[~]` only for a committed partial slice that is useful but not enough for final PASS.
- A native capability task can be `[x]` only with live PA + live WeKnora evidence, unless the task is explicitly an audit/map task whose acceptance criteria says no live PASS is claimed.
- A frontend task can be `[x]` only after browser validation or a documented browser-validation blocker.
- A backend task can be `[x]` only after API/smoke validation or a documented runtime blocker.
- Keep validation reports honest: separate live, fixture, mock, cached, partial, blocked, and backlog evidence.
- Keep unrelated dirty/untracked files out of the task commit.

### 4.4 Repo-Local Skill Mirror

The reusable sprint skill also has a tracked mirror at
`.github/skills/pa-weknora-first-sprint/SKILL.md`. This mirror exists because
the outer workspace skill path is outside the nested `pa-ai-workbench` git repo
and cannot be proven by a repo-local commit.

Execution rule:

- Read the repo-local mirror for every new sprint conversation.
- Read the outer `.agents` skill when it exists in the active workspace.
- If the two diverge, obey the stricter rule and update the repo-local mirror
  in the same governance task when the divergence affects sprint execution.
- Do not stage the outer `.agents` path from the nested PA repo; it is not owned
  by this git repository.

## 5. P0/P1/P2 Capability Priority

### P0

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P0-01 | WeKnora native capability map | Confirm native endpoints/modules for knowledge upload/status/chunks/search, Wiki, AgentQA, custom Agent, MCP, web search, and vector store. |
| WF-P0-02 | Knowledge base and document native path | PA upload/status/library views rely on WeKnora native ingestion/indexing as the source of truth. |
| WF-P0-03 | RAG debug native alignment | PA RAG debug becomes a thin WeKnora-first adapter while retaining citation/evidence display and current-run validation. |
| WF-P0-04 | Truthful status and report gates | Homepage/backend status exposes native capability readiness without hiding fallback, partial, blocked, or mock states. |
| WF-P0-05 | Evidence/citation contract preservation | Every native integration maps to PA `source`, `source_type`, `evidence_id`, locator, and history fields. |

#### WF-P0-01: WeKnora native capability map

目标：
确认 WeKnora native endpoints/modules for knowledge upload/status/chunks/search, Wiki, AgentQA, custom Agent, MCP, web search, and vector store, then map which PA product surfaces should consume them.

范围：
只做 source/API audit and PA gap mapping. This task does not implement backend/frontend behavior and does not claim live capability PASS.

输入：
`docs/PA_EXISTING_WORK_REVIEW_FOR_WEKNORA_FIRST.md`, current sprint spec, WeKnora router/handler/service/type files listed in the sprint skill, and PA adapter/product files such as `knowledge_engine/backends/weknora_api_backend.py`, `backend/app/api/*`, `backend/app/services/*`, and `frontend/src/pages/*`.

输出产物/报告文件：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`.

可修改文件范围：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`, `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md` status/progress rows after validation, and small report-safety/checker docs if needed.

不可修改或不可做的事：
Do not change product code, runtime config, `.env`, API keys, local databases, uploads, logs, caches, or WeKnora source. Do not mark native features complete from route existence alone.

验收标准：
The report lists each native area, source files/routes inspected, observed endpoint/module shape, PA owner surface, adapter gap, validation recommendation, and blocked/backlog decision. It explicitly says audit/map evidence is not live capability PASS. The final section must be named `P0 execution order and exact file touch plan`, and it must give the recommended order for `WF-P0-02` through `WF-P0-05` plus the likely files or directories each task may touch.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md
rg -n "knowledge|wiki|AgentQA|custom Agent|MCP|web search|vector store|blocked|backlog|not live PASS" docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md
rg -n "P0 execution order and exact file touch plan|WF-P0-02|WF-P0-05" docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md
git diff --check
```

PASS 证据要求：
Source inspection evidence, a complete gap table, and the final P0 execution/file-touch plan are enough for this audit PASS; no live runtime PASS is claimed. The progress row must label evidence as `audit/map`, not `live`.

blocked/backlog 判定：
Mark `[!]` if key source files or route definitions cannot be inspected. Mark `[b]` for native areas intentionally deferred beyond the five-day P0 slice, with concrete next steps.

状态字段：
Status source is Section 4.1 row `WF-P0-01`; keep this card's final state aligned with that row.

#### WF-P0-02: Knowledge base and document native path

目标：
Make PA library/upload/status behavior rely on WeKnora native ingestion/indexing as the source of truth while preserving PA business records and product status display.

范围：
One smallest live document path: upload or register a sanitized file through PA, obtain native WeKnora identifiers/status, refresh status/events/chunks where available, and record truthful blocker if indexing cannot complete.

输入：
Native capability map from `WF-P0-01`, PA document API/service/schema files, `knowledge_engine/backends/weknora_api_backend.py`, frontend library page code if the visible state changes, and a sanitized fixture input used only through the live system.

输出产物/报告文件：
`docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md`.

可修改文件范围：
PA document/library backend adapter files, PA document schemas/tests/smokes, affected frontend library/status files, the report file, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not commit uploaded files, raw document bodies, local databases, logs, caches, screenshots, `.env`, provider payloads, or private endpoint values. Do not deepen PA-native parser/chunker/vector-store logic when WeKnora native ingestion is available. Do not substitute `mock` or `extracted` backend evidence for PASS.

验收标准：
A current live run proves PA -> WeKnora native upload/status/index path or records a real blocked state. The report includes native ids such as `external_doc_id` or equivalent, status transitions, evidence type labels, and whether chunk/status preview is live, partial, blocked, or backlog.

推荐验证命令/API/browser check：

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_connection.py
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_m1.py
curl -s http://127.0.0.1:8000/api/status
curl -s http://127.0.0.1:8000/api/model/status
```

Browser check: library page upload/status/chunk preview if frontend changes are included.

PASS 证据要求：
PASS requires current live PA backend/frontend or PA API calling real WeKnora native ingestion/indexing, with non-mock embedding when indexing depends on embedding. Report must distinguish live input fixture from fixture-only proof and include traceable native ids without raw content.

blocked/backlog 判定：
Mark `[!]` if WeKnora, model, embedding, KB binding, upload API, status API, or indexing runtime is unavailable. Mark `[b]` only for optional chunk preview/admin UX that is consciously deferred after the core live document path is decided.

状态字段：
Status source is Section 4.1 row `WF-P0-02`; update it only after live validation or a real blocked/backlog decision.

#### WF-P0-03: RAG debug native alignment

目标：
Keep PA RAG debug as a thin WeKnora-first adapter around native search while preserving PA current-run validation, diagnostics, citation/evidence display, and safety labels.

范围：
Align one real RAG debug path with native WeKnora search semantics, including query/top_k/source_type/filter handling where supported, and fail closed when native evidence cannot satisfy the PA citation contract.

输入：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`, `docs/WEKNORA_FIRST_DOCUMENT_RAG_LIVE_REPORT.md` if available, PA RAG API/service/retriever files, `knowledge_engine/*`, existing Phase 5 real RAG scripts/reports, and native WeKnora search route/service/type files.

输出产物/报告文件：
`docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md`.

可修改文件范围：
PA RAG debug backend/API/service files, adapter normalization code, focused tests/smokes, affected RAG debug frontend files, the live report, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not rewrite WeKnora retrieval, build a parallel PA general retrieval engine, hide unsupported native parameters, use historical Phase 5 reports as current PASS, or mark PASS from mock/static UI.

验收标准：
At least one current PA RAG debug run calls native WeKnora search and returns PA-normalized evidence with `source=weknora_api`, `source_type`, `evidence_id`, native ids where available, score/rank/trace metadata, and visible warnings for unsupported or partial fields.

推荐验证命令/API/browser check：

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_connection.py
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_m1.py
test -f docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md
rg -n "source=weknora_api|source_type|evidence_id|trace|rank|live|mock|blocked|partial" docs/WEKNORA_FIRST_RAG_DEBUG_LIVE_REPORT.md
```

Browser check: RAG debug page evidence list, trace/warning panel, and source status if frontend changes are included.

PASS 证据要求：
PASS requires current live PA API or browser evidence calling real WeKnora native search, with real non-mock model/embedding posture when the path depends on it. The report must identify current-run evidence and reject cached/old evidence ids.

blocked/backlog 判定：
Mark `[!]` if native search, KB mapping, current-run scope, embedding, or citation fields are unavailable. Mark `[b]` for advanced search controls that are not required for the smallest live RAG debug path.

状态字段：
Status source is Section 4.1 row `WF-P0-03`; update it only after live validation or a real blocked/backlog decision.

#### WF-P0-04: Truthful status and report gates

目标：
Make backend/homepage/report status surfaces expose real/native/mock/fallback/partial/blocked/backlog states truthfully and prevent report PASS from unsafe evidence.

范围：
Extend status and report gate logic for WeKnora-first P0 evidence. Cover `/health`, `/api/status`, `/api/model/status`, capability readiness, frontend visible cards, and report safety checks as needed.

输入：
Current status endpoints/services, frontend homepage/status components, existing report safety scripts, Phase 5 report safety rules, and P0 report files created by earlier tasks.

输出产物/报告文件：
`docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md`.

可修改文件范围：
Backend status endpoints/services/schemas, report safety checker scripts, homepage/status frontend components, focused tests/smokes, the gate report, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not make UI cards green by hiding fallback/mock/partial states. Do not merge model readiness and embedding readiness into one ambiguous field. Do not print or commit secrets, provider payloads, logs, local DB contents, screenshots, or raw uploaded material.

验收标准：
Status surfaces separately show PA backend health, WeKnora connectivity, chat model readiness, embedding/index readiness, native capability availability, and blocked/backlog labels. Report gates fail or warn on mock, fixture-only, cached, partial, unsafe, or missing citation evidence.

推荐验证命令/API/browser check：

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/status
curl -s http://127.0.0.1:8000/api/model/status
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_STATUS_REPORT_GATES.md
```

Browser check: homepage/status cards and any affected report/status page must visibly distinguish real, mock, fallback, partial, blocked, and backlog states.

PASS 证据要求：
PASS requires current API and browser evidence if frontend changes are present. The report must show the exact evidence categories observed without raw private values.

blocked/backlog 判定：
Mark `[!]` if status endpoints cannot run, if the runtime cannot distinguish model versus embedding readiness, or if report gates cannot detect unsafe evidence. Mark `[b]` for nonessential visual polish after truthful status is present.

状态字段：
Status source is Section 4.1 row `WF-P0-04`; update it only after API/browser validation or a real blocked/backlog decision.

#### WF-P0-05: Evidence/citation contract preservation

目标：
Preserve PA's citation/evidence contract across WeKnora-first native integrations so downstream history, reports, and frontend locators remain trustworthy.

范围：
Define and validate the minimum cross-capability contract for document chunks, wiki pages, AgentQA/custom Agent outputs, and future native surfaces. Implement only the smallest code/test/report changes needed to keep P0 integrations fail-closed.

输入：
Existing evidence/citation schemas/builders/checkers, PA history/output models, native response mappings from `WF-P0-01` through `WF-P0-04`, and existing Phase 5 evidence reports.

输出产物/报告文件：
`docs/WEKNORA_FIRST_CITATION_CONTRACT.md`.

可修改文件范围：
Citation/evidence schemas, builder/checker code, adapter normalization tests, report safety checks, affected frontend citation rendering if necessary, the contract report, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not invent fake `evidence_id`, `chunk_id`, `external_doc_id`, or `wiki_page_id` values. Do not broaden metadata allowlists to include secrets, raw content, prompts, provider payloads, logs, private endpoints, or local file paths. Do not let missing native ids silently degrade to PASS.

验收标准：
The contract document defines required/optional fields, per-source mapping rules, metadata allowlist, fail-closed behavior, and report/browser expectations. Focused validation proves native evidence retains `source`, `source_type`, `evidence_id`, native ids where applicable, locator fields, and history traceability.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_CITATION_CONTRACT.md
rg -n "source_type|evidence_id|chunk_id|external_doc_id|wiki_page_id|locator|fail closed|allowlist" docs/WEKNORA_FIRST_CITATION_CONTRACT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_CITATION_CONTRACT.md
```

Browser check: citation/evidence rendering on RAG debug, Wiki, knowledge QA, and history pages if frontend citation UI changes are included.

PASS 证据要求：
PASS requires contract validation from current focused tests/smokes and, when code changes touch live paths, a current live PA + WeKnora evidence sample. Report must label partial native citation support as partial/blocked, not PASS.

blocked/backlog 判定：
Mark `[!]` if a native response lacks the identifiers required to preserve traceability and no safe mapping exists. Mark `[b]` for source types whose native integration is intentionally deferred to P1/P2.

状态字段：
Status source is Section 4.1 row `WF-P0-05`; update it only after validation or a real blocked/backlog decision.

### P1

P1 tasks use the same executable card shape as P0. They should preserve PA product shell value while consuming WeKnora native Wiki, AgentQA/custom Agent, workspace/KB, and frontend status surfaces where live evidence exists.

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P1-01 | WeKnora native AgentQA/custom Agent | Add PA adapter entry for native AgentQA and store returned answer/citations/history through PA. |
| WF-P1-02 | Native Wiki browse/search/index/graph/lint | Let PA show or link to WeKnora native Wiki capabilities while preserving PA navigation. |
| WF-P1-03 | Knowledge base selection and mapping | Make active workspace/KB selection more visible and less dependent on hidden config assumptions. |
| WF-P1-04 | Frontend integration polish | Update pages to show WeKnora-first state, blocked/backlog labels, and native jump targets. |

#### WF-P1-01: WeKnora native AgentQA/custom Agent

目标：
Add the smallest PA adapter entry for native WeKnora AgentQA/custom Agent while preserving PA output/history and citation fail-closed behavior.

范围：
Call native WeKnora AgentQA through `POST /api/v1/agent-chat/{session_id}` after creating a native session, parse SSE answer/reference events, store the answer through PA output/history, and save citations only when native references are traceable. This task does not add frontend AgentQA UI or claim citation PASS when native references are absent.

输入：
Native WeKnora session/custom Agent/AgentQA router, handler, service, and stream types; PA `WeKnoraApiBackend`; PA output/history services; citation builder/checker contract from `WF-P0-05`.

输出产物/报告文件：
`docs/WEKNORA_FIRST_AGENTQA_LIVE_REPORT.md`.

可修改文件范围：
`knowledge_engine/backends/weknora_api_backend.py`, focused native AgentQA smoke script, the AgentQA live report, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not invent fake `source_type`, `evidence_id`, `chunk_id`, `external_doc_id`, or `wiki_page_id` values. Do not treat missing native references as citation PASS. Do not broaden this slice into frontend integration, Agent configuration UI, MCP, web search, or vector-store admin work.

验收标准：
Focused validation calls live native AgentQA/custom Agent, receives a non-empty live answer stream, stores a completed PA output/history record, and either saves traceable citations or records an explicit citation blocker.

推荐验证命令/API/browser check：

```bash
backend/.venv/bin/python -m py_compile knowledge_engine/backends/weknora_api_backend.py backend/scripts/smoke_weknora_agentqa_native_live.py
backend/.venv/bin/python backend/scripts/smoke_weknora_agentqa_native_live.py
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_AGENTQA_LIVE_REPORT.md
rg -n "AgentQA|agent-chat|CITATION_BLOCKED|source_type|evidence_id|live|mock|blocked|backlog" docs/WEKNORA_FIRST_AGENTQA_LIVE_REPORT.md
```

Browser check: not required for this slice because no frontend files changed.

PASS 证据要求：
PASS requires current live PA + WeKnora AgentQA evidence for the adapter/history slice. Citation mapping can count only when native references include traceable fields; otherwise the report must mark citation mapping as blocked.

blocked/backlog 判定：
Mark citation mapping blocked if native AgentQA emits no `references` event or lacks required citation identifiers. Keep frontend AgentQA integration and richer custom Agent selection as backlog unless selected as a later `WF-*` task.

状态字段：
Status source is Section 4.1 row `WF-P1-01`; update it only after validation or a real blocked/backlog decision.

#### WF-P1-02: Native Wiki browse/search/index/graph/lint

目标：
Expose WeKnora native Wiki browse/search/read/index surfaces through PA or clear native jump links while preserving PA Wiki navigation, citation traceability, and blocked/backlog labels.

范围：
Start with read-only native Wiki list/search/read/index status. Add graph/stats/lint/issues only as read-only status or native-admin jump if the core browse/search/read path is stable. Mutation actions such as auto-fix, rebuild-links, issue status updates, or broad Wiki admin workflows stay out of this task unless explicitly rescoped.

输入：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`, `docs/WEKNORA_FIRST_CITATION_CONTRACT.md`, WeKnora Wiki route/handler/service/type files, PA `WeKnoraApiBackend`, `backend/app/api/wiki.py`, `backend/app/services/wiki_service.py`, `frontend/src/pages/WikiPage.tsx`, and History/citation locator behavior when native Wiki ids are displayed.

输出产物/报告文件：
`docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md`.

可修改文件范围：
`knowledge_engine/backends/weknora_api_backend.py`, `backend/app/api/wiki.py`, `backend/app/services/wiki_service.py`, relevant schemas/tests/smokes, `frontend/src/pages/WikiPage.tsx`, optional History citation locator rendering if required, the report file, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not rebuild WeKnora Wiki admin in PA. Do not implement graph/lint/auto-fix engines in PA. Do not mutate native Wiki pages/issues unless explicitly scoped. Do not mark read-only jump links as live browse/search PASS. Do not invent `wiki_page_id`, `source_refs`, or citation locators.

验收标准：
PA can read or link native Wiki pages/search/index with visible native ids/status, and any unsupported graph/lint/issues capability is labeled partial, blocked, backlog, or jump. Citation fields remain traceable for native Wiki pages.

推荐验证命令/API/browser check：

```bash
backend/.venv/bin/python -m py_compile knowledge_engine/backends/weknora_api_backend.py backend/app/api/wiki.py backend/app/services/wiki_service.py
test -f docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md
rg -n "wiki|wiki_page_id|search|index|graph|lint|live|partial|blocked|backlog|jump" docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md
```

Browser check: Wiki page read/search/index/jump/status states if frontend files change.

PASS 证据要求：
PASS requires current live PA API or browser evidence calling real WeKnora native Wiki surfaces, or an explicit read-only native jump plus blocked/backlog labels for surfaces not implemented. Fixture-only Wiki examples and old Phase 5 Wiki reports do not count as current PASS.

blocked/backlog 判定：
Mark `[!]` if native Wiki endpoints, KB mapping, auth, or citation identifiers are unavailable. Mark `[b]` for graph/lint/auto-fix/admin mutations that are consciously deferred after core browse/search/read is decided.

状态字段：
Status source is Section 4.1 row `WF-P1-02`; update it only after validation or a real blocked/backlog decision.

#### WF-P1-03: Knowledge base selection and mapping

目标：
Make active workspace/knowledge-base selection visible, testable, and consistent across PA Library, RAG debug, Wiki, AgentQA, status, and reports.

范围：
Expose the current workspace/KB mapping from safe config/API state, validate the active KB against WeKnora where feasible, and make page-level behavior honest when a user-facing task depends on a different or unavailable KB. This task does not build a broad KB admin UI.

输入：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`, existing PA settings and runtime status services, `knowledge_engine/factory.py`, `knowledge_engine/backends/weknora_api_backend.py`, backend status/document/rag/wiki/analysis APIs, and frontend pages that display source/KB context.

输出产物/报告文件：
`docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md`.

可修改文件范围：
PA settings/schema/status services, backend document/rag/wiki/analysis request/response schemas where KB mapping must be surfaced, `frontend/src/pages/HomePage.tsx`, `LibraryPage.tsx`, `RagDebugPage.tsx`, `WikiPage.tsx`, `AnalysisPage.tsx`, focused tests/smokes, the report file, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not print `.env` values, tokens, private endpoints, or raw provider payloads. Do not store secrets in reports. Do not add credential-management UI. Do not silently fall back to a hidden default KB when the selected or configured KB is unavailable.

验收标准：
PA surfaces the active workspace/KB source clearly enough that document upload, RAG debug, Wiki, AgentQA, and status reports can say which KB was used or why the mapping is blocked/backlog. Runtime checks distinguish missing config, unreachable WeKnora, invalid KB, and partial capability readiness.

推荐验证命令/API/browser check：

```bash
curl -s http://127.0.0.1:8000/api/status
curl -s http://127.0.0.1:8000/api/model/status
test -f docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md
rg -n "workspace|knowledge base|KB|mapping|configured|validated|blocked|backlog|partial" docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md
```

Browser check: affected pages must show the selected or active KB context if frontend files change.

PASS 证据要求：
PASS requires current API/status or browser evidence proving the active mapping is visible and validated, or an explicit blocked state if validation cannot run. The report must show variable names and sanitized ids only; never secret values.

blocked/backlog 判定：
Mark `[!]` if active workspace/KB cannot be determined safely, if WeKnora cannot validate it, or if page behavior depends on ambiguous hidden defaults. Mark `[b]` for multi-KB management, KB CRUD, or native admin replacement.

状态字段：
Status source is Section 4.1 row `WF-P1-03`; update it only after validation or a real blocked/backlog decision.

#### WF-P1-04: Frontend integration polish

目标：
Make the six PA product pages present the WeKnora-first state coherently, including native live paths, explicit citation blockers, partial surfaces, blocked/backlog labels, and safe native jump targets.

范围：
Frontend integration only unless a tiny backend response field is required for truthful display. Cover 首页、资料库、RAG 调试、Wiki、知识问答、历史. Preserve dense product workflow ergonomics and avoid turning PA into a WeKnora admin clone.

输入：
P0 and P1 reports, status endpoints, frontend page components, API client types, and existing Phase 5 browser acceptance assets.

输出产物/报告文件：
`docs/WEKNORA_FIRST_FRONTEND_BROWSER_ACCEPTANCE_REPORT.md`.

可修改文件范围：
`frontend/src/pages/HomePage.tsx`, `LibraryPage.tsx`, `RagDebugPage.tsx`, `WikiPage.tsx`, `AnalysisPage.tsx`, `HistoryPage.tsx`, shared frontend API/types/components if needed, minimal backend schema/status fields only if required, the browser acceptance report, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not hide mock/fallback/partial/blocked states to make cards look healthy. Do not add marketing/landing-page content. Do not commit screenshots, browser cache, `frontend/dist`, `node_modules`, or local runtime artifacts. Do not introduce unrelated redesigns.

验收标准：
Browser validation covers the six pages, with no broken primary workflows, no incoherent overlap, and visible labels for live/native/mock/fallback/partial/blocked/backlog states. Citation and AgentQA blockers remain visible rather than hidden.

推荐验证命令/API/browser check：

```bash
cd frontend
npm run build
```

If `npm` is unavailable, use existing local frontend binaries under `frontend/node_modules/.bin/`.

Browser check: 首页、资料库、RAG 调试、Wiki、知识问答、历史 against the running local app.

Report checks:

```bash
test -f docs/WEKNORA_FIRST_FRONTEND_BROWSER_ACCEPTANCE_REPORT.md
rg -n "首页|资料库|RAG|Wiki|知识问答|历史|live|mock|fallback|partial|blocked|backlog" docs/WEKNORA_FIRST_FRONTEND_BROWSER_ACCEPTANCE_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_FRONTEND_BROWSER_ACCEPTANCE_REPORT.md
```

PASS 证据要求：
PASS requires current browser evidence for all six pages and a build/type check when feasible. Static UI review, old screenshots, or cached browser state cannot complete this task.

blocked/backlog 判定：
Mark `[!]` if the local app cannot run, build/type check fails, or browser validation cannot reach affected pages. Mark `[b]` for nonessential visual polish after truthfulness and primary workflows pass.

状态字段：
Status source is Section 4.1 row `WF-P1-04`; update it only after browser validation or a real blocked/backlog decision.

### P2

P2 remains backlog by default, but each P2 item still has an executable task card so future work can start with a safe read-only or native-admin jump slice instead of broad admin rebuilds.

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P2-01 | MCP service visibility | Surface native MCP services/tools/approval state or link to WeKnora admin. |
| WF-P2-02 | Web search provider visibility | Surface native web-search provider readiness if AgentQA depends on it. |
| WF-P2-03 | Vector store management visibility | Show vector-store binding/readiness, or link to WeKnora native admin rather than rebuilding admin UI. |
| WF-P2-04 | Advanced Wiki maintenance | Auto-fix, issue management, graph filtering, and lint workflows after core browse/search/read is stable. |

#### WF-P2-01: MCP service visibility

目标：
Surface WeKnora native MCP service/tool/resource/approval readiness in PA as read-only status or native-admin jump links without copying credential management into PA.

范围：
Read-only native MCP visibility only: list service readiness, tools/resources availability, approval status, and safe jump targets. Credential CRUD, tool execution, approval mutation, and secret handling are out of scope unless explicitly accepted as a separate secure task.

输入：
`docs/WEKNORA_FIRST_NATIVE_CAPABILITY_MAP.md`, WeKnora MCP route/handler/service/DTO files, PA status/capability services, frontend status surfaces, and citation/report safety rules.

输出产物/报告文件：
`docs/WEKNORA_FIRST_MCP_VISIBILITY_REPORT.md`.

可修改文件范围：
Backend capability/status adapters, safe schemas that omit secrets, homepage/status/frontend jump surfaces, focused read-only smoke/report files, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not expose, print, store, or commit MCP credentials, tokens, headers, private endpoints, provider payloads, or approval secrets. Do not implement MCP service CRUD, tool execution, or credential forms in PA during this task.

验收标准：
PA shows read-only MCP readiness or a clearly labeled native jump/backlog state. Any native response included in reports is sanitized and contains no secret values. Unsupported MCP mutation/execution remains blocked/backlog.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_MCP_VISIBILITY_REPORT.md
rg -n "MCP|service|tool|resource|approval|read-only|jump|blocked|backlog|secret" docs/WEKNORA_FIRST_MCP_VISIBILITY_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_MCP_VISIBILITY_REPORT.md
```

API/browser check: use a focused PA API/status smoke or browser status card only if this backlog task is explicitly activated.

PASS 证据要求：
PASS requires current read-only PA API/browser evidence or a deliberate `[b]` backlog decision. No credential-bearing response can count as PASS.

blocked/backlog 判定：
Keep `[b]` by default unless the user scopes this slice. Mark `[!]` if native read-only MCP endpoints are unavailable or unsafe to display without leaking secrets.

状态字段：
Status source is Section 4.1 row `WF-P2-01`; update it only after validation or a real blocked/backlog decision.

#### WF-P2-02: Web search provider visibility

目标：
Expose WeKnora native web-search provider readiness only where it helps AgentQA/status truthfulness, without duplicating provider credential configuration in PA.

范围：
Read-only provider catalog/status or native-admin jump. Do not implement provider CRUD, secret forms, raw search debugging, or independent PA web-search orchestration unless a later task explicitly scopes it.

输入：
WeKnora web-search provider routes/services/types, AgentQA live report blocker context, PA status/capability services, frontend status surfaces, and report safety rules.

输出产物/报告文件：
`docs/WEKNORA_FIRST_WEB_SEARCH_VISIBILITY_REPORT.md`.

可修改文件范围：
Backend status/capability adapters, safe schemas that omit credentials, homepage/AgentQA readiness surfaces, focused read-only smoke/report files, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not expose provider API keys, endpoints with secrets, raw provider payloads, or credential forms. Do not make web search appear required for AgentQA unless live validation proves that dependency.

验收标准：
PA can label native web-search readiness, unavailable state, or native jump target truthfully. AgentQA-related status must say whether web search is required, optional, unavailable, or backlog.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_WEB_SEARCH_VISIBILITY_REPORT.md
rg -n "web search|provider|readiness|AgentQA|required|optional|jump|blocked|backlog" docs/WEKNORA_FIRST_WEB_SEARCH_VISIBILITY_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_WEB_SEARCH_VISIBILITY_REPORT.md
```

API/browser check: use focused PA status/API or browser status only when this backlog slice is explicitly activated.

PASS 证据要求：
PASS requires current read-only PA API/browser evidence or a deliberate `[b]` backlog decision. Provider credentials and raw payloads must be absent from reports and commits.

blocked/backlog 判定：
Keep `[b]` by default unless AgentQA or user scope requires visibility. Mark `[!]` if provider readiness cannot be queried safely or if native API shape is unavailable.

状态字段：
Status source is Section 4.1 row `WF-P2-02`; update it only after validation or a real blocked/backlog decision.

#### WF-P2-03: Vector store management visibility

目标：
Show WeKnora native vector-store readiness/binding status or a native-admin jump while preserving the PA/WeKnora storage boundary.

范围：
Read-only vector-store type/list/health readiness and KB binding context. Do not build vector-store CRUD, connection testing with raw secrets, or PA-native vector administration.

输入：
WeKnora vector-store routes/services/types, `docs/WEKNORA_FIRST_KB_SELECTION_MAPPING_REPORT.md` if available, PA status/model/embedding readiness services, and frontend status surfaces.

输出产物/报告文件：
`docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md`.

可修改文件范围：
Backend status/capability adapters, safe vector-store readiness schemas, homepage/status/KB readiness UI, focused read-only smoke/report files, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not expose connection strings, database credentials, provider tokens, raw health-check payloads, local DB contents, or vector records. Do not confuse PA SQLite business state with WeKnora authoritative vector/chunk storage.

验收标准：
PA status/report can distinguish embedding readiness, WeKnora vector-store readiness, KB binding readiness, unavailable vector store, and backlog/admin-jump state without leaking secrets.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md
rg -n "vector store|embedding|KB|binding|readiness|env|user|shared|unavailable|jump|blocked|backlog" docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_VECTOR_STORE_VISIBILITY_REPORT.md
```

API/browser check: use focused PA status/API or browser status only when this backlog slice is explicitly activated.

PASS 证据要求：
PASS requires current read-only PA API/browser evidence or a deliberate `[b]` backlog decision. Sanitized readiness/state is acceptable; raw connection data is not.

blocked/backlog 判定：
Keep `[b]` by default unless user scope activates this slice. Mark `[!]` if native vector-store readiness cannot be queried safely or if response masking is insufficient.

状态字段：
Status source is Section 4.1 row `WF-P2-03`; update it only after validation or a real blocked/backlog decision.

#### WF-P2-04: Advanced Wiki maintenance

目标：
Plan or expose WeKnora native Wiki maintenance capabilities such as lint, issues, graph filtering, auto-fix, and link rebuild without moving broad maintenance engines into PA.

范围：
Default slice is read-only lint/issues/graph status or native-admin jump. Auto-fix, rebuild-links, issue mutation, and maintenance scheduling require a separate explicit task and stronger safety review.

输入：
`docs/WEKNORA_FIRST_WIKI_NATIVE_BROWSE_REPORT.md` if available, WeKnora Wiki lint/issues/graph routes/services/types, PA Wiki/status frontend, and report safety rules.

输出产物/报告文件：
`docs/WEKNORA_FIRST_WIKI_MAINTENANCE_BACKLOG_REPORT.md`.

可修改文件范围：
Read-only Wiki status adapters, frontend Wiki maintenance status/jump surfaces, focused read-only smoke/report files, and sprint spec status/progress rows after validation.

不可修改或不可做的事：
Do not run auto-fix, rebuild-links, issue status mutation, or mass Wiki maintenance from PA unless explicitly rescoped. Do not create a PA-native graph/lint engine. Do not commit raw Wiki content or screenshots.

验收标准：
PA either exposes read-only maintenance readiness/jump status or records a clear backlog decision. Users can tell which advanced Wiki maintenance actions are native-owned, blocked, or deferred.

推荐验证命令/API/browser check：

```bash
test -f docs/WEKNORA_FIRST_WIKI_MAINTENANCE_BACKLOG_REPORT.md
rg -n "Wiki|lint|issues|graph|auto-fix|rebuild-links|read-only|jump|blocked|backlog" docs/WEKNORA_FIRST_WIKI_MAINTENANCE_BACKLOG_REPORT.md
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py docs/WEKNORA_FIRST_WIKI_MAINTENANCE_BACKLOG_REPORT.md
```

Browser check: Wiki page maintenance status/jump only when this backlog slice is explicitly activated.

PASS 证据要求：
PASS requires current read-only PA API/browser evidence or a deliberate `[b]` backlog decision. Mutation actions require separate evidence and cannot be inferred from route existence.

blocked/backlog 判定：
Keep `[b]` until core Wiki browse/search/read is stable and the user explicitly scopes maintenance. Mark `[!]` if read-only maintenance routes are unavailable or unsafe to surface.

状态字段：
Status source is Section 4.1 row `WF-P2-04`; update it only after validation or a real blocked/backlog decision.

### P3

This sprint currently has no `WF-P3-*` rows in Section 4.1. Do not invent P3 implementation work during the five-day sprint. If future post-sprint work needs P3, first add explicit `WF-P3-*` rows to the task board and create a full task card with the same fields used by P0/P1/P2:

- 目标
- 范围
- 输入
- 输出产物/报告文件
- 可修改文件范围
- 不可修改或不可做的事
- 验收标准
- 推荐验证命令/API/browser check
- PASS 证据要求
- blocked/backlog 判定
- 状态字段

Future P3 should default to post-sprint backlog unless it is deliberately scoped, validated, and committed as one `WF-P3-*` task at a time.

## 6. Five-Day Roadmap

| Timebox | Focus | Deliverables |
| --- | --- | --- |
| Day 0.5 | Review, branches, docs, sprint skill | Baseline branch, sprint branch, this spec, existing-work review, reusable sprint skill. |
| Day 1 | WeKnora native capability map and PA adapter entry design | Route/API map, gap table, P0 implementation order, blocked/backlog list. |
| Day 2 | Native knowledge base/document/RAG | Real upload/status/chunks/search path, RAG debug adapter, status updates, live smoke report. |
| Day 3 | Native AgentQA/custom Agent | Adapter slice for AgentQA, PA history/citation mapping, live backend/API validation. |
| Day 4 | Native Wiki browse/search/read/index/graph | PA Wiki page uses native surfaces or jump links, with clear blocked/backlog states. |
| Day 5 | Frontend integration and real acceptance | Browser matrix, live evidence reports, report safety scan, final sprint summary. |

## 7. WeKnora Native Capability Connection Checklist

| WeKnora native area | Observed native surface | PA action |
| --- | --- | --- |
| Health | `/health` | Keep as readiness source. |
| Knowledge upload | `/api/v1/knowledge-bases/{kb_id}/knowledge/file`, URL/manual variants | PA library upload should call native upload where possible. |
| Knowledge status | `/api/v1/knowledge/{knowledge_id}` | PA document status should refresh from native status. |
| Chunk preview | `/api/v1/chunks/{knowledge_id}`, chunk by id | PA chunk/evidence preview should use native chunks. |
| Knowledge search | `/api/v1/knowledge-search` | PA RAG debug and retriever adapter should thin around native search. |
| Knowledge chat | `/api/v1/knowledge-chat/{session_id}` | Backlog unless needed after AgentQA decision. |
| AgentQA | `/api/v1/agent-chat/{session_id}` | P1 adapter target for general Agent. |
| Custom Agent | `/api/v1/agents`, `/api/v1/agents/type-presets` | P1/P2 for native agent selection and configuration visibility. |
| Wiki pages | `/api/v1/knowledgebase/{kb_id}/wiki/pages` | P0/P1 for list/create/read/update where real access is available. |
| Wiki index/log | `/api/v1/knowledgebase/{kb_id}/wiki/index`, `/log` | P1 for native browse entry. |
| Wiki graph/stats | `/api/v1/knowledgebase/{kb_id}/wiki/graph`, `/stats` | P1/P2, can start with jump or read-only card. |
| Wiki search | `/api/v1/knowledgebase/{kb_id}/wiki/search` | P0/P1 for PA Wiki search. |
| Wiki lint/issues/auto-fix | `/lint`, `/issues`, `/auto-fix`, `/rebuild-links` | P2 unless simple read-only status is safe. |
| MCP services | `/api/v1/mcp-services` and subresources | P2 visibility/jump; no credential handling in PA unless explicitly scoped. |
| Web search providers | native web search provider routes/services | P2 status only; do not duplicate credential forms. |
| Vector stores | `/api/v1/vector-stores` and `/types` | P2 status/jump; WeKnora remains native admin owner. |

## 8. PA Adapter And Product-Layer Responsibilities

PA should implement:

- Frontend navigation and product experience.
- Backend adapter endpoints that normalize WeKnora responses into PA-friendly schemas.
- Business records: documents, conversations, generation tasks, outputs, citations, Wiki draft links, and history.
- Evidence/citation mapping: `source`, `source_type`, `evidence_id`, `chunk_id`, `external_doc_id`, `wiki_page_id`, score, locator, and metadata allowlist.
- Runtime status surfaces that distinguish real, mock, fallback, partial, blocked, backlog, and cached evidence.
- Report generation and safety checks for live evidence.
- Professional templates and workflow entry points, without deepening PA-native general Agent logic during this sprint.

PA should not implement during this sprint:

- General-purpose parser/chunker/embedding/vector store administration.
- General-purpose Wiki graph/lint/auto-fix engine.
- General-purpose Agent tool orchestration when WeKnora native AgentQA/custom Agent is available.
- Credential management for WeKnora native MCP/web-search/vector-store admin unless a specific secure adapter task is accepted.

## 9. Backlog, Placeholder, And Jump Rules

| Capability | Allowed five-day treatment |
| --- | --- |
| Large WeKnora admin screens | Add a clear link/jump to WeKnora native admin or mark backlog. |
| MCP credential editing | Backlog by default; avoid copying credential forms into PA. |
| Vector-store CRUD | Backlog or read-only readiness; use WeKnora native admin for mutation. |
| Web search provider CRUD | Backlog or read-only readiness. |
| Advanced Wiki graph/lint/auto-fix | P2; jump/read-only is acceptable before mutation. |
| PA-native professional Agent expansion | Backlog; preserve baseline but do not expand in this sprint. |
| Unavailable native API | Mark blocked with cause and next step; do not replace with mock. |

Placeholders are allowed only when they are honest product placeholders: they must say blocked/backlog/jump, not pretend the capability works.

## 10. Acceptance Criteria By Capability

| Capability | PASS criteria |
| --- | --- |
| Native capability map | Source files/routes inspected; route list and PA gap table documented; no live PASS claimed. |
| Document upload/status | A sanitized file uploads through PA to WeKnora, receives native id/status, reaches indexed or reports a real blocked state. |
| Chunk preview | PA displays chunks from native WeKnora evidence/chunk API or marks unavailable with clear reason. |
| RAG debug | Query through PA returns WeKnora native evidence with `source=weknora_api`, `source_type`, `evidence_id`, and trace metadata. |
| AgentQA | PA calls native AgentQA/custom agent path, stores returned output/history, and maps citations or explicitly reports unsupported citation mapping. |
| Wiki browse/search/read | PA reads native Wiki pages/search/index or links to native UI; citation mapping stays traceable. |
| Frontend | Browser check covers 首页、资料库、RAG 调试、Wiki、知识问答、历史; no hidden mock/fallback green states. |
| Reports | Each real PASS report distinguishes live, fixture, mock, cached, blocked, and backlog evidence. |

## 11. Evidence Classification Rules

| Evidence type | Definition | Can count as sprint PASS |
| --- | --- | --- |
| live evidence | Produced by current real PA backend/frontend calling real WeKnora and real non-mock model/embedding runtime | Yes |
| fixture evidence | Synthetic sanitized corpus or test input | Only if processed through live system; fixture-only proof is no |
| mock evidence | Any `mock` backend, mock model, static sample, fake response, or generated UI-only state | No |
| cached evidence | Old report, old evidence id, stale browser state, saved output, or prior run result | No, unless rerun live and labeled current |
| partial evidence | Real call that proves only part of a contract | No final PASS; mark partial or blocked |
| blocked evidence | Native API/config/runtime unavailable with cause recorded | No PASS; mark blocked/backlog |

Every report must explicitly state which evidence type it uses.

## 12. Risk And Degradation Plan

| Risk | Response |
| --- | --- |
| WeKnora native API differs from current PA adapter assumptions | Document the gap, add a thin compatibility adapter, and keep raw response out of logs/reports. |
| Native AgentQA citation mapping is incomplete | Mark AgentQA partial/blocked for citation PASS; keep PA history output honest. |
| WeKnora service/model/embedding unavailable | Mark blocked with endpoint category and next step, without printing secrets or falling back to mock. |
| Frontend is tempted to hide partial state | Keep real/partial/mock/fallback labels visible on status cards and page sections. |
| Current-run evidence polluted by old materials | Reuse current-run isolation and fail closed when out-of-scope evidence appears. |
| Scope too large for five days | Prefer smallest live slice plus jump/backlog over broad demo coverage. |

## 13. Real Capability Acceptance Rule

A task is PASS only when all of these are true:

1. The active path is real PA frontend/backend or real PA backend API.
2. PA calls real WeKnora native capability or a documented WeKnora API adapter.
3. Model and embedding runtime are non-mock if the capability depends on them.
4. Evidence includes traceable `source`, `source_type`, `evidence_id`, and native identifiers where applicable.
5. Validation output distinguishes live evidence from fixture/mock/cache.
6. No secrets, private endpoints, raw uploaded files, local databases, logs, caches, or provider payloads are printed or committed.

Mock, demo, static UI, fixture-only, or historical cached evidence cannot complete this sprint.

When a task is completed or blocked, update Section 4 in the same branch so the next conversation can recover project progress from this spec, `git log --oneline`, and `git status -sb`.
