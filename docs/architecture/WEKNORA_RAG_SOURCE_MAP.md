# WeKnora RAG / Wiki Integration Map

更新日期：2026-07-16

本文记录 PA AI Workbench 中知识处理、检索、引用、Wiki 和智能对话能力的
当前实现位置与协作关系。源码级归属和许可证信息分别见
[`platform/weknora/UPSTREAM.md`](../../platform/weknora/UPSTREAM.md)、
[`platform/weknora/PA_PATCHES.md`](../../platform/weknora/PA_PATCHES.md) 和
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)。

## System flow

```text
apps/pa-web
  -> apps/pa-api
  -> packages/knowledge-engine
  -> platform/weknora

packages/agent-runtime
  -> packages/knowledge-engine
  -> normalized evidence, history, citations, and audit
```

Web 工作区负责资料管理、智能对话、专业分析、Wiki、能力配置、历史和引用
定位。FastAPI 服务组织业务流程、状态、确认、安全响应与持久化。
Knowledge Engine 统一适配知识平台响应并规范化证据。WeKnora 提供知识库、
文档处理、分块、检索、知识对话、Wiki、AgentQA、模型、向量库、MCP、Web
Search 和数据源能力。

## Capability map

| Capability | WeKnora implementation | Workbench integration | Result exposed to users |
| --- | --- | --- | --- |
| 文档解析与索引 | `platform/weknora/internal/application/service/knowledge_process.go`、`platform/weknora/internal/infrastructure/docparser/`、`platform/weknora/internal/infrastructure/chunker/` | `apps/pa-api/app/services/document_service.py`、`packages/knowledge-engine/knowledge_engine/backends/weknora_api_backend.py` | 上传、URL/手工资料、处理阶段、状态、分块预览和恢复操作 |
| 检索与 RAG | `platform/weknora/internal/application/service/knowledgebase_search*.go`、`platform/weknora/internal/application/service/retriever/` | `apps/pa-api/app/services/rag_service.py`、`packages/knowledge-engine/knowledge_engine/retrieval/` | 按知识范围检索、排序结果、可追踪证据和诊断信息 |
| 知识对话 | `platform/weknora/internal/application/service/chat_pipeline/` 和知识会话路由 | `apps/pa-api/app/services/native_chat_service.py`、`apps/pa-web/src/pages/DialoguePage.tsx` | 多轮问答、模式选择、工具过程、建议问题、引用和历史 |
| Wiki | `platform/weknora/internal/application/service/wiki_page.go`、`wiki_ingest*.go` | `apps/pa-api/app/services/wiki_service.py`、`apps/pa-web/src/pages/WikiPage.tsx` | 页面浏览、搜索、阅读、草稿、发布、引用定位和状态 |
| AgentQA / custom Agent | WeKnora Agent、AgentQA、工具和会话服务 | `apps/pa-api/app/services/native_agent_service.py`、`packages/agent-runtime/agent/` | 快速问答、Agent 分析、专业工作流、工具轨迹和输出历史 |
| Embedding 与向量库 | WeKnora 模型配置和 vector-store 服务 | `apps/pa-api/app/services/model_config_service.py`、`vector_store_service.py`、Knowledge Engine provider/store 接口 | 掩码配置状态、可用性、检索能力与安全管理入口 |
| MCP / Web Search / 数据源 | WeKnora MCP、Web Search 和 datasource 服务 | `apps/pa-api/app/services/mcp_service.py`、`web_search_service.py`、`data_source_service.py` | 能力目录、状态、确认受控的管理操作和审计记录 |

## Module responsibilities

### `platform/weknora`

- 处理知识库、文档、分块、索引和检索。
- 执行知识对话、AgentQA、custom Agent、工具、MCP 和 Web Search。
- 管理模型、解析器、向量库、数据源及其运行配置。
- 返回文档、分块、Wiki、会话、Agent 和工具的原生标识及状态。

### `packages/knowledge-engine`

- `backends/weknora_api_backend.py` 提供统一的 WeKnora API 适配入口。
- `schemas.py`、`evidence.py` 和 `citations/` 将平台结果转换为稳定的
  evidence/citation 结构。
- `current_run.py`、`source_scope.py`、`answer_ranking.py` 和
  `distractor_guard.py` 处理当前运行证据、知识范围、排序与干扰项保护。
- `parsers/`、`chunking/`、`embeddings/`、`retrieval/`、`vectorstores/` 和
  `wiki/` 提供统一接口以及本地/测试场景所需实现。

### `apps/pa-api`

- `api/documents.py` 与 `services/document_service.py` 组织资料生命周期。
- `api/rag.py` 与 `services/rag_service.py` 组织检索和 RAG 响应。
- `services/native_chat_service.py` 与 `native_agent_service.py` 组织知识对话、
  AgentQA 和 custom Agent 流程。
- `api/wiki.py` 与 `services/wiki_service.py` 组织 Wiki 读取、草稿、发布和
  引用绑定。
- `services/citation_locator_service.py`、`history_service.py` 和
  `native_audit_service.py` 提供引用定位、业务历史与审计。
- `services/model_config_service.py`、`mcp_service.py`、
  `web_search_service.py`、`vector_store_service.py` 和
  `data_source_service.py` 提供经过掩码和确认控制的能力管理。

### `packages/agent-runtime` and `apps/pa-web`

- Agent Runtime 提供知识问答、政策分析、案例复盘及其工具编排。
- Web 工作区展示实时状态、部分可用、阻塞、回退和模拟状态，避免把配置
  状态当作引用证据。
- 分析、对话、Wiki 和历史页面复用统一 evidence/citation 模型，以便从输出
  返回原始资料、分块或 Wiki 页面。

## Data and evidence flow

### Document ingestion

1. Web 工作区提交文件、URL 或手工内容。
2. API 创建业务资料记录，并通过 Knowledge Engine 调用 WeKnora 知识接口。
3. WeKnora 完成解析、分块、向量化与索引并返回阶段状态。
4. API 保存外部资料标识、安全状态快照和处理事件；运行时分块与向量由
   WeKnora 维护。

### Retrieval and answer generation

1. API 根据知识库、资料和会话范围构造检索或知识对话请求。
2. WeKnora 返回命中结果、原生标识、分数和可用引用信息。
3. Knowledge Engine 生成包含 `source_type`、`evidence_id`、原生定位字段、
   score、rank 和安全元数据的证据。
4. API 将回答、警告、引用、会话和审计写入业务历史。
5. Web 工作区展示引用并提供资料、分块或 Wiki 页面的定位操作。

### Wiki and professional workflows

1. Wiki 页面可以从资料、检索证据或分析输出形成草稿。
2. 发布和其他变更操作经过显式确认，并写入审计与历史。
3. 专业工作流通过 Agent Runtime 组合检索、Wiki 和引用检查工具，也可以
   调用 WeKnora AgentQA/custom Agent。
4. 只有带稳定来源身份和定位信息的结果可以通过引用验收。

## Runtime and safety boundaries

- 业务数据库保存对话、输出、业务资料记录、安全状态快照、审计事件和引用
  定位元数据。
- WeKnora 运行时维护知识分块、向量、模型/提供商配置、解析器状态、Wiki
  平台状态和 Agent/工具执行状态。
- API 密钥、服务令牌、私有端点、原始提供商请求/响应、上传正文、向量、
  日志和数据库内容不得进入前端响应、验证报告或 Git。
- 配置与服务状态用于可用性展示，不作为事实引用。
- 缺少稳定来源标识时可以保存输出，但引用验收保持失败关闭。

## Validation references

- 根命令入口：[`Makefile`](../../Makefile) 与 [`scripts/README.md`](../../scripts/README.md)
- 产品合同：[`PRODUCT_SPEC.md`](../../PRODUCT_SPEC.md)
- 总体架构：[`ARCHITECTURE.md`](../../ARCHITECTURE.md)
- 能力架构：[`WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md`](WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md)

本图描述当前仓库中的实现关系。具体能力是否可用，仍以对应的静态、服务、
工作流和浏览器验证结果为准。
