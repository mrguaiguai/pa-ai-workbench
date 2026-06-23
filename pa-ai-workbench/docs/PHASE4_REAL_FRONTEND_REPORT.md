# Phase 4 Real Frontend Acceptance Report

## Test Metadata

| Field | Value |
| --- | --- |
| Task | P4-G6 frontend Chinese terminology and real-status display acceptance |
| Test time | 2026-06-15 17:22:42 CST |
| Test environment | Local PA AI Workbench frontend source/build inspection plus backend service-layer status probe |
| Backend source | `weknora_api` |
| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; chat provider `openai_compatible`; embedding provider `mock`; WeKnora config present; token and endpoint intentionally omitted |
| Test scope | 首页, 资料库, RAG 调试, Wiki, 知识问答 |
| Test result / 测试结果 | PARTIAL / 部分通过 |

## Validation Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript check | PASS | Ran bundled Node equivalent of `tsc --noEmit` successfully |
| Frontend production build | PASS | Ran bundled Node equivalent of `vite build`; output generated under `frontend/dist` |
| Backend HTTP availability | PARTIAL | Local HTTP backend was not already running during this report, so browser-level API calls were not counted as live |
| Backend service-layer status | PARTIAL | Service-layer probe returned `knowledge_backend=weknora_api`, `mock_mode=False`, `weknora.status=unavailable`, `weknora.configured=True` |
| Capability status | PASS with risk | Capability snapshot reported active backend `weknora_api`, `can_debug_retrieve=True`, and `can_use_real_citations=True`; health was still unavailable |
| Model status | PARTIAL | Chat was non-mock `openai_compatible`; embedding provider was `mock`, so frontend model cards must not imply full real embedding |
| Browser screenshot | NOT CAPTURED | Browser automation was unavailable in this tool session; this report uses source/build-derived visible text evidence |

## Page Matrix

| Page | Checks | Chinese terminology | Real-status distinction | Result | Text evidence summary |
| --- | --- | --- | --- | --- | --- |
| 首页 | Navigation, runtime cards, backend badge, metrics | PARTIAL | PARTIAL | PARTIAL | Navigation uses `首页`, `资料库`, `智能分析`, `RAG 调试`, `Wiki`, `历史`; runtime cards still show `Chat Model`, `Embedding`, `RAG Pipeline`, `Capability`, `Agent Workflows`, `Workspace`; status strings include `weknora unavailable`, `mock fallback`, `configured`, `missing config`, `dev only` |
| 资料库 | Upload, filters, document pipeline, index readiness | PARTIAL | PASS with wording risk | PARTIAL | Major workflow labels use `上传资料`, `总资料`, `已索引`, `处理中`, `失败`, `解析`, `分块`, `索引`, `可提问`; remaining English includes `Upload`, `Documents`, `Chunks`, `uploaded`, `processing`, `indexed`, `failed`, `unavailable`, `mock`, `extracted`, `embedding` |
| RAG 调试 | Debug controls, source filters, evidence trace | FAIL for Chinese terminology; PASS for debug separation | PASS | PARTIAL | Page is correctly isolated as `RAG 调试`; advanced controls remain on debug page only. Visible controls still use `Query`, `Top K`, `Source`, `Document IDs`, `KB ID`, `Business`, `Document Type`, `Run`, `Reset`, `No evidence`, `Debug unavailable`, `Score unavailable` |
| Wiki | Search/read/edit/publish/index state, citation source type | PARTIAL | PASS | PARTIAL | Wiki state can distinguish `草稿不可检索`, `索引中`, `未进入 RAG`, `同步失败`, `可被 RAG 检索`; publish risks prevent treating draft/not-indexed pages as searchable. Remaining English includes `Search`, `Pages`, `Reader`, `Editor`, `Publish confirmation`, `source refs`, `bindings`, `status`, `Score unavailable`, and citation labels `Document`, `Wiki`, `Mock`, `Evidence` |
| 知识问答 | Workflow selector, answer area, evidence summary, citations | PARTIAL | PARTIAL | PARTIAL | Task labels are Chinese (`知识问答`, `政策分析`, `案例复盘`), inputs use `问题或主题`, `标题`, `业务域`, `资料类型`, `额外要求`; evidence area still shows `Conversations`, `Messages`, `Workflow`, `Wiki Draft`, `Evidence`, `Real WeKnora RAG`, `Mock fallback`, `Document`, `Total`, `ready`, `locatable`, `not locatable` |

## Real Status Display Findings

| Area | Finding | Impact |
| --- | --- | --- |
| Backend badge | 首页 reads backend and model status from `/api/status` and `/api/model/status`, then shows `weknora connected`, `weknora unavailable`, `missing config`, `mock fallback`, or `real ready`. | Good separation exists, but labels are English-heavy and can confuse Chinese users. |
| WeKnora health | Service-layer status during this run was `weknora.status=unavailable` with config present. | Frontend must show unavailable/health failure, not merely `weknora_api` as usable. |
| Model status | Chat provider is real non-mock, but embedding provider is mock. | 首页 model cards should make partial real/mock status more obvious in Chinese. |
| Document index state | 资料库 distinguishes `已索引`, `索引中`, `失败`, `超时`, and `可提问`. | Good workflow state coverage; English raw statuses in filters should be localized. |
| Wiki publish/index state | Wiki page has explicit RAG availability labels and publish warnings. | Strongest page for not mixing draft/published/not-indexed/retrievable state. |
| QA evidence state | 知识问答 distinguishes document/wiki/WeKnora counts and shows `依据不足或引用需要复核`. | Good high-level signal, but labels such as `Real WeKnora RAG` and `Mock fallback` should be localized. |
| RAG debug isolation | RAG debug exposes raw filters, source type, evidence id, chunk id, wiki page id, and metadata only on the debug page. | Matches Phase 4 boundary: normal QA page does not expose all raw debug controls. |

## Risk Diagnosis

| Risk | Status | Notes |
| --- | --- | --- |
| English terminology in normal pages | FAIL | 首页, 资料库, Wiki, and 知识问答 still include English headings and state labels. |
| Debug controls exposed in normal QA | Controlled | Advanced fields such as `top_k`, `KB ID`, `Document IDs`, and raw metadata are kept in RAG 调试 / Wiki debug contexts. |
| Mock/fallback status hidden | PARTIAL | UI has mock/fallback fields, but many are English and easy to under-read; embedding was mock during this run. |
| Not-indexed Wiki treated as searchable | Controlled | Wiki page has separate labels for draft, indexing, not indexed, failed, and searchable. |
| Live browser evidence missing | PARTIAL | Build and source checks passed, but no browser screenshot was captured because browser automation was unavailable. |
| Backend local server not running | PARTIAL | The frontend build is valid, but a user opening the app without the backend service will see API errors rather than live status. |

## Improvement Recommendations / 改进建议

### RAG

- Localize RAG debug labels while preserving its engineer-facing role: `Query` -> `查询`, `Top K` -> `返回数量`, `Source` -> `来源范围`, `Run` -> `运行检索`, `Reset` -> `重置`.
- Keep evidence identifiers visible on RAG 调试, but add Chinese labels for `source_type`, `evidence_id`, `chunk_id`, `wiki_page_id`, and `external_doc_id`.
- Add a concise Chinese warning when `weknora.status=unavailable` so users do not mistake configured WeKnora for connected WeKnora.

### Wiki

- Localize publish and citation panels: `Publish confirmation`, `source refs`, `bindings`, `status`, `Score unavailable`, and `Evidence`.
- Preserve current state separation for `草稿不可检索`, `未进入 RAG`, `索引中`, `同步失败`, and `可被 RAG 检索`; this is the correct behavior for Phase 4.
- Show whether a retrieved Wiki item is a published user page, an auto-generated page, or a document-derived summary.

### QA

- Replace normal QA labels such as `Evidence`, `Real WeKnora RAG`, `Mock fallback`, `Document`, `Total`, `ready`, `locatable`, and `not locatable` with Chinese equivalents.
- For insufficient evidence, keep the existing Chinese warning but make it visible before the citation list, not only inside the side panel.
- Make partial real/mock status clearer: chat can be real while embedding or evidence can still be mock/fallback.

### Frontend

- Replace topbar/page eyebrow English labels (`Overview`, `Library`, `Analysis`, `Retrieve Debug`, `History`) with Chinese labels or remove them.
- Replace status values in filters (`uploaded`, `processing`, `indexed`, `failed`, `unavailable`, `mock`, `extracted`) with Chinese display labels while preserving API values internally.
- Add an acceptance screenshot workflow once browser automation is available, covering desktop and narrow viewport.

### Config / Ops

- Start the local backend service before manual frontend acceptance so `/api/status`, document lists, Wiki search, and QA calls are visible in the browser.
- Keep service tokens, endpoints, uploaded files, databases, and raw provider payloads out of frontend reports.
- Record whether a frontend report used source/build evidence, browser screenshots, or both; this run used source/build evidence only.
