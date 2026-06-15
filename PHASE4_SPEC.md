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
| P4-A2 | 测试问题集与期望命中矩阵规范 | [x] |
| P4-A3 | 测试语料安全检查规则 | [x] |
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

规范输出：

#### P4-A2.1 问题集定位与规模

Phase 4 问题集用于把检索调试从“看起来回答不错”变成可复核的命中、引用和拒答检查。问题集必须与合成语料包一一对应，当前基准文件为 `backend/fixtures/phase4_rag_wiki_qa/questions.json`，当前规模为 24 个问题。

问题集要求：

- 总量保持 20-25 个问题，避免过少导致覆盖不足，也避免过多让人工回归成本失控。
- 每个问题必须能回到一个或多个测试锚点，或明确声明没有期望锚点。
- 每个问题必须记录答案要点，而不是只记录关键词。
- 每个问题必须明确是否必须引用文档、是否必须引用 Wiki、是否应该回答“依据不足”。
- 问题文本必须使用中文，并尽量接近真实用户提问方式，但不得包含真实机构、真实客户、真实政策编号或真实敏感信息。

#### P4-A2.2 `questions.json` 字段规范

`questions.json` 顶层字段：

| 字段 | 类型 | 要求 |
| --- | --- | --- |
| `corpus_id` | string | 必须与 `manifest.json` 中的语料包 ID 一致 |
| `version` | string | 问题集版本，语料或题目变更时递增 |
| `questions` | array | 20-25 个问题对象 |

每个问题对象字段：

| 字段 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | 使用 `P4Q-NNN`，编号稳定，不因排序调整复用 |
| `type` | string | 是 | 问题类型，见 P4-A2.3 |
| `query` | string | 是 | 用户问题文本 |
| `expected_anchors` | string[] | 是 | 期望命中的 `TEST-RAG-*`、`TEST-WIKI-*` 或 `TEST-DISTRACTOR-*`；无答案问题为空数组 |
| `expected_answer_points` | string[] | 是 | 期望答案要点，用于人工判断回答是否覆盖关键事实 |
| `expected_source_types` | string[] | 是 | 期望 evidence 类型，允许 `document_chunk`、`wiki_page`；无答案问题为空数组 |
| `must_cite_document` | boolean | 是 | 回答是否必须引用文档 evidence |
| `must_cite_wiki` | boolean | 是 | 回答是否必须引用 Wiki evidence |
| `should_answer_insufficient` | boolean | 是 | 是否应该提示依据不足或资料库无依据 |
| `retrieval_scope` | string | 是 | 推荐检索范围：`document`、`wiki`、`all` |
| `forbidden_anchors` | string[] | 否 | 不应被当作依据的干扰锚点 |

字段约束：

1. `expected_anchors` 中的锚点必须存在于 `manifest.json`，除非数组为空。
2. `expected_source_types` 必须与 `must_cite_document`、`must_cite_wiki` 保持一致。
3. `should_answer_insufficient=true` 时，`expected_anchors` 和 `expected_source_types` 应为空，且 `must_cite_document=false`、`must_cite_wiki=false`。
4. `retrieval_scope=wiki` 的问题应至少要求 `must_cite_wiki=true`，除非用于验证 Wiki 无答案。
5. 带有 `forbidden_anchors` 的问题必须在期望答案要点中说明为什么不能引用该锚点。

#### P4-A2.3 问题类型覆盖

问题集必须覆盖以下类型：

| 类型 | 当前建议数量 | 检查重点 |
| --- | --- | --- |
| `precise_fact` 精确事实 | 4-6 | 单一锚点事实是否命中，是否误用相似材料 |
| `article_lookup` 条款定位 | 3-5 | 能否定位法规法条、校验要求、撤回要求等结构化条款 |
| `cross_document_synthesis` 跨文档综合 | 3-5 | 能否同时引用多个文档或 Wiki / 文档混合 evidence |
| `case_review` 案例复盘 | 2-4 | 能否区分相似案例的原因、结果和处置动作 |
| `wiki_retrieval` Wiki 检索 | 2-4 | Wiki 发布后能否以 `wiki_page` evidence 命中并引用 |
| `insufficient_evidence` 无答案 | 2-3 | 是否提示依据不足，不编造外部事实 |
| `distractor_suppression` 干扰排除 | 1-3 | 是否避免把干扰材料当成政策或法规依据 |
| `version_conflict` 新旧版本冲突 | 1-2 | 是否说明新版优先，并解释旧版差异 |

覆盖要求：

- 至少一题必须同时要求文档引用和 Wiki 引用。
- 至少两题必须要求回答“依据不足”。
- 至少一题必须包含 `forbidden_anchors`，用于检查干扰材料是否被错误采用。
- 新旧版本冲突题必须同时包含旧版和新版锚点，并在答案要点中说明当前优先规则。

#### P4-A2.4 期望命中矩阵格式

期望命中矩阵文件为 `backend/fixtures/phase4_rag_wiki_qa/hit_matrix.md`，用于人工回归和调试页记录。矩阵至少包含：

| 列 | 说明 |
| --- | --- |
| 问题 ID | 对应 `questions.json` 的 `id` |
| 类型 | 中文问题类型，便于人工扫描 |
| 期望命中锚点 | 对应 `expected_anchors`；无答案问题写“无” |
| 推荐范围 | `document`、`wiki` 或 `all` |
| 必须文档引用 | 对应 `must_cite_document` |
| 必须 Wiki 引用 | 对应 `must_cite_wiki` |
| 应提示依据不足 | 对应 `should_answer_insufficient` |
| 主要检查点 | 对应 `expected_answer_points` 的人工摘要 |

矩阵维护规则：

1. 新增、删除、替换问题时，必须同步更新 `questions.json` 和 `hit_matrix.md`。
2. 矩阵中的“期望命中锚点”必须与问题集字段一致，不得只写自然语言描述。
3. 矩阵中的“主要检查点”必须覆盖答案要点、禁用锚点或依据不足要求。
4. Wiki 题必须标出必须 Wiki 引用；文档题必须标出必须文档引用。
5. 无答案题必须在矩阵中明确“应提示依据不足=是”。

#### P4-A2.5 人工判定口径

一次问题回归至少记录：

- 问题 ID 和原始 `query`。
- 检索范围和 `top_k`。
- 实际命中锚点及其排序。
- 实际 `source_type`：`document_chunk`、`wiki_page` 或其他。
- 答案是否覆盖全部期望答案要点。
- 是否满足必须引用文档 / 必须引用 Wiki。
- 是否正确提示依据不足。
- 是否命中或引用了 `forbidden_anchors`。

通过标准：

1. 非无答案问题必须命中至少一个期望锚点，并覆盖关键答案要点。
2. 标记必须引用文档的问题，答案引用中必须出现可追溯的 `document_chunk`。
3. 标记必须引用 Wiki 的问题，答案引用中必须出现可追溯的 `wiki_page`。
4. 无答案问题即使检索到相似或干扰材料，也必须明确说明资料库依据不足。
5. 干扰排除问题不得把 `forbidden_anchors` 当成政策、法规或案例依据。

状态：[x]

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

规则输出：

#### P4-A3.1 禁止内容清单

Phase 4 测试语料只能使用合成脱敏内容。任何新增或替换语料、问题集、命中矩阵和验收记录中，均禁止出现：

| 类型 | 禁止内容 | 处理要求 |
| --- | --- | --- |
| 真实主体 | 真实公司、真实机构、真实客户、真实项目、真实个人 | 必须替换为虚构名称，不得只做部分遮挡 |
| 真实标识 | 真实政策编号、真实合同编号、真实监管编号、真实工单号 | 必须改为虚构编号，例如 `SYN-POLICY-001` |
| 联系信息 | 手机号、邮箱、身份证号、地址、银行卡号 | 不得进入 fixture；如需格式测试，使用明显虚构样例 |
| 私有系统 | 真实内网地址、私有系统 URL、内部域名、数据库地址 | 不得提交；用 `example.invalid` 或文字说明替代 |
| 凭据密钥 | API Key、service token、Bearer token、secret、password、数据库连接串 | 发现即阻断提交，不能进入 diff |
| 真实文件 | 上传文件、客户资料、真实日志、数据库、缓存、导出包 | 不得放入 `backend/fixtures/phase4_rag_wiki_qa/` |
| 模型输出 | 未脱敏模型输出、真实用户问答、真实 prompt / completion | 必须人工重写为合成材料后再使用 |

#### P4-A3.2 人工安全检查清单

每次新增或修改 `backend/fixtures/phase4_rag_wiki_qa/` 或相关 spec 前，必须人工确认：

1. 文档标题、正文、表格、脚注、引用片段均不含真实公司、真实个人、真实客户或真实项目。
2. 所有政策、法规、案例、FAQ、Wiki 种子材料均为虚构，不能复刻真实政策编号或真实案例细节。
3. 所有锚点均为 `TEST-RAG-*`、`TEST-WIKI-*` 或 `TEST-DISTRACTOR-*`，不夹带真实业务 ID。
4. `manifest.json`、`questions.json`、`hit_matrix.md` 中的标题、答案要点和主要检查点不包含敏感信息。
5. 无答案问题不得暗示真实监管部门、真实客户或真实个人信息。
6. 干扰材料只能是合成材料，不得从真实活动安排、真实会议纪要或真实排期复制。
7. 提交前检查 `git status --ignored --short`，确认 `.env`、上传文件、数据库、日志、`backend/data/`、`backend/uploads/`、`frontend/dist/`、`node_modules/` 等没有被 stage。

#### P4-A3.3 后续可脚本化检查方向

后续如需把安全检查自动化，可新增只读 checker，但不在 P4-A3 中实现。脚本化方向：

1. 扫描 fixture 文档和 JSON 中的敏感关键词：`API Key`、`service token`、`Bearer`、`password`、`secret`、`jdbc:`、`postgres://`、`mysql://`。
2. 扫描常见个人信息模式：手机号、邮箱、身份证样式、银行卡样式、URL 和内网 IP。
3. 校验 `manifest.json` 中所有 `safety` 字段为 true。
4. 校验所有文档只包含允许锚点前缀：`TEST-RAG-`、`TEST-WIKI-`、`TEST-DISTRACTOR-`。
5. 校验 `questions.json` 中的 `expected_anchors` 和 `forbidden_anchors` 均来自 manifest。
6. 输出只读报告，不自动改写语料，避免把误报修正成新的失真内容。

#### P4-A3.4 提交前阻断规则

出现以下任一情况时，必须停止 commit 并报告：

- `git status --short` 显示 `.env`、数据库、日志、上传文件、真实导出文件或未脱敏输出被修改或新增。
- `git status --ignored --short` 中的敏感路径被显式 stage。
- diff 中出现 API Key、service token、Bearer token、私有 URL 或数据库连接串。
- fixture 文档中出现真实公司、真实个人、真实客户、真实项目或真实政策编号。
- 问题集或命中矩阵要求系统回答真实客户名称、真实监管口径或真实内网资料。

允许提交的范围仅限：

- 合成脱敏 Markdown fixture。
- `manifest.json`、`questions.json`、`hit_matrix.md`。
- 与本阶段任务直接相关的 spec、测试脚本或只读 checker。

#### P4-A3.5 安全验收记录口径

完成每次语料或问题集相关任务时，报告中必须说明安全检查层级：

- `fixture`：只验证合成脱敏 fixture 与 spec。
- `mock`：只验证 mock 行为，不代表真实 RAG / Wiki 安全验收。
- `local live`：本地真实链路，但不得使用真实敏感资料。
- `真实 WeKnora live`：只能使用已批准的脱敏材料，且不能提交上传结果、日志或数据库。

无论哪一层，mock / fixture 结果都不能冒充真实 RAG / Wiki live 验收。

状态：[x]

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
| P4-B2 | RAG 检索质量基线指标 | [x] |
| P4-B3 | 文档 / Wiki 混合检索对照测试规划 | [x] |

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

指标输出：

#### P4-B2.1 基线目标

RAG 检索质量基线用于判断后续检索、Wiki 和知识问答优化是否真的提升，而不是只让回答更流畅。基线评估以 `backend/fixtures/phase4_rag_wiki_qa/questions.json` 和 `hit_matrix.md` 为准，先记录 fixture / mock / local live / 真实 WeKnora live 的层级，再比较同一层级内的变化。

本阶段第一版基线只定义指标和人工记录口径，不实现自动评分脚本。

#### P4-B2.2 核心指标

| 指标 | 定义 | 记录方式 | 适用问题 |
| --- | --- | --- | --- |
| 命中正确锚点 | 检索结果中出现 `expected_anchors` 中至少一个锚点 | 记录实际命中锚点、rank、source_type | 非无答案问题 |
| top_k 内命中 | 期望锚点是否出现在当前 `top_k` 返回范围内 | 固定记录 `top_k`，建议先用 8，再对比 3 / 5 / 10 | 全部非无答案问题 |
| 多锚点覆盖 | 跨文档问题是否命中全部关键锚点 | 记录每个期望锚点是否命中及排序 | 跨文档综合、新旧版本冲突 |
| 错误召回 | 检索结果是否包含与问题无关或禁止采用的锚点 | 记录错误锚点、rank、是否进入引用 | 干扰排除、无答案、相似材料问题 |
| 相似文档混淆 | 系统是否把相似政策、法规或案例当成正确依据 | 记录被混淆的锚点和正确锚点 | 政策、法规、案例组 |
| 新旧版本判断 | 当前问题是否同时检索旧版和新版，并在回答中优先新版 | 记录 `TEST-RAG-001` / `TEST-RAG-002` 的 rank 和最终引用 | 新旧版本冲突题 |
| 无答案拒答 | 无依据问题是否提示依据不足，而不是编造答案 | 记录是否出现依据不足提示、是否引用不相关材料 | `insufficient_evidence` 问题 |
| source_type 正确性 | 文档证据和 Wiki 证据是否按预期返回 | 记录 `document_chunk`、`wiki_page`、其他类型 | Wiki 检索、混合引用题 |
| 引用可追溯性 | 命中证据是否带有可定位字段 | 记录 `evidence_id`、`chunk_id`、`wiki_page_id` | 必须引用的问题 |

#### P4-B2.3 最低通过标准

第一版人工基线的最低通过标准：

1. 精确事实、条款定位、案例复盘题：期望锚点应在 `top_k=8` 内命中。
2. 跨文档综合题：至少命中一个关键锚点；正式优化目标是 `top_k=8` 内命中全部期望锚点。
3. Wiki 检索题：发布并索引后，`retrieval_scope=wiki` 时应命中 `TEST-WIKI-001`，且 `source_type=wiki_page`。
4. 干扰排除题：不得把 `forbidden_anchors` 当作政策、法规或案例依据；若错误召回出现在低 rank，需要标记为风险。
5. 新旧版本冲突题：应同时记录旧版和新版是否命中；回答判断必须优先新版，并说明旧版差异。
6. 无答案题：即使命中相似材料，也必须提示依据不足；不得编造真实监管部门、真实客户或真实政策要求。
7. 必须引用文档的问题，至少一个引用应来自 `document_chunk`；必须引用 Wiki 的问题，至少一个引用应来自 `wiki_page`。

#### P4-B2.4 记录模板

每次运行 RAG debug 或知识问答回归时，建议记录以下字段：

| 字段 | 示例 |
| --- | --- |
| 验收层级 | fixture / mock / local live / 真实 WeKnora live |
| 问题 ID | `P4Q-010` |
| 检索范围 | document / wiki / all |
| top_k | 8 |
| 命中锚点 | `TEST-RAG-001@rank1`, `TEST-RAG-002@rank3` |
| 错误召回 | `TEST-DISTRACTOR-001@rank7` 或无 |
| source_type | `document_chunk`, `wiki_page` |
| 引用字段 | `evidence_id`, `chunk_id`, `wiki_page_id` |
| 答案要点覆盖 | 全部 / 部分 / 未覆盖 |
| 依据不足判断 | 正确拒答 / 错误回答 / 不适用 |
| 人工结论 | pass / warn / fail |

#### P4-B2.5 指标解释规则

- `pass`：关键锚点命中、引用类型满足要求、答案要点覆盖，且无禁止锚点被当作依据。
- `warn`：关键锚点命中但排序过低、错误召回出现在结果中但未被引用、答案要点部分缺失，或引用字段不完整。
- `fail`：期望锚点未命中、相似文档混淆导致错误答案、无答案问题未拒答、必须 Wiki / 文档引用缺失，或引用了禁止锚点。

统计时必须分层：

- fixture / mock 只能作为开发和回归信号。
- local live 可用于本地真实链路趋势判断。
- 真实 WeKnora live 才能作为真实 RAG / Wiki 链路验收依据。
- 不同层级之间不得直接比较通过率。

状态：[x]

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

规划输出：

#### P4-B3.1 对照测试目标

文档 / Wiki 混合检索对照测试用于定位问题来源：是文档索引未命中、Wiki 发布后未进入检索、混合检索排序不稳定，还是回答阶段引用选择错误。每个对照测试必须在同一验收层级内比较，不得把 fixture / mock / local live / 真实 WeKnora live 混在一起判断。

对照范围：

- 文档-only：只允许 `source_type=document_chunk`。
- Wiki-only：只允许 `source_type=wiki_page`。
- all-source：不传 `source_type`，允许 document_chunk 和 wiki_page 同时返回。

#### P4-B3.2 测试问题分组

| 分组 | 问题示例 | 对照目的 |
| --- | --- | --- |
| 文档-only 基线 | P4Q-001 到 P4Q-012、P4Q-014 到 P4Q-016、P4Q-022 到 P4Q-024 | 验证政策、法规、案例、FAQ 和版本冲突主要由 `document_chunk` 支撑 |
| Wiki-only 基线 | P4Q-017 到 P4Q-019 | 验证 Wiki 发布并索引后能以 `wiki_page` 独立命中 |
| 混合引用 | P4Q-013 | 验证 all-source 下可同时返回 `document_chunk` 与 `wiki_page` |
| 无答案 / 干扰排除 | P4Q-020 到 P4Q-023 | 验证错误召回不应升级为错误引用或编造答案 |

#### P4-B3.3 执行步骤

同一问题至少按以下顺序执行：

1. 准备材料：确认 `backend/fixtures/phase4_rag_wiki_qa/documents/*.md` 已进入当前验收层级的知识库。
2. Wiki 准备：涉及 Wiki 的问题，先将 `TEST-WIKI-001` 作为 Wiki 草稿发布，并确认索引状态可检索。
3. 文档-only：在 RAG debug 中设置来源为“仅文档”，实际 filters 应包含 `source_type=document_chunk`。
4. Wiki-only：在 RAG debug 中设置来源为“仅 Wiki”，实际 filters 应包含 `source_type=wiki_page`。
5. all-source：在 RAG debug 中设置来源为“全部来源”，不传 `source_type`。
6. 统一参数：同一轮对照保持相同 `top_k`、KB ID、Document IDs、business_area、document_type、score threshold、hybrid 和 rerank 设置。
7. 记录结果：分别记录命中锚点、rank、score、source_type、evidence_id、chunk_id、wiki_page_id 和人工结论。

#### P4-B3.4 判定口径

| 场景 | 通过 | 警告 | 失败 |
| --- | --- | --- | --- |
| 文档-only | 文档题命中期望 `TEST-RAG-*`，且 source_type 为 `document_chunk` | 期望锚点命中但 rank 过低，或出现少量无关文档 | 未命中期望文档，或返回 `wiki_page` |
| Wiki-only | Wiki 题命中 `TEST-WIKI-001`，且 source_type 为 `wiki_page` | 命中 Wiki 但缺少 `wiki_page_id` 或排序过低 | Wiki 题不命中，或返回 `document_chunk` |
| all-source | 混合题可同时看到 document_chunk 和 wiki_page，或按问题要求命中正确来源 | 只命中一种来源但答案仍可部分成立 | 混合题关键来源缺失，或错误来源主导答案 |
| 无答案 | 即使命中相似材料，也提示依据不足 | 错误召回出现但未被引用 | 把错误召回当作依据或编造答案 |
| 干扰排除 | 不引用 forbidden_anchors 作为政策 / 法规依据 | forbidden_anchors 排名靠后但未被引用 | forbidden_anchors 被当作主要依据 |

#### P4-B3.5 记录模板

每个问题建议记录三行，分别对应 document-only、Wiki-only、all-source：

| 字段 | 说明 |
| --- | --- |
| 问题 ID | 例如 `P4Q-013` |
| 对照范围 | 文档-only / Wiki-only / all-source |
| 请求 filters | 记录是否包含 `source_type=document_chunk`、`source_type=wiki_page` 或不传 source_type |
| top_k 与调试参数 | 记录 `top_k`、threshold、hybrid、rerank |
| 实际命中 | 锚点、rank、score |
| source_type | `document_chunk` / `wiki_page` / 其他 |
| 追溯字段 | `evidence_id`、`chunk_id`、`wiki_page_id` |
| 人工判断 | pass / warn / fail |
| 备注 | 错误召回、相似文档混淆、无答案拒答或版本冲突说明 |

#### P4-B3.6 常见定位结论

- 文档-only 失败、Wiki-only 正常：优先检查文档上传、chunking、文档索引和 document filter。
- 文档-only 正常、Wiki-only 失败：优先检查 Wiki 发布、索引状态和 `source_type=wiki_page` 映射。
- 两者单独正常、all-source 失败：优先检查混合排序、score threshold、hybrid / rerank 设置和引用选择。
- all-source 命中但知识问答引用错误：优先检查回答阶段的 citation 绑定和 evidence 选择，不要先改检索。
- 无答案问题命中相似材料：记录为错误召回风险，但最终回答仍应依据不足。

状态：[x]

### P4-C：Wiki 创建、发布、索引、检索闭环

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-C1 | Wiki 测试闭环验收流程 | [x] |
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

流程输出：

#### P4-C1.1 测试前置条件

Wiki 闭环测试使用合成脱敏材料 `TEST-WIKI-001`，不得使用真实 Wiki 页面、真实内部知识库或真实客户资料。开始前确认：

1. `backend/fixtures/phase4_rag_wiki_qa/documents/008_timeliness_wiki_seed.md` 可作为 Wiki 种子材料。
2. 与 Wiki 关联的问题已在 `questions.json` 中定义，重点包括 P4Q-013、P4Q-017、P4Q-018、P4Q-019。
3. RAG debug 可按 `source_type=wiki_page` 过滤 Wiki evidence。
4. 当前验收层级已标明为 fixture、mock、local live 或真实 WeKnora live。
5. 若使用真实 WeKnora live，只能上传合成脱敏材料，不提交上传产物、日志、数据库或 `.env`。

#### P4-C1.2 Wiki 闭环步骤

Wiki 测试闭环必须按以下顺序执行并记录结果：

1. 创建草稿：将 `TEST-WIKI-001` 种子材料创建为 Wiki 草稿，标题建议使用“时限管理专题 Wiki 种子材料”，slug 建议使用稳定测试值，例如 `phase4-timeliness-wiki-seed`。
2. 编辑草稿：确认草稿正文包含 `TEST-WIKI-001`、关联政策锚点、关联法规锚点、关联案例锚点和“常见误区”段落。
3. 保存草稿：保存后重新打开页面，确认标题、摘要、正文、业务域、标签和来源引用未丢失。
4. 发布：执行 Wiki 发布操作，确认页面状态从 draft 进入 published 或等价发布状态。
5. 刷新索引：发布后执行刷新索引状态或 reindex 操作，不能只看 published；必须记录 `embedding_status`、`indexed_at`、`wiki_retrievable`、`weknora_sync_status`、`weknora_index_status`。
6. RAG debug 命中：在 RAG debug 中使用 Wiki-only 范围，即 `source_type=wiki_page`，测试 P4Q-017、P4Q-018、P4Q-019 是否命中 `TEST-WIKI-001`。
7. 混合检索：在 all-source 范围测试 P4Q-013，确认结果可同时记录 Wiki evidence 和文档 evidence。
8. 知识问答引用：在正式知识问答或 `knowledge_qa` 流程中测试 Wiki 相关问题，确认回答引用中能展示 Wiki 来源，且不会把 Wiki evidence 伪装成文档 evidence。

#### P4-C1.3 每步记录字段

| 步骤 | 必记字段 |
| --- | --- |
| 创建草稿 | slug、title、page_type、business_area、source refs、创建时间 |
| 编辑草稿 | 是否包含 `TEST-WIKI-001`、关联锚点、常见误区、脱敏说明 |
| 发布 | 发布前 status、发布后 status、published_at、发布风险提示 |
| 刷新索引 | embedding_status、indexed_at、vector_id、wiki_retrievable、wiki_index_timed_out |
| RAG debug | query、top_k、filters、trace_id、rank、source_type、wiki_page_id、evidence_id |
| 知识问答引用 | 问题 ID、答案要点、引用类型、引用标题、是否依据不足 |

#### P4-C1.4 通过 / 警告 / 失败口径

| 检查项 | 通过 | 警告 | 失败 |
| --- | --- | --- | --- |
| 草稿创建 | 可保存并重新读取，正文包含 `TEST-WIKI-001` | 元信息不完整但正文完整 | 草稿无法创建或锚点丢失 |
| 发布 | 状态变为 published，发布时间可见 | published 但来源引用为空 | 发布失败或状态不稳定 |
| 索引 | 刷新索引后显示可检索，或可通过 RAG debug 命中 | published 但暂未 indexed，需要继续等待或重试 | published 后长期不可检索且无错误说明 |
| Wiki-only 检索 | P4Q-017 到 P4Q-019 命中 `TEST-WIKI-001` 且 source_type 为 `wiki_page` | 命中但缺少 `wiki_page_id` 或排序过低 | 不命中 Wiki，或返回 `document_chunk` |
| all-source 混合检索 | P4Q-013 能同时记录 Wiki 与文档 evidence | 只命中一种来源但答案部分可用 | 关键来源缺失或错误来源主导答案 |
| 知识问答引用 | 回答展示 Wiki 引用并覆盖答案要点 | 回答正确但引用展示不完整 | 回答无引用、引用错误或编造 Wiki 来源 |

#### P4-C1.5 闭环验收结论

Wiki 闭环只有在以下条件同时满足时才算通过：

- 草稿创建、编辑、保存、发布均可复现。
- 发布后执行过刷新索引或 reindex，并记录索引状态。
- RAG debug 的 Wiki-only 测试能命中 `source_type=wiki_page`。
- all-source 测试能解释 Wiki evidence 与 document_chunk evidence 的关系。
- 知识问答引用能展示 Wiki 来源，并能与原始文档引用区分。
- 验收报告明确当前层级是 fixture、mock、local live 还是真实 WeKnora live。

如果只完成发布但没有 RAG debug 命中，不能认定 Wiki 检索闭环通过；如果只在 mock / fixture 通过，不能冒充真实 WeKnora live 通过。

状态：[x]

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
