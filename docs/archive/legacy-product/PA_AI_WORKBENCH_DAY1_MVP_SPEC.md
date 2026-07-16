# PA AI Workbench Day 1 MVP Spec

## 1. 项目目标

在 1 天内开发完成一个可本地演示的独立 AI 产品第一版：

**PA AI Workbench：金融 PA 智能工作台**

第一版核心链路：

```text
用户在独立前端输入议题背景和问题
-> FastAPI 后端接收请求
-> Python PA Agent 处理任务
-> WeKnora Adapter 调用 WeKnora RAG 检索，失败时使用 mock fallback
-> 返回结构化口径结果
-> 前端展示核心口径、引用依据、风险点、媒体追问、建议回复
```

本产品是独立新产品，不是 WeKnora 子产品。

WeKnora 在第一版中只作为本地 Knowledge Engine 使用。

## 2. 开发边界

### 必须做到

1. 创建独立目录 `pa-ai-workbench/`。
2. 不修改 WeKnora 原有代码。
3. 后端使用 Python FastAPI。
4. Agent 层使用 Python。
5. 前端使用 React + Vite。
6. WeKnora 调用通过 Adapter 封装。
7. WeKnora 不可用时必须有 mock fallback。
8. 第一版必须能本地启动和演示。
9. 添加 README 和 DEMO_SCRIPT。
10. 添加 `.gitignore`，避免提交敏感信息。

### 不做内容

1. 不做完整多 Agent。
2. 不做登录系统。
3. 不做权限系统。
4. 不做审批流。
5. 不做 Word/PDF 导出。
6. 不物理剥离 WeKnora。
7. 不重构 WeKnora 后端。
8. 不接入真实部门敏感文件。
9. 不提交 `.env`、API Key、日志、上传文件、部门材料。

## 3. 推荐目录结构

在仓库根目录创建：

```text
pa-ai-workbench/
  README.md
  .gitignore
  docs/
    DEMO_SCRIPT.md
  backend/
    main.py
    requirements.txt
    .env.example
    weknora_adapter.py
  agent/
    __init__.py
    pa_briefing_agent.py
    prompts.py
  frontend/
    package.json
    index.html
    src/
      main.tsx
      App.tsx
      styles.css
```

## 4. 后端 Spec

后端使用 FastAPI。

### 4.1 启动要求

默认端口：

```text
8000
```

启动命令示例：

```bash
cd pa-ai-workbench/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 依赖文件

`backend/requirements.txt` 至少包含：

```text
fastapi
uvicorn
python-dotenv
requests
pydantic
```

### 4.3 环境变量

`backend/.env.example`：

```text
WEKNORA_BASE_URL=http://localhost:8080/api/v1
WEKNORA_API_KEY=
PA_AGENT_USE_MOCK=true
```

不得提交真实 `.env`。

## 5. API Spec

### 5.1 Health Check

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "service": "pa-ai-workbench"
}
```

### 5.2 生成 PA 口径

```http
POST /api/briefing/generate
```

请求体：

```json
{
  "issue_background": "议题背景",
  "question": "用户问题",
  "kb_id": "可选知识库 ID"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| issue_background | string | 是 | 当前议题、事件或材料背景 |
| question | string | 是 | 用户希望系统处理的问题 |
| kb_id | string | 否 | WeKnora 知识库 ID，可为空 |

响应体：

```json
{
  "core_position": [
    "核心口径 1",
    "核心口径 2"
  ],
  "evidence": [
    {
      "title": "来源标题",
      "snippet": "引用片段",
      "source": "weknora",
      "knowledge_id": "",
      "chunk_id": ""
    }
  ],
  "risks": [
    "风险点 1",
    "风险点 2"
  ],
  "follow_up_questions": [
    "媒体可能追问 1",
    "媒体可能追问 2"
  ],
  "suggested_response": "建议回复正文",
  "confidence": "medium",
  "status": "ok"
}
```

当没有依据时：

```json
{
  "core_position": [
    "资料不足，无法判断。"
  ],
  "evidence": [],
  "risks": [
    "当前知识库未检索到足够依据，不建议直接形成对外口径。"
  ],
  "follow_up_questions": [],
  "suggested_response": "建议补充相关政策文件、历史口径或正式材料后再生成。",
  "confidence": "low",
  "status": "insufficient_evidence"
}
```

## 6. WeKnora Adapter Spec

文件：

```text
backend/weknora_adapter.py
```

### 6.1 目标

封装所有对 WeKnora 的调用，前端和 Agent 不直接依赖 WeKnora 内部接口。

### 6.2 需要实现的函数

```python
search_knowledge(query: str, kb_id: str | None = None) -> list[dict]
search_wiki(query: str, kb_id: str | None = None) -> list[dict]
read_wiki_page(kb_id: str, slug: str) -> dict | None
```

Day 1 只要求 `search_knowledge` 被实际使用。

`search_wiki` 和 `read_wiki_page` 可以先保留 mock / TODO。

### 6.3 search_knowledge 返回格式

```python
[
    {
        "title": "文件标题或知识标题",
        "snippet": "命中的文本片段",
        "source": "weknora",
        "knowledge_id": "knowledge id",
        "chunk_id": "chunk id",
        "score": 0.82
    }
]
```

### 6.4 fallback 规则

如果 WeKnora 不可用、API Key 缺失、接口调用失败：

1. 不让程序崩溃。
2. 返回 mock 检索结果。
3. mock 结果中 `source` 必须为 `"mock"`。
4. 后端响应中要能看出当前是 mock 数据。

## 7. Agent Spec

文件：

```text
agent/pa_briefing_agent.py
```

### 7.1 核心函数

```python
generate_briefing(
    issue_background: str,
    question: str,
    kb_id: str | None = None
) -> dict
```

### 7.2 处理流程

1. 接收 `issue_background`、`question`、`kb_id`。
2. 拼接检索 query。
3. 调用 `weknora_adapter.search_knowledge()`。
4. 判断是否有有效 evidence。
5. 如果没有 evidence，返回 `insufficient_evidence`。
6. 如果有 evidence，用规则模板生成结构化结果。

### 7.3 生成规则

Day 1 可以不接真实 LLM，先用规则模板生成。

输出必须包含：

```text
核心口径
引用依据
风险点
媒体可能追问
建议回复
置信度
状态
```

### 7.4 安全规则

1. 没有依据时，不允许编造。
2. 不允许伪造来源。
3. 不输出“确定性过强”的结论。
4. 对外回应建议使用谨慎表达。
5. mock 数据必须明确标记。

## 8. 前端 Spec

前端使用 React + Vite。

### 8.1 页面目标

首页就是工作台，不做营销页。

页面标题：

```text
PA AI Workbench
金融 PA 智能工作台
```

### 8.2 页面布局

建议左右布局：

左侧：输入区

右侧：结果区

### 8.3 输入区

包含：

1. 议题背景 textarea
2. 用户问题 textarea/input
3. 知识库 ID input，可选
4. 生成按钮

### 8.4 结果区

展示：

1. 核心口径
2. 引用依据
3. 风险点
4. 媒体可能追问
5. 建议回复
6. 置信度
7. 状态

### 8.5 状态要求

必须实现：

1. loading 状态
2. error 状态
3. empty 状态
4. mock source 提示

### 8.6 Wiki 入口

Day 1 不做完整 Wiki 浏览器，只做一个卡片：

```text
Wiki 知识库
第一版保留入口，后续接入 Wiki 页面浏览、搜索和图谱。
```

## 9. README Spec

文件：

```text
pa-ai-workbench/README.md
```

README 必须包含：

1. 产品定位
2. 第一版能力
3. 架构说明
4. 目录结构
5. 启动方式
6. 环境变量说明
7. 当前限制
8. 下一步计划

### 9.1 产品定位示例

```text
PA AI Workbench 是一个面向金融公共事务团队的内部 AI 工作台。
第一版支持基于本地知识库的议题问答、口径初稿生成、风险点提示和媒体追问模拟。
WeKnora 在本项目中作为 Knowledge Engine 使用，负责 RAG 和 Wiki 知识能力。
```

## 10. DEMO_SCRIPT Spec

文件：

```text
pa-ai-workbench/docs/DEMO_SCRIPT.md
```

必须包含演示步骤：

```text
1. 启动本地 WeKnora
2. 启动 PA AI Workbench backend
3. 启动 PA AI Workbench frontend
4. 打开前端页面
5. 输入议题背景
6. 输入用户问题
7. 点击生成
8. 展示核心口径
9. 展示引用依据
10. 展示风险点和媒体追问
11. 说明 Wiki 功能后续接入
```

## 11. Git 与安全要求

### 11.1 .gitignore

`pa-ai-workbench/.gitignore` 至少包含：

```text
.env
*.log
__pycache__/
.pytest_cache/
.venv/
venv/
node_modules/
dist/
uploads/
data/
tmp/
.DS_Store
```

### 11.2 禁止提交

禁止提交：

```text
.env
API Key
部门文件
上传材料
日志
数据库文件
模型文件
生成的敏感结果
```

### 11.3 提交前检查

提交前必须运行：

```bash
git status
```

确认只提交 `pa-ai-workbench` 内的安全文件。

## 12. 开发任务拆分

### Task 1：创建目录结构

创建 `pa-ai-workbench/` 及所有基础文件。

验收：

```text
目录结构完整
不修改 WeKnora 原有代码
```

### Task 2：实现 FastAPI 基础服务

实现：

```text
backend/main.py
backend/requirements.txt
backend/.env.example
```

接口：

```text
GET /health
POST /api/briefing/generate
```

验收：

```text
/health 可访问
/generate 可返回 mock 结构化结果
```

### Task 3：实现 WeKnora Adapter

实现：

```text
backend/weknora_adapter.py
```

函数：

```text
search_knowledge
search_wiki
read_wiki_page
```

验收：

```text
WeKnora 不可用时不崩溃
mock fallback 可用
source 标记为 mock
```

### Task 4：实现 PA Briefing Agent

实现：

```text
agent/pa_briefing_agent.py
agent/prompts.py
```

验收：

```text
generate_briefing 可返回完整结构化结果
无 evidence 时返回 insufficient_evidence
```

### Task 5：后端接入 Agent

`POST /api/briefing/generate` 调用 `generate_briefing()`。

验收：

```text
前端或 curl 调接口能返回 Agent 结果
```

### Task 6：创建 React 前端

实现：

```text
frontend/package.json
frontend/index.html
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/styles.css
```

验收：

```text
前端能启动
页面可输入议题和问题
```

### Task 7：前端调用后端

前端调用：

```text
POST http://localhost:8000/api/briefing/generate
```

验收：

```text
点击生成后展示结构化结果
loading/error 状态正常
```

### Task 8：补充文档

实现：

```text
README.md
docs/DEMO_SCRIPT.md
```

验收：

```text
README 可指导本地启动
DEMO_SCRIPT 可指导演示
```

### Task 9：Git 检查

运行：

```bash
git status
```

确认：

```text
没有 .env
没有 API Key
没有敏感材料
没有日志
```

## 13. Day 1 验收标准

Day 1 结束时必须满足：

```text
1. pa-ai-workbench 独立目录存在
2. 后端 /health 可访问
3. 后端 /api/briefing/generate 可访问
4. 前端可打开
5. 点击生成能返回结构化结果
6. WeKnora 不可用时 mock fallback 可用
7. 页面展示核心口径、引用依据、风险点、媒体追问、建议回复
8. Wiki 有预留入口
9. README 完成
10. DEMO_SCRIPT 完成
11. .gitignore 生效
12. 没有敏感信息进入 git
```

## 14. 给 Codex 的执行指令

请严格按照本 Spec 开发 Day 1 MVP。

要求：

1. 在当前仓库根目录创建 `pa-ai-workbench/`。
2. 不修改 WeKnora 原有代码。
3. 优先保证本地可运行和可演示。
4. 后端使用 FastAPI。
5. 前端使用 React + Vite。
6. Agent 使用 Python。
7. WeKnora 通过 Adapter 调用。
8. WeKnora 不可用时使用 mock fallback。
9. 每完成阶段后运行必要验证。
10. 最后汇报：
    - 修改了哪些文件
    - 如何启动
    - 前端访问地址
    - 后端访问地址
    - 当前限制
    - 下一步建议
