# WeKnora Native Intelligent Dialogue Parity Map

> Task: `WNID-0-02`
>
> Date: 2026-06-25
>
> Evidence type: audit/map.
>
> Scope: no product code implementation, no service startup, and no WNFC
> conclusion rewrite.

## Evidence Boundary

This report maps the WeKnora README **Intelligent Conversation** table to
native WeKnora routes, handlers, services, types, client fields, and current
PA AI Workbench surfaces. It completes the WNID-0-02 governance mapping task
only. It does not mark any README row as final WNID PASS.

State terms below mean:

| State | Meaning in this map |
| --- | --- |
| `complete` | The mapped native and PA surfaces are present for the audited slice, but later WNID tasks still need live evidence before final PASS. |
| `partial` | Native support exists, but PA lacks a first-class workflow, required evidence shape, audit/history integration, browser proof, or live configured dependency. |
| `blocked` | A real provider, MCP service, native endpoint, approval path, credential, workspace, or live data gap prevents the required WNID workflow. |

## README Intelligent Conversation Rows

The WeKnora README defines these six rows:

| README capability | README meaning |
| --- | --- |
| Intelligent Reasoning | ReACT progressive multi-step reasoning, autonomously orchestrating knowledge retrieval, MCP tools, and web search; custom agent support. |
| Quick Q&A | RAG-based Q&A over knowledge bases for fast and accurate answers. |
| Wiki Mode | Agent-driven auto-generation of structured, interlinked markdown Wiki pages from raw documents. |
| Tool Calling | Built-in tools, MCP tools, web search. |
| Conversation Strategy | Online Prompt editing, retrieval threshold tuning, multi-turn context awareness. |
| Suggested Questions | Auto-generated question suggestions based on knowledge base content. |

## Parity Matrix

| README row | Native WeKnora surfaces | Current PA surfaces | State | Gap and next WNID task |
| --- | --- | --- | --- | --- |
| Intelligent Reasoning | `internal/handler/session/qa.go` exposes `/sessions/{session_id}/agent-qa`; `internal/application/service/session_agent_qa.go` builds AgentQA config and loads multi-turn history; `internal/application/service/agent_service.go` registers RAG, Wiki, MCP, Web Search, Web Fetch, data, thinking, and final-answer tools; `internal/handler/session/agent_stream_handler.go` persists thinking/tool/reference/answer/approval SSE events; `client/agent.go` exposes `AgentQAStreamWithRequest`. | `backend/app/api/analysis.py` exposes `/api/analysis/native-agentqa`; `backend/app/services/native_agent_service.py` creates PA conversation/task/output/history and saves citations from native references; `knowledge_engine/backends/weknora_api_backend.py` calls `/api/v1/agent-chat/{session_id}` and normalizes answer, references, event counts, and tool names; `frontend/src/pages/AnalysisPage.tsx` renders a hidden advanced AgentQA panel. | `partial` | AgentQA exists but is not a first-class dialogue workspace, MCP execution is not proven, Web Search references are not structured as provider/url/title/snippet/rank evidence, and strategy/run trace is summarized rather than fully inspectable. Next: `WNID-P1-01`, `WNID-P2-02`, `WNID-P3-02`, `WNID-P4-02`, `WNID-P7-01`. |
| Quick Q&A | `internal/handler/session/qa.go` exposes `/sessions/{session_id}/knowledge-qa`; `internal/application/service/session_knowledge_qa.go` emits answer and references events; `internal/application/service/chat_pipeline/*` covers search, rerank, top-k filtering, history merge, Wiki boost, and web fetch; `internal/types/retrieval_config.go` defines tenant retrieval thresholds. | `backend/app/api/rag.py` exposes `/api/rag/knowledge-chat`; `backend/app/services/native_chat_service.py` persists conversations, outputs, citations, and current-run guards; `knowledge_engine/backends/weknora_api_backend.py` calls `/api/v1/knowledge-chat/{session_id}`; `frontend/src/api/client.ts` has `runNativeKnowledgeChat`; Analysis/RAG debug/History pages expose citations and history. | `partial` | Core native path and PA persistence exist, but Quick Q&A is not yet launched from a first-class WNID dialogue shell with selected scope, strategy summary, trace, citation blockers, and browser proof. Next: `WNID-P1-01`, `WNID-P1-02`, `WNID-P7-01`, `WNID-P8-01`. |
| Wiki Mode | `internal/handler/wiki_page.go` exposes Wiki pages/index/log/graph/stats/issues/search/rebuild-links/lint/auto-fix routes; `internal/application/service/wiki_ingest.go` performs Agent/LLM-backed raw-document to Wiki ingestion; `internal/application/service/wiki_page.go` manages pages, graph, stats, issues, links, and search; `internal/agent/tools/wiki_*.go` exposes read/search/write/replace/rename/delete/source-doc/issue tools to AgentQA. | `knowledge_engine/backends/weknora_api_backend.py` maps native Wiki browse/search/read/mutate/status APIs; `backend/app/api/wiki.py` and `backend/app/services/wiki_service.py` expose PA Wiki management with audit and citation locators; `frontend/src/pages/WikiPage.tsx` and `HistoryPage.tsx` expose Wiki browsing and citation location. | `partial` | Native Wiki and PA Wiki management are strong, but WNID requires an Agent-driven Wiki Mode dialogue workflow that can generate, maintain, and reference Wiki pages from the dialogue shell with safe mutation controls and locatable Wiki citations. Next: `WNID-P5-01`, `WNID-P7-01`, `WNID-P8-01`. |
| Tool Calling | Built-in tools are registered in `internal/application/service/agent_service.go`; MCP service CRUD/tools/resources/approvals are in `internal/handler/mcp_service.go`, `internal/application/service/mcp_service.go`, `internal/application/service/mcp_tool_approval_service.go`, and `internal/types/mcp.go`; Web Search tool lives in `internal/agent/tools/web_search.go`; Web Search provider CRUD/test/credentials live in `internal/handler/web_search*.go`, `internal/application/service/web_search*.go`, and `internal/types/web_search_provider.go`. | `backend/app/services/mcp_service.py` exposes service CRUD, masked credentials, safe test, tools/resources status, approval flags, and explicit tool-execution blocker; `backend/app/services/web_search_service.py` exposes provider types/list/detail/test status and explicit AgentQA dependency status; `frontend/src/pages/CapabilityCenterPage.tsx` surfaces MCP/Web Search status. | `blocked` | MCP final PASS needs a configured safe MCP service with real tool/resource list and approval-gated execution or denial. Web Search final PASS needs a configured/tested provider and AgentQA run with traceable web references. Current PA map records status and blockers, not execution proof. Missing items: safe live MCP service/tool and Web Search provider credential or approved no-credential provider config. Next: `WNID-P3-01`, `WNID-P3-02`, `WNID-P4-01`, `WNID-P4-02`, `WNID-P7-01`. |
| Conversation Strategy | `internal/types/custom_agent.go` and `client/agent_manage.go` expose `system_prompt`, `context_template`, `allowed_tools`, `mcp_selection_mode`, `mcp_services`, `web_search_enabled`, `web_search_provider_id`, `web_fetch_enabled`, `web_fetch_top_n`, `multi_turn_enabled`, `history_turns`, `embedding_top_k`, `keyword_threshold`, `vector_threshold`, `rerank_top_k`, `rerank_threshold`, and `suggested_prompts`; `internal/handler/custom_agent.go` exposes agents CRUD, placeholders, type presets, and suggested questions; `internal/application/service/custom_agent.go` persists custom Agent config. | `backend/app/services/native_agent_service.py` exposes list/create/update/copy/delete with confirmation and audit, but `_agent_payload` forces `web_search_enabled=false`; PA only summarizes safe agent fields and does not expose a full strategy editor. | `partial` | Native strategy fields exist, but PA lacks online editing for the full WNID field set, safe raw prompt handling, Web Search/MCP selection, retrieval thresholds, multi-turn/history controls, and mutation audit UX for each strategy change. Next: `WNID-P2-01`, `WNID-P4-01`, `WNID-P3-01`, `WNID-P7-01`. |
| Suggested Questions | `internal/handler/custom_agent.go` exposes `/agents/{id}/suggested-questions`; `internal/application/service/custom_agent.go` combines `suggested_prompts`, KB document generated questions, and Wiki-derived suggestions; `client/agent_manage.go` exposes `GetSuggestedQuestions`. | `backend/app/services/native_agent_service.py` fetches suggested questions in `native_agent_catalog`; `backend/app/schemas.py` and `frontend/src/api/client.ts` define suggested question shapes, but `frontend/src/pages/AnalysisPage.tsx` does not render or launch suggestions. | `partial` | Native endpoint and PA BFF catalog field exist, but PA lacks visible suggested-question chips, empty/blocked states, source labels, and click-to-run into live Quick Q&A or AgentQA. Next: `WNID-P6-01`, `WNID-P1-01`, `WNID-P7-01`. |

## Native Source Map

| Area | Routes, services, types, clients checked | Key mapped contract |
| --- | --- | --- |
| README table | `README.md` | Six Intelligent Conversation rows listed above. |
| AgentQA and session chat | `internal/handler/session/qa.go`; `internal/application/service/session_agent_qa.go`; `internal/application/service/agent_service.go`; `internal/handler/session/agent_stream_handler.go`; `internal/types/session.go`; `internal/types/agent.go`; `client/agent.go` | `/api/v1/agent-chat/{session_id}` and `/api/v1/knowledge-chat/{session_id}` SSE paths; request fields for `agent_id`, KB/file scope, `web_search_enabled`, and session last-request state; SSE response types for thinking/tool/references/answer/error/approval. |
| Custom Agent and suggestions | `internal/handler/custom_agent.go`; `internal/application/service/custom_agent.go`; `internal/types/custom_agent.go`; `client/agent_manage.go` | Agent CRUD/copy/list/read, placeholders, type presets, suggested questions, and the full strategy field set needed by WNID. |
| MCP | `internal/handler/mcp_service.go`; `internal/application/service/mcp_service.go`; `internal/application/service/mcp_tool_approval_service.go`; `internal/types/mcp.go`; `client/mcp_service.go` | Service CRUD/test, tools/resources list, per-tool approval flags, pending approval resolution, masked credential subresource. Native prompt list/read API was not found in the checked MCP handler/service/client surface. |
| Web Search | `internal/handler/web_search.go`; `internal/handler/web_search_provider.go`; `internal/handler/web_search_provider_credentials.go`; `internal/application/service/web_search.go`; `internal/application/service/web_search_provider.go`; `internal/application/service/web_search_state.go`; `internal/types/web_search.go`; `internal/types/web_search_provider.go`; `client/web_search.go`; `internal/agent/tools/web_search.go` | Provider type/list/read/create/update/delete/test/credential paths; Agent web_search and web_fetch tools; provider resolution and RAG compression path. |
| Wiki | `internal/handler/wiki_page.go`; `internal/application/service/wiki_ingest.go`; `internal/application/service/wiki_page.go`; `internal/application/service/wiki_lint.go`; `internal/application/service/wiki_linkify.go`; `internal/types/wiki_page.go`; `internal/agent/tools/wiki_*.go`; `internal/agent/prompts_wiki.go` | Wiki page CRUD, index/log/graph/stats/search/issues/lint/rebuild/auto-fix plus Agent tools for read/search/write/update/delete/source-doc/issue workflows. |
| Knowledge-chat and retrieval | `internal/application/service/session_knowledge_qa.go`; `internal/application/service/chat_pipeline/*`; `internal/application/service/knowledgebase_search*.go`; `internal/types/retrieval_config.go`; `internal/agent/tools/knowledge_search.go`; `internal/agent/tools/list_knowledge_chunks.go`; `client/knowledge.go` | Native RAG answer stream with references, retrieval config thresholds, rerank/top-k, history merge, Wiki boost, and Agent knowledge tools. |

## PA Surface Map

| PA area | Files checked | Current mapped surface |
| --- | --- | --- |
| Native adapter | `knowledge_engine/backends/weknora_api_backend.py` | Calls native agents, suggested questions, AgentQA, knowledge-chat, MCP, Web Search, Wiki, and normalizes safe public responses. AgentQA currently stores answer, references, event counts, tool names, and citation evidence. |
| BFF APIs | `backend/app/api/analysis.py`; `backend/app/api/rag.py`; `backend/app/api/mcp.py`; `backend/app/api/web_search.py`; `backend/app/api/wiki.py`; `backend/app/api/history.py`; `backend/app/api/citations.py`; `backend/app/api/native_audit.py`; other `backend/app/api/*` were searched for WNID keywords. | AgentQA, knowledge-chat, MCP overview/detail/test/mutations, Web Search overview/detail/test, Wiki browse/mutations, history, citations, and audit endpoints exist. |
| Services | `backend/app/services/native_agent_service.py`; `backend/app/services/native_chat_service.py`; `backend/app/services/mcp_service.py`; `backend/app/services/web_search_service.py`; `backend/app/services/wiki_service.py`; `backend/app/services/history_service.py`; `backend/app/services/citation_locator_service.py`; `backend/app/services/native_audit_service.py`; other `backend/app/services/*` were searched for WNID keywords. | Conversation/output/citation persistence is present for AgentQA and knowledge-chat. Native mutation audit exists for risky native changes. MCP and Web Search services expose blockers truthfully. |
| Schemas and client | `backend/app/schemas.py`; `frontend/src/api/client.ts` | Types exist for Native Agent catalog/run, knowledge-chat, MCP/Web Search overview, citations, history, and audit. Suggested questions are typed but not rendered as a runnable workflow. |
| Frontend pages | `frontend/src/pages/AnalysisPage.tsx`; `frontend/src/pages/HistoryPage.tsx`; `frontend/src/pages/WikiPage.tsx`; `frontend/src/pages/RagDebugPage.tsx`; `frontend/src/pages/CapabilityCenterPage.tsx`; `frontend/src/pages/LibraryPage.tsx`; `frontend/src/pages/HomePage.tsx` | Analysis has normal analysis and hidden advanced AgentQA; History exposes native AgentQA filters and citation blockers; Wiki and Capability Center expose native status. No first-class WNID dialogue shell yet. |
| Check scripts | `backend/scripts/check_weknora_*`; `backend/scripts/smoke_weknora_*` | Existing WNX/WNFC scripts prove prior non-WNID capabilities and explicit MCP/Web Search blockers. A WNID acceptance harness is still absent and belongs to `WNID-0-03`. |

## Blockers And Exact Requests

The map found these user-action or environment blockers for later WNID tasks:

| Blocker | Needed from user or environment | Used by |
| --- | --- | --- |
| Safe live MCP service/tool | Provide or authorize one low-risk MCP service config with at least one harmless tool, expected approval policy, and whether execution or denial should be proven first. | `WNID-P3-01`, `WNID-P3-02` |
| Native MCP prompt list/read gap | If prompt support is required for final WNID MCP parity, provide the desired native endpoint contract or approve a controlled native exception task after `WNID-P3-01` confirms absence. | `WNID-P3-01` |
| Web Search provider readiness | Provide a configured provider credential or approved no-credential provider setup such as a reachable SearXNG instance, plus permission to run the native provider test. | `WNID-P4-01`, `WNID-P4-02` |
| Web Search answer references | If native AgentQA only emits web tool output without structured references, approve a native exception task for provider/url/title/snippet/rank evidence propagation. | `WNID-P4-02`, `WNID-P7-01` |
| First-class dialogue shell | No external credential needed; requires PA product implementation and browser validation. | `WNID-P1-01`, `WNID-P8-01` |

## Proposed Follow-Up Task Precision

The existing WNID task board is directionally correct. This map refines the
task boundaries as follows:

| Task | Precision from WNID-0-02 |
| --- | --- |
| `WNID-P1-01` | Promote native dialogue out of the hidden Analysis advanced panel into a first-class workspace with Agent picker, run controls, selected KB/file scope, strategy summary, tool trace, citations, history, and suggested question entry. |
| `WNID-P1-02` | Wire Quick Q&A from that workspace through `/api/rag/knowledge-chat`, preserving current-run/citation blockers and selected native scope. |
| `WNID-P2-01` | Implement a full custom Agent strategy editor for prompt/context templates, tools, MCP selection, Web Search/Web Fetch, multi-turn/history, retrieval thresholds, rerank thresholds, KB/file scope, and suggested prompts. |
| `WNID-P2-02` | Expand AgentQA run evidence from summary counts into inspectable thinking/tool/result/reference/answer events with selected Agent config and PA conversation continuity. |
| `WNID-P3-01` | Prove MCP tools/resources read path with a real service or record exact service/prompt API blocker; do not count service CRUD alone. |
| `WNID-P3-02` | Prove approval-gated MCP tool execution or denial with audit/history, timeout/error class, and no raw secret leakage. |
| `WNID-P4-01` | Implement/validate masked Web Search provider create/update/credential/test, or record the exact provider credential/config blocker. |
| `WNID-P4-02` | Prove native AgentQA with `web_search_enabled=true` and structured web references; add native exception only if WeKnora lacks the reference shape. |
| `WNID-P5-01` | Prove Wiki Mode from Agent dialogue, not only Wiki admin pages, including generation/maintenance/reference and safe mutation controls. |
| `WNID-P6-01` | Render native suggested questions and launch one into a live dialogue run with source labels and empty/blocked states. |
| `WNID-P7-01` | Unify history/citation/audit for AgentQA, Quick Q&A, Wiki Mode, MCP, Web Search, and strategy mutations with evidence-state filters. |
| `WNID-P8-01` | Browser matrix for the WNID dialogue workspace across desktop/mobile. |
| `WNID-P8-02` | Final WNID PASS report after the acceptance harness and all live evidence are current. |

## Validation Plan For This Task

This task should be validated with:

```bash
git diff --check -- docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md
rg -n "T[O]DO|\[T[O]DO|BEGIN (RSA|OPENSSH|PRIVATE) KEY|[A-Za-z0-9_]*(API_KEY|SERVICE_TOKEN|PASSWORD|SECRET|AUTHORIZATION)[A-Za-z0-9_]*\s*=" docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md
```

The `rg` command is expected to return no matches.
