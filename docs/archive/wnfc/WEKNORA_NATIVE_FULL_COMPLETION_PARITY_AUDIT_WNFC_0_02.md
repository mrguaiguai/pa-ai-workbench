# WNFC-0-02 Native Parity Audit Excluding Web Search

Date: 2026-06-24
Task: `WNFC-0-02: Native parity audit excluding Web Search`
Task type: governance audit / parity map
PASS evidence type: audit/map
Status: complete for audit only; no implementation PASS is claimed.

## 1. Boundary

This report audits non-Web-Search WeKnora native capability parity for WNFC.
Web Search routes and PA web-search BFF code were observed only as exclusion
boundaries and are not counted toward the WNFC 14/14 completion target.

No code changes, database changes, credential changes, live external probes, or
capability PASS claims are part of this task.

## 2. Source Inventory

Native WeKnora source inspected:

- `internal/router/router.go`
- `internal/handler/mcp_service.go`
- `internal/handler/mcp_credentials.go`
- `internal/application/service/mcp_service.go`
- `internal/application/service/mcp_tool_approval_service.go`
- `internal/types/mcp.go`
- `internal/agent/approval/gate.go`
- `internal/agent/tools/mcp_tool.go`
- `internal/handler/vectorstore.go`
- `internal/application/service/vectorstore.go`
- `internal/application/service/vectorstore_healthcheck.go`
- `internal/types/vectorstore.go`
- `internal/handler/model.go`
- `internal/handler/model_credentials.go`
- `internal/application/service/model.go`
- `internal/types/model.go`
- `internal/infrastructure/docparser/engine_registry.go`
- `internal/types/docparser.go`
- `internal/datasource/connector.go`
- `internal/datasource/connector/feishu`
- `internal/datasource/connector/notion`
- `internal/datasource/connector/yuque`
- `internal/datasource/connector/rss`
- `internal/application/service/datasource_service.go`
- `internal/types/datasource.go`
- `internal/handler/knowledge_faq.go`
- `internal/application/service/knowledge_faq.go`
- `internal/types/faq.go`
- `internal/handler/knowledge_tag.go`
- `internal/application/service/knowledge_tag.go`
- `internal/handler/user_favorite.go`
- `internal/application/service/user_favorite.go`
- `internal/handler/skill_handler.go`
- `internal/application/service/skill_service.go`
- `internal/types/interfaces/skill.go`
- `internal/handler/knowledge_base.go`
- `internal/handler/chunk.go`
- `internal/handler/custom_agent.go`
- `internal/types/custom_agent.go`
- `internal/handler/wiki_page.go`
- `internal/application/service/wiki_page.go`
- `internal/types/wiki.go`

PA source inspected:

- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/api/mcp.py`
- `backend/app/api/vector_store.py`
- `backend/app/api/model.py`
- `backend/app/api/data_source.py`
- `backend/app/api/organization.py`
- `backend/app/api/knowledge_bases.py`
- `backend/app/api/documents.py`
- `backend/app/api/wiki.py`
- `backend/app/api/analysis.py`
- `backend/app/api/rag.py`
- `backend/app/services/mcp_service.py`
- `backend/app/services/vector_store_service.py`
- `backend/app/services/model_config_service.py`
- `backend/app/services/data_source_service.py`
- `backend/app/services/organization_service.py`
- `backend/app/services/knowledge_base_service.py`
- `backend/app/services/native_agent_service.py`
- `backend/app/services/wiki_service.py`
- `backend/app/models.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/CapabilityCenterPage.tsx`
- `frontend/src/components/workbench.tsx`
- `frontend/src/pages/LibraryPage.tsx`
- `frontend/src/pages/AnalysisPage.tsx`
- `frontend/src/pages/WikiPage.tsx`

## 3. Executive Findings

1. Native WeKnora already contains broad administrative surfaces for MCP,
   vector stores, models, data sources, FAQ, tags, favorites, KBs, chunks,
   custom agents, and Wiki. Most WNFC gaps can be closed PA-first by adding
   safe BFF routes, masked forms, confirmation gates, mutation audit, and
   browser UI around existing native routes.
2. PA currently exposes many visibility surfaces and some confirmation-gated
   actions, but it is not yet a complete local productivity tool. Existing PA
   coverage is strongest for Wiki and RAG/AgentQA citation workflows. MCP,
   vector store, data source, model, and organization surfaces remain mostly
   read-only or test/sync-only.
3. Native exception lane is required or probable for:
   - MCP prompts: native routes/types expose tools and resources, but no
     prompt-list/read route or prompt type was found.
   - Native skill management: native exposes only preloaded skill listing/read;
     create/update/delete/test management routes are absent.
   - Unregistered data-source connectors: metadata lists more connector types
     than are actually registered. Feishu, Notion, Yuque, and RSS are registered;
     Confluence, GitHub, Google Drive, OneDrive, DingTalk, Web Crawler, Slack,
     and IMAP are metadata-only unless new connector implementations are added.
   - Chunk search-by-chunk and advanced rewrite/re-embedding, if WNFC requires a
     dedicated native operation beyond existing chunk update/delete/reparse APIs.
   - Direct PA-driven MCP tool execution, if the product contract requires
     executing a tool outside the native AgentQA tool path.
4. The next implementation task should not jump directly into connector or MCP
   UI. `WNFC-0-03` should come first to create shared credential masking,
   confirmation tokens, audit records, timeout/error classes, and reusable UI
   affordances. This prevents repeating one-off safety logic across every
   high-risk native admin flow.

## 4. Native / PA Parity Map

### 4.1 MCP

Native routes:

- `GET/POST /api/v1/mcp-services`
- `GET/PUT/DELETE /api/v1/mcp-services/:id`
- `POST /api/v1/mcp-services/:id/test`
- `GET /api/v1/mcp-services/:id/tools`
- `GET /api/v1/mcp-services/:id/resources`
- `PUT /api/v1/mcp-services/:id/credentials`
- `DELETE /api/v1/mcp-services/:id/credentials/:field`
- `GET /api/v1/mcp-services/:id/tool-approvals`
- `PUT /api/v1/mcp-services/:id/tool-approvals/:tool_name`
- `POST /api/v1/agent/tool-approvals/:pending_id`

Native handlers, services, and types:

- `MCPServiceHandler` handles service CRUD, test, tools, resources, and approval
  policy read/write.
- `MCPCredentialsHandler` handles per-field secret updates/deletes.
- `mcp_service.go` implements CRUD, credential redaction, test, tools, and
  resources.
- `mcp_tool_approval_service.go` implements approval policy lookup/mutation.
- `types/mcp.go` defines service, auth, advanced config, stdio config, tools,
  approvals, resources, and test result shapes.
- `agent/approval/gate.go` implements pending approval, timeout, resolve, and
  fail-closed behavior.
- `agent/tools/mcp_tool.go` wraps MCP tools for Agent execution and prefixes
  external output to reduce indirect prompt-injection risk.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` supports service list/get/test, tools, resources, and tool
  approval listing.
- `backend/app/api/mcp.py` exposes overview, service detail, and confirmed test.
- `backend/app/services/mcp_service.py` reports `safe_read_confirmed_test`,
  exposes tools/resources only behind safety surfaces, and keeps mutations in a
  backlog.
- Frontend currently fetches native MCP overview in the workbench/status area,
  but has no complete MCP management screen.

PA-first work possible:

- Service CRUD and credentials can be wired PA-first because native routes
  already exist.
- Tool/resource listing and service test can be wired PA-first with
  confirmation and redaction.
- Tool approval policy mutation can be wired PA-first around the existing native
  approval route.

Native exception / blocker:

- Native MCP prompts are absent from route/type/service audit. `WNFC-P2-02`
  must either narrow "prompts" out with explicit evidence or add a minimal
  native prompt list/read lane if WeKnora's MCP client supports it.
- Direct PA tool execution is not exposed as an admin BFF route. Existing
  execution path is through native Agent tool use with approval gating. If PA
  needs direct operator-triggered execution, add a small auditable native or PA
  lane rather than bypassing Agent approval semantics.

Required external input:

- One real low-risk MCP service configuration, including transport, endpoint or
  command, auth if needed, at least one safe tool/resource, and operator
  approval for connection tests and any tool execution.

First implementation task:

- After `WNFC-0-03`, start with `WNFC-P2-01` for service CRUD and credentials.

### 4.2 Vector Store

Native routes:

- `GET /api/v1/vector-stores/types`
- `POST /api/v1/vector-stores/test`
- `GET/POST /api/v1/vector-stores`
- `GET/PUT/DELETE /api/v1/vector-stores/:id`
- `POST /api/v1/vector-stores/:id/test`

Native handlers, services, and types:

- `VectorStoreHandler` handles CRUD, engine type listing, raw tests, and saved
  store tests.
- `vectorstore.go` handles registration, env default/store views, validation,
  masking, detected versions, and CRUD.
- `vectorstore_healthcheck.go` implements engine-specific connection tests.
- `types/vectorstore.go` defines connection config, index config, display
  model, response model, type metadata, and env-store construction.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` supports vector store type/list/get/test surfaces.
- `backend/app/api/vector_store.py` exposes overview, safe-index detail, and
  confirmed test.
- `backend/app/services/vector_store_service.py` reports readiness and keeps
  vector CRUD, raw config tests, and KB rebind in backlog.
- Frontend fetches overview only. No full vector admin UI exists.

PA-first work possible:

- CRUD, raw test, saved-store test, redacted status, and safe detail pages can be
  wired through existing native APIs.
- KB rebind can likely be PA-first by using native initialization/config routes,
  but it must be confirmation-gated and audited.

Native exception / blocker:

- None confirmed for basic vector CRUD/test.
- Native exception may be needed only if WNFC requires a KB rebind operation not
  representable through current initialization/config APIs.

Required external input:

- Operator choice of target vector store. If using the current env/default
  store, no new credential is necessarily required, but any live connection test,
  CRUD, or KB rebind needs explicit confirmation. If using an external store,
  provide the engine, endpoint, index/collection, auth material, and permission
  to create/update/delete test entries.

First implementation task:

- `WNFC-P3-04`, after `WNFC-0-03` and model/embedding readiness checks.

### 4.3 Model, Embedding, Rerank, Parser, and Storage

Native routes:

- `GET /api/v1/models/providers`
- `GET/POST /api/v1/models`
- `GET/PUT/DELETE /api/v1/models/:id`
- `PUT /api/v1/models/:id/credentials`
- `DELETE /api/v1/models/:id/credentials/:field`
- `GET /api/v1/initialization/config/:kbId`
- `POST /api/v1/initialization/initialize/:kbId`
- `PUT /api/v1/initialization/config/:kbId`
- `GET /api/v1/initialization/ollama/status`
- `GET /api/v1/initialization/ollama/models`
- `POST /api/v1/initialization/ollama/models/check`
- `POST /api/v1/initialization/ollama/models/download`
- `GET /api/v1/initialization/ollama/download/progress/:taskId`
- `GET /api/v1/initialization/ollama/download/tasks`
- `POST /api/v1/initialization/remote/check`
- `POST /api/v1/initialization/embedding/test`
- `POST /api/v1/initialization/rerank/check`
- `POST /api/v1/initialization/asr/check`
- `POST /api/v1/initialization/multimodal/test`
- `POST /api/v1/initialization/extract/text-relation`
- `POST /api/v1/initialization/extract/fabri-tag`
- `POST /api/v1/initialization/extract/fabri-text`
- `GET /api/v1/system/info`
- `GET /api/v1/system/parser-engines`
- `POST /api/v1/system/parser-engines/check`
- `POST /api/v1/system/docreader/reconnect`
- `GET /api/v1/system/storage-engine-status`
- `POST /api/v1/system/storage-engine-check`

Native handlers, services, and types:

- `ModelHandler` and `ModelCredentialsHandler` expose provider/model CRUD and
  secret subresources.
- `model.go` service handles tenant model config, credential status, and active
  chat/embedding/rerank/vision/asr model selection.
- `types/model.go` and builtin model config files define provider/model shapes.
- `InitializationHandler` owns remote, embedding, rerank, ASR, multimodal, and
  extraction checks.
- `SystemHandler` owns parser engine and storage engine diagnostics.
- `docparser/engine_registry.go` registers builtin/simple/weknoracloud/mineru
  parser engines.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` lists providers/models.
- `backend/app/api/model.py` exposes `/api/model/status` and
  `/api/model/native/overview`.
- `backend/app/services/model_config_service.py` surfaces provider/model/parser
  and storage readiness, but active checks are marked blocked/admin-only.
- UI status surfaces exist, but no full operator model config/admin page exists.

PA-first work possible:

- Product-grade model overview, provider/model CRUD bridge, credential masking,
  and active test actions can be wired PA-first around existing native routes.
- Parser/storage diagnostics can be wired PA-first if confirmation, redaction,
  timeout, and audit are centralized in `WNFC-0-03`.

Native exception / blocker:

- No confirmed native blocker for model CRUD or active tests.
- Native exception may be required if the product-grade source-of-truth
  requirement needs file/config provenance not exposed by native APIs.

Required external input:

- Real chat, embedding, and rerank provider configuration, or explicit local
  runtime/model names if using Ollama/local engines.
- Parser/storage runtime choice for active tests. Builtin/simple parser may need
  no extra credential; WeKnoraCloud, MinerU Cloud, DocReader, or external
  storage engines need operator-provided credentials and permission to probe.

First implementation task:

- `WNFC-P3-01`, then `WNFC-P3-02`, then `WNFC-P3-03`.

### 4.4 Data Sources and Connectors

Native routes:

- `GET /api/v1/datasource/types`
- `POST /api/v1/datasource/validate-credentials`
- `GET/POST /api/v1/datasource`
- `GET/PUT/DELETE /api/v1/datasource/:id`
- `PUT /api/v1/datasource/:id/credentials`
- `DELETE /api/v1/datasource/:id/credentials/:field`
- `POST /api/v1/datasource/:id/validate`
- `GET /api/v1/datasource/:id/resources`
- `POST /api/v1/datasource/:id/sync`
- `POST /api/v1/datasource/:id/pause`
- `POST /api/v1/datasource/:id/resume`
- `GET /api/v1/datasource/:id/logs`
- `GET /api/v1/datasource/logs/:log_id`

Native handlers, services, and types:

- `DataSourceHandler` handles connector metadata, credential validation,
  source CRUD, resource listing, sync controls, and logs.
- `DataSourceCredentialsHandler` owns credential subresources.
- `datasource_service.go` handles CRUD, validation, resources, manual sync,
  pause/resume, logs, processing, and ingestion into KB content.
- `types/datasource.go` defines data source config, credentials, resource IDs,
  settings, fetched items, cursors, sync result, and connector constants.
- `datasource/connector.go` defines the connector interface:
  `Type`, `Validate`, `ListResources`, `FetchAll`, and `FetchIncremental`.
- Registered connectors are Feishu, Notion, Yuque, and RSS.
- Metadata-only connector types include Confluence, GitHub, Google Drive,
  OneDrive, DingTalk, Web Crawler, Slack, and IMAP.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` lists connector types/sources, supports source detail,
  validation, resources, sync logs, sync, pause, resume, and RSS creation helper
  code.
- `backend/app/api/data_source.py` exposes overview, detail by safe index, and
  confirmed sync/pause/resume.
- `backend/app/services/data_source_service.py` keeps credential forms, raw
  credential validation, external resource listing, raw logs, create/update,
  delete, and deletion sync controls in backlog.
- Frontend has status-center visibility but no complete connector setup wizard.

PA-first work possible:

- For registered connectors, PA can build credential setup, masked credential
  state, resource selection, validate, sync, pause/resume, logs, delete, and
  ingestion evidence using existing native routes.

Native exception / blocker:

- Any connector outside Feishu/Notion/Yuque/RSS requires native connector
  implementation/registration before it can be counted as complete.

Required external input:

- At least one credential-bearing connector must be selected and provided before
  `WNFC-P1-01`. Valid first choices:
  - Notion: internal integration token plus an accessible page/database shared
    to that integration.
  - Yuque: personal/team token plus accessible namespace/book/repo.
  - Feishu/Lark: app id, app secret, required document/wiki/export/download
    permissions, and an accessible workspace/wiki space.
- RSS cannot be used to satisfy the credential-bearing connector requirement.

First implementation task:

- `WNFC-P1-01`, after `WNFC-0-03` and once a real credential-bearing connector
  path is chosen.

### 4.5 FAQ, Tags, Favorites, and Skills

Native routes:

- FAQ:
  - `GET/POST /api/v1/knowledge-bases/:id/faq/entries`
  - `GET /api/v1/knowledge-bases/:id/faq/entries/export`
  - `GET/PUT /api/v1/knowledge-bases/:id/faq/entries/:entry_id`
  - `POST /api/v1/knowledge-bases/:id/faq/entry`
  - `POST /api/v1/knowledge-bases/:id/faq/entries/:entry_id/similar-questions`
  - `PUT /api/v1/knowledge-bases/:id/faq/entries/fields`
  - `PUT /api/v1/knowledge-bases/:id/faq/entries/tags`
  - `DELETE /api/v1/knowledge-bases/:id/faq/entries`
  - `POST /api/v1/knowledge-bases/:id/faq/search`
  - `PUT /api/v1/knowledge-bases/:id/faq/import/last-result/display`
  - `GET /api/v1/faq/import/progress/:task_id`
- Tags:
  - `GET/POST /api/v1/knowledge-bases/:id/tags`
  - `PUT/DELETE /api/v1/knowledge-bases/:id/tags/:tag_id`
- Favorites:
  - `GET/POST /api/v1/user/favorites`
  - `DELETE /api/v1/user/favorites/:type/:id`
- Skills:
  - `GET /api/v1/skills`

Native handlers, services, and types:

- FAQ handler/service/types support list, create/upsert, update, delete, search,
  export, import progress, field updates, tag updates, and similar questions.
- Tag handler/service supports list/create/update/delete.
- Favorite handler/service supports list/add/remove for user-owned favorites.
- Skill handler/service supports preloaded skill discovery and loading only.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` supports FAQ list, KB tags, favorites, and skills list.
- `backend/app/api/organization.py` exposes a read-only native organization
  overview.
- `backend/app/services/organization_service.py` keeps FAQ mutations, tag CRUD,
  favorite add/remove, and skill upload/enable/execute in backlog.
- Frontend has no full organization/admin editor for these resources.

PA-first work possible:

- FAQ workflow, tags, and favorites can be completed PA-first around existing
  native routes, provided `WNFC-0-03` supplies common confirmation/audit.

Native exception / blocker:

- Native skill management is not present. `WNFC-P4-03` must either record exact
  native blockers or use the controlled native exception lane to add management
  APIs for create/update/delete/test if product scope requires them.

Required external input:

- FAQ requires a real FAQ-type or FAQ-compatible KB to validate the full flow.
- Tags/favorites need a real KB/agent resource to mutate.
- Skills need native product scope confirmation because current native support is
  read-only.

First implementation task:

- `WNFC-P4-01` for FAQ, then `WNFC-P4-02`, then `WNFC-P4-03`.

### 4.6 Knowledge Base Admin Residuals

Native routes:

- `GET/POST /api/v1/knowledge-bases`
- `GET/PUT/DELETE /api/v1/knowledge-bases/:id`
- `PUT /api/v1/knowledge-bases/:id/pin`
- `GET /api/v1/knowledge-bases/:id/hybrid-search`
- `POST /api/v1/knowledge-bases/copy`
- `GET /api/v1/knowledge-bases/copy/progress/:task_id`
- `GET /api/v1/knowledge-bases/:id/move-targets`
- Tag routes listed in section 4.5.

Native handlers, services, and types:

- Knowledge base handler/service provide CRUD, pin, hybrid search, copy, move
  targets, and KB config including vector store references.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` lists/reads KBs and tags.
- `backend/app/api/knowledge_bases.py` exposes native overview and active
  selection snapshot.
- `backend/app/services/knowledge_base_service.py` keeps create/update/delete,
  pin, and tag mutation backlog.
- Library page consumes KB overview/active selection but does not complete admin
  mutation flows.

PA-first work possible:

- KB create/update/delete/pin/tag residuals can be completed PA-first using
  existing native APIs and shared confirmation/audit.

Native exception / blocker:

- None confirmed for basic KB admin residuals.

Required external input:

- A real KB that can safely be used for create/update/delete/copy/pin/tag tests,
  or explicit permission to create and delete a WNFC test KB.

First implementation task:

- `WNFC-P5-01`.

### 4.7 Chunk Advanced Residuals

Native routes:

- `POST /api/v1/chunker/preview`
- `GET /api/v1/chunks/:knowledge_id`
- `GET /api/v1/chunks/by-id/:id`
- `DELETE /api/v1/chunks/:knowledge_id/:id`
- `DELETE /api/v1/chunks/:knowledge_id`
- `PUT /api/v1/chunks/:knowledge_id/:id`
- `DELETE /api/v1/chunks/by-id/:id/questions`
- Knowledge document routes for file/url/manual create, list, read, update,
  delete, reparse, cancel parse, download, preview, image metadata, tags, search,
  batch delete, and move.

Native handlers, services, and types:

- Chunk handler supports list/read/update/delete and generated-question delete.
- Knowledge handler/service supports document lifecycle, manual knowledge,
  reparse/cancel, preview/download, search, and batch operations.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` supports document/chunk list/read/update/delete and
  generated-question delete flows.
- `backend/app/api/documents.py` exposes chunk list, read, enabled patch,
  delete, and generated-question delete with confirmation/audit parameters.
- Library page exposes document/chunk operations, mostly through local document
  workflow plus native-backed adapter calls.

PA-first work possible:

- Existing chunk list/read/update/delete/generated-question delete can be
  closed PA-first with stronger audit/history integration and browser proof.

Native exception / blocker:

- Dedicated content rewrite/re-embedding and search-by-chunk were not confirmed
  as explicit native routes in this audit. If WNFC keeps those as required
  operations, they need either native-absent evidence and scope adjustment or a
  controlled native exception.

Required external input:

- A real KB document with chunks that can be safely modified/reparsed, plus
  operator confirmation before destructive chunk tests.

First implementation task:

- `WNFC-P5-02`.

### 4.8 Custom Agent Admin

Native routes:

- `GET /api/v1/agents/placeholders`
- `GET /api/v1/agents/type-presets`
- `GET/POST /api/v1/agents`
- `GET/PUT/DELETE /api/v1/agents/:id`
- `POST /api/v1/agents/:id/copy`
- `GET /api/v1/agents/:id/suggested-questions`
- Agent chat routes are available through `/api/v1/agent-chat/:session_id`.

Native handlers, services, and types:

- Custom agent handler/service supports create/list/read/update/delete/copy,
  placeholders, type presets, and suggested questions.
- Native AgentQA/tool execution integrates with chat/session, MCP tools, and
  approval gates.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` lists agents, presets, placeholders, suggested questions,
  and runs native AgentQA.
- `backend/app/services/native_agent_service.py` exposes catalog/run surfaces but
  keeps copy/update/delete in backlog.
- Analysis page can run native AgentQA and display citation status/history.

PA-first work possible:

- Agent copy/update/delete/ownership flows can be completed PA-first using
  existing native routes plus shared confirmation/audit.

Native exception / blocker:

- None confirmed for custom agent admin residuals.

Required external input:

- A real custom agent that may be copied/edited/deleted, or permission to create
  and delete a WNFC test agent.

First implementation task:

- `WNFC-P5-03`.

### 4.9 Wiki Global Maintenance

Native routes:

- `GET/POST /api/v1/knowledgebase/:kb_id/wiki/pages`
- `GET/PUT/DELETE /api/v1/knowledgebase/:kb_id/wiki/pages/*slug`
- `GET /api/v1/knowledgebase/:kb_id/wiki/index`
- `GET /api/v1/knowledgebase/:kb_id/wiki/log`
- `GET /api/v1/knowledgebase/:kb_id/wiki/graph`
- `GET /api/v1/knowledgebase/:kb_id/wiki/stats`
- `GET /api/v1/knowledgebase/:kb_id/wiki/search`
- `POST /api/v1/knowledgebase/:kb_id/wiki/rebuild-links`
- `GET /api/v1/knowledgebase/:kb_id/wiki/lint`
- `POST /api/v1/knowledgebase/:kb_id/wiki/auto-fix`
- `GET /api/v1/knowledgebase/:kb_id/wiki/issues`
- `PUT /api/v1/knowledgebase/:kb_id/wiki/issues/:issue_id/status`

Native handlers, services, and types:

- Wiki page handler/service supports page CRUD, index, log, graph, stats,
  search, rebuild links, lint, auto-fix, issue listing, and issue status update.

PA adapter/BFF/UI now:

- `WeKnoraApiBackend` supports native Wiki search/read/create/update/list,
  index/stats/graph/lint/issues/log/delete/rebuild/auto-fix/issue status.
- `backend/app/api/wiki.py` and `backend/app/services/wiki_service.py` expose
  confirmation-gated native Wiki mutations and maintenance actions.
- `frontend/src/pages/WikiPage.tsx` already has native page and maintenance
  actions with confirm-token prompts.

PA-first work possible:

- Wiki global maintenance closure is mostly PA-first: polish audit/history,
  browser matrix, and operator diagnostics around existing BFF/UI.

Native exception / blocker:

- None confirmed for current WNFC Wiki maintenance scope.

Required external input:

- A real Wiki-enabled KB with pages/issues suitable for rebuild, auto-fix, and
  issue-status validation.

First implementation task:

- `WNFC-P5-04`.

## 5. PA Files Most Likely To Change Later

Shared foundation:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/api/*`
- `backend/app/services/*`
- `frontend/src/api/client.ts`
- shared frontend components/styles for confirmation, redaction, and audit
  surfaces.

Capability-specific PA files:

- MCP: `backend/app/api/mcp.py`, `backend/app/services/mcp_service.py`,
  `knowledge_engine/backends/weknora_api_backend.py`,
  `frontend/src/api/client.ts`, capability/admin UI pages.
- Vector store: `backend/app/api/vector_store.py`,
  `backend/app/services/vector_store_service.py`,
  `knowledge_engine/backends/weknora_api_backend.py`,
  `frontend/src/api/client.ts`, capability/admin UI pages.
- Model/parser/storage: `backend/app/api/model.py`,
  `backend/app/services/model_config_service.py`,
  `knowledge_engine/backends/weknora_api_backend.py`,
  `frontend/src/api/client.ts`, capability/admin UI pages.
- Data sources: `backend/app/api/data_source.py`,
  `backend/app/services/data_source_service.py`,
  `knowledge_engine/backends/weknora_api_backend.py`,
  `frontend/src/api/client.ts`, connector setup UI pages.
- Organization: `backend/app/api/organization.py`,
  `backend/app/services/organization_service.py`,
  `knowledge_engine/backends/weknora_api_backend.py`,
  `frontend/src/api/client.ts`, KB/organization admin UI pages.
- KB/chunk/agent/wiki residuals: `backend/app/api/knowledge_bases.py`,
  `backend/app/api/documents.py`, `backend/app/api/wiki.py`,
  `backend/app/api/analysis.py`, `backend/app/services/knowledge_base_service.py`,
  `backend/app/services/wiki_service.py`,
  `backend/app/services/native_agent_service.py`,
  `frontend/src/pages/LibraryPage.tsx`, `frontend/src/pages/WikiPage.tsx`,
  `frontend/src/pages/AnalysisPage.tsx`.

Native files likely to change only under controlled native exception lane:

- MCP prompts/direct execution if required:
  - `internal/router/router.go`
  - `internal/handler/mcp_service.go`
  - `internal/application/service/mcp_service.go`
  - `internal/types/mcp.go`
  - MCP client/tool integration files.
- Skill management if required:
  - `internal/router/router.go`
  - `internal/handler/skill_handler.go`
  - `internal/application/service/skill_service.go`
  - `internal/types/interfaces/skill.go`
  - `internal/agent/skills`.
- Unregistered connectors:
  - `internal/datasource/connector/*`
  - `internal/container/container.go`
  - `internal/types/datasource.go`.
- Missing chunk advanced operations if required:
  - `internal/router/router.go`
  - `internal/handler/chunk.go`
  - `internal/application/service/*chunk*`
  - related repository/types files.

## 6. Missing Credentials, APIs, Workspaces, and Permissions

These must be provided or confirmed before implementation tasks can pass with
real evidence:

1. Credential-bearing data source for `WNFC-P1-01`:
   - Choose Notion, Yuque, or Feishu/Lark as the first real connector.
   - Provide a non-production test workspace/resource that can be listed,
     synced, paused/resumed, logged, and deleted or disconnected safely.
2. MCP service for `WNFC-P2-*`:
   - Provide a real low-risk MCP service endpoint/transport and a safe tool or
     resource to test.
   - Confirm whether prompts are mandatory for this PA product scope. Native
     prompt support was not found.
3. Model/provider/runtime for `WNFC-P3-*`:
   - Provide real chat, embedding, and rerank configuration or confirm the local
     runtime/model names to use.
   - Confirm which parser/storage engines should receive active tests.
4. Vector store for `WNFC-P3-04`:
   - Confirm whether the current env/default vector store may be tested.
   - If a new external store is desired, provide endpoint, engine, index or
     collection name, auth material, and permission for CRUD/rebind validation.
5. FAQ, KB, chunk, agent, and Wiki validation resources:
   - Provide or allow creation of a WNFC test KB, FAQ data, document chunks,
     custom agent, and Wiki pages/issues.
6. Native skill management:
   - Confirm whether WNFC requires upload/create/update/delete/test for native
     skills. Current native capability is list/read-only.

No mock, demo connector, fixture credential, fake provider, or stale report can
substitute for the above.

## 7. Recommended Next Task Order

1. `WNFC-0-03: Credential, approval, and audit foundation`.
2. `WNFC-0-04: 100% acceptance harness`.
3. `WNFC-P1-01`, `WNFC-P1-02`, `WNFC-P1-03` after a real credential-bearing
   connector is chosen.
4. `WNFC-P2-01`, then `WNFC-P2-02` with the prompt blocker resolved, then
   `WNFC-P2-03`.
5. `WNFC-P3-01`, `WNFC-P3-02`, `WNFC-P3-03`, `WNFC-P3-04`.
6. `WNFC-P4-01`, `WNFC-P4-02`, `WNFC-P4-03`.
7. `WNFC-P5-01`, `WNFC-P5-02`, `WNFC-P5-03`, `WNFC-P5-04`.
8. `WNFC-P6-01`, then `WNFC-P6-02`.

Rationale: high-risk credential and mutation surfaces should share one audit and
confirmation foundation before building individual admin screens. Data-source
completion should come before final RAG evidence loops because it creates the
external knowledge that later retrieval, citations, AgentQA, and Wiki workflows
must prove.

## 8. WNFC-0-02 Acceptance Checklist

- Native files named: yes.
- Native API routes named: yes.
- Native handlers/services/types mapped: yes.
- PA adapter/BFF/UI surfaces mapped: yes.
- PA-first completion paths identified: yes.
- Controlled native exception candidates identified: yes.
- Missing credentials/API/workspace/permission items listed: yes.
- Best next implementation task named: yes, `WNFC-0-03`.
- Web Search excluded: yes.
- Code changes or PASS claims made: no.
