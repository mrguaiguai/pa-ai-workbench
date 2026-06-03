# PA 智能工作台 DEV_SPEC

> 版本：0.1
>
> 用途：作为 AI 开发工具的长期事实源，驱动 PA 智能工作台三天 MVP 开发。
>
> 产品定位：独立的金融 PA 内部 AI 工作台。WeKnora 只作为 Knowledge Engine 能力来源与源码参考，不是本产品本体。

## 0. 开发总原则

1. 所有新产品代码必须放在 `pa-ai-workbench/` 内。
2. 不修改 WeKnora 原有源码，除非用户明确要求。
3. 前端只调用 FastAPI 后端。
4. 后端只通过 AgentOrchestrator 调用 Agent。
5. Agent 只通过 Knowledge Engine / Tools 获取知识证据。
6. Knowledge Engine 封装 RAG / Wiki 能力，不向上暴露 WeKnora 原始响应。
7. 第一版必须支持 mock fallback，保证 WeKnora 不可用时仍可演示。
8. Agent 层按 Runtime 架构设计，业务 Agent 只是 profile / workflow，方便后续扩展复杂 Agent。
9. 所有关键结论必须带引用或返回依据不足。
10. `.env`、uploads、data、logs、node_modules、dist、API Key、敏感材料禁止提交。

## 1. 第一版功能范围

### 1.1 必须做

- 资料上传与资料库管理。
- 知识问答。
- 政策分析。
- Wiki 浏览与搜索。
- 任务进度展示。
- 本地数据库保存资料、会话、任务、结果、引用。
- Agent 会话级多轮记忆。
- Knowledge Engine mock backend。

### 1.2 轻量做

- 历史案例复盘。
- 生成结果历史。
- WeKnora API backend 雏形。
- Skill 系统雏形。
- Memory 系统雏形。

### 1.3 暂不做

- Word 导出。
- 用户反馈评分。
- 复杂权限体系。
- 审批流。
- Wiki 图谱可视化。
- 完整多 Agent Supervisor。
- 长期向量化记忆。
- Skill 沙箱执行。

## 2. 推荐技术栈

### 2.1 Frontend

```text
React + Vite + TypeScript
```

建议依赖：

```text
react
react-dom
vite
typescript
lucide-react
```

### 2.2 Backend

```text
Python + FastAPI + SQLModel + SQLite
```

建议依赖：

```text
fastapi
uvicorn
sqlmodel
python-dotenv
requests
pydantic
python-multipart
```

### 2.3 Agent

```text
Python package, in-process call in MVP
```

但必须按未来独立 Agent 服务设计：

- Runtime。
- Context。
- Memory。
- Skill。
- Tool。
- Policy。
- Event。
- Workflow。

### 2.4 Knowledge Engine

```text
mock | weknora_api | extracted
```

第一版必须完成 mock，尽量完成 weknora_api，预留 extracted。

## 3. 目标目录结构

```text
pa-ai-workbench/
  README.md
  DEV_SPEC.md
  PRODUCT_SPEC.md
  .gitignore
  backend/
    app/
      __init__.py
      main.py
      config.py
      database.py
      models.py
      schemas.py
      api/
        __init__.py
        health.py
        documents.py
        conversations.py
        analysis.py
        wiki.py
        history.py
      services/
        __init__.py
        document_service.py
        conversation_service.py
        analysis_service.py
        wiki_service.py
        history_service.py
      storage/
        __init__.py
        file_store.py
    requirements.txt
    .env.example
    data/
    uploads/
  agent/
    __init__.py
    orchestrator.py
    runtime.py
    schemas.py
    context/
      __init__.py
      manager.py
      run_context.py
    agents/
      __init__.py
      base.py
      profiles.py
      workflows.py
      qa_agent.py
      policy_agent.py
      case_agent.py
    events/
      __init__.py
      event_bus.py
    memory/
      __init__.py
      base.py
      conversation_memory.py
      manager.py
    skills/
      __init__.py
      base.py
      registry.py
      builtin/
        qa.md
        policy_analysis.md
        case_review.md
    policies/
      __init__.py
      guard.py
    tools/
      __init__.py
      base.py
      registry.py
      retriever_tool.py
      evidence_ranker.py
      citation_checker.py
      result_builder.py
    prompts/
      qa.md
      policy_analysis.md
      case_review.md
  knowledge_engine/
    __init__.py
    base.py
    factory.py
    schemas.py
    errors.py
    backends/
      __init__.py
      mock_backend.py
      weknora_api_backend.py
      extracted_backend.py
    adapters/
      __init__.py
      response_normalizer.py
    rag/
      __init__.py
      evidence.py
      filters.py
    wiki/
      __init__.py
      page_types.py
      markdown_utils.py
  frontend/
    package.json
    index.html
    src/
      main.tsx
      App.tsx
      api/
      components/
      pages/
      types/
      styles.css
  docs/
    DEMO_SCRIPT.md
    ARCHITECTURE.md
```

## 4. 数据模型

### 4.1 documents

```text
id
title
business_area
document_type
source
keywords_json
file_name
file_path
file_size
mime_type
knowledge_backend
external_doc_id
summary
status
error_message
created_at
updated_at
```

status:

```text
uploaded | indexing | indexed | failed
```

### 4.2 conversations

```text
id
title
summary
default_task_type
created_by
created_at
updated_at
```

### 4.3 conversation_messages

```text
id
conversation_id
role
content
metadata_json
created_at
```

role:

```text
user | assistant | system_status
```

### 4.4 generation_tasks

```text
id
conversation_id
task_type
title
input_json
status
current_step
progress
error_message
created_at
updated_at
```

task_type:

```text
knowledge_qa | policy_analysis | case_review | wiki_search
```

status:

```text
created | retrieving | generating | checking | completed | failed | insufficient_evidence
```

### 4.5 generated_outputs

```text
id
task_id
conversation_id
task_type
title
content_json
content_markdown
warnings_json
status
created_at
updated_at
```

### 4.6 citations

```text
id
task_id
output_id
document_id
external_doc_id
chunk_id
title
text
score
source
metadata_json
created_at
```

source:

```text
mock | weknora_api | extracted | manual
```

### 4.7 wiki_pages_cache

```text
id
slug
title
page_type
summary
content
source
metadata_json
created_at
updated_at
```

## 5. API Contract

### 5.1 Health

```http
GET /health
GET /api/status
```

### 5.2 Documents

```http
POST /api/documents
GET /api/documents
GET /api/documents/{document_id}
POST /api/documents/{document_id}/retry-index
```

### 5.3 Conversations

```http
POST /api/conversations
GET /api/conversations
GET /api/conversations/{conversation_id}
GET /api/conversations/{conversation_id}/messages
```

### 5.4 Analysis

```http
POST /api/analysis/run
GET /api/tasks/{task_id}
GET /api/outputs/{output_id}
```

`POST /api/analysis/run` request:

```json
{
  "conversation_id": "optional",
  "task_type": "knowledge_qa",
  "title": "optional",
  "query_or_topic": "用户问题或分析主题",
  "business_area": "securities",
  "document_type": "policy",
  "document_ids": ["doc_001"],
  "extra_requirements": "补充要求"
}
```

Response:

```json
{
  "conversation_id": "conv_001",
  "task": {
    "id": "task_001",
    "task_type": "knowledge_qa",
    "status": "completed",
    "current_step": "completed",
    "progress": 100
  },
  "output": {
    "id": "out_001",
    "task_type": "knowledge_qa",
    "title": "结果标题",
    "content": {},
    "warnings": []
  },
  "citations": []
}
```

### 5.5 Wiki

```http
GET /api/wiki/search?query=xxx&kb_id=optional
GET /api/wiki/pages/{slug}?kb_id=optional
```

### 5.6 History

```http
GET /api/history
GET /api/history/{output_id}
```

## 6. Knowledge Engine Contract

```python
class KnowledgeEngine:
    def health(self) -> dict: ...
    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument: ...
    def get_document_status(self, external_doc_id: str) -> dict: ...
    def retrieve(self, query: str, filters: dict | None = None, top_k: int = 8) -> list[Evidence]: ...
    def search_wiki(self, query: str, kb_id: str | None = None, limit: int = 10) -> list[WikiPageSummary]: ...
    def read_wiki_page(self, slug: str, kb_id: str | None = None) -> WikiPage | None: ...
```

Evidence:

```python
class Evidence:
    document_id: str | None
    external_doc_id: str | None
    chunk_id: str | None
    title: str
    text: str
    score: float | None
    source: str
    metadata: dict
```

WikiPage:

```python
class WikiPage:
    slug: str
    title: str
    page_type: str
    summary: str
    content: str
    citations: list[Evidence]
    source: str
    metadata: dict
```

## 7. Agent Runtime Contract

### 7.1 Runtime Modules

```text
AgentOrchestrator
AgentRuntime
ContextManager
MemoryManager
SkillRegistry
ToolRegistry
PolicyGuard
EventBus
AgentProfile
Workflow
```

### 7.2 AgentRequest

```python
class AgentRequest:
    task_id: str
    conversation_id: str
    task_type: str
    title: str | None
    query_or_topic: str
    business_area: str | None
    document_type: str | None
    document_ids: list[str]
    extra_requirements: str | None
```

### 7.3 AgentResult

```python
class AgentResult:
    task_id: str
    conversation_id: str
    task_type: str
    status: str
    title: str
    content: dict
    markdown: str
    citations: list[Citation]
    warnings: list[str]
    memory_updates: list[dict]
```

### 7.4 Built-in Workflows

```text
knowledge_qa
policy_analysis
case_review
```

### 7.5 Memory Rules

第一版必须实现会话级多轮记忆：

- 保存 user / assistant / system_status 消息。
- `/api/analysis/run` 如果 conversation_id 为空，自动创建会话。
- Agent 运行时读取最近 N 条消息，默认 10。
- Agent 回复写回 conversation_messages。
- 不保存系统 Prompt、API Key、完整敏感长文。

## 8. Frontend Contract

第一版主页面：

```text
/
/library
/analysis
/wiki
/history
```

核心组件：

```text
AppShell
TaskProgress
CitationList
ResultPanel
DocumentStatusBadge
BackendStatusBadge
EmptyState
ErrorState
```

`/analysis` 必须支持：

- 会话列表。
- 当前会话消息流。
- task_type 切换。
- knowledge_qa / policy_analysis / case_review。
- 多轮追问。
- citations 展示。
- warnings 展示。

## 9. 开发阶段与任务表

状态标记：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
```

### 阶段 A：工程骨架

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| A1 | 创建目录与基础文档 | [x] |
| A2 | 初始化 FastAPI 后端骨架 | [x] |
| A3 | 初始化 React + Vite 前端骨架 | [x] |
| A4 | 建立配置与环境变量模板 | [x] |

### 阶段 B：后端数据库与 API

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| B1 | 实现 SQLite / SQLModel 数据库基础 | [x] |
| B2 | 实现 documents API 与本地文件存储 | [x] |
| B3 | 实现 conversations 与 messages API | [x] |
| B4 | 实现 tasks / outputs / citations 数据写入 | [x] |
| B5 | 实现 status / history API | [x] |

### 阶段 C：Knowledge Engine

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| C1 | 定义 KnowledgeEngine 抽象接口与 schema | [x] |
| C2 | 实现 MockKnowledgeBackend | [x] |
| C3 | 实现 KnowledgeEngine factory | [x] |
| C4 | 实现 WeKnoraApiBackend 雏形 | [x] |
| C5 | 实现 Wiki search / read API service 对接 | [x] |

### 阶段 D：Agent Runtime

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| D1 | 定义 Agent schemas / AgentResult / Citation / Event | [x] |
| D2 | 实现 AgentRuntime / ContextManager / EventBus | [x] |
| D3 | 实现 ConversationMemory / MemoryManager | [x] |
| D4 | 实现 SkillRegistry 与内置 Skill 文档 | [x] |
| D5 | 实现 ToolRegistry / RetrieverTool / CitationChecker | [x] |
| D6 | 实现 QA workflow | [x] |
| D7 | 实现 PolicyAnalysis workflow | [x] |
| D8 | 实现 CaseReview workflow 轻量版 | [x] |
| D9 | 实现 AgentOrchestrator 并接入 /api/analysis/run | [x] |

### 阶段 E：前端工作台

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| E1 | 实现 AppShell / 导航 / API client | [x] |
| E2 | 实现工作台首页 | [x] |
| E3 | 实现资料库页面 | [x] |
| E4 | 实现智能分析台页面 | [x] |
| E5 | 实现 Wiki 页面 | [x] |
| E6 | 实现生成历史页面 | [x] |
| E7 | 完成统一引用、进度、错误状态组件 | [x] |

### 阶段 F：端到端验收

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| F1 | 编写 DEMO_SCRIPT | [ ] |
| F2 | 补充 README 启动说明 | [ ] |
| F3 | 后端基础 smoke test | [ ] |
| F4 | 前端构建 smoke test | [ ] |
| F5 | Git 安全检查 | [ ] |

## 10. 任务执行协议

AI 开发工具每次只执行一个任务编号。

执行格式：

```text
读取 DEV_SPEC
-> 定位任务编号
-> 列出计划修改文件
-> 实现
-> 运行验收命令
-> 汇报修改文件、测试结果、风险
-> 更新任务状态
```

禁止：

- 一次性实现多个未确认阶段。
- 修改 WeKnora 原源码。
- 跳过验收。
- 提交敏感文件。

推荐用户指令：

```text
请阅读 pa-ai-workbench/DEV_SPEC.md，执行任务 A1。只做 A1，不扩展范围。完成后运行验收命令并汇报。
```

继续任务：

```text
请继续执行 DEV_SPEC 中下一个未完成任务。
```

测试任务：

```text
请根据 DEV_SPEC 中已完成任务的验收标准执行 smoke test，失败时最多自动修复 3 轮。
```
