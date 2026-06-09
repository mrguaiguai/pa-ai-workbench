# PA AI Workbench PHASE3_SPEC

> 版本：0.3
>
> 阶段名称：WeKnora 后端能力复用与 PA 独立产品化阶段
>
> 用途：作为第三阶段 AI 开发的长期事实源，驱动 `PHASE3_SPEC.md + phase3-* skills` 的逐任务开发。
>
> 参考母版：仓库根目录 `DEV_SPEC_副本.md`
>
> 第一阶段事实源：`DEV_SPEC.md`
>
> 第二阶段事实源：`PHASE2_SPEC.md`
>
> 第三阶段事实源：`PHASE3_SPEC.md`

## 0. 第三阶段设计总则

第三阶段不是继续做 demo，也不是继续把 WeKnora 的 RAG / Wiki 能力用 Python 从零复刻。

第三阶段的核心方向是：

```text
复用 WeKnora 后端成熟 RAG / Wiki 能力
-> 建设 PA Workbench 自己的 KnowledgeBackend Adapter
-> 保持 PA 前端、PA Backend、PA Agent 层独立设计
-> 三周完成 M1 内网试点上线
-> 后续推进产品化增强与可替换架构
```

必须坚持以下边界：

1. PA AI Workbench 是独立 PA 产品，不是 WeKnora 前端皮肤。
2. WeKnora 是第三阶段 RAG / Wiki 能力底座和数据事实源。
3. PA 前端不直接调用 WeKnora API。
4. PA Agent 不直接读取 WeKnora 原始响应。
5. 所有 WeKnora 能力必须通过 PA `KnowledgeBackend Adapter` 标准化。
6. PA Backend 对前端暴露自己的 API shape，并保持第一、二阶段已经形成的产品边界。
7. 文档、chunk、向量、Wiki 页面在 M1/M2 默认以 WeKnora 为事实源。
8. PA 本地只保存会话、Agent 输出、引用映射、任务状态、展示缓存和必要外部 ID。
9. M1 内网试点环境必须关闭 mock 主链路：`KNOWLEDGE_BACKEND=weknora_api`，`MOCK_MODE=false`。
10. mock backend 仍保留，用于本地无 WeKnora 服务时的开发和 smoke，不得掩盖上线验收。
11. Python `extracted` backend 保留为 M3 可替换路线，不抢 M1 主线。
12. 真实资料、上传文件、数据库、日志、`.env`、API Key 禁止提交。
13. Agent 输出必须基于 evidence；无 evidence 时必须明确依据不足。
14. Citation 必须能追溯到 WeKnora chunk 或 Wiki page，不允许伪造。

第三阶段一句话定义：

```text
第三阶段以 WeKnora 后端复用为主线，将 PA AI Workbench 从“可演示的独立骨架”升级为“可在内网真实试点的 PA 智能工作台”，并为后续产品化和可替换架构打下稳定边界。
```

## 1. 阶段目标与里程碑

### 1.1 完整阶段目标

第三阶段完成后，PA 团队应能在内网环境中完成：

1. 使用 PA 前端上传真实或脱敏文档。
2. PA Backend 调用 WeKnora 后端完成文档解析、chunk、embedding、索引。
3. PA 前端展示处理状态、失败原因、chunk / evidence 信息。
4. PA Agent 通过 Adapter 检索 WeKnora RAG evidence。
5. Agent 输出知识问答、政策分析、案例复盘，带真实 citation。
6. 用户从 Agent output 生成 Wiki 草稿。
7. 用户编辑、发布 Wiki。
8. 发布后的 Wiki 进入 WeKnora 检索能力，并可被后续 Agent 引用。
9. 系统能清晰展示“真实 RAG / mock fallback / WeKnora 不可用 / evidence 不足”等状态。
10. 内网试点具备基础上线检查、安全边界和可恢复能力。

### 1.2 M1 / M2 / M3 定义

```text
M1：三周内网试点上线
M2：产品化增强与稳定性
M3：可替换架构与长期扩展
```

M1 不代表第三阶段结束。M1 的目标是让真实 PA 小团队能开始使用闭环。

M2 的目标是把试点中暴露的问题产品化收口，包括状态、错误、引用定位、调试、运维和可观测。

M3 的目标是增强抽象边界，为未来 Python fallback、混合检索、重排、评估和局部替换 WeKnora 做准备。

### 1.3 M1 内网试点成功标准

M1 必须完成：

1. WeKnora 后端可在本地或内网环境稳定启动。
2. WeKnora 模型、embedding、向量库、DocReader / doc parser 配置完成。
3. PA Backend 使用服务账号调用 WeKnora。
4. PA 前端上传脱敏 PDF / DOCX / Markdown 后能索引成功。
5. PA Agent 输出非 mock citation。
6. Citation 可追溯到 WeKnora chunk 或 Wiki page。
7. Wiki 草稿可编辑、发布、再进入 RAG。
8. 前端能显示 WeKnora 不可用、索引失败、无 evidence 等状态。
9. 上线配置关闭 mock 主链路。
10. Git 安全检查不包含 `.env`、uploads、数据库、API Key、真实资料。

## 2. 当前状态与路线调整

### 2.1 第一、二阶段事实

第一阶段已经完成：

- PA 独立产品骨架。
- React + Vite 前端。
- FastAPI 后端。
- Agent Runtime / Orchestrator 雏形。
- mock Knowledge Engine。
- 会话与历史输出。

第二阶段已经完成：

- Python `extracted` backend 的真实 RAG / Wiki 薄链路。
- ModelGateway / EmbeddingProvider。
- 文档 parse / chunk / index。
- 本地 vector store。
- Wiki draft / publish / index。
- Agent 接入 evidence workflow。
- 前端资料库、分析台、Wiki 页升级。
- L3/L4/L5 smoke。

第二阶段的问题：

1. 主线仍偏“独立 Python 复刻”，三周内追平 WeKnora RAG / Wiki 成熟能力风险过高。
2. 默认 mock 和本地 extracted 能力容易掩盖真实上线链路。
3. WeKnora 后端已有较完整能力，没有被作为 M1 上线主能力复用。
4. PA 产品真正的差异化应在前端体验、Agent 工作流、证据呈现和 PA 场景。

### 2.2 第三阶段路线调整

第三阶段主线从：

```text
Python extracted backend 完整复刻 WeKnora RAG / Wiki
```

调整为：

```text
WeKnora 后端复用
-> PA Adapter 标准化
-> PA Agent evidence workflow
-> PA 前端产品化
```

### 2.3 非目标

M1 不做：

- 完整 Python 复刻 WeKnora RAG / Wiki。
- 复杂多 Agent Supervisor。
- Agent 自主执行外部动作。
- 多租户 / RBAC 完整复刻。
- IM 集成。
- WeKnora 图谱可视化完整复刻。
- Word / PPT 正式导出。
- 生产级审计后台。

M2/M3 可视情况逐步增强，但必须单独任务化。

## 3. 总体架构设计

### 3.1 目标架构

```text
PA Frontend
  |
  v
PA FastAPI Backend
  |
  v
PA Agent Orchestrator
  |
  v
PA KnowledgeBackend Adapter
  |
  v
WeKnora Backend RAG / Wiki
```

### 3.2 模块职责

| 模块 | 职责 | 禁止事项 |
| --- | --- | --- |
| PA Frontend | 产品体验、资料库、分析台、Wiki、历史、状态展示 | 不直接调用 WeKnora，不处理 WeKnora 原始字段 |
| PA Backend | BFF、会话、任务、输出、引用映射、配置状态 | 不裸透 WeKnora 原始响应给前端 |
| PA Agent | QA / policy / case / wiki draft evidence workflow | 不直接依赖 WeKnora API shape，不编造 citation |
| KnowledgeBackend Adapter | WeKnora API 调用、响应标准化、错误映射 | 不保存真实长文，不绕过标准 schema |
| WeKnora Backend | 文档处理、chunk、embedding、RAG、Wiki、索引 | 不承担 PA 产品 UI / Agent 业务编排 |

### 3.3 后端调用边界

PA Backend 调用 WeKnora 使用服务账号：

```text
WEKNORA_BASE_URL=
WEKNORA_SERVICE_TOKEN=
WEKNORA_TIMEOUT_SECONDS=60
WEKNORA_WORKSPACE_ID=
WEKNORA_DEFAULT_KB_ID=
```

规则：

1. token 只存在 `.env` 或部署环境变量。
2. 前端永远不接触 token。
3. 日志只记录 request id、status、latency、operation，不记录完整敏感正文。
4. WeKnora 失败必须映射为 PA 可读错误。
5. PA API 不得返回 WeKnora token、internal trace、原始异常堆栈。

### 3.4 Adapter 模式

Adapter 必须把 WeKnora 能力转为 PA 标准模型：

```text
WeKnoraKnowledgeBackend.upload_document()
WeKnoraKnowledgeBackend.get_document_status()
WeKnoraKnowledgeBackend.list_document_chunks()
WeKnoraKnowledgeBackend.retrieve()
WeKnoraKnowledgeBackend.search_wiki()
WeKnoraKnowledgeBackend.read_wiki_page()
WeKnoraKnowledgeBackend.create_wiki_draft()
WeKnoraKnowledgeBackend.create_wiki_page()
WeKnoraKnowledgeBackend.update_wiki_page()
WeKnoraKnowledgeBackend.publish_wiki_page()
WeKnoraKnowledgeBackend.index_wiki_page()
```

## 4. 数据归属设计

### 4.1 M1 数据事实源

| 数据 | M1 事实源 | PA 是否保存 |
| --- | --- | --- |
| 原始文档 | WeKnora | 保存上传映射与外部 ID，不保存长期事实源 |
| chunk | WeKnora | 可保存展示缓存，但不得作为事实源 |
| embedding / vector | WeKnora | 不保存 |
| RAG evidence | WeKnora | 保存引用映射与必要 excerpt |
| Wiki page | WeKnora | 可保存 slug/id/status/cache，不作为事实源 |
| Agent conversation | PA | 保存 |
| Agent output | PA | 保存 |
| Citation mapping | PA | 保存 |
| 用户偏好 / 前端状态 | PA | 保存 |

### 4.2 标准 ID 映射

PA 必须保存外部 ID：

```text
Document.external_doc_id = WeKnora knowledge/document id
DocumentChunk.external_chunk_id = WeKnora chunk id
WikiPage.external_wiki_id = WeKnora wiki page id
Citation.evidence_id = stable PA evidence id
Citation.external_source_id = WeKnora chunk/wiki id
```

如果现有模型字段不足，M1 允许先放入 `metadata_json`，M2 再结构化迁移。

### 4.3 缓存原则

PA 可缓存：

- 文档标题。
- 文档状态。
- chunk count。
- evidence excerpt。
- wiki title / slug / status。
- citation 展示字段。

PA 不应缓存：

- 完整真实文档。
- 大段敏感 chunk 全文。
- WeKnora token。
- 模型完整 prompt。
- 未脱敏日志。

## 5. WeKnora Adapter 设计

### 5.1 Adapter 标准输出

#### KnowledgeDocument

```text
document_id
external_doc_id
title
status
source=weknora_api
metadata
```

#### DocumentStatus

```text
external_doc_id
status: uploaded | parsing | chunking | embedding | indexed | failed | unknown
source
message
failed_step
error_message
metadata
```

#### Evidence

```text
evidence_id
source_type: document_chunk | wiki_page
document_id
external_doc_id
chunk_id
wiki_page_id
title
text
score
source=weknora_api
metadata
```

#### WikiPageSummary

```text
slug
title
page_type
summary
source=weknora_api
metadata
```

#### WikiPage

```text
slug
title
page_type
summary
content
citations
source=weknora_api
metadata
```

### 5.2 状态映射

WeKnora 原始状态必须映射到 PA 状态：

```text
created / pending / uploaded -> uploaded
parsing / processing -> parsing
chunking / splitting -> chunking
embedding / indexing -> embedding
completed / indexed / ready -> indexed
failed / error -> failed
unknown -> unknown
```

状态映射必须集中在 Adapter 层，前端不得硬编码 WeKnora 状态。

### 5.3 错误映射

Adapter 需要定义统一错误：

```text
WeKnoraUnavailableError
WeKnoraAuthError
WeKnoraTimeoutError
WeKnoraRateLimitError
WeKnoraDocumentError
WeKnoraWikiError
WeKnoraResponseMappingError
```

PA API 返回：

```text
status_code
error_code
message
operation
retryable
request_id
```

### 5.4 RAG 检索规则

RAG 检索 flow：

```text
Agent query
-> RetrieverTool
-> KnowledgeBackend.retrieve(query, filters, top_k)
-> WeKnoraKnowledgeBackend.retrieve()
-> WeKnora search API
-> evidence normalize
-> CitationBuilder
-> Agent grounded prompt
```

M1 必须支持：

- query。
- top_k。
- business_area / document_type 轻量 filters。
- document ids scope。
- source_type 区分 document / wiki。
- score。
- title。
- excerpt。
- external ids。

M2 增强：

- retrieval debug trace。
- hybrid / rerank 参数展示。
- evidence dedup。
- citation 跳转定位。

### 5.5 Wiki 规则

Wiki flow：

```text
output + citations
-> create Wiki draft
-> edit draft
-> publish
-> WeKnora indexes wiki
-> retrieve as wiki_page evidence
```

M1 必须支持：

- search。
- read。
- draft from output。
- create / update。
- publish。
- index status。
- citation source refs。

如果 WeKnora Wiki API 不支持某个能力，M1 必须明确 fallback 策略：

1. PA 本地临时保存 draft，但发布必须同步 WeKnora。
2. 未同步 WeKnora 的 Wiki 不得标记为可检索。
3. 前端必须显示“未进入 RAG”的状态。

## 6. Agent 证据工作流设计

### 6.1 Agent 范围

M1 Agent 采用固定证据工作流，不做复杂自主工具调用。

内置 workflow：

```text
knowledge_qa
policy_analysis
case_review
wiki_draft_from_output
```

### 6.2 QA 工作流

```text
query
-> retrieve document/wiki evidence
-> evidence quality check
-> build grounded prompt
-> ModelGateway generate
-> CitationChecker
-> save output/citations/messages
```

输出必须包含：

- 直接回答。
- 依据列表。
- 引用编号。
- 不确定性。
- evidence 不足提示。

### 6.3 政策分析工作流

```text
topic
-> retrieve policy/case/wiki evidence
-> build policy analysis prompt
-> ModelGateway generate
-> CitationChecker
-> save structured markdown
```

输出结构：

```text
摘要
关键要求或变化
影响与风险
建议动作
不确定性与待补证据
```

### 6.4 案例复盘工作流

```text
case topic
-> retrieve case evidence
-> build case review prompt
-> ModelGateway generate
-> CitationChecker
```

输出结构：

```text
背景
时间线
关键动作
风险与问题
经验教训
待补材料
```

### 6.5 Wiki 草稿工作流

```text
output + citations
-> verify citations are real
-> build wiki draft prompt
-> ModelGateway generate title/summary/content/tags
-> create draft through Wiki Adapter
```

规则：

1. 没有真实 citation 的 output 不能默认生成正式 Wiki。
2. draft 必须保留 source_output_id。
3. draft 必须保留 source citation refs。
4. 发布前允许人工编辑。
5. 发布后必须显示是否进入 RAG 检索。

### 6.6 CitationChecker 规则

CitationChecker 必须检查：

- title 不为空。
- text 不为空。
- source 不为空。
- source_type 为 `document_chunk` 或 `wiki_page`。
- 非 mock citation 必须有 evidence_id。
- document citation 必须有 chunk_id 和 document id。
- wiki citation 必须有 wiki_page_id 或 external wiki id。
- citation text 必须来自 retrieved evidence 或已保存 binding。

## 7. 前端产品设计

### 7.1 资料库

M1 必须展示：

- 上传入口。
- 文件类型。
- WeKnora backend 状态。
- parse / chunk / embedding / indexed 状态。
- 失败原因。
- 外部 document id。
- chunk / evidence 预览。
- 重新同步状态。
- 重试索引入口。

禁止：

- 只显示“上传成功”但不显示 WeKnora 索引状态。
- mock 状态与真实 WeKnora 状态混在一起不标识。

### 7.2 智能分析台

M1 必须展示：

- workflow 类型。
- RAG mode：Real WeKnora / Mock / No evidence / Error。
- document evidence 数量。
- wiki evidence 数量。
- citation 列表。
- evidence score。
- source_type。
- 依据不足 warning。
- 生成 Wiki 草稿入口。

### 7.3 Wiki 页面

M1 必须支持：

- Wiki 搜索。
- Wiki 读取。
- 草稿查看。
- 新建 / 编辑。
- 发布。
- 索引状态。
- 来源引用。
- 是否进入 RAG。

### 7.4 历史页面

M1 必须支持：

- output 详情。
- citations。
- warnings。
- 从历史 output 生成 Wiki 草稿。
- 跳转 Wiki 草稿。

### 7.5 状态与错误展示

前端必须区分：

```text
WeKnora unavailable
WeKnora auth failed
Document indexing failed
No evidence
Mock fallback
Wiki not indexed
Model unavailable
```

## 8. 测试、上线与安全设计

### 8.1 M1 E2E 验收链路

使用脱敏样例完成：

```text
启动 WeKnora
-> 启动 PA Backend
-> 启动 PA Frontend
-> 上传 PDF/DOCX/MD
-> 等待索引完成
-> 运行知识问答
-> 检查非 mock citation
-> 生成 Wiki 草稿
-> 编辑发布 Wiki
-> 再次提问
-> 检查 wiki_page evidence
```

### 8.2 配置验收

上线环境必须：

```text
KNOWLEDGE_BACKEND=weknora_api
MOCK_MODE=false
WEKNORA_BASE_URL=...
WEKNORA_SERVICE_TOKEN=...
CHAT_MODEL_PROVIDER=...
EMBEDDING_PROVIDER由WeKnora侧管理或明确配置
```

如果 `MOCK_MODE=true`，M1 release checker 必须失败。

### 8.3 安全检查

禁止提交：

```text
.env
backend/data/
backend/uploads/
logs/
*.db
*.sqlite
API keys
真实资料
未脱敏输出
WeKnora service token
```

日志禁止：

- 完整 prompt。
- 完整文档正文。
- 长段 chunk 原文。
- token / key。
- 内网私有模型 endpoint 细节。

### 8.4 测试分层

M1 测试：

- Adapter contract tests。
- WeKnora health/status smoke。
- RAG evidence smoke。
- Agent citation smoke。
- Wiki draft/publish/retrieve smoke。
- Frontend build。
- Release safety check。

M2 测试：

- 错误恢复。
- 超时重试。
- citation 定位。
- 检索调试。
- 试点反馈回归。

M3 测试：

- backend 切换 contract。
- extracted fallback parity。
- retrieval quality regression。
- rerank / hybrid 参数回归。

## 9. 第三阶段 Skills 规划

第三阶段新增 skills：

```text
.github/skills/phase3-architect/SKILL.md
.github/skills/phase3-weknora-adapter/SKILL.md
.github/skills/phase3-agent-designer/SKILL.md
.github/skills/phase3-qa-tester/SKILL.md
.github/skills/phase3-release-checker/SKILL.md
```

### 9.1 phase3-architect

用途：

- 维护 `PHASE3_SPEC.md`。
- 拆分 M1/M2/M3 任务。
- 调整任务状态。
- 不写业务代码，除非用户明确切换到实现任务。

### 9.2 phase3-weknora-adapter

用途：

- 实现 WeKnora RAG / Wiki adapter。
- 标准化 Document / Evidence / Citation / WikiPage。
- 写 adapter contract tests。
- 禁止前端和 Agent 直接依赖 WeKnora 原始响应。

### 9.3 phase3-agent-designer

用途：

- 设计并实现 Agent evidence workflow。
- 强化 CitationChecker。
- 处理 evidence 不足。
- 保持 workflow 稳定，不引入复杂自主工具调用。

### 9.4 phase3-qa-tester

用途：

- 用脱敏资料验收 M1/M2/M3 任务。
- 不允许 inference-only pass。
- 验证真实 non-mock citation。
- 验证 Wiki 再检索。

### 9.5 phase3-release-checker

用途：

- 检查内网试点上线条件。
- 检查 mock 是否关闭。
- 检查 WeKnora 配置。
- 检查敏感文件和日志风险。

## 10. 开发阶段与任务表

状态标记：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
```

每个任务执行格式：

```text
读取 PHASE3_SPEC.md
-> 定位任务编号
-> 列出计划修改文件
-> 实现或设计
-> 运行验收命令
-> 汇报修改文件、测试结果、风险
-> 更新任务状态
```

### M1-A：WeKnora 内网部署与配置

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-A1 | WeKnora 本地/内网启动方式审计 | [x] |
| P3-M1-A2 | WeKnora 模型、embedding、向量库、DocReader 配置清单 | [x] |
| P3-M1-A3 | PA `.env.example` 增加 WeKnora service account 配置 | [x] |
| P3-M1-A4 | WeKnora health / auth / workspace smoke 脚本设计 | [x] |

#### P3-M1-A1：WeKnora 本地/内网启动方式审计

目标：
明确 M1 试点中 WeKnora 后端如何启动、依赖哪些服务、暴露哪些 API。

范围：
审计根目录 WeKnora README、docker-compose、config、docs，不修改代码。

输入：
WeKnora 根目录配置与部署文档。

输出：
`pa-ai-workbench/docs/PHASE3_WEKNORA_DEPLOYMENT_MAP.md`。

验收标准：
文档包含启动方式、依赖服务、端口、必要环境变量、健康检查、风险。

验证方式：
`test -f pa-ai-workbench/docs/PHASE3_WEKNORA_DEPLOYMENT_MAP.md`。

风险：
WeKnora 部署依赖外部模型或私有配置，需用占位说明，不写入真实密钥。

状态：[x]

#### P3-M1-A2：WeKnora 模型、embedding、向量库、DocReader 配置清单

目标：
形成 M1 试点需要的 WeKnora 能力配置 checklist。

范围：
模型服务、embedding、向量库、DocReader、数据库、Redis、对象存储或本地存储。

输入：
WeKnora config examples、docs、docker-compose。

输出：
部署配置 checklist 与缺失项列表。

验收标准：
可以按 checklist 判断当前环境是否支持真实 RAG / Wiki。

验证方式：
人工按 checklist 检查；敏感值只写变量名。

风险：
配置项可能因实际环境不同变化，必须保留“环境差异”章节。

状态：[x]

#### P3-M1-A3：PA `.env.example` 增加 WeKnora service account 配置

目标：
让 PA Backend 明确知道如何连接 WeKnora。

范围：
只更新 PA 配置示例和 Settings，不写真实值。

输入：
WeKnora 接入配置清单。

输出：
`WEKNORA_BASE_URL`、`WEKNORA_SERVICE_TOKEN`、`WEKNORA_WORKSPACE_ID`、`WEKNORA_DEFAULT_KB_ID`、`WEKNORA_TIMEOUT_SECONDS`。

验收标准：
`.env.example` 不含真实 token，Settings 可读取配置。

验证方式：
`python -m compileall backend/app`。

风险：
字段命名与现有 `weknora_api_backend.py` 不一致，需要同步。

状态：[x]

#### P3-M1-A4：WeKnora health / auth / workspace smoke 脚本设计

目标：
提供最小脚本验证 PA 能连接 WeKnora。

范围：
只做 health、auth、workspace/kb 读检查，不上传真实资料。

输入：
WeKnora service account 配置。

输出：
`backend/scripts/smoke_weknora_connection.py`。

验收标准：
成功时输出 base URL、auth ok、workspace/kb ok；失败时返回明确错误。

验证方式：
`python backend/scripts/smoke_weknora_connection.py`。

风险：
真实 WeKnora 不可用时脚本应清晰失败，不 fallback 到 mock。

状态：[x]

### M1-B：WeKnora RAG Adapter

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-B1 | WeKnora RAG API 审计与响应映射 | [x] |
| P3-M1-B2 | WeKnoraKnowledgeBackend 文档上传/状态适配 | [x] |
| P3-M1-B3 | WeKnoraKnowledgeBackend retrieve 适配 | [x] |
| P3-M1-B4 | Evidence / Citation 标准化与 contract tests | [x] |
| P3-M1-B5 | 文档 chunk / evidence 预览 API 接入 | [x] |

#### P3-M1-B1：WeKnora RAG API 审计与响应映射

目标：
明确 PA 需要调用哪些 WeKnora RAG API，以及原始响应如何映射为 PA schema。

范围：
审计 WeKnora docs/swagger、client、handler、service；不实现业务代码。

输入：
WeKnora API 文档和源码。

输出：
`pa-ai-workbench/docs/PHASE3_WEKNORA_API_MAP.md`。

验收标准：
文档包含 upload/status/search/chunk/citation API、字段映射、错误映射、未知项。

验证方式：
`rg -n "upload|retrieve|wiki|citation|Evidence" pa-ai-workbench/docs/PHASE3_WEKNORA_API_MAP.md`。

风险：
WeKnora API 与源码能力不完全一致，需要记录 gap。

状态：[x]

#### P3-M1-B2：WeKnoraKnowledgeBackend 文档上传/状态适配

目标：
让 PA `/api/documents` 能通过 WeKnora 完成真实文档上传和状态查询。

范围：
实现 adapter 的 upload/status；PA DB 保存 external ids。

输入：
WeKnora upload/status API map。

输出：
PA DocumentRead 显示 WeKnora 状态和 external_doc_id。

验收标准：
上传脱敏文件后可看到 WeKnora 处理状态，不 fallback 到 mock。

验证方式：
新增或更新 backend smoke；手动 curl 上传脱敏文件。

风险：
WeKnora 异步处理耗时较长，前端需要轮询或刷新。

状态：[x]

#### P3-M1-B3：WeKnoraKnowledgeBackend retrieve 适配

目标：
让 PA Agent 能通过 WeKnora 检索 document/wiki evidence。

范围：
实现 query、top_k、filters、document_ids、source_type 映射。

输入：
WeKnora search/retrieve API。

输出：
`KnowledgeEngine.retrieve()` 返回 PA `Evidence`。

验收标准：
同一脱敏文档索引后，query 能返回 `source=weknora_api` 的 evidence。

验证方式：
adapter contract test + smoke retrieve。

风险：
WeKnora score 范围和 PA score 假设不同，需要 normalize 或保留 metadata。

状态：[x]

#### P3-M1-B4：Evidence / Citation 标准化与 contract tests

目标：
保证 WeKnora evidence 一定能转成可追溯 citation。

范围：
CitationBuilder、CitationChecker、schemas、tests。

输入：
WeKnora retrieve response fixtures。

输出：
contract tests 覆盖 document_chunk 和 wiki_page。

验收标准：
非 mock citation 必须有 evidence_id、source_type、chunk/wiki id。

验证方式：
`python -m compileall agent knowledge_engine backend/app` 和 targeted tests。

风险：
WeKnora 返回字段缺失时必须 fail closed，不生成伪 citation。

状态：[x]

#### P3-M1-B5：文档 chunk / evidence 预览 API 接入

目标：
让前端资料库可查看 WeKnora chunk/evidence 预览。

范围：
PA `/api/documents/{id}/chunks` 适配 WeKnora 或本地缓存。

输入：
WeKnora chunk/list API。

输出：
DocumentChunkRead 或等价 response。

验收标准：
前端 chunk preview 显示真实 WeKnora chunk id、位置、excerpt。

验证方式：
curl chunks API + 前端页面检查。

风险：
若 WeKnora 不支持 chunk list，需要 M1 fallback 为检索 evidence preview，并明确标记。

状态：[x]

### M1-C：WeKnora Wiki Adapter

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-C1 | WeKnora Wiki API 审计与响应映射 | [x] |
| P3-M1-C2 | Wiki search/read 适配 | [x] |
| P3-M1-C3 | Wiki draft/create/update 适配 | [x] |
| P3-M1-C4 | Wiki publish/index 状态适配 | [x] |
| P3-M1-C5 | Wiki citation/source refs 标准化 | [ ] |

#### P3-M1-C1：WeKnora Wiki API 审计与响应映射

目标：
明确 WeKnora Wiki API 能力边界和 PA Wiki schema 映射。

范围：
审计 wiki_page、wiki_ingest、handler、docs/swagger。

输入：
WeKnora Wiki API 和源码。

输出：
Wiki API map，记录 draft/publish/index/source refs 能力。

验收标准：
明确哪些能力直接调用 WeKnora，哪些需要 PA 本地补偿。

验证方式：
`rg -n "WikiPage|draft|publish|slug|citation" docs/PHASE3_WEKNORA_API_MAP.md`。

风险：
Wiki ingest 能力可能与 PA “output -> draft” 不完全匹配。

状态：[x]

#### P3-M1-C2：Wiki search/read 适配

目标：
PA `/api/wiki/search` 和 `/api/wiki/pages/{slug}` 使用 WeKnora Wiki。

范围：
Adapter search/read、response mapper、错误处理。

输入：
WeKnora Wiki search/read API。

输出：
PA WikiPageSummary / WikiPage。

验收标准：
可搜索和读取 WeKnora published Wiki 页面。

验证方式：
curl search/read + contract fixtures。

风险：
slug 与 WeKnora page id 可能不是一一对应，需要 metadata 保存外部 id。

状态：[x]

#### P3-M1-C3：Wiki draft/create/update 适配

目标：
PA 能从 Agent output 创建 Wiki 草稿，并支持编辑保存。

范围：
draft from output service、Wiki Adapter create/update。

输入：
PA GeneratedOutput + citations。

输出：
WeKnora draft Wiki 或 PA local draft with sync state。

验收标准：
草稿保存后可在 PA Wiki 页面打开，且来源引用不丢失。

验证方式：
smoke：output -> draft -> read。

风险：
WeKnora 若无直接 draft API，需要本地 draft + publish sync 策略。

状态：[x]

#### P3-M1-C4：Wiki publish/index 状态适配

目标：
发布 Wiki 后可进入 WeKnora RAG 检索。

范围：
publish API、index status、frontend status。

输入：
Wiki draft。

输出：
published page + indexed status。

验收标准：
发布后 retrieve 能返回 `source_type=wiki_page` evidence。

验证方式：
smoke：publish -> retrieve query -> wiki evidence。

风险：
WeKnora Wiki 索引异步完成，需要轮询或刷新状态。

状态：[x]

#### P3-M1-C5：Wiki citation/source refs 标准化

目标：
Wiki 页面保留来源 output、document、chunk/citation refs。

范围：
WikiCitation mapper、metadata、frontend display。

输入：
PA output citations 与 WeKnora wiki response。

输出：
PA `wiki_citations` / `citations` 展示结构。

验收标准：
Wiki 页面可展示 source output、document refs、citation ids。

验证方式：
API response 检查 + 前端 Bindings/Sources 展示。

风险：
WeKnora 不保存 PA output id，需要 PA metadata 补充。

状态：[x]

### M1-D：PA Agent 证据工作流

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-D1 | RetrieverTool 切换 WeKnora evidence 验收 | [x] |
| P3-M1-D2 | QA workflow WeKnora evidence prompt | [x] |
| P3-M1-D3 | Policy workflow WeKnora evidence prompt | [ ] |
| P3-M1-D4 | Case workflow WeKnora evidence prompt | [ ] |
| P3-M1-D5 | Wiki draft workflow WeKnora refs | [ ] |
| P3-M1-D6 | CitationChecker fail-closed 策略 | [ ] |

#### P3-M1-D1：RetrieverTool 切换 WeKnora evidence 验收

目标：
确保 Agent 通过统一 RetrieverTool 获取 WeKnora evidence。

范围：
Agent tools、factory/env、smoke。

输入：
`KNOWLEDGE_BACKEND=weknora_api`。

输出：
Agent citations source 为 `weknora_api`。

验收标准：
不修改 workflow 业务逻辑即可从 WeKnora 获取 evidence。

验证方式：
agent smoke with patched/test WeKnora backend 或真实脱敏环境。

风险：
现有 tests 可能依赖 mock/extracted，需要分层保留。

状态：[x]

#### P3-M1-D2：QA workflow WeKnora evidence prompt

目标：
QA 输出严格基于 WeKnora evidence。

范围：
QA prompt、metadata、warnings。

输入：
question + citations。

输出：
markdown answer + citation_count + warnings。

验收标准：
无 evidence 时明确依据不足；有 evidence 时引用编号。

验证方式：
unit prompt test + smoke run_analysis。

风险：
模型可能不按编号引用，需要 prompt 和后处理提示。

状态：[x]

#### P3-M1-D3：Policy workflow WeKnora evidence prompt

目标：
政策分析输出可直接服务 PA 业务试点。

范围：
policy prompt、结构化输出、warnings。

输入：
topic + policy/case/wiki evidence。

输出：
摘要、要求、影响风险、建议动作、不确定性。

验收标准：
关键判断有 citation；证据不足列入待补证据。

验证方式：
smoke run_analysis policy_analysis。

风险：
模型输出可能过长或不稳定，M1 先固定模板。

状态：[ ]

#### P3-M1-D4：Case workflow WeKnora evidence prompt

目标：
案例复盘基于真实案例资料或 Wiki evidence。

范围：
case prompt、输出结构、citation。

输入：
case query + evidence。

输出：
背景、时间线、动作、风险、经验、待补材料。

验收标准：
无 evidence 不编造案例细节。

验证方式：
smoke run_analysis case_review。

风险：
案例资料不足时输出需要明显保守。

状态：[ ]

#### P3-M1-D5：Wiki draft workflow WeKnora refs

目标：
Wiki 草稿保留 WeKnora evidence refs。

范围：
WikiDraftWriterTool、wiki_service、adapter。

输入：
GeneratedOutput + citations。

输出：
Wiki draft payload with source refs。

验收标准：
草稿内容和 metadata 能追溯 output/citations。

验证方式：
smoke output -> draft。

风险：
WeKnora 与 PA refs 字段不同，需要 metadata bridge。

状态：[ ]

#### P3-M1-D6：CitationChecker fail-closed 策略

目标：
防止不完整 WeKnora citation 被保存为真实引用。

范围：
CitationChecker、generation_service validation。

输入：
malformed citation fixtures。

输出：
warnings 或 validation error。

验收标准：
缺少 evidence_id/source_type/chunk/wiki id 的非 mock citation 不通过。

验证方式：
targeted tests。

风险：
过严可能导致部分可用 evidence 被过滤，需在 adapter map 中补齐字段。

状态：[ ]

### M1-E：PA 前端试点体验

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-E1 | 首页/状态页展示 WeKnora backend 状态 | [ ] |
| P3-M1-E2 | 资料库 WeKnora 索引状态与错误展示 | [ ] |
| P3-M1-E3 | 分析台 Real WeKnora RAG evidence 展示 | [ ] |
| P3-M1-E4 | Wiki draft/publish/index 状态展示 | [ ] |
| P3-M1-E5 | 历史 output 到 Wiki 草稿入口核对 | [ ] |

#### P3-M1-E1：首页/状态页展示 WeKnora backend 状态

目标：
用户能看出当前是否连接真实 WeKnora。

范围：
status/model status API 和首页 UI。

输入：
backend status。

输出：
WeKnora connected/auth/workspace/kb 状态。

验收标准：
mock、weknora unavailable、weknora connected 三种状态清晰区分。

验证方式：
frontend build + browser check。

风险：
不要显示 token 或私有 endpoint 细节。

状态：[ ]

#### P3-M1-E2：资料库 WeKnora 索引状态与错误展示

目标：
资料库页面能服务真实上传和处理。

范围：
LibraryPage、DocumentStatusBadge、chunks preview。

输入：
DocumentRead/status/events/chunks。

输出：
parse/chunk/embedding/index/failure 展示。

验收标准：
用户能判断何时可以提问、失败在哪里。

验证方式：
frontend build + manual upload flow。

风险：
WeKnora 异步状态命名变化，依赖 Adapter 标准状态。

状态：[ ]

#### P3-M1-E3：分析台 Real WeKnora RAG evidence 展示

目标：
分析页能明确展示真实 evidence。

范围：
AnalysisPage、CitationList、WarningList。

输入：
AnalysisRunResponse citations。

输出：
RAG mode、document/wiki counts、evidence cards。

验收标准：
非 mock citation 显示为 Real WeKnora RAG。

验证方式：
frontend build + run_analysis。

风险：
metadata_json 解析失败时要降级展示基础字段。

状态：[ ]

#### P3-M1-E4：Wiki draft/publish/index 状态展示

目标：
Wiki 页面展示是否已发布、是否进入 RAG。

范围：
WikiPage UI、publish action、index status。

输入：
WikiPageRead。

输出：
draft/published/indexed/not indexed 状态。

验收标准：
发布前不误导用户“已可检索”。

验证方式：
frontend build + wiki smoke。

风险：
WeKnora 索引异步完成，状态刷新需清晰。

状态：[ ]

#### P3-M1-E5：历史 output 到 Wiki 草稿入口核对

目标：
历史记录可继续沉淀为 Wiki。

范围：
HistoryPage、output detail、create draft action。

输入：
GeneratedOutput + citations。

输出：
Wiki draft。

验收标准：
历史 output citation refs 不丢失。

验证方式：
manual: history -> draft -> wiki page。

风险：
历史中 mock output 不应默认标记为真实 Wiki 来源。

状态：[ ]

### M1-F：验收与发布检查

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M1-F1 | M1 WeKnora RAG E2E smoke | [ ] |
| P3-M1-F2 | M1 Wiki E2E smoke | [ ] |
| P3-M1-F3 | M1 Agent E2E smoke | [ ] |
| P3-M1-F4 | M1 frontend build 与主流程浏览器检查 | [ ] |
| P3-M1-F5 | M1 release checklist 与安全检查 | [ ] |

#### P3-M1-F1：M1 WeKnora RAG E2E smoke

目标：
验证真实脱敏文档能通过 WeKnora RAG 被 PA 检索。

范围：
脚本或手动验收文档。

输入：
脱敏 PDF/DOCX/MD。

输出：
non-mock document_chunk evidence。

验收标准：
evidence source 为 `weknora_api`，citation 可追溯。

验证方式：
`python backend/scripts/smoke_weknora_rag_m1.py`。

风险：
真实服务不可用时必须 fail，不 fallback。

状态：[ ]

#### P3-M1-F2：M1 Wiki E2E smoke

目标：
验证 Wiki 草稿、发布、再检索闭环。

范围：
output -> draft -> publish -> retrieve。

输入：
带 citation 的 Agent output。

输出：
wiki_page evidence。

验收标准：
发布后 query 命中 wiki_page source_type。

验证方式：
`python backend/scripts/smoke_weknora_wiki_m1.py`。

风险：
Wiki 索引异步，需要等待/重试策略。

状态：[ ]

#### P3-M1-F3：M1 Agent E2E smoke

目标：
验证 QA / policy / case 三个 workflow 使用 WeKnora evidence。

范围：
run_analysis API。

输入：
脱敏资料与 queries。

输出：
outputs + citations。

验收标准：
三个 workflow 至少各有一次 non-mock citation；无 evidence case 有 warning。

验证方式：
`python backend/scripts/smoke_weknora_agent_m1.py`。

风险：
模型输出差异导致断言要聚焦 citation 与状态，不断言完整文本。

状态：[ ]

#### P3-M1-F4：M1 frontend build 与主流程浏览器检查

目标：
确认 M1 前端可用。

范围：
frontend build、主要页面、关键状态。

输入：
已运行 backend/frontend。

输出：
浏览器检查记录。

验收标准：
首页、资料库、分析台、Wiki、历史无明显阻断错误。

验证方式：
`npm run build` + Browser/Playwright screenshot。

风险：
真实 WeKnora 环境不可用时至少要检查错误态。

状态：[ ]

#### P3-M1-F5：M1 release checklist 与安全检查

目标：
上线前阻止 mock、密钥和敏感文件进入试点。

范围：
release checklist、git status ignored、env sample。

输入：
当前工作树和部署配置。

输出：
`pa-ai-workbench/docs/PHASE3_M1_RELEASE_CHECKLIST.md`。

验收标准：
mock 关闭、WeKnora 配置存在、敏感文件未提交。

验证方式：
`git status --short`、`git status --ignored --short`、release checker。

风险：
根目录不是 git repo，需在 `pa-ai-workbench` repo 内检查。

状态：[ ]

### M2-A：稳定性与错误处理

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M2-A1 | WeKnora Adapter 超时、重试、错误码规范 | [ ] |
| P3-M2-A2 | 文档处理状态轮询与失败恢复 | [ ] |
| P3-M2-A3 | Wiki 发布/索引异步状态恢复 | [ ] |
| P3-M2-A4 | Agent 无证据和弱证据策略增强 | [ ] |

### M2-B：引用定位与检索调试

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M2-B1 | Citation 跳转到文档 chunk 或 Wiki page | [ ] |
| P3-M2-B2 | RAG retrieve 调试接口对接 WeKnora | [ ] |
| P3-M2-B3 | Evidence dedup 与 score 展示规范 | [ ] |
| P3-M2-B4 | 检索参数 top_k/source_type/filter 前端调试面板 | [ ] |

### M2-C：前端体验产品化

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M2-C1 | 资料库批量状态刷新与筛选 | [ ] |
| P3-M2-C2 | 分析台 evidence 展开、复制、定位体验 | [ ] |
| P3-M2-C3 | Wiki 编辑体验与发布确认 | [ ] |
| P3-M2-C4 | 历史页按任务类型、证据状态筛选 | [ ] |

### M2-D：运维与可观测

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M2-D1 | WeKnora 调用日志元数据与脱敏 | [ ] |
| P3-M2-D2 | PA task / adapter request id 串联 | [ ] |
| P3-M2-D3 | 试点反馈问题模板与回归清单 | [ ] |
| P3-M2-D4 | 内网部署 README 和故障排查文档 | [ ] |

### M3-A：Adapter 抽象增强

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M3-A1 | KnowledgeBackend contract tests 完整化 | [ ] |
| P3-M3-A2 | mock / weknora_api / extracted parity matrix | [ ] |
| P3-M3-A3 | backend feature flags 与能力探测 | [ ] |
| P3-M3-A4 | 多 KB / workspace 映射抽象 | [ ] |

### M3-B：Python extracted fallback

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M3-B1 | extracted fallback 与 WeKnora API schema 对齐 | [ ] |
| P3-M3-B2 | Python chunk / retrieval 与 WeKnora 结果对照测试 | [ ] |
| P3-M3-B3 | Wiki fallback 的最小同步策略 | [ ] |
| P3-M3-B4 | 可切换 backend 的 E2E smoke | [ ] |

### M3-C：混合检索、重排、评估预留

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P3-M3-C1 | WeKnora hybrid/rerank 能力参数透出设计 | [ ] |
| P3-M3-C2 | PA retrieval quality golden set | [ ] |
| P3-M3-C3 | RAG 质量指标与人工评价表 | [ ] |
| P3-M3-C4 | Agent 输出 faithfulness 回归验收 | [ ] |

## 11. 任务执行协议

AI 开发工具每次只执行一个任务编号。

默认执行流程：

```text
读取 PHASE3_SPEC.md
-> 定位一个任务编号
-> 列出计划修改文件与验证方式
-> 实现或编写对应文档
-> 运行验收
-> 验收通过后更新 PHASE3_SPEC.md 任务状态
-> 运行 git 安全检查
-> 只 stage 当前任务相关文件
-> 自动创建一个任务级 commit
-> 汇报 commit hash、验证结果、风险和下一个建议任务
```

自动 commit 规则：

1. 一个任务编号一个 commit。
2. 只有验收通过后才允许 commit。
3. commit 必须包含任务编号。
4. commit 只包含当前任务相关文件。
5. 不自动 push；push 必须等用户明确要求。
6. 如果工作树里有与当前任务无关的修改，不能 stage 这些文件，并需在报告中说明。
7. 如果发现敏感文件、数据库、上传文件、日志或真实资料，必须停止 commit 并报告。

commit message 格式：

```text
docs: complete P3-M1-A1 weknora deployment audit
feat: complete P3-M1-B3 weknora retrieve adapter
test: complete P3-M1-F1 weknora rag smoke
chore: complete P3-M1-F5 release checklist
```

自动 commit 前必须运行：

```bash
git status --short
git status --ignored --short
```

禁止自动 stage / commit：

```text
.env
backend/data/
backend/uploads/
logs/
*.db
*.sqlite
node_modules/
dist/
API keys
service tokens
真实资料
未脱敏输出
```

推荐指令：

```text
请使用 phase3-architect，执行 PHASE3_SPEC.md 中的 P3-M1-A1。只做设计审计，不写产品代码。验收通过后自动 commit，不要 push。
```

```text
请使用 phase3-weknora-adapter，执行 PHASE3_SPEC.md 中的 P3-M1-B2。完成后运行验收，更新任务状态，自动 commit，不要 push。
```

```text
请使用 phase3-qa-tester，验收 PHASE3_SPEC.md 中的 P3-M1-F1。若产生测试脚本或文档修改，验收通过后自动 commit，不要 push。
```

禁止：

- 一次性实现多个未确认任务。
- 前端直接调用 WeKnora。
- Agent 直接依赖 WeKnora 原始响应。
- 跳过验收就标记 `[x]`。
- 把 mock 结果作为 M1 上线通过依据。
- 提交敏感文件。
- 自动 push。
- 编造 citation。

## 12. 第三阶段验收标准

### 12.1 M1 最小验收

M1 最小验收必须通过：

1. WeKnora 后端可启动。
2. PA 能通过服务账号认证 WeKnora。
3. 脱敏文档可上传并索引。
4. PA retrieve 返回 `source=weknora_api` evidence。
5. QA / policy / case 至少各有一次 non-mock citation。
6. Citation 可追溯到 chunk 或 Wiki page。
7. Wiki draft 可创建、编辑、发布。
8. 发布 Wiki 可被 retrieve。
9. 前端 build 通过。
10. release checker 确认 mock 关闭、敏感文件未提交。

### 12.2 M2 最小验收

M2 最小验收：

1. WeKnora 常见错误有可读提示。
2. 文档和 Wiki 异步状态可恢复。
3. Citation 可定位。
4. 检索调试可用。
5. 试点反馈回归清单通过。

### 12.3 M3 最小验收

M3 最小验收：

1. backend contract tests 覆盖 mock / weknora_api / extracted。
2. extracted fallback 可在无 WeKnora 环境跑通最小链路。
3. 有 retrieval quality golden set。
4. hybrid/rerank/评估能力有明确扩展接口。

## 13. 后续阶段预留

第四阶段可考虑：

- 更深的 PA 工作流 Agent。
- 审批流。
- 多用户权限。
- IM 集成。
- Word / PPT 输出。
- Wiki 版本 diff。
- 知识图谱。
- 长期记忆。
- 数据治理与审计。
