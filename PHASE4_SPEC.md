# PA AI Workbench PHASE4_SPEC

> 版本：0.4
>
> 阶段名称：RAG / Wiki / 知识问答质量优化与前端中文化阶段
>
> 用途：作为第四阶段 AI 开发的长期事实源，驱动 `PHASE4_SPEC.md + phase4-rag-wiki-qa skill` 的逐任务开发。
>
> 第一阶段事实源：`DEV_SPEC.md`
>
> 第二阶段事实源：`PHASE2_SPEC.md`
>
> 第三阶段事实源：`PHASE3_SPEC.md`
>
> 第四阶段事实源：`PHASE4_SPEC.md`

## 0. 第四阶段设计总则

第四阶段第一段不做新功能扩张，而是把已经形成的 RAG、Wiki、知识问答和前端体验打磨成可测试、可解释、可复用的闭环。

第四阶段第一段核心方向：

```text
准备合成脱敏测试语料
-> 建立 RAG / Wiki 检索质量基线
-> 优化知识问答单工作流
-> 中文化关键前端术语
-> 保持调试参数和正式问答体验分层
```

必须坚持以下边界：

1. PA AI Workbench 仍是独立 PA 产品，不是 WeKnora 前端皮肤。
2. 本阶段主线是能力质量和易用性，不是继续扩功能面。
3. RAG / Wiki 能力仍必须通过 PA `KnowledgeBackend Adapter` 标准化。
4. 正式知识问答界面保持低门槛，不暴露复杂工程参数。
5. RAG / Wiki 调试参数只放在专门调试页，用于测试、定位和调参。
6. Agent 范围只聚焦 `knowledge_qa`，暂不设计复杂 Agent 编排。
7. `policy_analysis` 和 `case_review` 在本阶段保持现状，除非后续单独任务化。
8. 前端中文化优先覆盖用户可见核心术语，不改产品架构。
9. mock、fixture、本地 live、真实 WeKnora live 必须分开记录。
10. mock / fixture 结果不能冒充真实 RAG / Wiki 验收通过。
11. 真实资料、上传文件、数据库、日志、`.env`、API Key 禁止提交。

第四阶段第一段一句话定义：

```text
第四阶段第一段以 RAG / Wiki / 知识问答质量测试为主线，用合成脱敏语料验证检索、Wiki、引用和拒答能力，同时把前端核心英文术语降为中文可理解表达。
```

## 1. 阶段目标与成功标准

### 1.1 完整阶段目标

第四阶段第一段完成后，应能做到：

1. 使用一组合成脱敏中文测试文档反复验证 RAG / Wiki 能力。
2. 测试文档覆盖政策、法规法条、历史案例、FAQ、Wiki 专题、干扰材料、新旧版本冲突。
3. 每个测试问题都有期望命中文档、答案要点和 citation 要求。
4. RAG 调试页能调整关键检索参数并显示可追溯证据。
5. Wiki 草稿、发布、索引、检索、引用链路可被测试。
6. `knowledge_qa` 能优先使用真实 evidence 回答，并在无依据时明确拒答或提示依据不足。
7. 知识问答结果能展示文档证据和 Wiki 证据来源。
8. 前端首页、资料库、RAG 调试页、Wiki 页、知识问答页中的关键英文术语完成中文化。
9. 阶段验收能区分 mock、fixture、本地 live、真实 WeKnora live。

### 1.2 非目标

本阶段第一段不做：

- Word / PPT 导出。
- 复杂多 Agent 工作流。
- Agent Supervisor。
- 权限 / 审批 / IM 集成。
- 知识图谱。
- 长期记忆。
- 前端大改版或视觉重构。
- 真实敏感资料接入。
- WeKnora 后端能力重写。

## 2. 测试语料策略

### 2.1 定位

测试语料不是 PA 场景演示稿，而是面向 RAG / Wiki 性能与可靠性的通用知识库测试集。

内容形态可以参考 PA 常见材料：

- 政策通知。
- 法规法条。
- 历史案例。
- FAQ / 操作手册。
- Wiki 专题。
- 干扰材料。
- 新旧版本冲突材料。

核心测试目标：

1. RAG 能否在长文档中命中正确条款。
2. 相似政策、法规或案例之间是否会混淆。
3. 新旧版本冲突时能否引用正确版本。
4. Wiki 发布后能否进入检索。
5. 文档证据和 Wiki 证据能否一起被知识问答引用。
6. 没有依据时能否明确说资料不足。
7. 干扰文档是否会被错误召回。

### 2.2 语料包要求

测试语料包应包含：

1. 8-10 份中文 Markdown 文档。
2. 每份文档 800-1800 字。
3. 每份文档必须包含唯一测试锚点，例如 `TEST-RAG-001`。
4. 文档之间要设计相似点、冲突点和交叉引用。
5. 所有内容必须虚构、脱敏。
6. 禁止包含真实公司、真实个人、真实客户、真实项目、真实内网地址、真实政策编号或敏感信息。

建议文档类型：

| 类型 | 数量 | 作用 |
| --- | --- | --- |
| 政策通知类 | 2 | 测试适用范围、执行期限、例外情形 |
| 法规法条类 | 2 | 测试条款定位、相似条款区分 |
| 历史案例类 | 2 | 测试时间线、处置方式、复盘结论 |
| FAQ / 操作手册类 | 1 | 测试流程型问答 |
| Wiki 种子材料 | 1 | 测试 Wiki 创建、发布、检索、引用 |
| 干扰材料 | 1 | 测试错误召回控制 |
| 新旧版本冲突材料 | 0-1 | 测试时间和版本判断 |

### 2.3 问题集要求

测试问题集应包含 20-25 个问题，每个问题包含：

- 问题文本。
- 问题类型：精确事实 / 条款定位 / 跨文档综合 / 案例复盘 / Wiki 检索 / 无答案 / 干扰排除 / 新旧版本冲突。
- 期望命中的文档锚点。
- 期望答案要点。
- 是否必须引用文档。
- 是否必须引用 Wiki。
- 是否应该回答“依据不足”。

### 2.4 测试文档生成提示词

如需生成语料，可使用：

```text
请准备一组合成脱敏测试文档，用于测试 RAG、Wiki 检索和知识问答能力。

核心目标：
测试系统的检索准确性、跨文档综合、条款定位、Wiki 发布后检索、引用追溯、无答案判断和干扰文档排除能力。

不需要过分贴近真实 PA 业务，但文档类型可以参考公共事务、政策研究、法规分析、历史案例复盘等常见材料形态。

内容要求：
1. 所有内容必须虚构、脱敏，不包含真实公司、真实个人、真实客户、真实项目、真实内网地址、真实政策编号或敏感信息。
2. 生成 8-10 份中文 Markdown 文档，每份 800-1800 字。
3. 每份文档必须有唯一测试锚点，例如 TEST-RAG-001。
4. 文档之间要故意设计一些相似点、冲突点和交叉引用，方便测试检索区分能力。

文档类型建议：
1. 政策通知类 2 份：
   - 包含发布日期、适用范围、核心要求、例外情形、执行期限。
   - 两份政策在主题上相似，但适用对象或时间要求不同。

2. 法规法条类 2 份：
   - 使用条款结构，例如第一条、第二条、第三条。
   - 包含定义、禁止事项、豁免条件、处罚或整改要求。
   - 至少设计一条容易和另一份文档混淆的相似条款。

3. 历史案例类 2 份：
   - 包含背景、时间线、关键动作、处理结果、复盘结论。
   - 两个案例有相似事件类型，但结果或处置方式不同。

4. FAQ / 操作手册类 1 份：
   - 包含常见问题、操作步骤、注意事项。
   - 用于测试系统能否回答流程型问题。

5. Wiki 种子材料 1 份：
   - 写成可沉淀为 Wiki 的专题材料。
   - 包含主题定义、关联政策、历史案例、常见误区。
   - 用于测试 Wiki 创建、发布、检索和知识问答引用。

6. 干扰材料 1 份：
   - 主题表面相似，但关键内容与测试问题无关。
   - 用于测试系统是否错误召回。

7. 可选：新旧版本冲突材料 1 份：
   - 同一主题下旧版要求和新版要求不同。
   - 用于测试系统是否能识别时间和版本。

问题集要求：
请额外生成 20-25 个测试问题，每个问题包含：
- 问题文本
- 问题类型：精确事实 / 条款定位 / 跨文档综合 / 案例复盘 / Wiki 检索 / 无答案 / 干扰排除 / 新旧版本冲突
- 期望命中的文档锚点
- 期望答案要点
- 是否必须引用文档
- 是否必须引用 Wiki
- 是否应该回答“依据不足”

输出格式：
使用 Markdown，分为：
1. 测试文档清单
2. 每份测试文档正文
3. 测试问题集
4. 期望命中矩阵
```

## 3. 调试参数与正式体验分层

### 3.1 正式知识问答页

正式知识问答页应保持简单：

- 问题输入。
- 可选检索范围：全部 / 文档 / Wiki。
- 回答。
- 引用。
- 依据不足提示。

正式知识问答页不展示：

- raw filters。
- raw metadata。
- rerank trace。
- hybrid trace。
- score threshold。
- backend raw response。
- WeKnora 原始字段。

### 3.2 RAG / Wiki 调试页

RAG / Wiki 调试页用于测试和定位问题，可以开放：

- `top_k`。
- 检索来源：全部 / 文档 / Wiki。
- KB ID。
- Document IDs。
- business_area。
- document_type。
- 分数阈值。
- hybrid 开关。
- rerank 开关。
- trace / debug 信息。
- evidence source / source_type / evidence_id / chunk_id / wiki_page_id。

调试页必须中文化，但可以保留必要技术字段名。

## 4. 开发阶段与任务表

状态标记：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
```

每个任务执行格式：

```text
读取 PHASE4_SPEC.md
-> 定位任务编号
-> 列出计划修改文件
-> 实现或设计
-> 运行验收命令
-> 汇报修改文件、测试结果、风险
-> 更新任务状态
```

### P4-A：测试语料与问题集规范

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-A1 | 合成脱敏测试语料规范定稿 | [x] |
| P4-A2 | 测试问题集与期望命中矩阵规范 | [ ] |
| P4-A3 | 测试语料安全检查规则 | [ ] |
| P4-A4 | 合成脱敏测试语料包生成 | [x] |

#### P4-A1：合成脱敏测试语料规范定稿

目标：
确定 RAG / Wiki / 知识问答测试语料的内容类型、长度、锚点、结构和脱敏规则。

范围：
只写测试语料规范或 fixture 说明，不创建真实敏感资料，不接入产品代码。

输入：
本文件第 2 节测试语料策略。

输出：
测试语料规范文档或本文件对应章节更新。

验收标准：
规范能指导生成 8-10 份合成脱敏文档，并覆盖政策、法规、案例、FAQ、Wiki、干扰、新旧版本冲突。

验证方式：
`rg -n "TEST-RAG|政策通知|法规法条|历史案例|Wiki|干扰|新旧版本" PHASE4_SPEC.md`。

风险：
语料过度贴近真实业务会带来敏感信息风险；语料过度抽象会降低检索测试价值。

规范输出：

#### P4-A1.1 语料包定位

Phase 4 第一版语料包定位为 RAG / Wiki / 知识问答质量测试基准，不是演示稿，也不是用户真实业务资料。语料必须优先服务以下测试目标：

1. 文档 chunk 是否能命中正确条款、事实和案例段落。
2. 相似主题之间是否会混淆，例如旧版 / 新版专项信息报送政策。
3. Wiki 发布后是否能以 `source_type=wiki_page` 进入检索和引用。
4. 干扰材料是否会被错误当成政策或法规依据。
5. 无答案问题是否能触发“依据不足”，而不是编造外部事实。
6. 新旧版本冲突时是否能识别当前应优先引用新版要求。

#### P4-A1.2 文档数量、长度与文件结构

第一版语料包采用 8-10 份中文 Markdown 文档。当前基准为 9 份，位于 `backend/fixtures/phase4_rag_wiki_qa/documents/`。

每份文档要求：

- 使用 Markdown，正文适合被段落切分和 chunking。
- 单篇建议 800-1800 字；若低于该范围，必须仍覆盖足够的条款、时间线或问答细节。
- 文件名使用三位序号加英文语义名，例如 `001_old_reporting_policy.md`。
- 标题、正文和 manifest 中必须能定位同一个唯一测试锚点。
- 不依赖外部图片、附件、真实链接或私有系统地址。

推荐目录结构：

```text
backend/fixtures/phase4_rag_wiki_qa/
├── manifest.json
├── questions.json
├── hit_matrix.md
└── documents/
    ├── 001_*.md
    ├── ...
    └── 009_*.md
```

#### P4-A1.3 文档类型与覆盖比例

语料包必须覆盖以下材料形态，后续替换或扩展时也应保持这些类别：

| 类型 | 建议数量 | 当前锚点示例 | 测试用途 |
| --- | --- | --- | --- |
| 政策通知 | 2 | `TEST-RAG-001`、`TEST-RAG-002` | 测试适用范围、执行期限、例外情形和新旧版本冲突 |
| 法规法条 | 2 | `TEST-RAG-003`、`TEST-RAG-004` | 测试条款定位、相似条款区分、发布校验和访问审计 |
| 历史案例 | 2 | `TEST-RAG-005`、`TEST-RAG-006` | 测试时间线、处置动作、复盘结论和案例混淆 |
| FAQ / 操作手册 | 1 | `TEST-RAG-007` | 测试流程型问答、上传前检查和调试步骤 |
| Wiki 种子材料 | 1 | `TEST-WIKI-001` | 测试 Wiki 草稿、发布、索引、检索和 Wiki 引用 |
| 干扰材料 | 1 | `TEST-DISTRACTOR-001` | 测试错误召回控制和干扰排除 |
| 新旧版本冲突 | 贯穿政策组 | `TEST-RAG-001`、`TEST-RAG-002` | 测试当前版本优先和旧版差异说明 |

#### P4-A1.4 锚点、manifest 与测试字段

每份文档必须有唯一锚点，锚点写入正文，并同步登记到 `manifest.json`。锚点命名规则：

- 普通 RAG 文档使用 `TEST-RAG-NNN`。
- Wiki 种子材料使用 `TEST-WIKI-NNN`。
- 干扰材料使用 `TEST-DISTRACTOR-NNN`。
- 锚点编号不可复用；删除或替换文档时，必须同步更新 `questions.json` 与 `hit_matrix.md`。

`manifest.json` 中每份文档至少包含：

- `anchor`：唯一测试锚点。
- `filename`：相对 `backend/fixtures/phase4_rag_wiki_qa/` 的文件路径。
- `title`：中文标题。
- `type`：材料类型，例如 `policy_notice`、`regulation_articles`、`historical_case`、`faq_manual`、`wiki_seed`、`distractor`。
- `test_purpose`：测试目的，例如 `version_conflict`、`citation_accuracy`、`article_lookup`、`wiki_retrieve`。
- `key_terms`：用于检索调试的关键词。

#### P4-A1.5 内容设计要求

语料正文需要故意包含可测试结构，而不是只写泛泛背景：

1. 政策通知必须包含发布日期、适用范围、普通事项时限、例外情形、附件或复核规则。
2. 法规法条必须使用条款结构，至少包含定义、禁止或限制事项、校验要求、整改或撤回要求。
3. 历史案例必须包含背景、时间线、关键动作、结果、复盘结论，并与另一案例存在表面相似但结论不同的点。
4. FAQ / 操作手册必须包含可直接回答的步骤型问题，也要包含“依据不足”或调试边界说明。
5. Wiki 种子材料必须能沉淀成专题页，并包含关联政策、法规、案例和常见误区。
6. 干扰材料必须与主问题表面相似，但关键结论不能作为政策、法规或案例依据。
7. 新旧版本冲突必须让旧版和新版同时可被检索到，以测试回答阶段是否说明版本差异。

#### P4-A1.6 脱敏与禁止内容边界

所有语料必须是合成脱敏材料。允许使用虚构机构、虚构案例名、虚构编号和虚构时间线；禁止包含：

- 真实公司、真实个人、真实客户、真实项目。
- 真实政策编号、真实合同编号、真实监管编号。
- 真实内网地址、私有系统 URL、邮箱、手机号、身份证号。
- API Key、service token、Bearer token、数据库连接串。
- 上传文件、数据库、日志、未脱敏模型输出或真实用户问答记录。

如果后续需要加入更接近真实形态的测试材料，必须先脱敏并作为单独任务审查，不能直接放入当前 fixture。

状态：[x]

#### P4-A2：测试问题集与期望命中矩阵规范

目标：
定义 20-25 个测试问题的结构、类型和评估字段。

范围：
只定义问题集格式，不实现自动评测脚本。

输入：
测试语料规范。

输出：
问题集字段说明和期望命中矩阵格式。

验收标准：
每个问题都能记录问题类型、期望命中文档锚点、答案要点、文档引用要求、Wiki 引用要求和依据不足要求。

验证方式：
`rg -n "期望命中|答案要点|必须引用文档|必须引用 Wiki|依据不足" PHASE4_SPEC.md`。

风险：
只写问题不写期望命中会让 RAG 调试变成主观感觉。

状态：[ ]

#### P4-A3：测试语料安全检查规则

目标：
确保测试语料不包含真实敏感信息。

范围：
定义禁止内容、人工检查清单和后续可脚本化检查方向。

输入：
测试语料规范和仓库安全边界。

输出：
安全检查规则。

验收标准：
规则覆盖真实公司、真实个人、真实客户、真实项目、真实内网地址、真实政策编号、API Key、服务 token、上传文件和未脱敏输出。

验证方式：
`rg -n "真实公司|真实个人|API Key|service token|未脱敏|上传文件" PHASE4_SPEC.md`。

风险：
测试阶段最容易把真实资料误提交，必须先把边界写清楚。

状态：[ ]

#### P4-A4：合成脱敏测试语料包生成

目标：
生成第一版可上传测试的合成脱敏语料包，用于验证 RAG、Wiki、知识问答、引用追溯、无答案拒答和干扰召回。

范围：
只新增合成脱敏 fixture 文件，不改前端、后端、RAG 逻辑、Wiki 逻辑或 Agent 逻辑；不自动上传到系统。

输入：
P4-A1 到 P4-A3 的语料、问题集和安全规则。

输出：
`backend/fixtures/phase4_rag_wiki_qa/`，包含 9 份独立 Markdown 测试文档、`manifest.json`、`questions.json` 和 `hit_matrix.md`。

验收标准：
9 份文档均有唯一锚点；问题集包含 24 个问题；命中矩阵覆盖所有问题；内容均为虚构脱敏材料；问题覆盖精确事实、条款定位、跨文档综合、案例复盘、Wiki 检索、无答案、干扰排除和新旧版本冲突。

验证方式：
`test -d backend/fixtures/phase4_rag_wiki_qa/documents`；
`find backend/fixtures/phase4_rag_wiki_qa/documents -name "*.md" | wc -l`；
`python -m json.tool backend/fixtures/phase4_rag_wiki_qa/manifest.json`；
`python -m json.tool backend/fixtures/phase4_rag_wiki_qa/questions.json`；
`rg -n "TEST-RAG|TEST-WIKI|TEST-DISTRACTOR" backend/fixtures/phase4_rag_wiki_qa`。

风险：
合成语料过于规整会高估检索质量；后续 live 测试仍需用脱敏真实形态材料复核。

状态：[x]

### P4-B：RAG 调试页参数与检索质量基线

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-B1 | RAG 调试参数前端规划 | [x] |
| P4-B2 | RAG 检索质量基线指标 | [ ] |
| P4-B3 | 文档 / Wiki 混合检索对照测试规划 | [ ] |

#### P4-B1：RAG 调试参数前端规划

目标：
明确哪些检索参数应放在调试页，哪些不进入正式知识问答页。

范围：
规划调试页参数，不实现前端代码。

输入：
现有 RAG debug API、现有前端调试页、用户测试需求。

输出：
调试参数清单与正式问答页隐藏参数清单。

验收标准：
覆盖 `top_k`、来源范围、KB ID、Document IDs、business_area、document_type、score threshold、hybrid、rerank、trace。

验证方式：
`rg -n "top_k|score threshold|hybrid|rerank|Document IDs|trace" PHASE4_SPEC.md`。

风险：
参数暴露过多会提高使用门槛；参数暴露过少会降低调试效率。

规划输出：

#### P4-B1.1 调试页参数分层

RAG / Wiki 调试页只服务测试、定位和调参，不作为正式知识问答入口。调试参数分为三层：

| 层级 | 参数 | 当前状态 | 用途 | 前端呈现建议 |
| --- | --- | --- | --- | --- |
| 基础检索 | `query` | 已有 | 输入测试问题或期望命中矩阵问题 | 中文标签“测试问题”，保留字段名 `query` 作为技术提示 |
| 基础检索 | `top_k` | 已有，范围 1-50 | 验证 top_k 内命中、错误召回和相似文档混淆 | 中文标签“返回数量”，显示 `top_k` |
| 来源范围 | `source_type=document_chunk` | 已有 | 仅测文档 chunk evidence | 中文选项“仅文档” |
| 来源范围 | `source_type=wiki_page` | 已有 | 仅测 Wiki evidence | 中文选项“仅 Wiki” |
| 来源范围 | 不传 `source_type` | 已有 | 文档 / Wiki 混合检索，即 all-source | 中文选项“全部来源” |
| 精确过滤 | `kb_id` / `knowledge_base_id` | API 允许，前端已有 `kb_id` | 指定知识库范围，区分 fixture、本地 live、真实 WeKnora live | 中文标签“知识库 ID”，保留 `KB ID` 辅助说明 |
| 精确过滤 | `document_ids` | 已有 | 限定一组文档，复现命中矩阵问题 | 中文标签“文档 ID”，支持逗号分隔 |
| 精确过滤 | `business_area` | 已有 | 按业务域过滤 | 中文标签“业务域” |
| 精确过滤 | `document_type` | 已有 | 按政策、法规、案例、FAQ、Wiki seed、干扰材料等类型过滤 | 中文标签“资料类型” |
| 质量调参 | `retrieval_options.threshold.score` | API 允许，前端待补 | 调试 score threshold 对错误召回和无答案问题的影响 | 中文标签“分数阈值”，仅调试页开放 |
| 质量调参 | `retrieval_options.hybrid.enabled` | API 预留，前端待补 | 对照 hybrid 开关对关键词锚点命中的影响 | 中文开关“混合检索”，显示 `hybrid` |
| 质量调参 | `retrieval_options.hybrid.keyword_weight` / `vector_weight` / `match_count` | API 预留，前端待补 | 调整关键词与向量权重、候选数 | 高级折叠区，避免默认干扰 |
| 质量调参 | `retrieval_options.rerank.enabled` | API 预留，前端待补 | 对照 rerank 开关对相似文档混淆和新旧版本判断的影响 | 中文开关“重排”，显示 `rerank` |
| 质量调参 | `retrieval_options.rerank.model` / `top_n` | API 预留，前端待补 | 记录重排模型与重排候选数 | 高级折叠区，默认关闭 |
| 追溯信息 | `trace_id` | 后端已返回 | 关联一次调试请求、日志和人工记录 | 结果顶部显示“调试追踪 ID” |
| 追溯信息 | `debug_trace` | 后端已返回 | 展示 hybrid / rerank / threshold 的 requested 或 skipped 状态 | 结果区显示“调试 trace”，保留 stage/status/reason |
| 追溯信息 | `evidence_id` / `chunk_id` / `wiki_page_id` / `source_type` | 后端已返回 | 判断 document_chunk 与 wiki_page 是否可追溯 | 每条 evidence 的元信息区展示 |

#### P4-B1.2 正式知识问答页隐藏参数

正式知识问答页只保留低门槛输入，不暴露工程调参。以下内容不得进入默认知识问答页：

- raw `filters`、raw `metadata`、WeKnora 原始字段和后端原始响应。
- `score threshold`、`hybrid`、`rerank`、`retrieval_options`、`debug_trace`。
- `kb_id`、`document_ids`、`business_area`、`document_type` 的自由文本调试输入。
- `trace_id`、`chunk_id`、`evidence_id` 等定位字段的主视觉展示。

正式知识问答页允许保留：

- 问题输入。
- 简单检索范围：全部来源 / 仅文档 / 仅 Wiki。
- 答案、引用、来源类型中文标签。
- 依据不足提示。

若后续需要在正式页展示技术细节，只能放入引用详情或开发者调试折叠区，默认不展开。

#### P4-B1.3 与合成语料问题集的使用关系

P4-B1 调试参数用于复现 `backend/fixtures/phase4_rag_wiki_qa/questions.json` 与 `hit_matrix.md`：

1. 精确事实、条款定位和案例复盘题，先用“仅文档”范围验证 `document_chunk` 命中。
2. Wiki 检索题，先发布 `TEST-WIKI-001` 后用“仅 Wiki”范围验证 `wiki_page` 命中。
3. 跨文档综合、版本冲突和混合引用题，用“全部来源”记录 document_chunk / wiki_page 的共同命中情况。
4. 无答案和干扰排除题，记录 top_k 内错误召回、score threshold 变化和是否仍应提示依据不足。
5. 每次人工记录至少包含问题 ID、检索范围、top_k、命中锚点、source_type、score、trace_id 和判断结论。

状态：[x]

#### P4-B2：RAG 检索质量基线指标

目标：
定义本阶段判断 RAG 质量是否提升的基线指标。

范围：
指标规划，不实现自动评分。

输入：
测试问题集和期望命中矩阵。

输出：
RAG 基线指标说明。

验收标准：
至少覆盖命中正确锚点、top_k 内命中、错误召回、相似文档混淆、新旧版本判断、无答案拒答。

验证方式：
`rg -n "top_k 内命中|错误召回|相似文档|新旧版本|无答案拒答" PHASE4_SPEC.md`。

风险：
只看主观回答质量会掩盖检索层问题。

状态：[ ]

#### P4-B3：文档 / Wiki 混合检索对照测试规划

目标：
规划如何区分文档 evidence、Wiki evidence 和混合 evidence 的检索表现。

范围：
只设计测试方法，不实现检索逻辑。

输入：
RAG 调试参数、Wiki 发布检索要求、问题集。

输出：
文档-only、Wiki-only、all-source 对照测试说明。

验收标准：
同一问题可分别测试仅文档、仅 Wiki、全部来源；结果能记录 `source_type=document_chunk` 与 `source_type=wiki_page`。

验证方式：
`rg -n "document_chunk|wiki_page|文档-only|Wiki-only|all-source" PHASE4_SPEC.md`。

风险：
混合检索如果不拆开测试，会难以判断问题来自文档索引还是 Wiki 索引。

状态：[ ]

### P4-C：Wiki 创建、发布、索引、检索闭环

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-C1 | Wiki 测试闭环验收流程 | [ ] |
| P4-C2 | Wiki citation 追溯验收规则 | [ ] |
| P4-C3 | Wiki 状态中文化规划 | [ ] |

#### P4-C1：Wiki 测试闭环验收流程

目标：
定义 Wiki 从草稿到发布、索引、检索、知识问答引用的测试流程。

范围：
规划验收流程，不改 Wiki API 或前端。

输入：
Wiki 种子材料、已有 Wiki API 和已有 RAG debug 能力。

输出：
Wiki 闭环测试步骤。

验收标准：
流程包含创建草稿、编辑、发布、刷新索引状态、RAG debug 命中、知识问答引用。

验证方式：
`rg -n "创建草稿|发布|刷新索引|RAG debug|知识问答引用" PHASE4_SPEC.md`。

风险：
只验证页面显示 published 不等于 Wiki 已进入 RAG 检索。

状态：[ ]

#### P4-C2：Wiki citation 追溯验收规则

目标：
明确 Wiki 证据必须具备的追溯字段。

范围：
只写验收规则，不改 citation 代码。

输入：
PA Evidence / Citation 约定和 Phase 3 WeKnora Wiki 规则。

输出：
Wiki citation 验收规则。

验收标准：
Wiki evidence 至少能说明 `source_type=wiki_page`、`evidence_id`、`wiki_page_id`、标题、摘要或片段、来源状态。

验证方式：
`rg -n "source_type=wiki_page|evidence_id|wiki_page_id" PHASE4_SPEC.md`。

风险：
不可追溯 Wiki citation 会导致知识问答看似有来源、实际无法定位。

状态：[ ]

#### P4-C3：Wiki 状态中文化规划

目标：
规划 Wiki 页面中草稿、发布、索引、失败、可检索、不可检索等状态的中文表达。

范围：
只规划前端文案，不实现。

输入：
现有 Wiki 页面文案和状态字段。

输出：
Wiki 状态中文术语表。

验收标准：
覆盖 draft、published、indexing、ready、failed、retrievable、sync pending、fallback unavailable。

验证方式：
`rg -n "draft|published|indexing|retrievable|sync pending|中文" PHASE4_SPEC.md`。

风险：
状态文案如果过于技术化，用户无法判断下一步该做什么。

状态：[ ]

### P4-D：知识问答单工作流质量优化

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-D1 | `knowledge_qa` 默认检索策略规划 | [ ] |
| P4-D2 | 知识问答引用与拒答验收规则 | [ ] |
| P4-D3 | 知识问答结果展示中文化规划 | [ ] |

#### P4-D1：`knowledge_qa` 默认检索策略规划

目标：
定义正式知识问答默认使用的检索范围、证据数量和 Wiki 参与策略。

范围：
只规划默认策略，不改 Agent 代码。

输入：
RAG 调试页测试结果和问题集表现。

输出：
默认检索策略说明。

验收标准：
策略说明正式知识问答默认是否检索文档、Wiki、all-source，默认 `top_k`，以及何时提示依据不足。

验证方式：
`rg -n "knowledge_qa|默认|top_k|依据不足|all-source" PHASE4_SPEC.md`。

风险：
默认策略如果过宽，容易引入干扰；过窄则容易漏掉 Wiki 或关键条款。

状态：[ ]

#### P4-D2：知识问答引用与拒答验收规则

目标：
定义知识问答答案什么时候必须有引用，什么时候必须拒答或提示依据不足。

范围：
只写验收规则，不改 Agent 或 prompt。

输入：
测试问题集、Evidence / Citation 规则、无答案问题。

输出：
知识问答引用与拒答规则。

验收标准：
精确事实、条款定位、跨文档综合、案例复盘必须引用；无答案问题必须说明资料库依据不足，不得编造。

验证方式：
`rg -n "精确事实|条款定位|跨文档综合|案例复盘|不得编造" PHASE4_SPEC.md`。

风险：
如果拒答规则不清，知识问答优化会滑向“看起来流畅但不可信”。

状态：[ ]

#### P4-D3：知识问答结果展示中文化规划

目标：
规划知识问答页面的中文术语和低门槛展示。

范围：
只规划前端文案和信息层级，不实现。

输入：
现有分析台页面、引用组件、历史输出。

输出：
知识问答中文展示清单。

验收标准：
`Evidence`、`Citation`、`Score`、`Source`、`No evidence`、`Mock fallback`、`Real WeKnora RAG` 等用户可见术语都有中文表达。

验证方式：
`rg -n "Evidence|Citation|Score|Source|No evidence|Mock fallback|Real WeKnora RAG" PHASE4_SPEC.md`。

风险：
只翻译标题不翻译状态和错误提示，仍会形成使用门槛。

状态：[ ]

### P4-E：前端中文化与低门槛体验

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-E1 | 首页与运行状态中文化规划 | [ ] |
| P4-E2 | 资料库与 RAG 调试页中文化规划 | [ ] |
| P4-E3 | Wiki 与知识问答页中文化规划 | [ ] |

#### P4-E1：首页与运行状态中文化规划

目标：
规划首页中模型、RAG、能力矩阵、工作流、工作区的中文表达。

范围：
只规划文案，不改前端。

输入：
现有首页文案。

输出：
首页中文术语表。

验收标准：
`Chat Model`、`Embedding`、`RAG Pipeline`、`Capability`、`Agent Workflows`、`Workspace` 等术语有中文替代。

验证方式：
`rg -n "Chat Model|Embedding|RAG Pipeline|Capability|Agent Workflows|Workspace" PHASE4_SPEC.md`。

风险：
运行状态如果翻译不准确，可能误导用户对 mock / real 状态的判断。

状态：[ ]

#### P4-E2：资料库与 RAG 调试页中文化规划

目标：
规划资料库和 RAG 调试页中的上传、索引、筛选、调试、证据结果中文表达。

范围：
只规划文案和参数分层，不实现。

输入：
现有资料库页面和 RAG debug 页面。

输出：
资料库 / RAG 调试中文术语表。

验收标准：
`Query`、`Top K`、`Source`、`Document IDs`、`Business`、`Document Type`、`Run`、`Reset`、`No evidence`、`Debug unavailable` 等术语有中文替代。

验证方式：
`rg -n "Query|Top K|Document IDs|Run|Reset|Debug unavailable" PHASE4_SPEC.md`。

风险：
调试页可以保留技术字段名，但必须让测试者知道字段作用。

状态：[ ]

#### P4-E3：Wiki 与知识问答页中文化规划

目标：
规划 Wiki 和知识问答页面中的搜索、阅读、编辑、发布、引用、证据、依据不足中文表达。

范围：
只规划文案，不实现。

输入：
现有 Wiki 页面、分析台页面、引用组件。

输出：
Wiki / 知识问答中文术语表。

验收标准：
`Search`、`Pages`、`Editor`、`Reader`、`Score unavailable`、`Backend retrieval score`、`Assistant`、`Status`、`You` 等术语有中文替代。

验证方式：
`rg -n "Search|Pages|Editor|Reader|Score unavailable|Assistant|Status|You" PHASE4_SPEC.md`。

风险：
角色、状态和引用说明混用中英文会影响非技术用户理解。

状态：[ ]

### P4-F：阶段验收 checklist 与回归标准

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-F1 | Phase 4 fixture / mock / live 验收分层 | [ ] |
| P4-F2 | RAG / Wiki / QA 回归 checklist | [ ] |
| P4-F3 | Phase 4 阶段收口检查 | [ ] |

#### P4-F1：Phase 4 fixture / mock / live 验收分层

目标：
定义 Phase 4 验收时如何区分 mock、fixture、本地 live、真实 WeKnora live。

范围：
只写验收分层，不实现 checker。

输入：
Phase 3 验收纪律和本阶段测试目标。

输出：
验收分层规则。

验收标准：
明确 mock / fixture 只作为开发和回归信号；真实 WeKnora live 才能证明 RAG / Wiki 真实链路。

验证方式：
`rg -n "mock|fixture|本地 live|真实 WeKnora live|不能冒充" PHASE4_SPEC.md`。

风险：
如果验收层级混淆，会重复 Phase 3 早期 mock 掩盖真实链路的问题。

状态：[ ]

#### P4-F2：RAG / Wiki / QA 回归 checklist

目标：
形成每次优化后必须回归的检查清单。

范围：
只写 checklist，不实现脚本。

输入：
P4-A 至 P4-E 的规则。

输出：
回归 checklist。

验收标准：
checklist 覆盖文档上传/index、RAG debug 命中、Wiki 发布/retrieve、knowledge_qa 引用、无答案拒答、中文化页面检查。

验证方式：
`rg -n "上传|index|RAG debug|Wiki 发布|knowledge_qa|无答案|中文化" PHASE4_SPEC.md`。

风险：
只做单点调试会导致改好一个问题、破坏另一个闭环。

状态：[ ]

#### P4-F3：Phase 4 阶段收口检查

目标：
定义 Phase 4 第一段何时可以认为完成。

范围：
只写收口标准，不运行真实测试。

输入：
所有 Phase 4 任务完成状态和验证记录。

输出：
Phase 4 第一段收口标准。

验收标准：
所有 P4-A 到 P4-F 任务完成；测试语料规范和问题集可用；RAG/Wiki/QA 验收分层清晰；前端中文化范围明确；下一阶段开发可以按任务执行。

验证方式：
`rg -n "P4-A|P4-B|P4-C|P4-D|P4-E|P4-F" PHASE4_SPEC.md`。

风险：
如果没有收口标准，Phase 4 会从质量打磨滑向无边界优化。

状态：[ ]

## 5. 阶段验收标准

Phase 4 第一段最小验收：

1. `PHASE4_SPEC.md` 存在，且 P4-A 到 P4-F 任务表完整。
2. Phase 4 skill 存在，且要求每次只执行一个任务编号。
3. 测试语料规范覆盖 8-10 份合成脱敏文档和 20-25 个测试问题。
4. RAG 调试参数和正式知识问答体验边界清晰。
5. Wiki 闭环测试覆盖草稿、发布、索引、检索、知识问答引用。
6. `knowledge_qa` 是本阶段唯一重点 Agent 工作流。
7. 前端中文化范围覆盖首页、资料库、RAG 调试页、Wiki 页、知识问答页。
8. mock、fixture、本地 live、真实 WeKnora live 验收分层清晰。
9. 不包含真实资料、密钥、上传文件、数据库或日志。

## 6. 任务执行协议

AI 开发工具每次只执行一个任务编号。

默认执行流程：

```text
读取 PHASE4_SPEC.md
-> 定位一个任务编号
-> 列出计划修改文件与验证方式
-> 实现或编写对应文档
-> 运行验收
-> 验收通过后更新 PHASE4_SPEC.md 任务状态
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
docs: complete P4-A1 test corpus specification
feat: complete P4-B1 rag debug parameter controls
test: complete P4-C1 wiki retrieval loop smoke
chore: complete P4-F3 phase4 acceptance check
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
请使用 phase4-rag-wiki-qa，执行 PHASE4_SPEC.md 中的 P4-A1。只做测试语料规范，不写产品代码。验收通过后自动 commit，不要 push。
```

```text
请使用 phase4-rag-wiki-qa，执行 PHASE4_SPEC.md 中的 P4-B1。只规划 RAG 调试参数和正式问答页边界，不改代码。验收通过后自动 commit，不要 push。
```

```text
请使用 phase4-rag-wiki-qa，执行 PHASE4_SPEC.md 中的 P4-D2。只定义知识问答引用和拒答规则，不设计复杂 Agent 工作流。验收通过后自动 commit，不要 push。
```

禁止：

- 一次性实现多个未确认任务。
- 本阶段顺手做 Word / PPT 导出。
- 本阶段顺手做复杂 Agent 编排。
- 本阶段顺手做权限、审批、IM、知识图谱或长期记忆。
- 前端直接调用 WeKnora。
- Agent 直接依赖 WeKnora 原始响应。
- 跳过验收就标记 `[x]`。
- 把 mock / fixture 结果作为真实 RAG / Wiki 通过依据。
- 提交敏感文件。
- 自动 push。
- 编造 citation。

## 7. 后续阶段预留

Phase 4 第一段完成后，可考虑：

- Word / PPT 输出。
- 更深的 PA 工作流 Agent。
- 用户反馈评分与质量闭环。
- 权限与审计。
- IM 集成。
- Wiki diff。
- 知识图谱。
- 长期记忆。
