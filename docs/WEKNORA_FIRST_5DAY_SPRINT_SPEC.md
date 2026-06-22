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

## 4. P0/P1/P2 Capability Priority

### P0

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P0-01 | WeKnora native capability map | Confirm native endpoints/modules for knowledge upload/status/chunks/search, Wiki, AgentQA, custom Agent, MCP, web search, and vector store. |
| WF-P0-02 | Knowledge base and document native path | PA upload/status/library views rely on WeKnora native ingestion/indexing as the source of truth. |
| WF-P0-03 | RAG debug native alignment | PA RAG debug becomes a thin WeKnora-first adapter while retaining citation/evidence display and current-run validation. |
| WF-P0-04 | Truthful status and report gates | Homepage/backend status exposes native capability readiness without hiding fallback, partial, blocked, or mock states. |
| WF-P0-05 | Evidence/citation contract preservation | Every native integration maps to PA `source`, `source_type`, `evidence_id`, locator, and history fields. |

### P1

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P1-01 | WeKnora native AgentQA/custom Agent | Add PA adapter entry for native AgentQA and store returned answer/citations/history through PA. |
| WF-P1-02 | Native Wiki browse/search/index/graph/lint | Let PA show or link to WeKnora native Wiki capabilities while preserving PA navigation. |
| WF-P1-03 | Knowledge base selection and mapping | Make active workspace/KB selection more visible and less dependent on hidden config assumptions. |
| WF-P1-04 | Frontend integration polish | Update pages to show WeKnora-first state, blocked/backlog labels, and native jump targets. |

### P2

| ID | Capability slice | Intended outcome |
| --- | --- | --- |
| WF-P2-01 | MCP service visibility | Surface native MCP services/tools/approval state or link to WeKnora admin. |
| WF-P2-02 | Web search provider visibility | Surface native web-search provider readiness if AgentQA depends on it. |
| WF-P2-03 | Vector store management visibility | Show vector-store binding/readiness, or link to WeKnora native admin rather than rebuilding admin UI. |
| WF-P2-04 | Advanced Wiki maintenance | Auto-fix, issue management, graph filtering, and lint workflows after core browse/search/read is stable. |

## 5. Five-Day Roadmap

| Timebox | Focus | Deliverables |
| --- | --- | --- |
| Day 0.5 | Review, branches, docs, sprint skill | Baseline branch, sprint branch, this spec, existing-work review, reusable sprint skill. |
| Day 1 | WeKnora native capability map and PA adapter entry design | Route/API map, gap table, P0 implementation order, blocked/backlog list. |
| Day 2 | Native knowledge base/document/RAG | Real upload/status/chunks/search path, RAG debug adapter, status updates, live smoke report. |
| Day 3 | Native AgentQA/custom Agent | Adapter slice for AgentQA, PA history/citation mapping, live backend/API validation. |
| Day 4 | Native Wiki browse/search/read/index/graph | PA Wiki page uses native surfaces or jump links, with clear blocked/backlog states. |
| Day 5 | Frontend integration and real acceptance | Browser matrix, live evidence reports, report safety scan, final sprint summary. |

## 6. WeKnora Native Capability Connection Checklist

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

## 7. PA Adapter And Product-Layer Responsibilities

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

## 8. Backlog, Placeholder, And Jump Rules

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

## 9. Acceptance Criteria By Capability

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

## 10. Evidence Classification Rules

| Evidence type | Definition | Can count as sprint PASS |
| --- | --- | --- |
| live evidence | Produced by current real PA backend/frontend calling real WeKnora and real non-mock model/embedding runtime | Yes |
| fixture evidence | Synthetic sanitized corpus or test input | Only if processed through live system; fixture-only proof is no |
| mock evidence | Any `mock` backend, mock model, static sample, fake response, or generated UI-only state | No |
| cached evidence | Old report, old evidence id, stale browser state, saved output, or prior run result | No, unless rerun live and labeled current |
| partial evidence | Real call that proves only part of a contract | No final PASS; mark partial or blocked |
| blocked evidence | Native API/config/runtime unavailable with cause recorded | No PASS; mark blocked/backlog |

Every report must explicitly state which evidence type it uses.

## 11. Risk And Degradation Plan

| Risk | Response |
| --- | --- |
| WeKnora native API differs from current PA adapter assumptions | Document the gap, add a thin compatibility adapter, and keep raw response out of logs/reports. |
| Native AgentQA citation mapping is incomplete | Mark AgentQA partial/blocked for citation PASS; keep PA history output honest. |
| WeKnora service/model/embedding unavailable | Mark blocked with endpoint category and next step, without printing secrets or falling back to mock. |
| Frontend is tempted to hide partial state | Keep real/partial/mock/fallback labels visible on status cards and page sections. |
| Current-run evidence polluted by old materials | Reuse current-run isolation and fail closed when out-of-scope evidence appears. |
| Scope too large for five days | Prefer smallest live slice plus jump/backlog over broad demo coverage. |

## 12. Real Capability Acceptance Rule

A task is PASS only when all of these are true:

1. The active path is real PA frontend/backend or real PA backend API.
2. PA calls real WeKnora native capability or a documented WeKnora API adapter.
3. Model and embedding runtime are non-mock if the capability depends on them.
4. Evidence includes traceable `source`, `source_type`, `evidence_id`, and native identifiers where applicable.
5. Validation output distinguishes live evidence from fixture/mock/cache.
6. No secrets, private endpoints, raw uploaded files, local databases, logs, caches, or provider payloads are printed or committed.

Mock, demo, static UI, fixture-only, or historical cached evidence cannot complete this sprint.
