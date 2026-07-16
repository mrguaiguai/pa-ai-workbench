# WeKnora RAG / Wiki Source Map

审计日期：2026-06-03

本文件是 PHASE2 G1 的源码审计产物。审计范围限于外层 WeKnora 源码的 RAG / Wiki / Embedding / Chat pipeline 相关模块；本轮不写 PA AI Workbench 产品实现代码，不修改外层 WeKnora 原项目源码。

## Scope

优先审计路径：

- `../internal/infrastructure/chunker/`
- `../internal/application/service/retriever/`
- `../internal/application/service/chat_pipeline/`
- `../internal/application/service/knowledge_process.go`
- `../internal/application/service/knowledge_post_process.go`
- `../internal/application/service/knowledgebase_search*.go`
- `../internal/application/service/wiki_ingest*.go`
- `../internal/application/service/wiki_page.go`
- `../internal/types/chunk.go`
- `../internal/types/retriever.go`
- `../internal/types/retrieval_config.go`
- `../internal/types/wiki_page.go`
- `../internal/types/search.go`
- `../internal/types/embedding.go`
- `../internal/types/interfaces/retriever.go`
- `../internal/types/interfaces/wiki_page.go`
- `../internal/models/embedding/`

## Executive Decision

G1 结论：

- 不直接复制整套 WeKnora backend。WeKnora 的实现深度绑定 Go、GORM、asynq、Redis、多租户、RBAC、多向量库注册和现有 handler/service 类型。
- Chunker、Retriever abstraction、Knowledge indexing/search、Wiki page / ingest / Citation 的工程思路值得参考，但应在 PA AI Workbench 中 Python 化、自建简化实现。
- Embedding adapters 不直接剥离。PA 第二阶段应实现自己的 `EmbeddingProvider`，先支持 mock 与 OpenAI-compatible provider。
- Chat pipeline 不迁移。只参考“query understanding -> search -> merge/rerank -> prompt render -> model completion -> evidence persistence”的流程形状，落到 PA 自己的 Agent runtime / tools。
- 多租户、RBAC、IM、外部数据源、GraphRAG、十多个向量数据库适配器、WeKnoraCloud provider 暂不剥离。

## Source Module Map

| Source module | Responsibility | Key structs / functions / interfaces | Dependencies and risks | Extraction decision | Target PA module |
| --- | --- | --- | --- | --- | --- |
| `../internal/infrastructure/chunker/` | 文档文本切分，保护 Markdown/code/table/image/link/LaTeX span，保留 offset，支持 heading/heuristic/recursive/legacy 策略和 diagnostics。 | `Chunk`, `SplitterConfig`, `Split`, `SplitWithDiagnostics`, `SplitParentChild`, `HeadingHierarchy`, `DocProfile`, `splitByStrategy`, `splitByHeading`, `splitByHeuristic`。 | 依赖 Go rune offset、regex、`docparser` 常量；需小心中文/英文混排、表格/代码块、标题层级、overlap 与 offset 对齐。 | Reference + Python rewrite。保留策略分层、protected span、breadcrumb context、diagnostics 思路，不复制 Go 文件。 | `knowledge_engine/chunking/` |
| `../internal/types/chunk.go` | 持久化 chunk schema 与 chunk 类型枚举；支持 parent-child、relation chunks、image info、metadata、context header。 | `Chunk`, `ChunkTypeText`, `ChunkTypeParentText`, `ChunkTypeWikiPage`, `ChunkStatusStored`, `ChunkStatusIndexed`, `Chunk.EmbeddingContent()`。 | WeKnora schema 面向大平台，字段多，含 tenant/tag/image/relation/FAQ；PA P0 不需要完整复制。 | Reference + self-built schema。仅吸收 `content`, `source`, `chunk_index`, `start/end`, `parent`, `metadata`, `wiki` source 这些必要字段。 | `knowledge_engine/chunking/`, `knowledge_engine/retrieval/`, backend DB models |
| `../internal/types/embedding.go` | 索引输入与命中类型。 | `SourceType`, `MatchType`, `IndexInfo`。 | 与 WeKnora chunk/knowledge/kb/tag 模型强耦合；PA 需要自己的 document/wiki/output IDs。 | Reference + Python rewrite。保留 source type / match type 概念，字段简化。 | `knowledge_engine/citations/`, `knowledge_engine/vectorstores/` |
| `../internal/models/embedding/` | 多 provider embedding 适配、批处理、debug/langfuse wrapper。 | `Embedder`, `EmbedderPooler`, `Config`, `ConfigFromModel`, `NewEmbedder`, `OpenAIEmbedder`, `AzureOpenAIEmbedder`, `OllamaEmbedder`, `BatchEmbedWithPool`。 | provider 分支多，携带 API Key/BaseURL/custom headers；存在 provider 特有请求格式和维度处理。不能把任何真实凭证带入仓库。 | Do not copy。只参考接口形状、batch embedding、维度一致性、输入截断/重试；PA 实现自己的 `EmbeddingProvider`。 | `knowledge_engine/embeddings/` |
| `../internal/application/service/retriever/` | Retriever service 层，封装 engine registry、store binding、composite fan-out、hybrid indexing、score normalization。 | `RetrieveEngineRegistry`, `CompositeRetrieveEngine`, `KeywordsVectorHybridRetrieveEngineService`, `EngineAwareNormalizer`, `CreateRetrieveEngineForKB`, `VerifyBinding`, `sanitizeForEmbedding`, `batchEmbedWithBackoff`。 | 深度依赖 tenant context、vector store registry、WeKnora interfaces、logger/tracing；composite 多 store 并发对 PA P0 过重。 | Reference + Python rewrite。P0 做单本地 VectorStore + Retriever；P1 再引入 hybrid / RRF / multi-store。 | `knowledge_engine/retrieval/`, `knowledge_engine/vectorstores/` |
| `../internal/types/retriever.go` and `../internal/types/interfaces/retriever.go` | Retriever 领域抽象、检索参数、检索结果、索引/删除/复制接口。 | `RetrieverEngineType`, `RetrieverType`, `RetrieveParams`, `IndexWithScore`, `RetrieveResult`, `RetrieveEngineService`, `RetrieveEngineRepository`, `RetrieveEngineRegistry`。 | 接口覆盖多引擎、多 KB、tag、tenant、copy indices；PA 初期只需 query/filter/top_k/threshold/result metadata。 | Reference + Python rewrite。保留 `Retriever`、`VectorStore`、`RetrieveResult` 三层概念。 | `knowledge_engine/retrieval/`, `knowledge_engine/vectorstores/` |
| `../internal/types/retrieval_config.go` | 检索阈值、top-k、rerank、RRF 参数默认值。 | `RetrievalConfig`, `GetEffectiveEmbeddingTopK`, `GetEffectiveRRFK`, `GetEffectiveRRFWeights`。 | 阈值与 WeKnora 多引擎分数分布相关，不能照搬为 PA 默认值。 | Reference。采用配置项思路；具体默认值在 PA 自测后确定。 | `knowledge_engine/retrieval/` |
| `../internal/application/repository/retriever/*` | Postgres/SQLite/Qdrant/Milvus/Weaviate/OpenSearch/Doris/TencentVectorDB/Elasticsearch/Neo4j 等检索存储适配。 | 各仓库的 `Save`, `BatchSave`, `Retrieve`, delete/update/copy 方法。 | 外部依赖重，部署与配置成本高；Neo4j/GraphRAG 属 P2；直接迁移会扩大第二阶段范围。 | Skip for G/H P0。仅把 query/filter/schema 经验作为参考；未来确需特定后端时再单独审计。 | `knowledge_engine/vectorstores/` later only |
| `../internal/application/service/knowledge_process.go` | 文档处理主链路：解析文档、构建 splitter config、生成 chunks、保存 chunk、生成 embedding、索引、状态流转、summary/question 任务。 | `ProcessChunksOptions`, `buildSplitterConfig`, `buildParentChildConfigs`, `processChunks`, `updateChunkVector`, `ProcessDocument`, `ProcessManualUpdate`, `ProcessSummaryGeneration`, `ProcessQuestionGeneration`。 | 依赖 asynq、docreader、knowledge repo、chunk repo、model service、FAQ/question generation、image/OCR，多数超出 PA P0。 | Reference + Python rewrite of flow only。P0 实现 parse -> chunk -> embed -> index -> status；summary/question/image pipeline 暂不剥离。 | `knowledge_engine/parsers/`, `knowledge_engine/chunking/`, `knowledge_engine/backends/extracted_backend.py` |
| `../internal/application/service/knowledge_post_process.go` | 文档处理后的异步后处理，触发 summary/question/wiki 等任务。 | `KnowledgePostProcessService`, `Handle`, `enqueueSummaryGenerationTask`, `enqueueQuestionGenerationTasks`。 | 与 WeKnora task queue、span tracker、summary/question generator 强耦合。 | Reference only。PA 可在后续任务中做同步或轻量后台任务，不迁移 asynq 架构。 | backend task orchestration later |
| `../internal/application/service/knowledgebase_search*.go` | RAG 检索入口：query embedding、KB 分组、multi-store fan-out、vector/keyword 参数构建、RRF 融合、FAQ 后处理、上下文 enrichment、SearchResult 组装。 | `HybridSearch`, `GetQueryEmbedding`, `ResolveEmbeddingModelKeys`, `buildRetrievalParams`, `retrieveFromStores`, `classifyRetrievalResults`, `fuseOrDeduplicate`, `fuseWithRRF`, `processSearchResults`, `assembleSearchResults`。 | 跨租户共享 KB、混合 embedding model 校验、store group、多引擎 score normalization 都是平台复杂度；PA P0 可先单 KB / 单 embedding space。 | Reference + Python rewrite。P0 vector retrieval + evidence assembly；P1 hybrid keyword + RRF + rerank。 | `knowledge_engine/retrieval/`, `knowledge_engine/citations/` |
| `../internal/types/search.go` | 搜索目标、SearchResult、SearchParams 和分页结构。 | `SearchTarget`, `SearchTargets`, `SearchResult`, `SearchParams`。 | SearchResult 包含 WeKnora knowledge/channel/image/FAQ 字段；PA 需要面向文档、wiki、analysis output 的统一 evidence。 | Reference + self-built Citation schema。保留 score、match_type、source id、chunk index、start/end、metadata。 | `knowledge_engine/citations/`, backend API schemas |
| `../internal/types/wiki_page.go` | Wiki 页面领域模型、页面状态、配置、图谱/统计/list schema。 | `WikiPage`, `WikiPageStatusDraft`, `WikiPageStatusPublished`, `WikiPageStatusArchived`, `WikiConfig`, `WikiExtractionGranularity`, `WikiPageListRequest`, `WikiGraphData`, `WikiPageIssue`, `WikiIndexResponse`。 | WeKnora Wiki 默认多类型页面与图谱/issue/stats，PA 第二阶段只要求 draft/publish/read/search/retrieve。 | Reference + self-built CRUD schema。保留 `slug`, `title`, `status`, `markdown`, `source_refs`, `chunk_refs`, `version`。 | `knowledge_engine/wiki/`, backend DB models |
| `../internal/application/service/wiki_page.go` | Wiki CRUD、link parsing、in/out links、index/log pages、graph/stats、search、issue、cross-link injection。 | `wikiPageService`, `CreatePage`, `UpdatePage`, `GetPageBySlug`, `ListPages`, `DeletePage`, `GetIndexView`, `GetGraph`, `SearchPages`, `InjectCrossLinks`, `parseOutLinks`。 | 与 GORM repo、Redis、task pending、chunk deletion、KB service 绑定；graph/stats/issue 不是 PA P0 必需。 | Reference + Python rewrite。P0 自建 draft/publish CRUD、search、published page indexing；link graph 和 lint/auto-fix 暂后置。 | `knowledge_engine/wiki/`, backend wiki APIs |
| `../internal/application/repository/wiki_page.go` and `../internal/handler/wiki_page.go` | Wiki DB repository 与 Gin HTTP handler。 | `WikiPageRepository`, `Create`, `Update`, `ListBySourceRef`, `Search`, `CountByType`, `WikiPageHandler.ListPages/CreatePage/GetPage/UpdatePage/DeletePage/SearchPages`。 | GORM/Gin 与 PA FastAPI/SQLModel 不兼容；handler auth/tenant 逻辑不可移植。 | Reference only。API shape 可参考，代码不迁移。 | backend FastAPI routers, `knowledge_engine/wiki/` |
| `../internal/application/service/wiki_ingest*.go` | LLM 驱动的 Wiki ingest：pending op、batch map/reduce、候选 slug、chunk Citation 分类、dedup、source/chunk refs、dead link cleanup、index/log rebuild。 | `WikiIngestPayload`, `WikiPendingOp`, `WikiBatchContext`, `SlugUpdate`, `mapOneDocument`, `extractCandidateSlugs`, `classifyChunkCitations`, `mergeCitationsIntoItems`, `resolveCitedChunks`, `reconstructEnrichedContent`, `rebuildIndexPage`, `publishDraftPages`。 | 依赖 asynq、Redis lock、dead letters、LLM prompt templates、chunk repo、knowledge repo、wiki repo；LLM 可能幻觉，需要 Citation checker 和人工发布门槛。 | Reference workflow + Python rewrite. PA 实现 output -> wiki draft、manual edit -> publish -> index；大规模 batch、dead letter、auto cross-link 后置。 | `knowledge_engine/wiki/`, `knowledge_engine/citations/`, `agent/tools/` |
| `../internal/application/service/wiki_ingest_cite.go` | Wiki chunk Citation pass：把候选 entity/concept slug 与具体 chunks 建立证据关系。 | `citationBatchResult`, `newSlugFromCitation`, `splitChunksIntoCitationBatches`, `classifyChunkCitations`, `resolveCitedChunks`, `collectCitedChunkContent`, `mergeCitationsIntoItems`。 | LLM 输出 JSON 解析不稳定；需要 alias -> real chunk ID 映射、防止引用未知 chunk、保证 chunk 顺序。 | Reference + Python rewrite。此处是 PA evidence workflow 的重点参考，应转成可测试的 CitationChecker / WikiCitation 逻辑。 | `knowledge_engine/citations/`, `agent/tools/` |
| `../internal/application/service/chat_pipeline/` | Chat 插件管线：query understand、search、parallel search、wiki boost、merge、neighbor expansion、rerank、prompt rendering、model completion、streaming、memory/web/data plugins。 | `Plugin`, `EventManager`, `PluginSearch`, `PluginSearchParallel`, `PluginWikiBoost`, `PluginMerge`, `PluginRerank`, `PluginIntoChatMessage`, `PluginChatCompletion`, `PluginQueryUnderstand`, `Extractor`, `Formater`。 | 与 WeKnora `ChatManage`, session/message/model/KB services 耦合；插件数量大且覆盖 PA 暂不需要的 web/data/memory/graph 能力。 | Do not migrate. Reference workflow only。PA Agent 必须经 `ModelGateway` 和 tools，不复刻 Go plugin pipeline。 | `agent/`, `agent/tools/`, `knowledge_engine/citations/` |

## Target PA Workbench Module Map

| PA target | G1 extraction guidance |
| --- | --- |
| `knowledge_engine/parsers/` | 参考 `knowledge_process.go` 的 parse -> chunk -> index 流程，但解析器在 H2 自建 PDF/DOCX/TXT/MD。 |
| `knowledge_engine/chunking/` | Python 化 WeKnora chunker 的分层策略。H3 先实现稳定 paragraph/heading splitter，再逐步补 protected span 和 diagnostics。 |
| `knowledge_engine/embeddings/` | 自建 `EmbeddingProvider`。G6/G7/G8 实现 mock 与 OpenAI-compatible；不得绕过 provider 直接调外部 embedding API。 |
| `knowledge_engine/vectorstores/` | P0 本地向量存储；不迁移 WeKnora 多引擎 repository。后续如果引入 Qdrant/Postgres，再单独设计 adapter。 |
| `knowledge_engine/retrieval/` | 自建 `Retriever`、`RetrieveRequest`、`RetrieveResult`、score/threshold/top-k；P1 再实现 keyword/RRF/rerank。 |
| `knowledge_engine/citations/` | 自建 Citation/Evidence schema，支持 chunk 和 wiki page 两种来源，保留 source id、chunk id、score、span、metadata。 |
| `knowledge_engine/wiki/` | 自建 WikiPage / WikiCitation / WikiStore / publish-index flow；参考 WeKnora `source_refs` 和 `chunk_refs`，不迁移 graph/stats/issue。 |
| `knowledge_engine/backends/extracted_backend.py` | 承接真实 parse/chunk/embed/index/retrieve/wiki 能力，对 backend 暴露统一 Knowledge Engine 接口。 |
| `agent/tools/` | 自建 `RealRetrieverTool`, `WikiReadTool`, `WikiDraftWriterTool`, `CitationChecker`；只参考 WeKnora chat/wiki workflow。 |
| backend FastAPI routers | API shape 可参考 WeKnora handler，但实现保持 FastAPI/SQLModel 风格。 |

## Extraction Decisions By Capability

| Capability | Extraction decision | Reason |
| --- | --- | --- |
| Chunker | Python rewrite | 逻辑相对独立，适合变成 PA 可测试组件；Go 代码不直接复制。 |
| Retriever abstraction | Python rewrite | PA 需要更小的接口面；WeKnora 多租户/多 store registry 过重。 |
| Hybrid search | Reference, P1 | RRF 和 dedup 值得保留，但 P0 先保证真实 vector retrieval。 |
| Embedding adapters | Skip direct copy | PA 只做统一 `EmbeddingProvider`，避免复制 provider 分支与凭证处理逻辑。 |
| Citation / evidence | Python rewrite | Evidence workflow 是第二阶段核心，需要绑定 PA 数据模型和 agent outputs。 |
| Wiki page | Self-built CRUD | 参考 WeKnora model，不迁移 GORM/Gin/Redis。 |
| Wiki ingest | Reference workflow | PA 从 generated output 生成 draft，不先做大规模文档批处理 ingest。 |
| Chat pipeline | Reference only | PA 已有 Agent runtime，应保持自己的 orchestration 和 ModelGateway 边界。 |
| Vector DB adapters | Skip for P0 | 外部基础设施与配置复杂，超出 G/H P0。 |
| RBAC / tenant / IM / external sources | Skip | 与 PA 第二阶段真实 RAG/Wiki 闭环无直接关系。 |
| GraphRAG / Neo4j | Skip / P2 | PHASE2_SPEC 已明确后置。 |

## Risks And Notes

- Offset integrity: chunk `start/end` 必须在 Python 实现里自测，尤其是中文、emoji、Markdown 表格、代码块、标题上下文。
- Embedding dimension consistency: 同一 vector store 只能混用同维度、同语义空间的 embedding；WeKnora 的跨 KB 校验值得参考。
- Citation faithfulness: Wiki/Agent 输出必须引用真实 chunk 或 Wiki page。LLM 生成的 source ids 需要严格校验，不能信任模型直接返回的 UUID。
- Sensitive data: WeKnora provider config 中存在 API Key/BaseURL/custom header 字段。本轮只审计类型，不读取或提交任何 `.env`、数据库、上传文件、真实资料或密钥。
- Operational complexity: asynq、Redis lock、dead letters、multi-store fan-out 是 WeKnora 生产化能力，PA P0 不应一次性引入。
- License: 外层 WeKnora `LICENSE` 显示主体为 MIT License，版权声明为 `Copyright (C) 2025 Tencent. All rights reserved.`。后续若抽取 substantial portions 或改写明显源自 WeKnora 的代码，应在 `NOTICE.md` 或相关源码注释中保留版权与 MIT attribution。G1 仅产出审计文档，未复制产品实现代码。

## G1 Conclusion

G1 审计完成后，PA AI Workbench 第二阶段建议按以下顺序推进：

1. G2 先创建 `NOTICE.md` 与剥离版权说明。
2. G3-G8 建立 Model Gateway / Embedding Provider，作为所有 LLM 和 embedding 调用的唯一入口。
3. H1-H5 实现 extracted backend、parser、chunker、chunk schema、local vector store。
4. H6-H9 接入真实检索、Citation 绑定和文档索引 pipeline。
5. I/J 阶段再把 Wiki draft/publish/retrieve 和 Agent evidence workflow 接上。

本轮没有修改外层 WeKnora 源码，也没有写 PA 产品运行时代码。
