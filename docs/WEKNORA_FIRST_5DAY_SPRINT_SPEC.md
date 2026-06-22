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
6. Execute one task id per run; split oversized work instead of silently completing multiple slices.
7. Do not mark `[x]` from mock, fixture-only, cached, old report, hidden fallback, or inference-only evidence.
8. If live validation cannot run, mark `[!]` with cause and next step, or `[b]` if the task is consciously deferred.

### 4.1 Task Status Overview

| ID | Priority | Capability slice | Status | Required status evidence |
| --- | --- | --- | --- | --- |
| WF-0 | Stage 0 | Existing-work review, branches, sprint spec, sprint skill | [x] | Review/spec committed on `weknora-first-mvp`; skill validates in workspace. |
| WF-P0-01 | P0 | WeKnora native capability map | [x] | Source/routes inspected and gap table documented; no live PASS claimed. |
| WF-P0-02 | P0 | Knowledge base and document native path | [x] | Live PA document service uploaded to WeKnora, persisted native id, reached indexed, and read native chunks. |
| WF-P0-03 | P0 | RAG debug native alignment | [x] | Live PA RAG debug path called native WeKnora search and returned traceable evidence/rank/trace metadata. |
| WF-P0-04 | P0 | Truthful status and report gates | [x] | Live API/browser status surfaces expose real/native/mock/fallback/partial/blocked/backlog; report checker gates unsafe PASS evidence. |
| WF-P0-05 | P0 | Evidence/citation contract preservation | [ ] | Native integrations preserve `source`, `source_type`, `evidence_id`, native ids, and locator fields. |
| WF-P1-01 | P1 | WeKnora native AgentQA/custom Agent | [ ] | PA calls native AgentQA/custom Agent and stores answer/history/citation mapping or explicit citation blocker. |
| WF-P1-02 | P1 | Native Wiki browse/search/index/graph/lint | [ ] | PA reads or links native Wiki surfaces with honest blocked/backlog labels. |
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

P1 tasks stay intentionally lightweight until P0 is complete. When a P1 task is selected, create or expand only that single `WF-P1-*` card using the P0 card structure above; do not turn all P1/P2 backlog into a giant document during a P0 run.

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P1-01 | WeKnora native AgentQA/custom Agent | Add PA adapter entry for native AgentQA and store returned answer/citations/history through PA. |
| WF-P1-02 | Native Wiki browse/search/index/graph/lint | Let PA show or link to WeKnora native Wiki capabilities while preserving PA navigation. |
| WF-P1-03 | Knowledge base selection and mapping | Make active workspace/KB selection more visible and less dependent on hidden config assumptions. |
| WF-P1-04 | Frontend integration polish | Update pages to show WeKnora-first state, blocked/backlog labels, and native jump targets. |

### P2

P2 remains backlog by default. A P2 task may start as a read-only status or native-admin jump slice only when explicitly scoped by the user, and it must still use a single `WF-P2-*` id.

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P2-01 | MCP service visibility | Surface native MCP services/tools/approval state or link to WeKnora admin. |
| WF-P2-02 | Web search provider visibility | Surface native web-search provider readiness if AgentQA depends on it. |
| WF-P2-03 | Vector store management visibility | Show vector-store binding/readiness, or link to WeKnora native admin rather than rebuilding admin UI. |
| WF-P2-04 | Advanced Wiki maintenance | Auto-fix, issue management, graph filtering, and lint workflows after core browse/search/read is stable. |

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
