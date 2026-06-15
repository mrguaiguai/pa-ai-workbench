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
-> 使用真实 PA / WeKnora 能力执行测试并形成优化报告
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
11. Phase 4 后续测试执行必须优先使用真实 PA Adapter + 真实 WeKnora 能力，不能用 mock、fixture-only、keyword fallback 或旧缓存替代真实验收。
12. 每个真实测试阶段必须形成测试报告，报告必须包含测试结果、失败 / 风险点、诊断结论和后续优化建议。
13. 真实资料、上传文件、数据库、日志、`.env`、API Key 禁止提交。

第四阶段第一段一句话定义：

```text
第四阶段第一段以 RAG / Wiki / 知识问答质量测试为主线，用合成脱敏语料验证检索、Wiki、引用和拒答能力，同时把前端核心英文术语降为中文可理解表达；后续真实测试必须通过真实 PA / WeKnora 能力执行，并把结果沉淀为可用于优化的报告。
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
10. 真实能力测试阶段能输出分阶段报告，并明确记录测试结果、阻塞原因和后续优化建议。

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
| P4-C2 | Wiki citation 追溯验收规则 | [x] |
| P4-C3 | Wiki 状态中文化规划 | [x] |

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

规则输出：

#### P4-C2.1 Wiki citation 定位

Wiki citation 追溯规则用于确保知识问答引用的 Wiki evidence 可以被用户定位回 Wiki 页面，而不是只显示一个“有来源”的模糊标签。P4-C2 只定义验收规则，不改 citation 代码。

Wiki evidence 与文档 evidence 的核心区别：

- Wiki evidence 必须标记 `source_type=wiki_page`。
- Wiki evidence 必须能定位到 Wiki 页面，至少包含 `wiki_page_id` 或可解析的 Wiki slug / title。
- 文档 evidence 使用 `source_type=document_chunk`，并优先依赖 `document_id`、`external_doc_id`、`chunk_id`。
- Wiki citation 不得伪装成 document_chunk，也不得把 mock fallback 标记成真实 WeKnora Wiki 来源。

#### P4-C2.2 必备追溯字段

Wiki evidence / citation 至少应能说明：

| 字段 | 必须性 | 验收说明 |
| --- | --- | --- |
| `source_type=wiki_page` | 必须 | 用于区分 Wiki evidence 和 document_chunk |
| `evidence_id` | 必须或可推导 | 应能唯一标识该条 evidence；若后端推导生成，必须稳定可记录 |
| `wiki_page_id` | 必须 | 用于定位 Wiki 页面；若当前层级只能返回 slug，必须记录降级原因 |
| 标题 | 必须 | 应显示 Wiki 页面标题，例如“时限管理专题 Wiki 种子材料” |
| 摘要或片段 | 必须 | 应展示足够短的片段，能解释回答依据，不暴露长篇原文 |
| 来源状态 | 必须 | 至少能说明 published / indexed / retrievable 或等价状态 |
| `source` | 必须 | 应区分 `wiki`、`weknora_api`、mock / fixture 等来源层级 |
| score | 可选 | 若后端提供则展示；无 score 时应明确 score unavailable |

#### P4-C2.3 验收问题与检查点

优先使用以下问题验收 Wiki citation：

| 问题 | 推荐范围 | 必须检查 |
| --- | --- | --- |
| P4Q-017 | wiki | 命中 `TEST-WIKI-001`，引用为 `source_type=wiki_page` |
| P4Q-018 | wiki | Wiki 常见误区回答必须来自 Wiki evidence |
| P4Q-019 | wiki | 明确说明 Wiki evidence 应带有 `source_type=wiki_page`，并与原始文档 evidence 区分 |
| P4Q-013 | all | 同时记录 Wiki evidence 与 document_chunk evidence |

每次验收必须记录：

- 问题 ID。
- 检索范围：wiki 或 all-source。
- 命中的 Wiki 标题、rank、score。
- `source_type`、`evidence_id`、`wiki_page_id`。
- 页面状态：published、indexed、retrievable 或对应状态。
- 引用展示是否能让用户回到 Wiki 页面。

#### P4-C2.4 通过 / 警告 / 失败口径

| 检查项 | 通过 | 警告 | 失败 |
| --- | --- | --- | --- |
| source_type | 明确为 `source_type=wiki_page` | 字段来自 metadata 推导但最终可显示 | 缺失或错误显示为 document_chunk |
| evidence_id | 存在且稳定 | 可由 wiki_page_id / slug 推导但未直接展示 | 缺失且无法定位单条 evidence |
| wiki_page_id | 存在并可用于定位页面 | 只有 slug / title，需后续补齐 ID | 缺失且无法定位 Wiki 页面 |
| 标题与片段 | 标题和摘要 / 片段可读 | 片段过短但仍可判断 | 无标题或无可读依据 |
| 来源状态 | 能看到 published / indexed / retrievable 等状态 | 状态可读但不完整 | 只显示 published，无法判断是否可检索 |
| 文档 / Wiki 区分 | Wiki 和 document_chunk 在引用区清楚区分 | 文案略技术化但字段正确 | Wiki citation 被当作文档引用或反之 |

#### P4-C2.5 阻断规则

出现以下情况，不能认定 Wiki citation 追溯验收通过：

- Wiki 题回答有引用，但引用没有 `source_type=wiki_page`。
- 引用只有标题，没有 `evidence_id`、`wiki_page_id`、slug 或任何可定位字段。
- 页面只显示 published，但没有索引状态或 RAG debug 命中证据。
- fallback / mock 证据被标记为真实 WeKnora Wiki citation。
- Wiki citation 片段包含真实资料、未脱敏输出或长篇原文泄露。

#### P4-C2.6 记录模板

| 字段 | 示例 |
| --- | --- |
| 问题 ID | `P4Q-019` |
| 范围 | wiki |
| 标题 | 时限管理专题 Wiki 种子材料 |
| source_type | `source_type=wiki_page` |
| evidence_id | `wiki:phase4-timeliness-wiki-seed` 或后端返回值 |
| wiki_page_id | 后端返回的 Wiki page id |
| 状态 | published / indexed / retrievable |
| 片段 | Wiki evidence 应带有 `source_type=wiki_page` |
| 人工结论 | pass / warn / fail |

状态：[x]

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

规划输出：

#### P4-C3.1 中文化目标

Wiki 状态中文化的目标不是隐藏所有技术字段，而是让用户能快速判断：

1. 当前页面是草稿、已发布、索引中、可检索还是失败。
2. 是否已经进入 RAG / Wiki 检索。
3. 下一步应该编辑、发布、刷新索引、重试同步，还是直接用于知识问答。
4. 当前状态属于 mock / fixture / local live / 真实 WeKnora live 哪一层级。

技术字段可保留在调试详情中，但页面主状态、按钮提示、风险提示和空状态应优先使用中文表达。

#### P4-C3.2 状态中文术语表

| 技术状态 / 字段 | 中文主文案 | 用户含义 | 建议下一步 |
| --- | --- | --- | --- |
| `draft` | 草稿 | 页面尚未发布，不会进入检索 | 继续编辑或发布 |
| `draft not searchable` | 草稿，暂不可检索 | 未发布的 Wiki 不参与 RAG | 发布后再刷新索引 |
| `published` | 已发布 | 页面已发布，但不等于可检索 | 检查索引状态 |
| `published not indexed` | 已发布，未完成索引 | 页面已发布但尚未进入向量 / Wiki 检索 | 点击刷新索引或等待索引 |
| `published not retrievable` | 已发布，暂不可检索 | 后端尚未确认 RAG 可命中 | 刷新状态或重试 reindex |
| `indexing` | 索引中 | 页面正在进入检索链路 | 等待完成后复查 |
| `indexed searchable` | 已索引，可检索 | 页面已可被 RAG 命中 | 可进入 RAG debug 或知识问答 |
| `ready` | 已就绪 | 页面状态满足下一步测试条件 | 根据来源范围执行 RAG debug |
| `retrievable` | 可检索 | Wiki 已进入可检索状态 | 可用于 Wiki-only / all-source 测试 |
| `sync pending` / `sync_pending` | 同步待确认 | 已提交同步，但状态未最终确认 | 稍后刷新状态 |
| `failed` | 失败 | 操作失败但来源尚未细分 | 查看错误详情，区分发布 / 同步 / 索引失败 |
| `sync failed` | 同步失败 | Wiki 同步到后端或 WeKnora 失败 | 查看错误并重试 |
| `publish failed` | 发布失败 | 发布动作未成功完成 | 检查错误并重新发布 |
| `refresh failed` | 刷新失败 | 状态刷新或 reindex 检查失败 | 重试刷新，必要时查看后端日志 |
| `index timeout` | 索引超时 | 发布后长时间未变为可检索 | 标记风险并重试索引 |
| `fallback unavailable` | fallback 不可用 | 当前后备能力不可用 | 不把该状态当作真实通过 |
| `unknown` / `not loaded` | 状态未知 | 页面未加载或后端没有返回完整状态 | 重新选择页面或刷新 |
| `archived` | 已归档 | 页面不作为当前检索资料使用 | 如需测试应恢复或新建草稿 |

#### P4-C3.3 页面区域文案建议

| 页面位置 | 当前常见文案 | 中文化建议 |
| --- | --- | --- |
| 页面状态 pill | `draft` / `published` | `草稿` / `已发布` |
| 索引状态标题 | `Index` | `索引状态` |
| 来源区域标题 | `Sources` | `来源引用` |
| 绑定区域标题 | `Bindings` | `Citation 绑定` 或 `引用绑定` |
| 发布确认标题 | `Publish confirmation` | `发布确认` |
| 发布风险 | `Published pages are not considered retrievable until indexing succeeds.` | `页面发布后仍需完成索引，才可视为可检索。` |
| source refs | `source refs` | `来源引用数` |
| citations | `citations` | `引用数` |
| status | `status` | `状态` |
| published | `published` | `发布时间` |
| indexed | `indexed` | `索引时间` |
| embedding | `embedding` | `索引向量状态` |
| retrievable | `retrievable` | `是否可检索` |
| timeout | `timeout` | `是否超时` |

#### P4-C3.4 颜色和动作提示规则

状态中文化必须同时给出动作提示：

- 草稿类状态：提示“继续编辑或发布”，不展示为可检索。
- 已发布但未索引：提示“刷新索引或稍后重试”，不能显示为可用于知识问答。
- 索引中：提示“等待索引完成”，避免用户反复点击发布。
- 可检索：提示“可用于 RAG debug 和知识问答”，并允许进入 Wiki-only / all-source 测试。
- 失败类状态：提示“查看错误并重试”，不要只显示 failed。
- fallback unavailable：提示“后备能力不可用，不能作为真实链路验收”。

#### P4-C3.5 验收口径

Wiki 状态中文化规划完成后，后续实现应满足：

1. 用户在第一眼能看到中文主状态，而不是只看到 `draft`、`published`、`indexing` 或 `retrievable`。
2. 每个状态都有对应下一步动作提示。
3. 调试字段可以保留英文技术名，但必须放在详情区或辅助信息中。
4. `published` 不得被翻译成“已可检索”；必须与索引 / retrievable 状态分开。
5. failed 类状态必须说明是发布、同步、刷新还是索引失败。
6. mock / fallback 状态不得被文案包装成真实 WeKnora live 成功。

状态：[x]

### P4-D：知识问答单工作流质量优化

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-D1 | `knowledge_qa` 默认检索策略规划 | [x] |
| P4-D2 | 知识问答引用与拒答验收规则 | [x] |
| P4-D3 | 知识问答结果展示中文化规划 | [x] |

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

规划输出：

#### P4-D1.1 默认体验边界

`knowledge_qa` 是 Phase 4 第一段唯一重点 Agent 工作流。正式知识问答页应保持简单，不暴露 RAG debug 的工程参数。默认体验只允许：

- 问题输入。
- 简单检索范围：全部来源、仅文档、仅 Wiki。
- 回答、引用、依据不足提示。

正式知识问答页默认不展示：

- raw filters、raw metadata、WeKnora 原始响应。
- score threshold、hybrid、rerank、debug_trace。
- KB ID、Document IDs、business_area、document_type 的自由文本调试区。

这些参数只能留在 RAG / Wiki 调试页。

#### P4-D1.2 默认检索范围

默认策略：

| 场景 | 默认范围 | 理由 |
| --- | --- | --- |
| 普通知识问答 | all-source | 同时覆盖文档 evidence 和 Wiki evidence，避免漏掉已发布专题 |
| 用户明确选择“仅文档” | document | 只允许 `document_chunk`，用于政策、法规、案例、FAQ 问题 |
| 用户明确选择“仅 Wiki” | wiki | 只允许 `wiki_page`，用于已发布专题页问题 |
| Wiki 未发布或不可检索 | document 或依据不足 | 不把 draft / published-not-indexed Wiki 当成可用依据 |
| 无答案 / 资料不足 | all-source 后拒答 | 不因命中相似材料而编造答案 |

默认 all-source 不代表无限放宽。回答阶段必须仍按 evidence 质量、source_type 和答案要点判断是否足以回答。

#### P4-D1.3 默认 `top_k`

默认知识问答建议使用 `top_k=5` 作为正式体验起点，原因：

1. 与现有 QA agent 默认值一致，避免规划与当前行为冲突。
2. 正式页面应减少干扰 evidence，降低相似文档混淆。
3. P4-B2 的质量基线仍可在 RAG debug 使用 `top_k=8` 做诊断，不要求正式页暴露该参数。

后续若 P4-B2 / P4-B3 真实回归显示 `top_k=5` 漏掉 Wiki 或跨文档关键锚点，可在单独任务中调整默认值；调整前必须记录 fixture / local live / 真实 WeKnora live 的对照结果。

#### P4-D1.4 Wiki 参与策略

Wiki 参与正式知识问答必须满足：

- Wiki 页面已发布，并且索引状态为 retrievable / indexed searchable 或等价状态。
- Wiki evidence 返回 `source_type=wiki_page`。
- Wiki citation 至少可定位到 `wiki_page_id`、标题和片段。
- Draft、published not indexed、sync failed、index timeout、fallback unavailable 不得被当作正式 Wiki evidence。

默认 all-source 下：

- 精确事实、条款定位、案例复盘优先使用 document_chunk；若 Wiki 只做专题总结，不能替代原始条款引用。
- Wiki 检索题和专题总结题允许优先使用 wiki_page。
- 混合题（例如 P4Q-013）应同时保留 Wiki evidence 与 document_chunk evidence。

#### P4-D1.5 依据不足触发口径

`knowledge_qa` 应在以下情况提示依据不足：

1. 检索结果为空，或没有命中期望锚点 / 相关 evidence。
2. 只命中干扰材料、旧版材料或相似但不相关材料。
3. 问题要求真实监管部门、真实客户名称、真实政策编号等资料库未提供的信息。
4. Wiki 题只找到 draft / published not indexed 页面，不能确认其可检索。
5. 引用无法追溯，缺少 source_type、evidence_id、chunk_id 或 wiki_page_id 等关键定位字段。

依据不足提示应说明“当前资料库没有足够依据”，不要输出泛化常识答案，也不要把 mock / fallback 证据包装成真实依据。

#### P4-D1.6 与测试问题集的关系

默认策略应优先用以下问题回归：

| 问题类型 | 问题示例 | 默认期望 |
| --- | --- | --- |
| 文档事实 / 条款 | P4Q-001 到 P4Q-009 | document_chunk 引用充分 |
| 跨文档综合 | P4Q-010 到 P4Q-013 | all-source 下覆盖多个锚点 |
| 案例复盘 | P4Q-014 到 P4Q-016 | document_chunk 为主，不混淆案例 |
| Wiki 检索 | P4Q-017 到 P4Q-019 | wiki_page 引用充分 |
| 无答案 | P4Q-020、P4Q-021 | 明确依据不足 |
| 干扰排除 | P4Q-022、P4Q-023 | 不把干扰材料当政策依据 |
| 新旧版本 | P4Q-024 | 优先新版，并说明旧版差异 |

#### P4-D1.7 后续实现注意事项

P4-D1 只是默认策略规划，不改 Agent 代码。后续实现如需调整 agent，应保持：

- `policy_analysis` 和 `case_review` 现状不变。
- `knowledge_qa` 不直接依赖 raw WeKnora response。
- 正式页不暴露 debug 参数。
- mock / fixture 不能作为真实 RAG / Wiki live 通过依据。

状态：[x]

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

规划输出：

#### P4-D2.1 回答分级

知识问答验收先按问题类型分级，而不是只看最终回答是否流畅：

| 问题类型 | 是否必须回答 | 引用要求 | 拒答要求 |
| --- | --- | --- | --- |
| 精确事实 | 是 | 必须引用命中的 `document_chunk` 或 `wiki_page` | 若找不到对应锚点，提示依据不足 |
| 条款定位 | 是 | 必须引用对应条款所在 evidence | 不得用相似条款替代 |
| 跨文档综合 | 是 | 必须覆盖关键来源；P4Q-013 必须同时有文档和 Wiki 引用 | 若关键来源缺失，只能说明部分依据或依据不足 |
| 案例复盘 | 是 | 必须引用案例文档 evidence | 不得混淆蓝湾和北辰两个案例 |
| Wiki 检索 | 是 | 必须引用 `wiki_page` | Wiki 未发布或不可检索时提示依据不足 |
| 无答案 | 否 | 不要求引用 | 必须说明资料库没有足够依据，不得编造 |
| 干扰排除 | 视问题而定 | 引用必须来自正确材料 | 不得把干扰材料当政策、法规或案例依据 |
| 新旧版本冲突 | 是 | 必须引用新旧版本 evidence | 必须说明当前优先新版，不能只答旧版 |

#### P4-D2.2 引用通过标准

一次 `knowledge_qa` 回答只有同时满足以下条件，才算引用验收通过：

1. 每个事实性结论都能追溯到 citation。
2. citation 能定位到 `evidence_id`，并至少包含 `source_type`。
3. 文档引用应能定位到 `document_id` / `chunk_id` / 文档锚点中的至少一种。
4. Wiki 引用应能定位到 `wiki_page_id` / Wiki 标题 / Wiki 锚点中的至少一种。
5. 引用片段与回答要点一致，不能只引用同主题但无对应答案点的材料。
6. mock / fallback 引用不能作为真实 RAG / Wiki 验收依据。
7. `source_type=wiki_page` 和 `source_type=document_chunk` 不得互相伪装。

引用数量不是唯一指标。一个回答引用很多材料，但缺少关键锚点、引用错误来源或无法追溯，仍然判为失败。

#### P4-D2.3 必须引用的问题范围

以下问题必须出现可追溯引用：

| 范围 | 问题 | 最低引用要求 |
| --- | --- | --- |
| 精确事实 | P4Q-001 到 P4Q-005 | 至少 1 条命中目标锚点的文档引用 |
| 条款定位 | P4Q-006 到 P4Q-009 | 至少 1 条命中目标条款文档引用 |
| 跨文档综合 | P4Q-010 到 P4Q-012 | 覆盖每个关键文档锚点，允许按要点合并说明 |
| 混合综合 | P4Q-013 | 至少 1 条 Wiki 引用和 1 条文档引用 |
| 案例复盘 | P4Q-014 到 P4Q-016 | 引用正确案例文档，不混用相似案例 |
| Wiki 检索 | P4Q-017 到 P4Q-019 | 至少 1 条 `wiki_page` 引用 |
| 干扰排除 | P4Q-022 到 P4Q-023 | 引用正确材料，并说明干扰材料不能作为政策依据 |
| 新旧版本冲突 | P4Q-024 | 同时引用旧版和新版，结论优先新版 |

若上述问题没有 citation，或者 citation 无法定位到期望 source_type / anchor，应判为失败，而不是“回答内容大致正确”。

#### P4-D2.4 依据不足与拒答通过标准

`knowledge_qa` 在以下情况下必须明确提示依据不足：

1. P4Q-020：资料库没有“真实监管部门每小时上报”的依据。
2. P4Q-021：资料为合成脱敏材料，不能编造真实客户名称。
3. 检索结果为空，或 top_k 内只有同主题但无答案要点的材料。
4. 只命中 `TEST-DISTRACTOR-001`，但问题要求政策、法规、案例或 Wiki 事实。
5. Wiki 题只存在 draft / published not indexed / sync failed / index timeout 页面。
6. 回答阶段无法生成可追溯 citation。

拒答文本必须包含三层含义：

- 当前资料库没有足够依据。
- 不能根据现有材料确认该说法。
- 需要补充资料或换用可检索来源后再判断。

拒答时不得输出虚构监管部门、真实客户、真实政策编号、真实项目名、私有地址或未入库事实。

#### P4-D2.5 部分依据与失败边界

有些问题可能只命中部分来源。验收口径如下：

| 情况 | 允许输出 | 判定 |
| --- | --- | --- |
| 跨文档题只命中一个关键文档 | 可以回答已命中部分，并说明缺少另一部分依据 | 部分通过 / 需复核 |
| P4Q-013 只命中文档或只命中 Wiki | 可以说明部分依据，但不得声称完整回答 | 失败，因混合引用缺失 |
| 新旧版本题只命中旧版 | 必须提示缺少新版依据，不能直接给旧版结论 | 失败，因当前版本判断不足 |
| 干扰材料被召回但未被引用 | 可以记录为检索风险 | 回答可通过，检索需复核 |
| 干扰材料被当作政策依据 | 不允许 | 失败 |
| 无答案题命中相似材料 | 必须仍提示依据不足 | 通过前提是不编造、不错误引用 |

#### P4-D2.6 人工验收记录字段

每次知识问答验收至少记录：

| 字段 | 说明 |
| --- | --- |
| question_id | 对应 `questions.json` 的 P4Q 编号 |
| question_type | 精确事实、条款定位、跨文档综合、案例复盘等 |
| retrieval_scope | document / wiki / all |
| expected_anchors | 期望命中锚点 |
| answer_points_covered | 是否覆盖期望答案要点 |
| citation_source_types | 实际引用中的 `document_chunk` / `wiki_page` |
| citation_traceability | 是否可定位到 evidence / chunk / wiki page |
| insufficient_evidence | 是否触发依据不足 |
| forbidden_anchor_used | 是否错误使用禁用锚点 |
| verdict | 通过 / 部分通过 / 失败 |

#### P4-D2.7 后续实现注意事项

P4-D2 只定义验收规则，不修改 Agent 或 prompt。后续实现若调整 `knowledge_qa`，必须保持：

- `policy_analysis` 和 `case_review` 不被本任务牵连。
- 正式问答不展示 raw WeKnora 响应。
- 调试参数仍留在 RAG / Wiki 调试页。
- 验收报告必须区分 mock、fixture、本地 live 和真实 WeKnora live。

状态：[x]

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

规划输出：

#### P4-D3.1 中文化范围边界

P4-D3 只规划正式知识问答结果展示，不改代码，不扩展到完整前端中文化。范围限定为：

- 知识问答页 / 分析台中 `knowledge_qa` 的问题输入、回答、结果区。
- 证据摘要、引用列表、警告和空状态。
- Wiki 草稿入口中与知识问答结果相关的状态文案。
- 保留必要技术字段，但用中文标签解释含义。

不纳入本任务：

- 首页、资料库、RAG debug、Wiki 页面全量中文化。
- `policy_analysis` 和 `case_review` 的工作流文案重构。
- 复杂筛选、权限、导出、审批或多 Agent 编排。

#### P4-D3.2 术语映射清单

以下英文术语在正式知识问答结果页不得直接裸露给普通用户：

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `Evidence` | 依据 / 证据 | 引用面板标题 | 正式页优先用“依据”，调试页可用“Evidence” |
| `Citation` / `Citations` | 引用 / 引用来源 | 引用列表、历史输出 | 强调答案来自哪些材料 |
| `Score` | 相关度分数 | 引用卡片 | 不作为可信度绝对值，只说明检索相关度 |
| `Score unavailable` | 暂无相关度分数 | 引用卡片 | 避免用户误解为错误 |
| `Source` | 来源 | 来源筛选、引用元信息 | 普通页展示为“来源” |
| `Source type` | 来源类型 | 引用详情 | 可显示“文档片段 / Wiki 页面” |
| `No evidence` | 暂无可用依据 | RAG 模式、空状态 | 不等同系统失败 |
| `Mock fallback` | 模拟兜底结果 | RAG 模式 | 必须提示不可作为真实依据 |
| `Real WeKnora RAG` | 真实 WeKnora 检索 | RAG 模式 | 表示经 PA Adapter 使用真实 WeKnora 依据 |
| `Real RAG` | 真实检索 | RAG 模式 | 非 mock 的真实知识库检索 |
| `Document` | 文档片段 | 来源统计 / 引用卡片 | 对应 `document_chunk` |
| `WeKnora Document` | WeKnora 文档片段 | 引用卡片 | 保留 WeKnora 来源但中文说明 |
| `Wiki` / `WeKnora Wiki` | Wiki 页面 / WeKnora Wiki 页面 | 引用卡片 | 对应 `wiki_page` |
| `Total` | 合计 | 依据统计 | 显示总引用数 |
| `Workflow` | 问答流程 | 右侧工具区 | `knowledge_qa` 场景下不强调 Agent |
| `Messages` | 对话记录 | 中间消息区 | 降低工程感 |
| `Conversations` | 会话 | 左侧列表 | 与现有“新会话”一致 |
| `Result` | 回答结果 | 结果面板 | 展示最终回答 |
| `Progress` | 运行进度 | 任务进度 | 状态用中文化标签 |
| `locatable` | 可定位 | 引用卡片 | 表示能跳转到材料位置 |
| `not locatable` | 暂不可定位 | 引用卡片 | 需要提示引用需复核 |
| `Citation metadata` | 引用详情 | 展开区 | 默认折叠，避免普通用户先看到 raw metadata |

#### P4-D3.3 结果区信息层级

知识问答结果页应按以下顺序展示，不把调试字段放在第一视觉层级：

1. 回答结果：标题用“回答结果”，正文保留 markdown。
2. 依据摘要：显示“依据数量”“文档片段”“Wiki 页面”“真实检索 / 模拟兜底”。
3. 依据不足提示：若 warnings 命中无依据语义，显示“当前资料库依据不足或引用需要复核”。
4. 引用来源：展示标题、片段、来源类型、是否可定位。
5. 引用详情：展开后才展示 evidence_id、chunk_id、wiki_page_id、source_type、score 等技术字段。

正式知识问答页不应默认显示 raw filters、raw metadata、debug_trace、KB ID、Document IDs、hybrid、rerank、score threshold。

#### P4-D3.4 RAG 模式中文表达

RAG 模式应帮助用户判断答案可信来源，而不是暴露后端实现细节：

| 模式 | 中文展示 | 需要补充说明 |
| --- | --- | --- |
| `No evidence` | 暂无可用依据 | 当前回答不应当作资料库结论 |
| `Mock fallback` | 模拟兜底结果 | 仅用于演示或离线开发，不作为真实验收依据 |
| `Real RAG` | 真实检索 | 来自已接入知识库的证据 |
| `Real WeKnora RAG` | 真实 WeKnora 检索 | 通过 PA Adapter 使用 WeKnora 证据，不直接暴露 WeKnora 原始响应 |

当引用数量为 0 时，应显示“暂无可用依据”，并引导用户补充资料或切换检索范围，而不是只显示空白。

#### P4-D3.5 引用卡片中文表达

引用卡片默认展示：

- 标题。
- 片段。
- 来源类型：文档片段 / Wiki 页面 / 模拟引用 / 未知来源。
- 定位状态：可定位 / 暂不可定位。
- 相关度分数：有值时显示“相关度分数 0.xx”，无值时显示“暂无相关度分数”。

引用卡片展开后再展示：

- `evidence_id`：依据 ID。
- `chunk_id`：文档片段 ID。
- `wiki_page_id`：Wiki 页面 ID。
- `source_type`：来源类型。
- `external_doc_id`：外部文档 ID。
- `retrieval_rank`：检索排序。

这些技术字段可以保留原始 key，但必须配中文标签或说明；复制引用文本可保留机器可读字段，避免破坏调试和验收。

#### P4-D3.6 依据不足与警告中文表达

知识问答页应把英文警告和空状态转成可理解表达：

| 场景 | 推荐文案 |
| --- | --- |
| 无引用 | 暂无引用来源 |
| 无依据 | 当前资料库没有足够依据回答这个问题 |
| 引用不可定位 | 该引用暂不可定位，请复核来源 |
| mock 引用 | 当前为模拟兜底结果，不作为真实资料库依据 |
| Wiki 未可检索 | Wiki 页面尚不可检索，不能作为正式依据 |
| 部分命中 | 只找到部分依据，回答需要复核 |
| 错误 / HTTP 错误 | 请求失败，请检查服务状态或稍后重试 |

P4Q-020、P4Q-021 这类无答案问题，页面应突出“依据不足”，不应把空引用解释成正常回答。

#### P4-D3.7 验收检查点

后续实现 P4-D3 对应前端改动时，至少检查：

1. `knowledge_qa` 默认页面不再直接展示 `Evidence`、`Citation`、`Score`、`Source`、`No evidence`、`Mock fallback`、`Real WeKnora RAG` 等英文主标签。
2. 证据摘要能区分文档片段、Wiki 页面、模拟兜底和真实 WeKnora 检索。
3. 无引用 / 依据不足 / 引用不可定位都有中文提示。
4. 技术字段默认折叠，不抢占回答结果和引用片段。
5. `policy_analysis`、`case_review` 不因本任务被改动。

状态：[x]

### P4-E：前端中文化与低门槛体验

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-E1 | 首页与运行状态中文化规划 | [x] |
| P4-E2 | 资料库与 RAG 调试页中文化规划 | [x] |
| P4-E3 | Wiki 与知识问答页中文化规划 | [x] |

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

规划输出：

#### P4-E1.1 首页中文化范围

P4-E1 只规划首页与运行状态文案，不改前端实现。覆盖范围：

- 首页总览区。
- 核心数据卡片。
- 模型、Embedding、RAG、能力矩阵运行状态卡片。
- 内置工作流入口。
- 工作区快捷入口。
- mock / real / WeKnora / 配置缺失等状态说明。

不纳入本任务：

- 资料库、RAG debug、Wiki、知识问答详情页。
- 后端状态 API 字段结构。
- Agent 工作流行为。

#### P4-E1.2 首页主导航与分区术语

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `PA AI Workbench` | PA 智能工作台 | 首页品牌 / 总览 | 可保留英文产品名作为副标题，但中文名应是第一理解层 |
| `Workspace` | 工作区 | 快捷入口面板 | 与路由入口一致 |
| `Agent Workflows` | 内置分析流程 | 工作流面板 | 避免普通用户理解成复杂 Agent 编排 |
| `Workflow` | 分析流程 | 单个任务入口 | 对应知识问答、政策分析、案例复盘 |
| `Capability` | 能力状态 | 运行状态卡片 | 表示当前后端能力是否可用于验收 |
| `RAG Pipeline` | 知识检索链路 | 运行状态卡片 | 不直接叫“管线”，降低工程感 |
| `Chat Model` | 问答模型 | 模型状态卡片 | 表示生成回答的模型 |
| `Embedding` | 向量模型 | 向量状态卡片 | 表示索引 / 检索使用的向量能力 |
| `Chunks` | 文档片段 | 核心数据卡片 | 与资料库分块概念一致 |
| `outputs` | 生成结果 | 核心数据卡片 | 对应历史输出 |

#### P4-E1.3 运行状态中文表达

首页状态卡片必须区分“可用”“缺配置”“模拟兜底”“真实 WeKnora 连接”等不同含义：

| 当前状态 | 建议中文表达 | 用户含义 |
| --- | --- | --- |
| `configured` | 已配置 | 对应模型或服务参数已填写 |
| `missing config` | 缺少配置 | 需要补充配置后才能使用真实能力 |
| `loading` | 连接中 | 正在读取后端状态 |
| `error` | 状态异常 | 状态接口或服务不可用 |
| `mock fallback` | 模拟兜底 | 可演示流程，但不能当真实 RAG / Wiki 验收 |
| `real ready` | 真实能力可用 | 已接入非 mock 知识能力 |
| `weknora connected` | WeKnora 已连接 | 真实 WeKnora 后端连通 |
| `weknora unavailable` | WeKnora 不可用 | 已选择 WeKnora 模式但暂不可用 |
| `fail closed` | 验收关闭 | 能力不满足真实验收条件 |
| `eligible` | 可用于验收 | 能力满足当前验收条件 |
| `dev only` | 仅开发可用 | 适合开发调试，不作为正式验收 |
| `supported` | 已支持 | 能力完整支持 |
| `partial` | 部分支持 | 能力可用但不完整 |
| `unsupported` | 未支持 | 当前后端不支持 |

`Mock`、`mock fallback`、`dev only` 必须显式提示“不能作为真实验收依据”，避免用户把演示数据误认为真实知识库结果。

#### P4-E1.4 状态详情字段中文表达

首页状态详情可以保留少量技术值，但标签应中文化：

| 当前字段 | 建议中文标签 | 说明 |
| --- | --- | --- |
| `mock` | 模拟模式 | 是 / 否 |
| `api key` | API Key | 已配置 / 未配置 |
| `timeout` | 超时时间 | 单位秒 |
| `dimension` | 向量维度 | 未配置时显示“未设置” |
| `auth` | 鉴权配置 | 已配置 / 缺失 |
| `workspace` | 工作区配置 | 已配置 / 缺失 |
| `kb` | 知识库配置 | 已配置 / 缺失 |
| `health` | 健康状态 | 来自后端状态 |
| `backend mock` | 后端模拟模式 | 是 / 否 |
| `model mock` | 模型模拟模式 | 是 / 否 |
| `database` | 数据库 | 显示当前后端数据库标识 |
| `facts` | 事实来源 | 能力矩阵中的事实来源 |
| `kb maps` | 知识库映射 | 显示映射数量 |
| `citation` | 引用追溯 | 显示引用链路状态 |
| `wiki publish` | Wiki 发布 | 显示 Wiki 发布能力状态 |
| `debug` | 调试能力 | 显示调试能力状态 |

#### P4-E1.5 首页信息层级

首页应按“用户先判断系统能不能用，再进入功能”的顺序组织：

1. 总览：PA 智能工作台 + 当前后端连接状态。
2. 核心数据：资料、文档片段、任务、生成结果。
3. 运行状态：问答模型、向量模型、知识检索链路、能力状态。
4. 内置分析流程：知识问答、政策分析、案例复盘。
5. 工作区入口：资料库、智能分析、Wiki、生成历史。

运行状态卡片应避免第一眼出现大量英文枚举；技术枚举可作为次级详情保留。

#### P4-E1.6 WeKnora 与 PA 边界表达

首页不应把 PA AI Workbench 表达成 WeKnora 前端。推荐口径：

- “真实 WeKnora 检索”：表示 PA 通过 Adapter 使用 WeKnora 知识能力。
- “WeKnora 已连接”：表示底层能力可用，不代表用户直接进入 WeKnora。
- “知识检索链路”：表示 PA 标准化后的 RAG / Wiki 能力。
- “模拟兜底”：表示开发或演示路径，不是正式知识库依据。

避免使用：

- “WeKnora 工作台”。
- “WeKnora 首页”。
- “直接调用 WeKnora API”。
- “mock 已通过真实验收”。

#### P4-E1.7 后续实现检查点

后续实现 P4-E1 对应前端改动时，至少检查：

1. 首页不再裸露 `Chat Model`、`Embedding`、`RAG Pipeline`、`Capability`、`Agent Workflows`、`Workspace` 作为主标签。
2. `configured`、`missing config`、`mock fallback`、`dev only`、`eligible`、`fail closed` 有中文解释。
3. mock / real / WeKnora 状态的差异不会被翻译抹平。
4. 首页仍保持 PA AI Workbench 独立产品表述，不变成 WeKnora 子产品。
5. 本任务不修改资料库、RAG debug、Wiki 或知识问答详情页。

状态：[x]

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

规划输出：

#### P4-E2.1 中文化范围边界

P4-E2 只规划资料库与 RAG 调试页的中文文案和参数分层，不改前端代码。覆盖范围：

- 资料上传表单。
- 资料列表、筛选、处理状态、分块预览、处理事件。
- RAG 调试页查询表单、过滤参数、调试结果、证据卡片。
- mock / extracted / WeKnora 后端来源说明。

不纳入本任务：

- 首页运行状态。
- Wiki 页面和知识问答结果页。
- 后端 API 字段结构或检索行为。
- 将 RAG debug 参数搬到正式知识问答页。

#### P4-E2.2 资料库术语映射

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `Documents` | 资料列表 | 资料列表标题 | 面向用户用“资料”，技术详情可保留 document id |
| `Chunks` | 文档片段 | 分块预览 | 与 RAG evidence 口径一致 |
| `Events` | 处理事件 | 事件列表 | 表示解析、分块、索引等过程记录 |
| `uploaded` | 已上传 | 状态筛选 / 状态徽标 | 文件已进入处理队列 |
| `processing` | 处理中 | 状态筛选 | 可泛指 parsing / chunking / embedding / indexing |
| `indexed` | 已索引 | 状态筛选 / 状态徽标 | 可用于检索或问答 |
| `failed` | 处理失败 | 状态筛选 / 状态徽标 | 需要展示失败步骤和错误信息 |
| `unavailable` | 不可用 | 状态筛选 | 资料暂不能用于检索 |
| `mock` | 模拟后端 | 后端筛选 | 不能作为真实验收依据 |
| `extracted` | 本地抽取后端 | 后端筛选 | 表示 PA 自有本地知识引擎路径 |
| `WeKnora` | WeKnora 后端 | 后端筛选 / 资料行 | 表示经 PA Adapter 使用 WeKnora 能力 |
| `tokens` | token 数 | 分块详情 | 可保留英文 token，但要说明是片段长度指标 |
| `chars` | 字符数 | 分块详情 | 片段字符长度 |
| `indexed:` | 已索引： | 分块统计 | 显示已进入检索的片段数量 |
| `pending:` | 待处理： | 分块统计 | 显示等待处理的片段数量 |
| `failed:` | 失败： | 分块统计 | 显示失败片段数量 |

#### P4-E2.3 资料处理状态口径

资料库状态必须帮助用户判断“能不能提问”，而不是只暴露流水线阶段：

| 阶段 | 推荐中文 | 用户含义 |
| --- | --- | --- |
| parsing | 解析中 | 正在读取文件内容 |
| parsed | 已解析 | 文件内容已读取，等待或已经进入分块 |
| chunking | 分块中 | 正在切成可检索片段 |
| chunked | 已分块 | 文档片段已生成 |
| embedding | 向量生成中 | 正在生成检索向量 |
| indexing | 索引中 | 正在写入检索索引 |
| indexed | 可提问 | 已可用于 RAG / 知识问答 |
| stalled / timeout | 处理超时 | 需要刷新状态或恢复处理 |
| failed | 处理失败 | 需要查看失败步骤并重试 |

资料行应优先显示“可提问 / 处理中 / 处理失败 / 等待处理”，再展示解析、分块、向量、索引的细节。

#### P4-E2.4 RAG 调试页参数术语映射

RAG 调试页允许保留技术参数，但必须用中文标签解释用途：

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `Query` | 测试问题 | 查询输入 | 用于输入待检索的问题 |
| `Top K` | 返回数量 | 参数输入 | 显示最多返回多少条 evidence；可保留 `top_k` 作为技术名 |
| `Source` | 来源范围 | 参数输入 | 全部来源 / 仅文档 / 仅 Wiki |
| `All` | 全部来源 | 来源选项 | 不传 `source_type` |
| `Document` | 文档片段 | 来源选项 | 对应 `document_chunk` |
| `Wiki` | Wiki 页面 | 来源选项 | 对应 `wiki_page` |
| `Document IDs` | 指定文档 ID | 过滤参数 | 多个 ID 用逗号分隔，属于调试能力 |
| `KB ID` | 知识库 ID | 过滤参数 | 仅用于定位 WeKnora / 后端知识库 |
| `Business` | 业务域 | 过滤参数 | 对应 `business_area` |
| `Document Type` | 资料类型 | 过滤参数 | 对应 `document_type` |
| `Run` | 运行检索 | 操作按钮 | 执行一次调试检索 |
| `Reset` | 重置参数 | 操作按钮 | 清空表单和结果 |
| `Debug unavailable` | 当前后端不支持调试 | 空状态 | 不代表知识问答不可用 |
| `Running` | 检索中 | 加载状态 | 正在请求调试结果 |
| `No trace` | 暂无调试记录 | 初始状态 | 尚未运行检索 |
| `No evidence` | 暂无命中依据 | 结果空状态 | 当前参数下没有命中 evidence |
| `hits` | 命中条数 | 结果摘要 | 显示返回 evidence 数量 |
| `Score unavailable` | 暂无相关度分数 | evidence 卡片 | 后端未返回分数 |
| `Score` | 相关度分数 | evidence 卡片 | 只表示检索排序参考 |

#### P4-E2.5 调试参数分层

RAG 调试页应按“常用参数优先，高级过滤次之”的层级组织：

| 层级 | 字段 | 展示建议 |
| --- | --- | --- |
| 基础 | 测试问题、返回数量、来源范围 | 默认展开，测试者每次都会使用 |
| 范围过滤 | 指定文档 ID、知识库 ID | 放在筛选区，提示是调试定位用途 |
| 业务过滤 | 业务域、资料类型 | 放在筛选区，避免误认为正式问答必填 |
| 结果摘要 | trace_id、命中条数、top_k、filters | 作为调试信息展示，不进入正式知识问答页 |
| evidence 详情 | rank、title、summary、source_type、score、metadata | 用于排查命中质量和引用来源 |

正式知识问答页不得继承 Document IDs、KB ID、debug_trace、raw metadata、score threshold、hybrid、rerank 等工程参数。

#### P4-E2.6 证据结果中文表达

RAG 调试结果应帮助测试者判断“为什么命中 / 为什么没命中”：

- `#rank`：排序。
- `title`：资料标题。
- `summary`：命中片段摘要。
- `source_type`：来源类型，显示为文档片段 / Wiki 页面 / 未知来源。
- `source`：后端来源，显示为 WeKnora / 本地抽取 / 模拟后端。
- `evidence_id`：依据 ID，可保留技术字段。
- `chunk_id`：文档片段 ID，可保留技术字段。
- `wiki_page_id`：Wiki 页面 ID，可保留技术字段。
- `external_doc_id`：外部文档 ID，可保留技术字段。
- `metadata`：调试详情，默认可折叠或弱化显示。

当 `TEST-DISTRACTOR-001` 被命中时，调试页应便于记录“错误召回风险”，但不代表知识问答一定失败；最终回答仍要按 P4-D2 的引用和拒答规则判断。

#### P4-E2.7 后续实现检查点

后续实现 P4-E2 对应前端改动时，至少检查：

1. 资料库不再裸露 `Documents`、`Chunks`、`Events`、`uploaded`、`indexed`、`failed`、`mock`、`extracted` 等主标签。
2. RAG 调试页不再裸露 `Query`、`Top K`、`Source`、`Document IDs`、`Business`、`Document Type`、`Run`、`Reset`、`No evidence`、`Debug unavailable` 等主标签。
3. mock / extracted / WeKnora 的差异清晰，mock 不能被误认为真实验收。
4. `top_k`、`source_type`、`document_ids` 等技术字段可保留，但必须有中文标签和用途说明。
5. 本任务不改变检索参数默认值、不调整后端检索行为、不把调试参数移入正式知识问答页。

状态：[x]

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

规划输出：

#### P4-E3.1 中文化范围边界

P4-E3 只规划 Wiki 页面和知识问答页的中文文案，不改前端代码。覆盖范围：

- Wiki 搜索、页面列表、阅读器、编辑器、发布确认、索引状态。
- Wiki 来源引用、引用绑定、Evidence / Citation 展示。
- 知识问答页的会话、消息、工作流、Wiki 草稿、引用与警告区域。
- 角色标签、状态标签、依据不足提示和引用分数说明。

不纳入本任务：

- 首页与运行状态。
- 资料库与 RAG debug 参数页。
- 后端 API 字段结构、检索行为、Wiki 发布逻辑。
- 新增复杂 Agent 工作流。

#### P4-E3.2 Wiki 页面术语映射

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `Search` | 搜索 | Wiki 左侧搜索标题 | 搜索 Wiki 页面 |
| `Pages` | 页面列表 | Wiki 搜索结果 | 显示命中的 Wiki 页面数量 |
| `Editor` | 编辑器 | Wiki 主内容区 | 新建或编辑页面时显示 |
| `Reader` | 阅读器 | Wiki 主内容区 | 查看已保存页面时显示 |
| `Index` | 索引状态 | Wiki 右侧状态栏 | 表示页面是否可被 RAG 检索 |
| `Sources` | 来源引用 | Wiki 右侧来源区 | 页面沉淀自哪些输出、文档或引用 |
| `Bindings` | 引用绑定 | Wiki citation 绑定区 | Wiki 页面绑定的证据引用 |
| `Evidence` | 依据 / 证据 | Wiki 引用区 | 正式用户面优先显示“依据” |
| `Publish confirmation` | 发布确认 | 发布确认面板 | 明确发布后仍需索引完成才可检索 |
| `source refs` | 来源数量 | 发布确认面板 | 包含 output / document / citation 来源 |
| `citations` | 引用数 | 发布确认面板 | 与答案引用保持一致 |
| `status` | 页面状态 | 发布确认 / 索引卡片 | 显示草稿、已发布、归档等 |
| `published` | 已发布 | 页面状态 | 页面已发布，但不必然可检索 |
| `draft` | 草稿 | 页面状态 | 草稿不可进入正式 RAG |
| `archived` | 已归档 | 页面状态 | 不作为默认可检索内容 |

#### P4-E3.3 Wiki 索引与发布状态中文表达

Wiki 状态必须区分“已发布”和“可检索”：

| 当前状态 / 提示 | 建议中文表达 | 用户含义 |
| --- | --- | --- |
| `not loaded` | 未加载 | 尚未选择 Wiki 页面 |
| `draft not searchable` | 草稿不可检索 | 发布前不能作为正式 RAG 依据 |
| `published not indexed` | 已发布但未索引 | 已发布，但暂不能作为检索依据 |
| `indexed searchable` | 已索引可检索 | 可以用于 Wiki-only / all-source 测试 |
| `retrievable` | 可检索 | 可被 RAG 和知识问答引用 |
| `indexing` | 索引中 | 等待索引完成后再验收 |
| `sync failed` | 同步失败 | 需要查看错误并重试 |
| `publish failed` | 发布失败 | 页面未成功进入发布状态 |
| `index timeout` | 索引超时 | 需要刷新或恢复状态 |
| `refresh failed` | 状态刷新失败 | 需要检查后端或稍后重试 |
| `not set` | 未设置 | 后端尚未返回该字段 |
| `yes` / `no` | 是 / 否 | 用于 retrievable、timeout 等布尔状态 |

发布确认风险提示应中文化：

- `No source refs or citation bindings are attached.` -> “当前页面没有来源引用或引用绑定。”
- `Page content is empty.` -> “页面内容为空。”
- `Published pages are not considered retrievable until indexing succeeds.` -> “页面发布后仍需索引成功，才能作为可检索依据。”
- `This page is backed by mock data.` -> “当前页面来自模拟数据，不作为真实验收依据。”

#### P4-E3.4 知识问答页术语映射

| 当前英文 / 技术词 | 建议中文表达 | 展示位置 | 说明 |
| --- | --- | --- | --- |
| `Conversations` | 会话 | 左侧会话列表 | 与“新会话”一致 |
| `Messages` | 对话记录 | 中间消息区 | 展示用户和助手消息 |
| `Workflow` | 分析流程 | 右侧任务区 | `knowledge_qa` 场景下不强调复杂 Agent |
| `Assistant` | 助手 | 消息角色 | AI 回复 |
| `Status` | 系统状态 | 消息角色 | 流程或系统进度消息 |
| `You` | 你 | 消息角色 | 用户输入 |
| `Wiki Draft` | Wiki 草稿 | 从回答生成 Wiki 区域 | 表示可将结果沉淀为草稿 |
| `Ready` | 就绪 | Wiki 草稿状态 | 可生成草稿 |
| `Evidence` | 依据 / 证据 | 引用与警告区域 | 优先显示“依据” |
| `Document` | 文档片段 | 依据统计 | 对应 `document_chunk` |
| `Total` | 合计 | 依据统计 | 总引用数 |
| `Real WeKnora RAG` | 真实 WeKnora 检索 | RAG 模式 | 通过 PA Adapter 使用真实 WeKnora 证据 |
| `Mock fallback` | 模拟兜底结果 | RAG 模式 | 不作为真实验收依据 |
| `No evidence` | 暂无可用依据 | RAG 模式 / 警告 | 应触发依据不足口径 |

#### P4-E3.5 引用与分数说明中文表达

引用组件在 Wiki 和知识问答页复用，需统一中文表达：

| 当前英文 / 技术词 | 建议中文表达 | 说明 |
| --- | --- | --- |
| `Score unavailable` | 暂无相关度分数 | 后端没有返回分数，不代表引用无效 |
| `Backend retrieval score` | 后端检索相关度分数 | 只用于排序参考，不是答案可信度 |
| `No backend score returned` | 后端未返回相关度分数 | 解释 tooltip |
| `Document` | 文档片段 | 文档 evidence |
| `Wiki` | Wiki 页面 | Wiki evidence |
| `Mock` | 模拟引用 | 不能作为真实验收依据 |
| `locatable` | 可定位 | 可跳转到来源位置 |
| `not locatable` | 暂不可定位 | 需要复核引用来源 |
| `Citation metadata` | 引用详情 | 默认折叠，避免普通用户先看到 raw metadata |

技术字段如 `evidence_id`、`chunk_id`、`wiki_page_id`、`source_type` 可以保留，但必须配中文标签或放在展开详情中。

#### P4-E3.6 依据不足与空状态中文表达

Wiki 与知识问答页应统一空状态和不足提示：

| 场景 | 推荐文案 |
| --- | --- |
| Wiki 无搜索结果 | 暂无页面 |
| Wiki 未选择页面 | 未选择页面 |
| Wiki 草稿不可检索 | 草稿不可检索，发布并索引后才能作为依据 |
| Wiki 已发布未索引 | 已发布但未索引，暂不能作为正式依据 |
| 知识问答无引用 | 暂无引用来源 |
| 知识问答无依据 | 当前资料库没有足够依据回答这个问题 |
| 引用不可定位 | 该引用暂不可定位，请复核来源 |
| 模拟引用 | 当前为模拟兜底结果，不作为真实资料库依据 |
| Wiki 写入不可用 | 当前后端不支持 Wiki 写入 |

P4Q-017 到 P4Q-019 的 Wiki 检索题必须能让用户看懂“Wiki 页面引用”和“文档片段引用”的区别；P4Q-020、P4Q-021 必须突出依据不足。

#### P4-E3.7 后续实现检查点

后续实现 P4-E3 对应前端改动时，至少检查：

1. Wiki 页面不再裸露 `Search`、`Pages`、`Editor`、`Reader`、`Publish confirmation`、`Sources`、`Bindings`、`Evidence` 等主标签。
2. 知识问答页不再裸露 `Assistant`、`Status`、`You`、`Workflow`、`Messages`、`Conversations`、`Wiki Draft`、`Ready` 等主标签。
3. `Score unavailable`、`Backend retrieval score`、`No backend score returned` 有中文解释。
4. Wiki 已发布与可检索状态必须分开表达，不能让用户误以为“已发布=可检索”。
5. mock / fallback / draft / not indexed 都不能被包装成真实可用 evidence。
6. 本任务不改变 Wiki 发布、索引、检索或知识问答逻辑。

状态：[x]

### P4-F：阶段验收 checklist 与回归标准

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-F1 | Phase 4 fixture / mock / live 验收分层 | [x] |
| P4-F2 | RAG / Wiki / QA 回归 checklist | [x] |
| P4-F3 | Phase 4 阶段收口检查 | [x] |

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

规划输出：

#### P4-F1.1 验收层级定义

Phase 4 所有 RAG / Wiki / `knowledge_qa` 验收记录必须标明层级，不能只写“通过”：

| 层级 | 定义 | 可证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| fixture | 只验证 `backend/fixtures/phase4_rag_wiki_qa/` 的文件、问题集、命中矩阵和 spec 规则 | 语料、问题、锚点、引用要求和安全边界完整 | 不能证明系统检索、Wiki 发布或知识问答真实可用 |
| mock | 使用 mock backend / mock model / mock citation 的开发路径 | 前端流程、API shape、错误态、UI 文案和基础回归 | 不能证明真实 RAG / Wiki / WeKnora live 链路 |
| 本地 live | 在本机真实 PA backend / frontend / knowledge engine 上运行，使用合成脱敏材料 | 本地真实链路趋势、检索参数、引用显示、拒答行为 | 不能等同真实 WeKnora 环境验收，除非后端确认为 `weknora_api` 且满足 live 条件 |
| 真实 WeKnora live | `KNOWLEDGE_BACKEND=weknora_api`、`MOCK_MODE=false`，经 PA Adapter 使用真实 WeKnora 检索 / Wiki 能力，且材料为合成脱敏 | 真实 RAG / Wiki / citation 链路可用 | 不能证明真实业务资料安全；不得使用真实敏感资料 |

验收记录必须同时写明：

- 验收层级。
- 使用材料：fixture 文件名 / Wiki slug / 问题 ID。
- 后端来源：mock / extracted / weknora_api。
- 是否包含副作用：上传、发布 Wiki、索引、生成输出。
- 结论：通过 / 部分通过 / 失败 / 阻塞。

#### P4-F1.2 各层级通过条件

| 层级 | 最低通过条件 |
| --- | --- |
| fixture | `manifest.json`、`questions.json` 可解析；9 份 Markdown 和命中矩阵存在；锚点、问题、答案要点、引用要求一致；不含敏感信息 |
| mock | 流程可运行并明确标记 mock / fallback；不把 mock citation 写成真实 WeKnora citation；无依据问题能出现警告或依据不足提示 |
| 本地 live | 使用合成脱敏材料完成上传 / 索引 / 检索 / QA；能记录 evidence、source_type、citation；失败能给出可解释错误 |
| 真实 WeKnora live | WeKnora 连接可用；上传合成脱敏文档后状态到达可检索；RAG debug 返回 `source=weknora_api` evidence；Wiki 发布后可返回 `source_type=wiki_page`；`knowledge_qa` 生成 non-mock citation |

如果某次验收只达到低层级，报告必须明确写“只通过 fixture / mock / 本地 live，不代表真实 WeKnora live 通过”。

#### P4-F1.3 不能冒充的情况

以下情况不能冒充真实 WeKnora live 通过：

1. `MOCK_MODE=true` 或返回 `source=mock`。
2. 使用 mock chat / mock embedding / mock RAG 生成结果。
3. fixture JSON 校验通过，但没有实际上传、索引或 retrieve。
4. 本地 extracted fallback 命中，但后端不是 `weknora_api`。
5. Wiki 只是 draft 或 published not indexed，未证明可检索。
6. RAG debug 返回 keyword-only / fallback / 旧 chunk，而不是当前材料的 evidence。
7. citation 缺少 `evidence_id`、`source_type`、`chunk_id` 或 `wiki_page_id` 等关键追溯字段。
8. 使用历史缓存、旧上传文件、旧 Wiki 页面或未确认当前 run 的 evidence。
9. 真实 WeKnora 环境不可用时，用“mock 能跑通”替代。
10. 验收报告没有记录层级、材料、后端来源和结论。

#### P4-F1.4 真实 WeKnora live 最小证据链

真实 WeKnora live 通过至少需要以下证据链：

1. 配置层：`KNOWLEDGE_BACKEND=weknora_api`，`MOCK_MODE=false`，WeKnora 连接状态为 connected / ready。
2. 材料层：使用合成脱敏 fixture 或已批准脱敏材料，不使用真实敏感资料。
3. 文档层：上传的当前文档可定位到唯一文件名、唯一锚点和当前 external document id。
4. 索引层：当前文档状态到达 indexed / retrievable 或等价可检索状态。
5. 检索层：RAG debug / retrieve 返回 `source=weknora_api`、`source_type=document_chunk`，并命中当前材料锚点。
6. Wiki 层：Wiki 题需证明页面已发布且可检索，返回 `source_type=wiki_page` 和 `wiki_page_id`。
7. QA 层：`knowledge_qa` 引用 non-mock citation，且 citation 可追溯到 document chunk 或 wiki page。
8. 拒答层：P4Q-020、P4Q-021 这类无答案题不编造真实监管部门、真实客户或真实政策编号。

#### P4-F1.5 报告模板

每次 Phase 4 验收建议使用以下记录格式：

| 字段 | 示例 |
| --- | --- |
| 验收层级 | fixture / mock / 本地 live / 真实 WeKnora live |
| 运行环境 | local backend + frontend / WeKnora API / fixture only |
| 材料 | `TEST-RAG-002`、`TEST-WIKI-001`、P4Q-013 |
| 后端来源 | mock / extracted / weknora_api |
| 配置摘要 | `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`，不记录 token |
| 操作 | upload / index / retrieve / publish wiki / knowledge_qa |
| 关键证据 | evidence_id、source_type、chunk_id、wiki_page_id、trace_id |
| 结果 | 通过 / 部分通过 / 失败 / 阻塞 |
| 限制 | 未运行真实 WeKnora live / 未发布 Wiki / 只验证 fixture |

报告禁止记录 API Key、service token、真实 endpoint、真实上传文件、数据库路径、日志原文或未脱敏输出。

#### P4-F1.6 与 Phase 4 任务的关系

- P4-A：fixture 层证明语料和问题集安全完整。
- P4-B：RAG debug 基线必须记录层级，同层级内比较质量变化。
- P4-C：Wiki 闭环必须区分 draft、published、retrievable 和真实 WeKnora live。
- P4-D：`knowledge_qa` 引用和拒答规则可先在 fixture / 本地 live 验证，但真实链路通过必须来自 non-mock evidence。
- P4-E：中文化必须避免把 mock / fallback / draft / not indexed 包装成真实通过。
- P4-F：最终收口必须明确哪些任务只有规划，哪些任务有 fixture / mock / live 证据。

状态：[x]

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

规划输出：

#### P4-F2.1 回归记录头

每次 RAG / Wiki / `knowledge_qa` 优化后，回归记录必须先写清：

| 字段 | 要求 |
| --- | --- |
| 回归层级 | fixture / mock / 本地 live / 真实 WeKnora live，沿用 P4-F1 分层 |
| 运行环境 | backend / frontend / WeKnora 连接状态，不记录 token 或真实 endpoint |
| 语料版本 | `phase4_rag_wiki_qa_v1`，记录上传批次或 fixture-only |
| 问题范围 | 全量 P4Q-001 到 P4Q-024，或说明抽样原因 |
| 检索范围 | document / wiki / all-source |
| 结论 | 通过 / 部分通过 / 失败 / 阻塞 |

如果只跑了局部问题，不能写成 Phase 4 回归通过，只能写“局部通过”。

#### P4-F2.2 资料上传与 index checklist

文档上传 / index 回归必须检查：

- 使用 `manifest.json` 的 `recommended_upload_order` 逐份上传 9 份合成脱敏 Markdown。
- 每份上传材料保留唯一锚点：`TEST-RAG-001` 到 `TEST-RAG-007`、`TEST-WIKI-001`、`TEST-DISTRACTOR-001`。
- 上传前再次确认材料不含真实公司、真实个人、真实客户、真实项目、内网地址、API Key、service token、真实政策编号。
- 每份资料至少记录文件名、标题、上传状态、索引状态、chunk 数量或等价 evidence 数量。
- `index` / `indexed` / `retrievable` 状态必须能区分“已上传但未入检索”和“已可用于 RAG / 知识问答”。
- 如果索引失败，记录失败阶段和可读错误，不把失败资料计入 RAG debug 命中率。
- 不提交上传产物、数据库、日志、`.env` 或真实运行输出。

#### P4-F2.3 RAG debug 命中 checklist

RAG debug 回归必须覆盖：

- 文档-only：P4Q-001 到 P4Q-016、P4Q-022 到 P4Q-024 至少按 `document` 范围跑一遍。
- Wiki-only：P4Q-017 到 P4Q-019 必须在 Wiki 发布并可检索后按 `wiki` 范围跑一遍。
- all-source：P4Q-010 到 P4Q-013、P4Q-016、P4Q-020 到 P4Q-024 必须按 `all` 范围跑一遍。
- 每题记录 query、top_k、filters、score threshold、实际命中锚点、rank、source_type、evidence_id。
- 非无答案问题必须检查 top_k 内是否命中至少一个期望锚点。
- 干扰排除题必须记录是否召回 `TEST-DISTRACTOR-001`，以及该召回是否被错误采用。
- 新旧版本冲突题必须确认新版 `TEST-RAG-002` 不被旧版 `TEST-RAG-001` 压过。
- RAG debug 失败时要先定位是上传 / index、filter、source_type、排序还是 citation 映射问题。

#### P4-F2.4 Wiki 发布 / retrieve checklist

Wiki 回归必须检查：

- 使用 `TEST-WIKI-001` 种子材料创建 Wiki 草稿，不使用真实 Wiki 内容。
- Wiki 页面从 draft 进入 published 后，必须继续检查 indexed / retrievable，不能只看发布成功。
- Wiki 发布后至少执行一次刷新索引或等价 reindex / status refresh。
- RAG debug 的 Wiki-only 检索必须能用 P4Q-017、P4Q-018、P4Q-019 命中 `TEST-WIKI-001`。
- Wiki evidence 必须带 `source_type=wiki_page`，并能区分原始文档 `source_type=document_chunk`。
- Wiki citation 至少能追溯到 wiki_page_id、标题、状态、更新时间或等价页面定位字段。
- 如果 Wiki published 但不可 retrieve，应记录为“已发布，暂不可检索”，不能计入 Wiki 闭环通过。

#### P4-F2.5 `knowledge_qa` 引用 checklist

正式知识问答 / `knowledge_qa` 回归必须检查：

- 默认问题入口保持简单，只暴露问题、可选资料范围、回答、引用和依据不足提示。
- 不在正式知识问答页暴露 RAG debug 的 top_k、threshold、hybrid weight、raw payload 等工程参数。
- P4Q-001 到 P4Q-019、P4Q-022 到 P4Q-024 的回答必须有可见引用。
- P4Q-013 必须同时允许 Wiki 与文档引用，且用户能看懂两类来源差异。
- P4Q-017 到 P4Q-019 必须使用 Wiki 引用，不把 Wiki evidence 伪装成文档引用。
- 引用卡片应展示中文标签：来源、类型、命中片段、相关度、引用编号或等价追溯信息。
- 如果 retrieval 命中但回答没有引用，应判为失败或至少阻断发布，不能只看回答文字正确。

#### P4-F2.6 无答案 / 拒答 checklist

无答案和资料不足问题必须检查：

- P4Q-020 必须提示资料库没有依据，不得编造真实监管部门每小时上报要求。
- P4Q-021 必须提示材料为合成脱敏文本或资料不足，不得编造真实客户名称。
- 如果无答案问题召回相似政策、案例或活动材料，最终回答仍应明确“依据不足”。
- 无答案回答不要求引用，但如果展示参考材料，必须明确“不能支持结论”。
- 不得把空引用解释成正常回答完成，不得用流畅措辞掩盖依据不足。

#### P4-F2.7 中文化页面 checklist

前端中文化回归必须覆盖：

- 首页：运行状态、Mock / Live / WeKnora 状态、导航入口使用中文主标签。
- 资料库：上传、处理中、已索引、失败、分块、事件等核心术语中文化。
- RAG 调试页：RAG debug 保留技术调试能力，但参数、证据结果、错误召回提示使用中文说明。
- Wiki 页：草稿、已发布、索引中、已索引可检索、同步失败、索引超时等状态中文化。
- 知识问答页：问题输入、回答、引用、依据不足、知识来源、运行进度等主文案中文化。
- mock / fallback / draft / not indexed 不能被包装成真实可用 evidence 或真实 WeKnora live 通过。
- 页面可以保留必要技术字段值，但用户第一眼看到的标签必须是中文。

#### P4-F2.8 最低全量回归集

一次完整 Phase 4 回归至少包含：

| 类别 | 问题 | 通过重点 |
| --- | --- | --- |
| 精确事实 | P4Q-001 到 P4Q-005 | 命中正确锚点，回答具体事实，不混用旧版 / 新版 |
| 条款定位 | P4Q-006 到 P4Q-009 | 命中条款材料，引用字段或规则完整 |
| 跨文档综合 | P4Q-010 到 P4Q-013 | 多来源引用完整，P4Q-013 覆盖 Wiki + 文档 |
| 案例复盘 | P4Q-014 到 P4Q-016 | 蓝湾 / 北辰不混淆 |
| Wiki 检索 | P4Q-017 到 P4Q-019 | Wiki 发布后可 retrieve，引用为 `wiki_page` |
| 无答案 | P4Q-020 到 P4Q-021 | 明确依据不足，不编造真实信息 |
| 干扰排除 | P4Q-022 到 P4Q-023 | 活动排期不被当成政策依据 |
| 新旧版本冲突 | P4Q-024 | 当前回答优先新版三个工作日，并说明旧版差异 |

#### P4-F2.9 阻断规则

出现以下任一情况，本次回归不能标为通过：

1. 文档上传或 index 未完成，却继续计算 RAG 命中通过率。
2. RAG debug 未命中期望锚点，但 `knowledge_qa` 仍给出确定结论。
3. Wiki 只完成发布，未证明可 retrieve。
4. `knowledge_qa` 回答缺少必需引用，或引用不能追溯到 evidence。
5. 无答案问题编造真实监管部门、真实客户、真实政策编号或真实外部事实。
6. 中文化页面把 mock / fallback / draft / not indexed 显示成真实可用。
7. 回归记录没有说明验收层级，导致 fixture / mock / live 结论混用。
8. 任何敏感文件、上传文件、数据库、日志或 `.env` 被加入待提交。

状态：[x]

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

规划输出：

#### P4-F3.1 收口定义

Phase 4 第一段可以收口，指的是以下边界已经在 spec、fixture 和验收规则层面稳定：

- 合成脱敏测试语料包已经可用于后续上传、索引、RAG debug、Wiki 发布和 `knowledge_qa` 回归。
- P4-A 到 P4-F 的任务表均已完成，且每个任务都有对应验证命令或具体产物。
- RAG / Wiki / `knowledge_qa` 的质量目标、引用要求、无答案拒答、干扰排除和版本冲突检查口径已经明确。
- 正式知识问答保持单工作流，不扩展复杂 Agent 编排。
- RAG debug 的工程参数和正式知识问答的低门槛体验已经分离。
- 首页、资料库、RAG 调试页、Wiki 页、知识问答页的中文化范围和风险文案已经明确。
- mock、fixture、本地 live、真实 WeKnora live 的验收层级已经分清，fixture / mock 不能冒充真实 live。

这个收口不等于真实 WeKnora live 全量验收已经完成；真实能力测试必须进入 P4-G，并按 P4-F1 和 P4-F2 的证据链逐阶段形成报告。

#### P4-F3.2 任务完成矩阵

| 分组 | 收口要求 | 当前结论 |
| --- | --- | --- |
| P4-A 测试语料 | 语料规范、问题集规范、安全规则、fixture 包完成 | 已完成；fixture 包位于 `backend/fixtures/phase4_rag_wiki_qa/` |
| P4-B RAG 基线 | RAG debug 参数、质量指标、文档 / Wiki 对照测试规划完成 | 已完成；后续实现必须按同一验收层级比较 |
| P4-C Wiki 闭环 | Wiki 创建、发布、索引、检索和 citation 追溯规则完成 | 已完成；published 不等于 retrievable 的风险已写明 |
| P4-D 知识问答 | `knowledge_qa` 默认检索策略、引用、拒答、中文结果展示规划完成 | 已完成；不扩展 `policy_analysis` / `case_review` |
| P4-E 中文化 | 首页、资料库、RAG 调试页、Wiki 页、知识问答页中文化规划完成 | 已完成；不把 mock / fallback 包装成真实可用 |
| P4-F 验收回归 | 验收分层、回归 checklist、阶段收口标准完成 | 已完成；后续真实执行进入 P4-G |

#### P4-F3.3 最小收口检查

执行阶段收口时，至少确认：

1. `PHASE4_SPEC.md` 中 P4-A 到 P4-F 所有任务状态为 `[x]`。
2. `.github/skills/phase4-rag-wiki-qa/SKILL.md` 存在，且仍要求每次只执行一个任务编号。
3. `backend/fixtures/phase4_rag_wiki_qa/manifest.json` 存在，且定义 9 份合成脱敏文档。
4. `backend/fixtures/phase4_rag_wiki_qa/questions.json` 存在，且定义 24 个问题。
5. `backend/fixtures/phase4_rag_wiki_qa/hit_matrix.md` 存在，且覆盖 P4Q-001 到 P4Q-024。
6. P4-F1 明确 fixture / mock / 本地 live / 真实 WeKnora live 的差异。
7. P4-F2 明确上传 / index、RAG debug、Wiki 发布 / retrieve、`knowledge_qa` 引用、无答案拒答、中文化页面回归 checklist。
8. 没有把真实资料、API Key、service token、上传文件、数据库或日志加入 git。
9. 最新 commit 只包含当前任务范围内的文件，不包含无关改动。

#### P4-F3.4 可进入下一阶段的条件

满足以下条件后，可以进入 Phase 4 下一段开发任务：

- 下一段任务必须从 P4-F2 checklist 中挑选具体产品行为或验证脚本，不再只停留在规划描述。
- 每个实现任务都要明确属于 RAG debug、Wiki、`knowledge_qa`、中文化或验收脚本中的哪一条链路。
- 正式知识问答页面继续保持低门槛，不引入复杂 Agent 工作流。
- 前端和 Agent 继续通过 PA backend / Adapter 使用知识能力，不直接调用 raw WeKnora API。
- 如果要声明真实 WeKnora live 通过，必须使用 `KNOWLEDGE_BACKEND=weknora_api`、`MOCK_MODE=false`，并记录 non-mock evidence。

#### P4-F3.5 阶段收口结论模板

后续收口报告建议使用：

| 字段 | 内容 |
| --- | --- |
| 阶段 | Phase 4 第一段：RAG / Wiki / 知识问答质量优化与前端中文化 |
| 状态 | 可收口 / 不可收口 / 部分收口 |
| 已完成 | P4-A 到 P4-F 任务状态 |
| 产物 | spec、skill、fixture、questions、hit matrix、回归 checklist |
| 验收层级 | fixture / mock / 本地 live / 真实 WeKnora live |
| 未覆盖 | 真实 live 未运行、产品代码未实现、脚本未自动化等限制 |
| 下一步 | 选择具体实现任务或真实 live 回归任务 |

本次 P4-F3 只定义收口标准并确认 spec 层面闭环，不运行真实测试、不启动服务、不修改产品代码。真实测试执行和优化建议从 P4-G 开始管理。

状态：[x]

### P4-G：真实测试执行与优化报告

P4-G 是 Phase 4 真实能力测试阶段。它不再只写 checklist，也不允许用 mock、fixture-only、静态检查或旧 smoke 冒充真实通过。

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P4-G1 | 真实测试环境与配置预检报告 | [x] |
| P4-G2 | 9 份合成语料真实上传、索引、可检索报告 | [x] |
| P4-G3 | RAG debug 24 问真实命中矩阵报告 | [x] |
| P4-G4 | Wiki 创建、发布、索引、检索、引用真实闭环报告 | [x] |
| P4-G5 | `knowledge_qa` 24 问真实回答、引用、拒答、干扰排除报告 | [x] |
| P4-G6 | 前端中文化与真实状态展示验收报告 | [ ] |
| P4-G7 | Phase 4 真实测试总结与优化建议报告 | [ ] |

#### P4-G0：真实测试统一定义

Phase 4 真实测试必须同时满足：

1. 使用合成脱敏语料包 `backend/fixtures/phase4_rag_wiki_qa/`，不使用真实敏感资料。
2. 使用真实 PA 后端和 PA `KnowledgeBackend Adapter`，前端和 Agent 不直接调用 raw WeKnora API。
3. 配置层明确为 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`。
4. RAG evidence 必须来自当前真实检索结果，不能来自 mock、fixture-only、keyword fallback、旧缓存或历史上传材料。
5. Wiki 测试必须证明 draft、publish、index / retrievable、retrieve、citation 全链路。
6. `knowledge_qa` 必须使用真实 evidence 生成回答和引用，不能把 mock citation 或 fallback evidence 当作真实通过。
7. 真实 WeKnora 不可用时，任务结论只能是阻塞或部分通过，并在报告中写明阻塞原因和改进建议。

fixture 静态检查仍然保留，但只作为真实测试前置安全检查，不算真实验收通过。

#### P4-G0.1 真实测试报告统一要求

每个 P4-G 任务必须产出对应报告文件；没有报告文件，不能把任务状态标为 `[x]`。

报告必须包含：

| 字段 | 要求 |
| --- | --- |
| 测试时间 | 使用明确日期和时间，避免只写“今天” |
| 测试环境 | 本地 / 远程、backend / frontend、WeKnora 连接状态 |
| 后端来源 | 必须记录 `weknora_api`；如不是则不能标为真实通过 |
| 配置摘要 | 记录 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`，不得记录 token |
| 测试范围 | fixture 文档、Wiki slug、P4Q 问题 ID、页面范围 |
| 测试结果 | 通过 / 部分通过 / 失败 / 阻塞 |
| 关键证据 | `source`、`source_type`、`evidence_id`、`chunk_id`、`wiki_page_id`、`trace_id` 等 |
| 风险判断 | 说明失败、误召回、缺引用、状态混淆或环境阻塞 |
| 改进建议 | 按 RAG、Wiki、QA、前端、配置 / 运维分类记录后续优化建议 |

报告禁止记录 API Key、service token、真实 endpoint、真实上传文件、数据库路径、日志原文或未脱敏输出。

#### P4-G0.2 报告文件映射

| 任务 | 报告文件 |
| --- | --- |
| P4-G1 | `docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md` |
| P4-G2 | `docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md` |
| P4-G3 | `docs/PHASE4_REAL_RAG_MATRIX_REPORT.md` |
| P4-G4 | `docs/PHASE4_REAL_WIKI_REPORT.md` |
| P4-G5 | `docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md` |
| P4-G6 | `docs/PHASE4_REAL_FRONTEND_REPORT.md` |
| P4-G7 | `docs/PHASE4_REAL_TEST_SUMMARY.md` |

#### P4-G1：真实测试环境与配置预检报告

目标：
确认真实测试环境具备运行条件，并记录不能运行真实能力时的阻塞原因。

范围：
只检查配置、服务可达性、后端来源、mock 状态和语料安全前置，不上传资料，不执行完整 RAG / Wiki / QA 回归。

输出：
`docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md`。

验收标准：
报告明确记录 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`、WeKnora 连接状态、PA backend 状态、前端构建或启动状态、fixture 安全检查结果；若任一真实能力不可用，报告必须给出阻塞原因和配置 / 运维改进建议。

验证方式：
`test -f docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md`；
`rg -n "MOCK_MODE=false|KNOWLEDGE_BACKEND=weknora_api|测试结果|改进建议|阻塞" docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md`。

状态：[x]

#### P4-G2：9 份合成语料真实上传、索引、可检索报告

目标：
使用真实 PA / WeKnora 能力上传 9 份合成脱敏 Markdown，确认每份资料完成上传、索引并进入可检索状态。

范围：
只使用 `manifest.json` 中的 9 份 fixture 文档；不提交上传产物、数据库、日志或真实运行输出。

输出：
`docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md`。

验收标准：
报告逐份记录文件名、测试锚点、上传状态、external document id 或等价脱敏定位字段、索引状态、chunk / evidence 数量或等价指标；失败项必须记录失败阶段和改进建议，不能计入通过。

验证方式：
`test -f docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md`；
`rg -n "TEST-RAG-001|TEST-RAG-007|TEST-WIKI-001|TEST-DISTRACTOR-001|indexed|retrievable|测试结果|改进建议" docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md`。

状态：[x]

#### P4-G3：RAG debug 24 问真实命中矩阵报告

目标：
使用真实 RAG debug / retrieve 能力运行 P4Q-001 到 P4Q-024，记录实际命中锚点、source_type、rank、trace 和通过情况。

范围：
覆盖 document-only、wiki-only、all-source；Wiki-only 问题只有在 P4-G4 的 Wiki 可检索条件满足后才能计入真实通过。

输出：
`docs/PHASE4_REAL_RAG_MATRIX_REPORT.md`。

验收标准：
报告覆盖 24 个问题，记录期望锚点、实际命中锚点、是否命中、是否误召回 `TEST-DISTRACTOR-001`、是否满足 source_type 要求、失败原因和 RAG 改进建议；不能只写总体通过。

验证方式：
`test -f docs/PHASE4_REAL_RAG_MATRIX_REPORT.md`；
`rg -n "P4Q-001|P4Q-024|source_type|evidence_id|trace_id|测试结果|改进建议" docs/PHASE4_REAL_RAG_MATRIX_REPORT.md`。

状态：[x]

#### P4-G4：Wiki 创建、发布、索引、检索、引用真实闭环报告

目标：
使用 `TEST-WIKI-001` 种子材料完成真实 Wiki 草稿、发布、索引 / 可检索、retrieve 和 citation 追溯闭环。

范围：
只使用合成脱敏 Wiki 种子材料；不得使用真实 Wiki 页面或真实内部知识库内容。

输出：
`docs/PHASE4_REAL_WIKI_REPORT.md`。

验收标准：
报告记录 Wiki slug、draft 状态、published 状态、indexed / retrievable 状态、Wiki-only 检索结果、`source_type=wiki_page` evidence、wiki_page_id 或等价定位字段、citation 展示结果；published 但不可 retrieve 必须记为失败或部分通过。

验证方式：
`test -f docs/PHASE4_REAL_WIKI_REPORT.md`；
`rg -n "TEST-WIKI-001|draft|published|retrievable|source_type=wiki_page|wiki_page_id|测试结果|改进建议" docs/PHASE4_REAL_WIKI_REPORT.md`。

状态：[x]

#### P4-G5：`knowledge_qa` 24 问真实回答、引用、拒答、干扰排除报告

目标：
使用真实 `knowledge_qa` 单工作流运行 P4Q-001 到 P4Q-024，验证回答、引用、拒答、干扰排除和新旧版本冲突处理。

范围：
只测试 `knowledge_qa`，不扩展 `policy_analysis`、`case_review` 或复杂 Agent 编排。

输出：
`docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md`。

验收标准：
报告逐题记录回答结论、引用数量、引用类型、是否满足必须引用文档 / Wiki、无答案题是否拒答、干扰材料是否被错误采用、新旧版本冲突是否优先新版；失败项必须写 QA / prompt / citation / retrieval 改进建议。

验证方式：
`test -f docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md`；
`rg -n "P4Q-001|P4Q-024|knowledge_qa|引用|依据不足|TEST-DISTRACTOR-001|新版|测试结果|改进建议" docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md`。

状态：[x]

#### P4-G6：前端中文化与真实状态展示验收报告

目标：
在真实或等价本地运行环境中检查首页、资料库、RAG 调试页、Wiki 页、知识问答页的中文化和真实状态展示。

范围：
只验收页面展示和交互状态；不借 P4-G6 修改 UI，不把 mock / fallback / draft / not indexed 文案包装成真实可用。

输出：
`docs/PHASE4_REAL_FRONTEND_REPORT.md`。

验收标准：
报告记录页面、检查点、截图或文字证据摘要、中文化结果、真实 / mock / fallback / indexed 状态是否区分清楚；发现英文术语、状态误导或引用显示不清时，写入前端改进建议。

验证方式：
`test -f docs/PHASE4_REAL_FRONTEND_REPORT.md`；
`rg -n "首页|资料库|RAG 调试|Wiki|知识问答|中文化|真实状态|测试结果|改进建议" docs/PHASE4_REAL_FRONTEND_REPORT.md`。

状态：[ ]

#### P4-G7：Phase 4 真实测试总结与优化建议报告

目标：
汇总 P4-G1 到 P4-G6 的真实测试结果，形成 Phase 4 后续优化路线。

范围：
只汇总报告和建议，不直接修改产品代码。

输出：
`docs/PHASE4_REAL_TEST_SUMMARY.md`。

验收标准：
报告明确哪些阶段通过、部分通过、失败或阻塞；按 RAG、Wiki、QA、前端、配置 / 运维分类列出改进建议；不能在 P4-G1 到 P4-G6 缺报告时声称 Phase 4 真实测试完成。

验证方式：
`test -f docs/PHASE4_REAL_TEST_SUMMARY.md`；
`rg -n "P4-G1|P4-G6|通过|部分通过|失败|阻塞|RAG|Wiki|QA|前端|配置|改进建议" docs/PHASE4_REAL_TEST_SUMMARY.md`。

状态：[ ]

## 5. 阶段验收标准

Phase 4 第一段规划最小验收：

1. `PHASE4_SPEC.md` 存在，且 P4-A 到 P4-F 任务表完整。
2. Phase 4 skill 存在，且要求每次只执行一个任务编号。
3. 测试语料规范覆盖 8-10 份合成脱敏文档和 20-25 个测试问题。
4. RAG 调试参数和正式知识问答体验边界清晰。
5. Wiki 闭环测试覆盖草稿、发布、索引、检索、知识问答引用。
6. `knowledge_qa` 是本阶段唯一重点 Agent 工作流。
7. 前端中文化范围覆盖首页、资料库、RAG 调试页、Wiki 页、知识问答页。
8. mock、fixture、本地 live、真实 WeKnora live 验收分层清晰。
9. 不包含真实资料、密钥、上传文件、数据库或日志。

Phase 4 真实能力验收必须额外满足：

1. P4-G1 到 P4-G7 均完成并有对应报告文件。
2. 真实测试使用 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`。
3. RAG / Wiki / `knowledge_qa` 证据来自当前真实 PA / WeKnora 链路。
4. 每份报告都包含测试结果、失败 / 风险点、诊断结论和改进建议。
5. 如真实 WeKnora 不可用，只能记录阻塞或部分通过，不能用 mock / fixture-only 替代通过。

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
docs: complete P4-G1 real env precheck report
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
