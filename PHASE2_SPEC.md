# PA 智能工作台 PHASE2_SPEC

> 版本：0.2
>
> 阶段名称：WeKnora RAG / Wiki 源码剥离与真实能力上线版
>
> 用途：作为第二阶段 AI 开发的长期事实源，驱动 v0.2 的 spec + skill 开发。
>
> 第一阶段事实源：`DEV_SPEC.md`
>
> 第二阶段事实源：`PHASE2_SPEC.md`

## 0. 第二阶段设计总则

第二阶段不是重新做一个产品，也不是把 PA 智能工作台改造成 WeKnora 子产品。

第二阶段的核心方向是：

```text
以 WeKnora RAG / Wiki 源码剥离为主线
-> 建设 PA 智能工作台自己的 extracted Knowledge Engine
-> 接入开源或内部 OpenAI-compatible 模型 API
-> 上线真实 RAG、真实 Wiki、真实 Agent evidence workflow
```

必须坚持以下边界：

1. PA 智能工作台仍然是独立产品。
2. 不直接把 WeKnora 整个后端搬进来。
3. 不把前端、后端、Agent 层改造成 WeKnora 架构。
4. WeKnora 作为 RAG / Wiki 源码剥离对象和工程参考。
5. 剥离后的能力必须进入 `pa-ai-workbench/knowledge_engine/` 边界。
6. Agent 层继续保持 Python 独立架构。
7. 前端继续只调用 PA Workbench 自己的 FastAPI 后端。
8. 所有 LLM 调用必须通过 `ModelGateway`。
9. 所有 embedding 调用必须通过 `EmbeddingProvider`。
10. `.env`、API Key、真实部门资料、上传文件、数据库、日志禁止提交。
11. 处理真实涉密资料时，只能使用公司允许的内网模型、本地模型或明确获批的 API。
12. mock backend / mock model provider 必须保留，用于 smoke test 和无密钥演示。

## 1. v0.2 产品目标

### 1.1 阶段目标

将 PA 智能工作台从 v0.1 mock 演示版升级为 v0.2 真实能力上线版。

v0.2 必须支持：

```text
真实文档上传
-> 文档解析
-> 文本切分
-> embedding / 索引
-> RAG 检索
-> Agent 基于证据回答或分析
-> 输出引用和风险提示
-> 一键生成 Wiki 草稿
-> 人工编辑并发布 Wiki
-> Wiki 再进入检索
-> 后续问答可以同时引用原始文档和 Wiki
```

主闭环：

```text
Document -> RAG -> Agent Output -> Wiki -> RAG Reuse
```

### 1.2 第二阶段一句话定义

```text
第二阶段以 WeKnora RAG / Wiki 源码剥离为主线，建设 PA 智能工作台自己的 extracted Knowledge Engine，让真实文档、RAG 检索、Agent 分析和 Wiki 沉淀形成可用闭环。
```

### 1.3 成功标准

v0.2 完成后，用户应该能在本地或内网环境中完成：

1. 上传真实或脱敏的 PDF / DOCX / TXT / Markdown 文档。
2. 系统解析文档并生成 chunk。
3. 系统调用 embedding API 或 mock embedding 建立索引。
4. 用户发起知识问答或政策分析。
5. Agent 检索真实 chunk / Wiki evidence。
6. 输出带引用的答案、风险提示和依据不足提醒。
7. 用户把分析结果生成 Wiki 草稿。
8. 用户编辑并发布 Wiki。
9. 后续 RAG 可以检索并引用 Wiki 页面。

## 2. 第一阶段现状回顾

第一阶段已经完成 v0.1 MVP 产品骨架：

```text
Frontend
-> Backend API
-> AgentOrchestrator
-> Agent Runtime
-> Knowledge Engine
-> mock / weknora_api / future extracted
```

已有能力：

- React + Vite + TypeScript 前端。
- FastAPI 后端。
- SQLite / SQLModel 本地持久化。
- 资料库页面。
- 智能分析页面。
- Wiki 页面。
- 生成历史页面。
- Agent Runtime / Orchestrator / Context / Memory / Event / Skill / Tool 雏形。
- Knowledge Engine 抽象。
- `MockKnowledgeBackend`。
- `WeKnoraApiBackend` 雏形。
- 对话记忆。
- 引用结构。
- 生成历史。

第一阶段本质：

```text
v0.1 = 独立产品骨架 + mock RAG/Wiki/Agent 工作流闭环
```

第二阶段要补齐的差距：

1. `extracted_backend` 尚未承接 WeKnora RAG/Wiki 源码剥离后的真实能力。
2. 上传文档尚未完成真实解析、chunk、embedding、向量索引。
3. Citation 尚未绑定真实 chunk / Wiki evidence。
4. Wiki 仍未形成可编辑、可发布、可再检索的知识沉淀闭环。
5. Agent 尚未基于真实 evidence 完成可靠分析。
6. 模型调用尚未统一进入 Model Gateway / Embedding Provider。

## 3. 第二阶段功能范围

### 3.1 P0 必须做

- WeKnora RAG / Wiki 源码审计与模块地图。
- `extracted_backend` 目标架构。
- Model Gateway。
- OpenAI-compatible Chat Provider。
- Mock Chat Provider。
- Embedding Provider。
- OpenAI-compatible Embedding Provider。
- Mock Embedding Provider。
- 文档解析：PDF / DOCX / TXT / Markdown。
- 文档 chunk 管线。
- Chunk 数据模型。
- 本地向量库。
- 真实 retrieve。
- Citation 证据链增强。
- Wiki CRUD。
- Wiki 草稿 / 发布状态。
- 分析结果生成 Wiki 草稿。
- Wiki 进入 RAG 检索。
- Agent 接入真实 RetrieverTool / Wiki tools / CitationChecker。
- 前端资料库索引状态升级。
- 前端 Wiki 编辑 / 发布。
- 前端分析结果生成 Wiki 草稿。
- 端到端 smoke test。
- Git 安全检查。

### 3.2 P1 尽量做

- BM25 keyword search。
- Vector + keyword hybrid retrieval。
- 检索调试面板。
- Chunk 预览。
- 重建索引。
- Wiki 标签。
- Wiki 来源文档关联。
- Rerank Provider 抽象。
- Streaming chat 输出。
- 基础敏感词提醒。

### 3.3 P2 暂不做

- 复杂 RBAC 权限系统。
- 审批流。
- 多人协同编辑 Wiki。
- 知识图谱可视化。
- 自动爬取外部政策网站。
- Word / PPT 正式导出。
- 生产级审计后台。
- 复杂 Supervisor 多 Agent。
- Agent 自动执行代码或外部动作。

## 4. WeKnora RAG / Wiki 源码剥离策略

### 4.1 剥离原则

1. 先审计，再移植，不允许盲目复制大段源码。
2. 剥离目标是工程能力，不是复制 WeKnora 产品形态。
3. Go 源码默认作为参考，优先 Python 化实现。
4. 只有当 Python 化成本过高时，才考虑 Go microservice。
5. 剥离后的代码必须落入 PA Workbench 自己的模块边界。
6. MIT License 相关版权声明必须保留在 `NOTICE.md` 或剥离审计文档中。

### 4.2 优先审计的 WeKnora 模块

```text
../internal/infrastructure/chunker/
../internal/application/service/retriever/
../internal/application/service/chat_pipeline/
../internal/application/service/knowledge_process.go
../internal/application/service/knowledge_post_process.go
../internal/application/service/knowledgebase_search*.go
../internal/application/service/wiki_ingest*.go
../internal/application/service/wiki_page.go
../internal/types/chunk.go
../internal/types/retriever.go
../internal/types/retrieval_config.go
../internal/types/wiki_page.go
../internal/models/embedding/
```

### 4.3 剥离后落点

```text
knowledge_engine/parsers/
knowledge_engine/chunking/
knowledge_engine/embeddings/
knowledge_engine/vectorstores/
knowledge_engine/retrieval/
knowledge_engine/citations/
knowledge_engine/wiki/
knowledge_engine/backends/extracted_backend.py
```

### 4.4 模块策略

| WeKnora 能力 | 第二阶段策略 | PA Workbench 落点 |
| --- | --- | --- |
| Chunker | 参考设计，Python 化实现 | `knowledge_engine/chunking/` |
| Retriever abstraction | 参考设计，Python 化实现 | `knowledge_engine/retrieval/` |
| Hybrid search | P0 vector，P1 hybrid | `knowledge_engine/retrieval/` |
| Embedding adapters | 不直接复制，做 OpenAI-compatible | `knowledge_engine/embeddings/` |
| Citation / evidence | 参考结构，自建 schema | `knowledge_engine/citations/` |
| Wiki page | 参考模型，自建 CRUD | `knowledge_engine/wiki/` |
| Wiki ingest | 参考流程，自建草稿生成 | `knowledge_engine/wiki/` + `agent/tools/` |
| Chat pipeline | 不移植，只参考流程 | `agent/` |
| RBAC / tenant | 不剥离 | 暂不做 |
| IM / 外部数据源 | 不剥离 | 暂不做 |
| GraphRAG | 暂不剥离 | P2 |

### 4.5 必须输出的审计文档

任务 G1 必须输出：

```text
docs/WEKNORA_RAG_SOURCE_MAP.md
```

内容必须包括：

- 源码模块列表。
- 每个模块职责。
- 是否剥离。
- 剥离方式：参考 / Python 化 / 服务化 / 暂不处理。
- 依赖风险。
- 许可证说明。
- 对应 PA Workbench 目标模块。

## 5. Model Gateway 设计

### 5.1 目标

所有 LLM Chat 调用必须通过统一 Model Gateway。

不允许在这些位置直接写模型 API：

- 前端。
- FastAPI router。
- Agent workflow。
- Tool 具体业务逻辑。
- Knowledge Engine。

### 5.2 目录结构

```text
agent/model_gateway/
  __init__.py
  base.py
  schemas.py
  factory.py
  providers/
    __init__.py
    mock.py
    openai_compatible.py
```

### 5.3 Provider 范围

P0：

- `mock`
- `openai_compatible`

P1：

- `ollama`
- `vllm`
- `streaming`
- `structured_output`

### 5.4 配置

`backend/.env.example` 必须新增：

```text
CHAT_MODEL_PROVIDER=mock
CHAT_MODEL_BASE_URL=
CHAT_MODEL_API_KEY=
CHAT_MODEL_NAME=
CHAT_MODEL_TIMEOUT_SECONDS=60
CHAT_MODEL_TEMPERATURE=0.2
MOCK_MODEL_MODE=true
```

### 5.5 接口

```python
class ModelGateway:
    def generate(self, request: ChatRequest) -> ChatResponse:
        ...
```

核心 schema：

```text
ChatMessage:
  role: system | user | assistant | tool
  content: str

ChatRequest:
  messages: list[ChatMessage]
  model: str | None
  temperature: float
  max_tokens: int | None
  metadata: dict

ChatResponse:
  content: str
  model: str
  provider: str
  usage: dict
  raw_metadata: dict
```

### 5.6 安全规则

- API Key 只能来自 `.env`。
- `.env` 禁止提交。
- 不记录完整 prompt 或完整敏感原文。
- 真实涉密材料不能默认发往公网 API。
- mock provider 必须可用。

## 6. Embedding Provider 设计

### 6.1 目标

所有 embedding 调用必须通过统一 Embedding Provider。

### 6.2 目录结构

```text
knowledge_engine/embeddings/
  __init__.py
  base.py
  schemas.py
  factory.py
  providers/
    __init__.py
    mock.py
    openai_compatible.py
```

### 6.3 配置

`backend/.env.example` 必须新增：

```text
EMBEDDING_PROVIDER=mock
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL_NAME=
EMBEDDING_DIMENSION=1024
EMBEDDING_TIMEOUT_SECONDS=60
```

### 6.4 接口

```python
class EmbeddingProvider:
    def embed_text(self, text: str) -> EmbeddingVector:
        ...

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        ...
```

核心 schema：

```text
EmbeddingVector:
  text_hash: str
  vector: list[float]
  dimension: int
  provider: str
  model: str
```

### 6.5 mock embedding

mock embedding 不是生产能力，只用于：

- 本地 smoke test。
- 无 API Key 的演示。
- CI / QA。

mock embedding 必须稳定：

```text
same text -> same vector
```

## 7. Knowledge Engine v0.2 架构

第一阶段：

```text
mock | weknora_api | extracted
```

第二阶段目标：

```text
mock: 演示与测试 fallback
weknora_api: 临时对接 / 对照测试
extracted: 真实主后端，承接剥离后的 RAG / Wiki 能力
```

### 7.1 extracted backend 目录

```text
knowledge_engine/backends/extracted_backend.py
knowledge_engine/parsers/
knowledge_engine/chunking/
knowledge_engine/embeddings/
knowledge_engine/vectorstores/
knowledge_engine/retrieval/
knowledge_engine/citations/
knowledge_engine/wiki/
```

### 7.2 extracted backend 职责

```text
DocumentParser
-> Chunker
-> EmbeddingProvider
-> VectorStore
-> Retriever
-> CitationBuilder
-> WikiStore
```

### 7.3 必须实现的能力

现有接口：

```text
upload_document()
get_document_status()
retrieve()
search_wiki()
read_wiki_page()
```

第二阶段扩展：

```text
parse_document()
chunk_document()
index_document()
reindex_document()
list_document_chunks()
create_wiki_draft()
create_wiki_page()
update_wiki_page()
publish_wiki_page()
index_wiki_page()
```

## 8. 真实 RAG 设计

### 8.1 文档格式

P0 支持：

- PDF
- DOCX
- TXT
- Markdown

解析实现建议：

```text
PDF -> pypdf
DOCX -> python-docx
TXT -> 原生读取
Markdown -> 原生读取 + 标题结构识别
```

### 8.2 文档状态

```text
uploaded
parsing
parsed
chunking
chunked
embedding
indexed
failed
```

失败必须保存：

```text
error_message
failed_step
updated_at
```

### 8.3 Chunk schema

建议新增 `DocumentChunk`：

```text
id
document_id
chunk_index
title
content
content_hash
token_count
char_count
page_number
section_path
business_area
document_type
source
metadata_json
embedding_status
vector_id
created_at
updated_at
```

### 8.4 Chunking 策略

P0：

- 按段落切分。
- 最大字符数限制。
- overlap。
- 保留标题路径。
- 保留页码或段落序号。

P1：

- 参考 WeKnora heading hierarchy。
- 参考 WeKnora heuristic splitter。
- 增加 chunk preview。
- 增加 chunk quality diagnostics。

默认参数：

```text
CHUNK_MAX_CHARS=1200
CHUNK_OVERLAP_CHARS=150
CHUNK_MIN_CHARS=120
```

### 8.5 Vector Store

P0 默认：

```text
LocalChromaVectorStore
```

必须通过抽象访问：

```text
knowledge_engine/vectorstores/base.py
knowledge_engine/vectorstores/chroma_store.py
knowledge_engine/vectorstores/mock_store.py
```

配置：

```text
VECTOR_STORE_PROVIDER=chroma
VECTOR_STORE_PATH=./data/chroma
VECTOR_COLLECTION_NAME=pa_workbench_chunks
```

### 8.6 Retrieval flow

```text
query
-> normalize query
-> embed query
-> vector search top-k
-> metadata filter
-> evidence normalize
-> citation build
-> return evidence list
```

P0:

```text
vector search
metadata filter
top-k
score
```

P1:

```text
BM25 search
hybrid fusion
rerank provider
retrieval debug panel
```

### 8.7 Evidence schema

```text
Evidence:
  id
  source_type: document_chunk | wiki_page
  document_id
  chunk_id
  wiki_page_id
  title
  excerpt
  content
  score
  source
  metadata
```

### 8.8 Citation 规则

Agent 输出必须遵守：

1. 有结论必须有 evidence。
2. 没有 evidence 时返回依据不足。
3. Citation 必须能追溯到 chunk 或 Wiki 页面。
4. Citation 不允许伪造。
5. Citation 显示必须区分 `document` 和 `wiki`。

## 9. Wiki 沉淀设计

### 9.1 Wiki 状态

```text
draft
published
archived
```

### 9.2 Wiki schema

建议新增或扩展 `WikiPage`：

```text
id
slug
title
summary
content_markdown
status
tags_json
business_area
page_type
source_output_id
source_document_ids_json
source_citation_ids_json
created_by
created_at
updated_at
published_at
```

建议新增 `WikiCitation`：

```text
id
wiki_page_id
document_id
chunk_id
output_id
citation_id
source_type
excerpt
created_at
```

### 9.3 Wiki 工作流

```text
用户从分析结果点击生成 Wiki 草稿
-> 后端读取 output + citations
-> Agent / ModelGateway 生成标题、摘要、正文、标签
-> 保存为 draft
-> 用户编辑
-> 用户发布
-> 系统索引 Wiki
-> RAG 可以检索 Wiki
```

### 9.4 Wiki API

P0 API：

```text
GET /api/wiki/search
GET /api/wiki/pages/{slug}
POST /api/wiki/pages
PUT /api/wiki/pages/{slug}
POST /api/wiki/pages/{slug}/publish
POST /api/wiki/drafts/from-output/{output_id}
POST /api/wiki/pages/{slug}/reindex
```

### 9.5 Wiki 进入 RAG

Wiki 发布后必须：

1. 生成 Wiki chunk。
2. 调用 EmbeddingProvider。
3. 写入 VectorStore。
4. retrieval evidence 中 `source_type=wiki_page`。
5. Agent 可以引用 Wiki。

## 10. Agent 接入真实 RAG / Wiki 设计

第二阶段 Agent 不优先做复杂多 Agent。

Agent 重点是把真实 RAG、Wiki、引用检查串成可靠工作流。

### 10.1 新增 / 增强 Tools

```text
agent/tools/real_retriever.py
agent/tools/wiki_reader.py
agent/tools/wiki_draft_writer.py
agent/tools/evidence_builder.py
agent/tools/citation_checker.py
```

### 10.2 Workflow 更新

知识问答：

```text
query
-> retrieve document/wiki evidence
-> build grounded prompt
-> ModelGateway generate
-> CitationChecker
-> save output/citations/messages
```

政策分析：

```text
topic
-> retrieve policy/case evidence
-> produce structured analysis
-> include risks / suggestions / uncertainty
-> CitationChecker
```

案例复盘：

```text
case topic
-> retrieve case evidence
-> summarize timeline/actions/lesson
-> CitationChecker
```

Wiki 草稿生成：

```text
output + citations
-> ModelGateway
-> wiki title/summary/content/tags
-> save draft
```

### 10.3 Memory

继续使用第一阶段 conversation memory。

第二阶段不做长期向量化记忆，但必须：

- 保留最近多轮消息。
- 不把完整敏感长文写入 memory summary。
- Agent prompt 中只放必要上下文和 evidence excerpt。

## 11. 后端 API 与数据模型升级

### 11.1 新增或扩展 models

建议：

```text
DocumentChunk
DocumentProcessingEvent
WikiPage
WikiCitation
RagQueryLog
ModelCallLog
```

`ModelCallLog` 只保存元数据：

```text
id
provider
model
purpose
status
latency_ms
error_message
created_at
```

禁止保存：

```text
完整 prompt
完整真实文档
API Key
敏感原文
```

### 11.2 文档 API 升级

```text
GET /api/documents
POST /api/documents
GET /api/documents/{document_id}
POST /api/documents/{document_id}/parse
POST /api/documents/{document_id}/index
POST /api/documents/{document_id}/reindex
GET /api/documents/{document_id}/chunks
GET /api/documents/{document_id}/events
```

### 11.3 RAG API

P0 可新增调试接口：

```text
POST /api/rag/retrieve
```

用途：

- 本地调试。
- QA 验证。
- 前端检索调试面板 P1。

前端正式分析仍通过：

```text
POST /api/analysis/run
```

### 11.4 Model API

不暴露 API Key。

可新增状态接口：

```text
GET /api/model/status
```

返回：

```text
chat_provider
embedding_provider
mock_mode
configured
```

## 12. 前端页面与交互升级

### 12.1 资料库

必须显示：

- 文档上传。
- 解析状态。
- chunk 状态。
- embedding / indexed 状态。
- 失败原因。
- 重新解析。
- 重新索引。
- chunk 数量。
- chunk 预览入口。

### 12.2 智能分析

必须显示：

- 是否使用真实 RAG。
- 检索到的 evidence。
- 引用来源类型：document / wiki。
- 依据不足 warning。
- 生成 Wiki 草稿按钮。

### 12.3 Wiki

必须支持：

- 搜索 Wiki。
- 查看 Wiki。
- 新建 Wiki。
- 编辑 Wiki。
- 保存草稿。
- 发布 Wiki。
- 展示引用来源。
- 展示是否已索引。

### 12.4 历史

必须支持：

- 从 output 进入详情。
- 从 output 生成 Wiki 草稿。
- 查看 citations。
- 查看 warnings。

## 13. 安全与涉密边界

第二阶段必须写死：

1. 不提交真实部门资料。
2. 不提交 `.env`。
3. 不提交 `backend/data/`、`backend/uploads/`、`logs/`。
4. 不把 API Key 写入代码。
5. 前端不接触模型 API Key。
6. 真实涉密资料默认不允许发往公网模型 API。
7. 模型调用日志只能保存元数据。
8. Agent 不得在依据不足时编造结论。
9. 引用不允许伪造。
10. Demo 使用脱敏样例文件。

## 14. 第二阶段 Skills 规划

第二阶段新增 skills：

```text
.github/skills/phase2-auto-coder/SKILL.md
.github/skills/phase2-rag-auditor/SKILL.md
.github/skills/phase2-qa-tester/SKILL.md
```

### 14.1 phase2-rag-auditor

用途：

- 执行 G1。
- 审计 WeKnora RAG / Wiki 源码。
- 输出 `docs/WEKNORA_RAG_SOURCE_MAP.md`。
- 不写产品代码。

### 14.2 phase2-auto-coder

用途：

- 读取 `PHASE2_SPEC.md`。
- 每次只执行一个第二阶段任务。
- 实现后运行验收。
- 更新任务状态。
- 根据用户要求 commit / push。

### 14.3 phase2-qa-tester

用途：

- 验收第二阶段任务。
- 检查真实 RAG / Wiki / Model Gateway。
- 检查安全文件。
- 最多自动修复 3 轮。

## 15. 开发阶段与任务表

状态标记：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
```

### 阶段 G：源码剥离设计与模型网关

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| G1 | WeKnora RAG/Wiki 源码审计与模块地图 | [x] |
| G2 | 创建 NOTICE.md 与剥离版权说明 | [x] |
| G3 | Model Gateway 抽象与 schemas | [x] |
| G4 | Mock Chat Provider | [ ] |
| G5 | OpenAI-compatible Chat Provider | [ ] |
| G6 | EmbeddingProvider 抽象与 schemas | [ ] |
| G7 | Mock Embedding Provider | [ ] |
| G8 | OpenAI-compatible Embedding Provider | [ ] |
| G9 | `/api/model/status` 与配置更新 | [ ] |

### 阶段 H：extracted Knowledge Engine 与真实 RAG

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| H1 | extracted_backend 骨架 | [ ] |
| H2 | 文档解析模块 PDF/DOCX/TXT/MD | [ ] |
| H3 | Chunker Python 化第一版 | [ ] |
| H4 | DocumentChunk 数据模型与迁移 | [ ] |
| H5 | 文档 parse/chunk/index 状态流转 | [ ] |
| H6 | VectorStore 抽象与 MockVectorStore | [ ] |
| H7 | Local Chroma VectorStore | [ ] |
| H8 | 文档索引管线接入 EmbeddingProvider | [ ] |
| H9 | 真实 retrieve 接入 document chunks | [ ] |
| H10 | Citation evidence 真实绑定 | [ ] |
| H11 | `/api/rag/retrieve` 调试接口 | [ ] |

### 阶段 I：Wiki 真实沉淀

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| I1 | WikiPage / WikiCitation 数据模型 | [ ] |
| I2 | Wiki CRUD API | [ ] |
| I3 | Wiki draft / publish 状态 | [ ] |
| I4 | 从 output 生成 Wiki 草稿 service | [ ] |
| I5 | Wiki 页面索引进入 VectorStore | [ ] |
| I6 | retrieve 同时支持 document + wiki evidence | [ ] |
| I7 | Wiki search/read 使用真实 WikiStore | [ ] |

### 阶段 J：Agent 接入真实 RAG / Wiki

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| J1 | RealRetrieverTool | [ ] |
| J2 | WikiReadTool | [ ] |
| J3 | WikiDraftWriterTool | [ ] |
| J4 | CitationChecker 增强真实 evidence 校验 | [ ] |
| J5 | QA workflow 接入 ModelGateway + real evidence | [ ] |
| J6 | Policy workflow 接入 ModelGateway + real evidence | [ ] |
| J7 | Case workflow 接入 ModelGateway + real evidence | [ ] |
| J8 | `/api/analysis/run` 返回 document/wiki citation 区分 | [ ] |

### 阶段 K：前端 v0.2 升级

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| K1 | 资料库解析/索引状态升级 | [ ] |
| K2 | Chunk 预览与重建索引入口 | [ ] |
| K3 | 智能分析 evidence/citation 展示升级 | [ ] |
| K4 | 分析结果生成 Wiki 草稿按钮 | [ ] |
| K5 | Wiki 新建/编辑/草稿/发布页面 | [ ] |
| K6 | Wiki 引用来源与索引状态展示 | [ ] |
| K7 | 模型与 RAG 状态展示 | [ ] |

### 阶段 L：端到端验收与安全

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| L1 | 更新 README v0.2 启动与模型配置说明 | [ ] |
| L2 | 编写 PHASE2_DEMO_SCRIPT.md | [ ] |
| L3 | 后端 smoke test：model/status/doc/index/retrieve | [ ] |
| L4 | Agent smoke test：QA/policy/case with evidence | [ ] |
| L5 | Wiki smoke test：draft/publish/retrieve | [ ] |
| L6 | 前端 build 与主要页面检查 | [ ] |
| L7 | Git 安全检查 | [ ] |

## 16. 任务执行协议

AI 开发工具每次只执行一个任务编号。

执行格式：

```text
读取 PHASE2_SPEC.md
-> 定位任务编号
-> 列出计划修改文件
-> 实现
-> 运行验收命令
-> 汇报修改文件、测试结果、风险
-> 更新任务状态
-> 如用户要求，commit 并 push
```

禁止：

- 一次性实现多个未确认任务。
- 修改 WeKnora 原源码。
- 跳过验收。
- 提交敏感文件。
- 绕过 ModelGateway 直接调用 Chat API。
- 绕过 EmbeddingProvider 直接调用 Embedding API。
- 让 Agent 编造引用。

推荐用户指令：

```text
请使用 phase2-rag-auditor，执行 PHASE2_SPEC.md 中的 G1。只做 G1，不写产品代码。完成后更新任务状态，并说明审计结论。
```

继续开发：

```text
请使用 phase2-auto-coder，继续执行 PHASE2_SPEC.md 中下一个未完成任务。完成后运行验收，更新任务状态，并等待我确认是否 commit/push。
```

提交同步：

```text
请提交当前已完成任务，commit 信息用 docs: add phase2 rag extraction spec，并推送到 GitHub。
```

## 17. 第二阶段验收标准

### 17.1 最小验收

v0.2 最小验收必须通过：

1. `GET /health` 正常。
2. `GET /api/status` 正常。
3. `GET /api/model/status` 正常。
4. 可上传脱敏 PDF/DOCX/TXT/MD。
5. 文档可 parse/chunk/index。
6. `/api/rag/retrieve` 返回真实 document evidence。
7. `/api/analysis/run` 能调用 real evidence 生成回答。
8. 输出 citations 可追溯到 chunk。
9. 可从 output 生成 Wiki draft。
10. Wiki 可编辑发布。
11. 发布 Wiki 可进入 retrieval。
12. 前端 build 通过。
13. Git 未包含 `.env`、数据库、上传文件、API Key、真实资料。

### 17.2 演示验收

用脱敏样例资料完成：

```text
上传资料
-> 索引成功
-> 问一个政策问题
-> 输出带 document citation
-> 生成 Wiki 草稿
-> 编辑发布
-> 再问一个问题
-> 输出同时引用 document 和 wiki
```

## 18. 后续阶段预留

v0.3 可考虑：

- 混合检索增强。
- Rerank。
- 长期记忆。
- 多 Agent Supervisor。
- 权限与审计。
- Wiki 版本 diff。
- 知识图谱。
- Word/PPT 导出。
- 部门内部部署脚本。
