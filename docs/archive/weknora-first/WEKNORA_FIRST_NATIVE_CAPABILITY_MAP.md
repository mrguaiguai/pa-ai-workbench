# WeKnora-First Native Capability Map

> Task: `WF-P0-01`
>
> Date: 2026-06-22
>
> Evidence type: audit/map. This document is not live PASS evidence and does
> not claim any live capability PASS.

## Scope And Evidence Boundary

This report maps WeKnora native source/API surfaces to PA owner surfaces and
adapter gaps. It is source/API audit evidence only: route existence, handler
shape, service shape, and PA adapter code inspection are enough for this task,
but they are not live PASS proof. Future tasks must still validate live PA +
real WeKnora + non-mock model/embedding behavior where the capability depends
on runtime execution.

No product code, runtime config, `.env`, database, logs, uploads, cache, or
secret-bearing command output was changed or inspected.

## Sources Inspected

WeKnora native files inspected:

- `internal/router/router.go`
- `internal/handler/knowledge.go`
- `internal/handler/chunk.go`
- `internal/application/service/knowledge.go`
- `internal/application/service/knowledge_create.go`
- `internal/application/service/knowledge_process.go`
- `internal/application/service/knowledgebase_search*.go`
- `internal/application/service/chunk.go`
- `internal/types/search.go`
- `internal/types/retriever.go`
- `internal/handler/session/qa.go`
- `internal/application/service/session_knowledge_qa.go`
- `internal/application/service/session_agent_qa.go`
- `internal/handler/custom_agent.go`
- `internal/application/service/custom_agent.go`
- `internal/types/custom_agent.go`
- `internal/handler/wiki_page.go`
- `internal/application/service/wiki_page.go`
- `internal/application/service/wiki_*.go`
- `internal/application/service/wiki_lint.go`
- `internal/types/wiki_page.go`
- `internal/handler/mcp_service.go`
- `internal/handler/dto/mcp.go`
- `internal/application/service/mcp_service.go`
- `internal/types/mcp.go`
- `internal/handler/web_search.go`
- `internal/handler/web_search_provider.go`
- `internal/application/service/web_search.go`
- `internal/application/service/web_search_provider.go`
- `internal/types/web_search.go`
- `internal/types/web_search_provider.go`
- `internal/handler/vectorstore.go`
- `internal/application/service/vectorstore.go`
- `internal/application/service/vectorstore_healthcheck.go`
- `internal/types/vectorstore.go`

PA adapter/product files inspected:

- `knowledge_engine/factory.py`
- `knowledge_engine/capabilities.py`
- `knowledge_engine/base.py`
- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/api/documents.py`
- `backend/app/api/rag.py`
- `backend/app/api/wiki.py`
- `backend/app/api/analysis.py`
- `backend/app/api/health.py`
- `backend/app/services/document_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/wiki_service.py`
- `backend/app/services/backend_capability_service.py`
- `backend/app/services/runtime_status_service.py`
- `backend/app/services/history_service.py`
- `agent/orchestrator.py`
- `agent/tools/registry.py`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/LibraryPage.tsx`
- `frontend/src/pages/RagDebugPage.tsx`
- `frontend/src/pages/WikiPage.tsx`
- `frontend/src/pages/AnalysisPage.tsx`
- `frontend/src/pages/HistoryPage.tsx`

## Native Capability Map

| Native capability | Endpoint / module shape | Source file evidence | PA owner surface | Current adapter gap | Validation recommendation | blocked/backlog decision |
| --- | --- | --- | --- | --- | --- | --- |
| knowledge upload | `POST /api/v1/knowledge-bases/{kb_id}/knowledge/file`; also URL/manual variants | `internal/router/router.go`, `internal/handler/knowledge.go`, `internal/application/service/knowledge_create.go` | PA Library upload and business document record in `backend/app/api/documents.py`, `backend/app/services/document_service.py`, `frontend/src/pages/LibraryPage.tsx` | PA already uploads to native file endpoint in `WeKnoraApiBackend.upload_document`, but `/parse`, `/index`, and `/reindex` routes still expose PA local parser/chunker/vector workflow. Need WeKnora-first action policy so local extracted path is not mistaken for native PASS. | WF-P0-02 should run a live PA upload/status path, confirm native `external_doc_id`, and label local index/reindex controls as native retry, disabled, or explicit local fallback. | P0 active. Not blocked by source audit. |
| knowledge status | `GET /api/v1/knowledge/{knowledge_id}` plus stage/span routes under `/knowledge/{id}/stages` and `/spans` | `internal/router/router.go`, `internal/handler/knowledge.go`, `internal/application/service/knowledge.go`, `internal/application/service/knowledge_process.go` | PA document status/events in `document_service.py`, Library status chips, `/api/documents/refresh-status` | PA maps native status to document states and records `weknora_status` events. Gap: status surface does not yet expose all native stage/span detail as a first-class capability readiness source. | WF-P0-02 should refresh status after upload; WF-P0-04 should decide whether stage/span data belongs in capability/status cards or document detail. | P0 active; stage/span richness can be backlog if core status works. |
| knowledge chunks | `GET /api/v1/chunks/{knowledge_id}` and `GET /api/v1/chunks/by-id/{id}` | `internal/router/router.go`, `internal/handler/chunk.go`, `internal/application/service/chunk.go` | PA chunk preview in Library and citation locator/history | PA already calls `list_document_chunks` and creates transient PA `DocumentChunk` reads from native chunks. Gap: fallback to local chunks after native failure must remain visibly partial/failed, not silent PASS. | WF-P0-02 should verify chunk preview or record native chunk blocker; WF-P0-05 should confirm `chunk_id`, `external_doc_id`, and locator mapping. | P0 active; native chunk preview may be partial if WeKnora indexing is not ready. |
| knowledge search / RAG | `POST /api/v1/knowledge-search`, backed by `HybridSearch`, `SearchParams`, `SearchResult` with `id`, `knowledge_id`, `knowledge_base_id`, `chunk_index`, `score`, `match_type`, `chunk_type`, `parent_chunk_id` | `internal/router/router.go`, `internal/handler/session/qa.go`, `internal/application/service/session_knowledge_qa.go`, `internal/application/service/knowledgebase_search*.go`, `internal/types/search.go`, `internal/types/retriever.go` | PA RAG debug, Agent retriever, analysis citation builder, History filters | PA calls native search through `WeKnoraApiBackend.retrieve` and normalizes `source=weknora_api`, `source_type`, `evidence_id`, `chunk_id`, metadata allowlist. Gap: advanced native retrieval options are reserved/partial and must show unsupported/partial warnings instead of hidden local semantics. | WF-P0-03 should run a live RAG debug query and assert traceable evidence fields plus warnings for unsupported options. | P0 active. Not live PASS in this report. |
| knowledge chat | `POST /api/v1/knowledge-chat/{session_id}` | `internal/router/router.go`, `internal/handler/session/qa.go`, `internal/application/service/session_knowledge_qa.go` | PA knowledge QA page and `agent/orchestrator.py` knowledge QA workflow | PA currently uses PA-native `KnowledgeQaWorkflow` plus `RealRetrieverTool`; no native knowledge-chat adapter is present. This may be redundant if AgentQA becomes the general native route. | Defer until AgentQA decision; if used, require live answer/history/citation mapping and fail closed on missing citation fields. | backlog for P0; possible P1 after AgentQA mapping. |
| AgentQA | `POST /api/v1/agent-chat/{session_id}` streaming AgentQA path | `internal/router/router.go`, `internal/handler/session/qa.go`, `internal/application/service/session_agent_qa.go` | PA knowledge QA / analysis run history, `agent/orchestrator.py`, `agent/tools/registry.py`, `frontend/src/pages/AnalysisPage.tsx`, History | PA has no native AgentQA client. Current PA agent stack is PA-native workflows and local tool registry. Citation shape from native AgentQA response needs a live contract check before PA history can count it. | WF-P1-01 should add the thinnest native AgentQA adapter, store answer/history, and mark blocked if returned citations lack `source`, `source_type`, `evidence_id`, or native ids. | backlog until P0 evidence/status contract is stable. |
| custom Agent | `/api/v1/agents`, `/api/v1/agents/type-presets`, `/api/v1/agents/{id}`, copy, suggested questions | `internal/router/router.go`, `internal/handler/custom_agent.go`, `internal/application/service/custom_agent.go`, `internal/types/custom_agent.go` | PA task type/workflow selection, future native Agent picker/status | PA has no native custom Agent list/config surface. Current PA workflows are builtin PA task types. | P1 should start read-only: list native agents/type presets and map selected agent id to AgentQA. Mutation/config UI should wait. | backlog for P0; P1 read-only/jump first. |
| Wiki pages | `GET/POST/PUT/DELETE /api/v1/knowledgebase/{kb_id}/wiki/pages`; page has `id`, `slug`, `title`, `page_type`, `status`, `source_refs`, `chunk_refs`, links, metadata | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go`, `internal/types/wiki_page.go` | PA Wiki page, Wiki citation records, output-to-Wiki draft flow, History locator | PA already uses native Wiki search/read/create/update through `WeKnoraApiBackend` and stores PA wiki/citation metadata. Gap: PA still owns a local Wiki record/workflow and does not expose native list/index/graph/lint surfaces directly. | WF-P0-05 should preserve citation contract for Wiki pages; P1 should add native browse/search/read/index or native jump surfaces. | P0 citation mapping active; richer Wiki browse/admin backlog to P1/P2. |
| Wiki index/log/graph/stats | `GET /wiki/index`, `/log`, `/graph`, `/stats`; graph supports overview/ego and type filters | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go`, `internal/types/wiki_page.go` | PA Wiki navigation and status panel | PA adapter lacks index/log/graph/stats methods. Current PA Wiki page focuses search/read/edit/publish and local metadata. | P1 should add read-only index/search/read first; graph/stats can be visible jump/read-only cards after core Wiki browse works. | backlog for P0; P1/P2 depending on size. |
| Wiki search/lint/issues/maintenance | `GET /wiki/search`, `/lint`, `/issues`; `POST /rebuild-links`, `/auto-fix`; `PUT /issues/{issue_id}/status` | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_lint.go`, `internal/types/wiki_page.go` | PA Wiki quality/status and report gates | PA has native search wrapper but no lint/issues/auto-fix adapter. Mutation actions are broad and should not be rebuilt inside PA during P0. | P1/P2 should use read-only lint/issues status or a jump link; mutation must require explicit secure scope. | backlog. |
| MCP | `/api/v1/mcp-services`, `/tools`, `/resources`, `/tool-approvals`; credentials are separate subresources and DTO omits secret values | `internal/router/router.go`, `internal/handler/mcp_service.go`, `internal/handler/dto/mcp.go`, `internal/application/service/mcp_service.go`, `internal/types/mcp.go` | PA status/capability page or future Agent tool visibility | PA has no MCP service adapter or UI. Do not copy credential forms into PA. Native DTO is already designed to avoid exposing secrets; PA should preserve that boundary. | WF-P2-01 can be read-only list/tools/resources/status or native-admin jump. Live PASS requires no secret values in response/report. | backlog by sprint spec unless explicitly scoped. |
| web search | Provider catalog at `/api/v1/web-search/providers`; provider CRUD/status under `/api/v1/web-search-providers`; runtime `WebSearchService.Search` and RAG compression | `internal/router/router.go`, `internal/handler/web_search.go`, `internal/handler/web_search_provider.go`, `internal/application/service/web_search.go`, `internal/application/service/web_search_provider.go`, `internal/types/web_search.go`, `internal/types/web_search_provider.go` | PA AgentQA readiness/status, future provider visibility | PA has no web search provider readiness surface and no native web search adapter. Credentials must remain native-owned. | WF-P2-02 should only expose readiness/jump unless AgentQA live validation needs provider state. | backlog. |
| vector store | `/api/v1/vector-stores/types`, list/get CRUD, test existing/raw; response masks sensitive connection fields and distinguishes `env`, `user`, `shared`, `unavailable` | `internal/router/router.go`, `internal/handler/vectorstore.go`, `internal/application/service/vectorstore.go`, `internal/application/service/vectorstore_healthcheck.go`, `internal/types/vectorstore.go` | PA status/capability page, KB mapping/readiness, evidence/report status | PA has a separate local vector store abstraction for `extracted` backend and no WeKnora native vector-store adapter. PA should not administer vector stores during P0. | WF-P2-03 can add read-only readiness/jump. WF-P0-04 should surface embedding/index readiness without leaking vector credentials. | backlog for admin; P0 may reference readiness only. |
| PA evidence/citation contract | Native identifiers include search `id`, `knowledge_id`, `knowledge_base_id`, chunk metadata, Wiki `id/slug/source_refs/chunk_refs`, vector-store source/status | Native types above plus PA `knowledge_engine/evidence.py`, `backend/app/api/rag.py`, `backend/app/services/wiki_service.py`, `backend/app/services/history_service.py` | PA citation rendering, report safety, History filters, locator API | Strong existing PA mapping for document chunks and Wiki pages. Gap: AgentQA/custom Agent/MCP/web search/vector store outputs do not yet have a PA-native evidence contract. | WF-P0-05 should write a minimum contract and fail closed for missing ids; P1/P2 source types should be marked blocked/backlog until mapped. | P0 active. |

## PA Surface Ownership Summary

PA should own:

- Product shell: Home, Library, RAG debug, Wiki, Analysis, History.
- Business state: PA document records, conversations, tasks, generated outputs,
  Wiki drafts, citation records, and status events.
- Adapter normalization: `source=weknora_api`, `source_type`, `evidence_id`,
  `chunk_id`, `external_doc_id`, `wiki_page_id`, score/rank/trace metadata,
  locator fields, and safe metadata allowlists.
- Truthful status: real/native/mock/fallback/partial/blocked/backlog labels.

PA should not own during this sprint:

- General parser/chunker/embedding/vector-store administration when WeKnora
  native ingestion/indexing is the intended source of truth.
- General Wiki graph/lint/auto-fix engines.
- General Agent tool orchestration when native AgentQA/custom Agent can carry
  the general path.
- MCP, web search, or vector-store credential management.

## Gap Decisions

| Gap | Decision | Next task |
| --- | --- | --- |
| PA local document parse/index endpoints can still run local extracted pipeline | Treat as a P0 risk. In WeKnora mode, they must be native retry/status actions, disabled, or explicitly labelled local fallback. | WF-P0-02 |
| Retrieval options are partially reserved for native search | Keep partial/unsupported warnings visible; do not fake support through local semantics. | WF-P0-03 |
| Capability matrix does not yet include AgentQA/custom Agent/MCP/web search/vector store readiness | Extend status/report gates only after the map is committed. | WF-P0-04 |
| Native AgentQA response citation contract is unverified | Mark P1 blocked until live response shape proves traceable citations or an explicit unsupported citation blocker. | WF-P1-01 |
| MCP/web search/vector store admin is credential-sensitive and broad | Keep backlog by default; allow only read-only readiness or native-admin jump slices. | WF-P2-01 to WF-P2-03 |

## Validation Recommendations

For later live tasks, PASS must include current-run evidence from real PA +
real WeKnora + non-mock model/embedding where relevant. Recommended gates:

- Document/native knowledge path: PA upload, native id/status refresh, chunk
  preview or explicit blocker, with report labels for live/partial/blocked.
- RAG debug: PA `/api/rag/debug` or browser flow showing `source=weknora_api`,
  `source_type`, `evidence_id`, native ids, rank/trace/warnings.
- Status gates: `/health`, `/api/status`, `/api/model/status`, homepage browser
  check, and report safety scan.
- Citation contract: focused checker or smoke that rejects missing native ids,
  unsafe metadata, mock evidence, cached evidence, and hidden fallbacks.

This WF-P0-01 report itself remains audit/map evidence and is not live PASS.

## P0 execution order and exact file touch plan

Recommended P0 order:

1. `WF-P0-02` Knowledge base and document native path.
   Likely touches: `knowledge_engine/backends/weknora_api_backend.py`,
   `backend/app/api/documents.py`, `backend/app/services/document_service.py`,
   `backend/app/schemas.py`, `frontend/src/pages/LibraryPage.tsx`, focused
   smoke/report files under `backend/scripts/` or `docs/`, and
   `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.

2. `WF-P0-03` RAG debug native alignment.
   Likely touches: `knowledge_engine/backends/weknora_api_backend.py`,
   `knowledge_engine/retrieval/*`, `knowledge_engine/evidence.py`,
   `backend/app/api/rag.py`, `backend/app/services/rag_service.py`,
   `frontend/src/pages/RagDebugPage.tsx`, focused smoke/report files, and
   `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.

3. `WF-P0-05` Evidence/citation contract preservation.
   Likely touches: `knowledge_engine/schemas.py`,
   `knowledge_engine/evidence.py`, `knowledge_engine/citations/*`,
   `backend/app/schemas.py`, `backend/app/services/wiki_service.py`,
   `backend/app/services/history_service.py`, `backend/app/api/citations.py`,
   `agent/tools/evidence_policy.py`, report safety checks under
   `backend/scripts/`, `frontend/src/pages/RagDebugPage.tsx`,
   `frontend/src/pages/WikiPage.tsx`, `frontend/src/pages/HistoryPage.tsx`,
   a contract report under `docs/`, and
   `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.

4. `WF-P0-04` Truthful status and report gates.
   Likely touches: `knowledge_engine/capabilities.py`,
   `backend/app/api/health.py`, `backend/app/services/backend_capability_service.py`,
   `backend/app/services/runtime_status_service.py`,
   `backend/app/services/model_status_service.py`, `backend/app/schemas.py`,
   `frontend/src/pages/HomePage.tsx`, report safety scripts under
   `backend/scripts/`, a status gate report under `docs/`, and
   `docs/WEKNORA_FIRST_5DAY_SPRINT_SPEC.md`.

The reason to run `WF-P0-05` before `WF-P0-04` is that status/report gates
should enforce the final citation contract rather than encode a temporary
contract twice. `WF-P0-04` can still move earlier if a live blocker appears in
`WF-P0-02` or `WF-P0-03` and truthful blocked/backlog surfacing becomes the
next safest slice.
