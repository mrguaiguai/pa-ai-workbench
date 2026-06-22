# PA Existing Work Review For WeKnora-First

> Date: 2026-06-22
>
> Branch context: `pa-native-baseline-20260622` freezes the current PA-native product baseline. `weknora-first-mvp` is the five-day WeKnora-first sprint branch.
>
> Safety rule: this review intentionally records architecture, reports, scripts, and public local paths only. It does not record `.env` values, API keys, service tokens, private endpoints, uploaded file bodies, local databases, logs, caches, or raw model/provider payloads.

## Review Purpose

PA is shifting from a PA-native general knowledge engine direction to a WeKnora-first product direction. The goal of this review is to decide which existing work must be preserved as PA product value, which general capability should move behind WeKnora native APIs, and which PA-native professional workflow work should be frozen for later design.

The key product judgment is:

- Preserve PA as product shell, workflow experience, history, evidence display, report generation, and domain task templates.
- Prefer WeKnora native capabilities for general RAG, Wiki, AgentQA, document parsing, knowledge base management, retrieval, custom Agent, MCP, web search, and vector store administration.
- Freeze PA-native professional Agent work into the baseline branch for later, rather than deepening it during this five-day sprint.

## Existing Capability Decision Table

| 能力/模块 | 当前实现方式 | 是否已经真实可用 | 是否应保留 | 是否应迁移为 WeKnora 原生能力 | 是否应冻结到 baseline 分支 | 五天冲刺优先级 | 判断理由 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RAG 接入能力 | PA `/api/rag/*` 调 `KnowledgeEngine`，`weknora_api` 后端转发 WeKnora `/api/v1/knowledge-search`；PA 叠加 current-run、source scope、distractor guard、answer-bearing ranking | 是。Phase 5 RAG 24Q PASS | 保留 PA 调试页、evidence 标准、current-run 验收规则 | 是。通用检索、召回、混合检索、rerank 尽量接 WeKnora 原生 | 当前实现冻结为对照基线 | P0 | 用户需要 PA 的调试体验和引用质量，但不需要 PA 继续自研通用检索引擎 |
| Wiki 接入能力 | PA 本地 `wiki_pages`/`wiki_citations` 记录状态，`WeKnoraApiBackend` 调 WeKnora Wiki create/update/read/search | 是。Phase 5 Wiki draft -> publish -> retrievable -> citation PASS | 保留 PA Wiki 展示、引用定位、历史联动 | 是。Wiki list/index/search/graph/lint/auto-fix 优先接 WeKnora 原生 | PA 本地 draft/publish 流程冻结为基线 | P0/P1 | WeKnora 已有更完整 Wiki 浏览器和图谱能力，PA 应做适配和展示 |
| 知识问答 | PA `AgentOrchestrator` 调 `KnowledgeQaWorkflow`，经 RetrieverTool 获取 WeKnora evidence，再经 ModelGateway 生成答案 | 是。Phase 5 knowledge_qa 24Q PASS | 保留问答入口、历史、引用展示、source scope UI | 部分迁移。通用 QA/AgentQA 优先接 WeKnora 原生；PA 保留产品包装 | 当前 PA-native QA workflow 冻结 | P0/P1 | 现有 QA 可用，但五天目标是验证 WeKnora native AgentQA 能否承接通用能力 |
| PA 专业 Agent 编排 | PA 内置 `policy_analysis`、`case_review` 等 workflow | 部分真实可用，依赖同一 evidence 规则 | 保留为未来 PA-native 专业层资产 | 暂不迁移为本冲刺主线 | 是 | Backlog | 专业工作流是长期价值，但五天内不要与 WeKnora 原生接入抢范围 |
| 文档上传/索引/状态展示 | PA 保存业务记录和上传文件；`weknora_api` 模式上传到 WeKnora，轮询 WeKnora document status，展示 processing events/chunks | 是。Phase 5 current-run 9 文档 upload/index/retrieval PASS | 保留 PA 资料库、业务元数据、状态 UI | 是。解析、分块、embedding、索引以 WeKnora 为准 | 当前 PA 状态模型冻结为基线 | P0 | PA 负责产品体验和业务记录，底层通用入库能力应由 WeKnora 承担 |
| 文档分块预览 | PA 从 WeKnora chunk preview 或本地 chunk 表展示分块 | 是，WeKnora chunk trace 可用 | 保留预览与引用定位能力 | 是。chunk 事实源优先 WeKnora | 冻结本地 extracted 分块路线 | P1 | 用户需要查看证据，但不应让 PA 维护另一套通用 chunk pipeline |
| evidence/citation 映射 | PA 标准化 `source`、`source_type`、`evidence_id`、`chunk_id`、`wiki_page_id`、locator、history filter | 是。Phase 5 报告全链路证明 | 必须保留 | 不迁移，作为 PA 适配层核心合同 | 冻结当前合同为基线并继续扩展 | P0 | 这是 PA 区别于纯 WeKnora 后台的产品价值和验收基础 |
| 首页运行状态检查 | `/health`、`/api/status`、`/api/model/status` 驱动首页真实状态卡 | 是。Phase 5 frontend PASS | 必须保留 | 扩展为 WeKnora 原生能力地图状态 | 不冻结，进入冲刺增强 | P0 | 前端必须反映真实后端状态，不能靠静态绿灯 |
| 前端首页 | React 页面展示工作台入口、运行状态、计数、能力卡 | 是。浏览器 PASS | 必须保留 | 只改状态/入口，不替换为 WeKnora UI | 冻结当前版本到 baseline | P0 | 首页是 PA 产品壳第一信号 |
| 资料库页面 | 上传、筛选、状态、分块和事件展示 | 是。浏览器 PASS | 必须保留 | 上传/知识库选择接 WeKnora 原生 | 当前体验冻结为 baseline | P0 | 资料库是 PA 用户最核心入口之一 |
| RAG 调试页面 | PA debug controls + evidence list + trace/warnings | 是。浏览器 PASS | 必须保留 | 检索执行和参数语义尽量对齐 WeKnora native | 当前 PA guard/ranking 逻辑冻结为 baseline | P0 | 调试页是验收和开发工具，不应退化为静态演示 |
| Wiki 页面 | 搜索、阅读、编辑、发布、状态、citation 展示 | 是。浏览器 PASS | 必须保留 | list/index/search/graph/lint/auto-fix 迁移到 WeKnora native | 本地 Wiki CRUD 路线冻结 | P0/P1 | 五天内应先接 native browse/search/read，再考虑管理能力 |
| 知识问答页面 | task type、retrieval scope、conversation、result、citations、Wiki draft action | 是。浏览器 PASS | 必须保留 | 通用 AgentQA 入口接 WeKnora native | PA-native task workflows 冻结 | P1 | PA 应保留业务入口，通用 Agent 推理由 WeKnora 承担 |
| 历史页面 | 输出列表、筛选、citation source/source_type/evidence_state、Wiki draft | 是。浏览器 PASS | 必须保留 | 不迁移；只接收更多 WeKnora native evidence 元数据 | 不冻结，继续演进 | P0/P1 | 历史和任务沉淀是 PA 长期价值 |
| 真实测试脚本 | Phase 3/4/5 smoke、matrix、current-run isolation、report safety、frontend browser checks | 是 | 必须保留 | 作为 WeKnora-first live gates 复用 | 不冻结，继续扩展 | P0 | 真实能力优先阶段必须靠这些资产防止假完成 |
| Phase 3 验收资产 | live WeKnora RAG/Wiki/Agent smokes、M1 release checker、API map | 是 | 保留 | 用于 adapter 差距分析 | baseline 保留 | P0/P1 | 提供历史 API 映射和 live smoke 经验 |
| Phase 4 验收资产 | P4-G real reports，记录 PARTIAL 与优化路线 | 是，报告可用但能力当时 PARTIAL | 保留 | 用作风险清单 | baseline 保留 | P1 | 明确哪些问题后来在 Phase 5 被修复，哪些规则仍要复用 |
| Phase 5 验收资产 | real env/upload/RAG/Wiki/QA/frontend/final PASS reports | 是，最终 PASS | 必须保留 | 作为五天 sprint 的最低验收风格 | baseline 保留并在 sprint 复用 | P0 | 证明当前版本不是 demo，并定义 live evidence 口径 |
| report safety 规则 | `check_phase5_report_safety.py` 检查敏感信息和 evidence 字段 | 是 | 必须保留 | 扩展到 WeKnora-first 报告 | 不冻结，继续扩展 | P0 | 防止密钥、端点、原始资料、缓存证据混入报告 |
| 本地服务常驻 | `scripts/pa-dev-services.sh`、LaunchAgents 安装/卸载脚本 | 是 | 必须保留 | 不迁移 | baseline 保留 | P0 | 运行稳定性是继续做 live 验收的前提 |
| PA 业务数据库 | 默认 SQLite 保存 PA 业务状态、任务、历史、citation | 是 | 必须保留 | 不迁移到 WeKnora | baseline 保留 | P0 | PA 业务状态和 WeKnora 知识/向量事实源必须分层 |
| WeKnora 向量库分层 | WeKnora 侧 PostgreSQL/ParadeDB/pgvector 等承载 chunks/vectors | 是，作为外部事实源 | 保留分层设计 | WeKnora native 管理和查询优先 | baseline 记录 | P0 | 防止把 PA SQLite 误认为向量库事实源 |
| mock backend | `MockKnowledgeBackend` 供 UI/dev/test 使用 | 不能作为真实 PASS | 仅保留 dev-only | 不迁移 | 冻结为开发辅助 | 全阶段规则 | mock 不能算完成依据，必须显式标记 |
| extracted backend | PA Python-native parser/chunker/vector prototype | 部分可用，不能作 release PASS | 保留为本地学习/单测辅助 | 通用能力应让位 WeKnora native | 冻结为 baseline | Backlog | 与 WeKnora-first 方向冲突，五天内不深化 |
| 静态样例/fixture/cache | fixture corpus、旧报告、旧 evidence id | 只能辅助 | 保留测试用途 | 不可作为完成证据 | 不作为冲刺成果 | 全阶段规则 | live evidence 必须来自当前真实 PA + WeKnora + model/embedding 运行 |

## Current Live-Capability Evidence

The current PA baseline has already proven these live capabilities in prior Phase 5 assets:

| 能力 | 证明资产 | 判定 |
| --- | --- | --- |
| Real environment and model posture | `docs/PHASE5_REAL_ENV_PASS_REPORT.md` | PASS |
| Fresh upload/index/retrieval | `docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md` | PASS |
| RAG debug 24-question matrix | `docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md` | PASS |
| Wiki draft/publish/read/retrieve/citation | `docs/PHASE5_REAL_WIKI_PASS_REPORT.md` | PASS |
| `knowledge_qa` 24-question matrix | `docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md` | PASS |
| Frontend six-page browser matrix | `docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md` | PASS |
| Final Phase 5 real gate | `docs/PHASE5_REAL_PASS_REPORT.md` | PASS |

These reports used sanitized fixture materials through real PA backend, real WeKnora, and non-mock model/embedding configuration. The fixture corpus is allowed as test input, but the PASS evidence comes from the live system path, not from fixture-only or cached output.

## Remaining Mock, Fixture, And Cache Boundaries

| Area | Current dependency | Five-day rule |
| --- | --- | --- |
| `mock` backend | UI/dev fallback and unit-level examples | Allowed only for development and unit tests; never PASS |
| `extracted` backend | Local Python RAG prototype and schema parity work | Allowed only as explicit partial/local path; never release evidence |
| Synthetic fixture corpus | Sanitized test materials for repeatable gates | Allowed as input corpus only when run through real PA + real WeKnora |
| Historical reports/evidence ids | Useful for review and comparison | Not valid as current sprint PASS unless rerun live |
| Browser screenshots in temp paths | Visual QA artifacts | Do not commit; cite only sanitized conclusions |
| Cached page/status/output | Useful for diagnosis | Must be marked cached; cannot prove live capability |

## Assets That Must Not Be Lost

- Existing PA frontend product experience: 首页、资料库、RAG 调试、Wiki、知识问答、历史.
- Citation and evidence standards: `source`, `source_type`, `evidence_id`, `chunk_id`, `wiki_page_id`, locator, and history filters.
- Real-test and report-safety rules: Phase 3/4/5 smokes, 24Q matrix, current-run isolation, report safety checker, browser acceptance.
- Homepage runtime checks: `/health`, `/api/status`, `/api/model/status`, backend capability snapshot, model and embedding status.
- Local persistent service scripts: `scripts/pa-dev-services.sh`, LaunchAgents install/uninstall scripts.
- Storage layering: PA business state in its own database; WeKnora owns authoritative knowledge chunks, embeddings, retrieval, Wiki, and vector-store layer.

## Assets To Deprioritize, Replace, Or Freeze

| Area | New stage decision |
| --- | --- |
| PA self-built general RAG | Replace/deepen via WeKnora native retrieval where possible. Keep PA debug and citation wrapping. |
| PA self-built general Wiki backend | Prefer WeKnora native Wiki list/index/search/graph/lint/read APIs. Keep PA display and citation mapping. |
| PA self-built general Agent orchestration | Connect WeKnora native AgentQA/custom agent first. Freeze PA-native professional workflows for later design. |
| extracted parser/chunker/vector store | Freeze as baseline/local learning path. Do not use for sprint PASS. |
| mock/static demo pages | Keep explicit dev/test only. Do not build sprint completion around static green states. |

## Impact On Five-Day Prioritization

| Priority | Workstream | Why this priority follows from the review |
| --- | --- | --- |
| P0 | WeKnora native capability map and adapter gap table | The repo already has PA wrappers; the next risk is not knowing which native APIs are ready to consume. |
| P0 | Native knowledge base/document/RAG path | Document upload/index/RAG is already live-proven and is the safest first WeKnora-first slice. |
| P0 | Truthful status and evidence/report gates | Existing quality guardrails are strong and must protect the new direction from demo drift. |
| P1 | Native AgentQA/custom agent | PA currently has working QA, but general Agent should move to WeKnora native once the API contract is proven. |
| P1 | Native Wiki browser/search/index/graph/lint | Current Wiki is live but PA-owned; WeKnora has richer native Wiki surfaces worth exposing through PA. |
| P2 | MCP, web search, vector store management, advanced admin | Valuable native capabilities, but too broad for first live slices unless earlier P0/P1 is stable. |
| Backlog | PA-native professional Agent layer | Long-term differentiator, but intentionally frozen during this five-day sprint. |

## Review Conclusion

The current PA version is worth freezing because it already proves a real WeKnora-backed product shell with citation discipline, history, status truthfulness, and live testing assets. The five-day sprint should not discard that product work. It should narrow PA's implementation responsibility: PA owns product experience and evidence-quality contracts, while WeKnora owns general knowledge ingestion, retrieval, Wiki, AgentQA, tools, search, and vector-store capabilities wherever a real native API is available.
