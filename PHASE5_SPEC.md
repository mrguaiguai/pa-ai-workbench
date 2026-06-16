# PA AI Workbench PHASE5_SPEC

> 版本：0.5
>
> 阶段名称：RAG / Wiki / knowledge_qa 质量修复与真实 PASS 门禁阶段
>
> 用途：作为第五阶段 AI 开发的长期事实源，驱动 `PHASE5_SPEC.md + phase5-rag-wiki-qa-optimization skill` 的逐任务开发。
>
> 第一阶段事实源：`DEV_SPEC.md`
>
> 第二阶段事实源：`PHASE2_SPEC.md`
>
> 第三阶段事实源：`PHASE3_SPEC.md`
>
> 第四阶段事实源：`PHASE4_SPEC.md`
>
> 第五阶段事实源：`PHASE5_SPEC.md`

## 0. 第五阶段设计总则

Phase 5 从 Phase 4 的真实测试结论出发，不重新扩展产品面，而是把 P4-G 暴露出的 PARTIAL / FAIL 项逐步修复到真实 PASS。

第五阶段主线：

```text
复用 Phase 4 合成脱敏语料与 24 问
-> 建立失败项映射与自动回归
-> 修复 RAG 当前语料隔离、范围过滤、排序和干扰抑制
-> 修复 Wiki 自然语言召回与 Wiki citation
-> 修复 knowledge_qa 的引用、拒答、干扰排除和版本冲突
-> 完成前端中文化与真实状态展示
-> 使用真实 PA / WeKnora live 门禁证明 24 问 PASS
```

必须坚持以下边界：

1. PA AI Workbench 仍是独立 PA 产品，不是 WeKnora 子产品或前端皮肤。
2. Phase 5 不新增真实资料，不重建测试语料，默认继续使用 `backend/fixtures/phase4_rag_wiki_qa/`。
3. Phase 5 不以 PARTIAL 报告收口；最终门禁必须是真实 PASS。
4. 最终真实 PASS 必须使用 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`。
5. mock、fixture-only、旧缓存、历史上传材料和本地 fallback 均不能冒充最终 PASS。
6. RAG / Wiki 能力必须继续通过 PA `KnowledgeBackend Adapter` 标准化。
7. 前端和 Agent 不直接调用 raw WeKnora API。
8. `knowledge_qa` 是本阶段唯一重点 Agent 工作流；`policy_analysis` 和 `case_review` 保持现状，除非单独任务化。
9. 正式知识问答界面只允许简单来源选择，不暴露 top_k、hybrid、rerank、threshold 等调试参数。
10. RAG 调试页可以保留高级参数，但调试参数不能泄漏到默认 QA 体验。
11. 所有真实报告必须记录证据字段和诊断结论，但不能记录密钥、私有地址、上传文件、数据库或日志原文。
12. 每次只执行一个 `P5-*` 任务编号；验证通过后才更新任务状态。
13. 每个任务完成后本地 commit，不 push，且只提交任务相关文件。

第五阶段一句话定义：

```text
第五阶段用 Phase 4 的同一组合成脱敏语料和 24 问作为唯一质量基准，把 RAG、Wiki、knowledge_qa 和前端状态从可诊断的部分通过修复到真实 WeKnora live 可重复 PASS。
```

## 1. 阶段目标与成功标准

### 1.1 完整阶段目标

Phase 5 完成后，应能做到：

1. Phase 4 的 24 个问题在真实 RAG debug 矩阵中全部 PASS。
2. Phase 4 的 24 个问题在真实 `knowledge_qa` 中全部 PASS。
3. P4Q-017、P4Q-018、P4Q-019 能通过自然语言问题命中 published Wiki evidence。
4. `source_type=document_chunk`、`source_type=wiki_page` 和 all-source 范围过滤稳定可复核。
5. 当前验收语料可与历史 live 数据隔离，避免旧上传材料污染 QA 结果。
6. `TEST-DISTRACTOR-001` 被纳入固定回归哨兵；政策问题不得错误引用活动排期材料。
7. P4Q-024 能同时说明旧版和新版差异，并明确优先新版规则。
8. 无答案问题能明确拒答，不能把检索上下文伪装成支持证据。
9. 前端核心页面完成中文化，并清楚展示真实 / mock / fallback / partial / unavailable / indexed / retrievable 状态。
10. 最终输出 `docs/PHASE5_REAL_PASS_REPORT.md`，结论为 PASS。

### 1.2 非目标

Phase 5 不做：

- 新语料体系重建。
- 接入真实敏感资料。
- Word / PPT 导出。
- 复杂多 Agent 编排。
- Agent Supervisor。
- 权限、审批、IM 集成。
- 知识图谱。
- 长期记忆。
- WeKnora 后端重写。
- 前端大改版或视觉重构。

## 2. 基准与证据来源

### 2.1 固定语料

Phase 5 固定复用：

```text
backend/fixtures/phase4_rag_wiki_qa/manifest.json
backend/fixtures/phase4_rag_wiki_qa/questions.json
backend/fixtures/phase4_rag_wiki_qa/hit_matrix.md
backend/fixtures/phase4_rag_wiki_qa/documents/
```

该语料包包含：

- 9 份合成脱敏 Markdown 文档。
- 24 个测试问题。
- 文档、Wiki、无答案、干扰排除和版本冲突场景。
- 唯一锚点：`TEST-RAG-*`、`TEST-WIKI-*`、`TEST-DISTRACTOR-*`。

不得在 Phase 5 中加入真实公司、真实个人、真实客户、真实项目、真实内网地址、真实政策编号、密钥、上传产物、数据库或日志。

### 2.2 Phase 4 问题来源

Phase 5 的优化项来自：

```text
docs/PHASE4_REAL_TEST_SUMMARY.md
docs/PHASE4_REAL_RAG_MATRIX_REPORT.md
docs/PHASE4_REAL_WIKI_REPORT.md
docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md
docs/PHASE4_REAL_FRONTEND_REPORT.md
```

当前已知重点失败或部分通过项：

| 问题 | Phase 5 修复方向 |
| --- | --- |
| 历史 live 数据污染 | 当前语料 / current-run 隔离 |
| Wiki 自然语言召回失败 | P4Q-017 到 P4Q-019 必须命中 `wiki_page` |
| QA 严格 24 问无 full PASS | `knowledge_qa` 检索、引用、拒答、回答策略修复 |
| 干扰材料误召回 | `TEST-DISTRACTOR-001` 回归哨兵 |
| 新旧版本冲突不稳定 | P4Q-024 新版优先逻辑 |
| 前端英文残留 | 核心页面中文化 |
| runtime 状态不一致 | 状态语义统一与报告 |

### 2.3 验收分层

Phase 5 继续区分四类证据：

| 层级 | 用途 | 是否可作为最终 PASS |
| --- | --- | --- |
| fixture contract | 校验语料和问题集格式 | 否 |
| offline smoke | 校验本地代码契约和确定性逻辑 | 否 |
| local live | 校验本地 PA 后端、前端和 Adapter 运行 | 否 |
| real WeKnora live | 最终门禁 | 是 |

fixture 或 offline 通过只能说明代码契约安全，不能说明真实能力已通过。

## 3. 接口与体验原则

### 3.1 `retrieval_scope` 最小接口意图

Phase 5 推荐为正式知识问答增加简单来源意图：

```text
retrieval_scope?: "all" | "document" | "wiki"
```

语义：

| 值 | 含义 | 后端映射 |
| --- | --- | --- |
| `all` | 文档与 Wiki 都可检索 | 不强制 source_type |
| `document` | 仅使用文档 chunk | `source_type=document_chunk` |
| `wiki` | 仅使用 Wiki page | `source_type=wiki_page` |

约束：

1. `retrieval_scope` 是面向普通用户的简单来源选择，不是调试参数。
2. 正式 QA 页面不能暴露 top_k、hybrid、rerank、threshold 等工程参数。
3. RAG debug 页仍可保留高级参数，用于定位和验收。
4. 默认值为 `all`，除非任务、问题集或用户明确选择 document / wiki。
5. `retrieval_scope` 必须进入 AgentRequest、analysis API、history 输入记录和报告证据。

### 3.2 当前语料隔离原则

Phase 5 可以通过 document ids、external doc ids、knowledge ids、metadata namespace 或等价 PA 层策略隔离当前验收语料。

要求：

1. 隔离逻辑必须在 PA 层可解释，不能依赖人工记忆历史上传编号。
2. `knowledge_qa` 默认体验仍保持简单。
3. 验收脚本可以显式传入当前 run 的文档范围。
4. 若 WeKnora 不支持某个过滤字段，PA 层必须在返回后做二次过滤并记录 warning。
5. 过滤失败不能被标为 PASS。

## 4. 任务总览

状态说明：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
```

### P5-A：阶段治理与基线转换

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-A1 | 创建 Phase 5 spec 与执行 skill | [x] |
| P5-A2 | 将 P4-G7 问题清单转成 Phase 5 失败映射表 | [x] |
| P5-A3 | 增加 Phase 4 fixture / 24 问契约检查脚本 | [x] |

### P5-B：RAG 检索隔离与质量修复

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-B1 | 设计并实现当前验收语料隔离策略 | [x] |
| P5-B2 | 稳定 document / wiki / all source 范围过滤 | [x] |
| P5-B3 | 优化 answer-bearing chunk 排名与 debug 诊断 | [x] |
| P5-B4 | 固化 `TEST-DISTRACTOR-001` 干扰材料回归哨兵 | [x] |
| P5-B5 | 真实 RAG 24 问矩阵达到 PASS | [x] |

### P5-C：Wiki 自然语言召回修复

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-C1 | 完善 published Wiki 索引字段覆盖 | [x] |
| P5-C2 | 修复 P4Q-017 到 P4Q-019 Wiki-only 自然语言召回 | [x] |
| P5-C3 | 稳定 Wiki evidence 与 citation traceability | [x] |
| P5-C4 | 真实 Wiki 闭环复测达到 PASS | [x] |

### P5-D：`knowledge_qa` 24 问质量修复

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-D1 | 增加 `retrieval_scope` 最小接口链路 | [x] |
| P5-D2 | 让 `knowledge_qa` 支持当前语料范围与 source_type 策略 | [x] |
| P5-D3 | 修复无答案拒答与引用支撑规则 | [x] |
| P5-D4 | 修复干扰排除与新旧版本冲突回答策略 | [x] |
| P5-D5 | 真实 `knowledge_qa` 24 问达到 PASS | [x] |

### P5-E：前端中文化与真实状态展示

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-E1 | 修复核心页面残留英文术语 | [x] |
| P5-E2 | 在知识问答页加入简单知识来源选择 | [x] |
| P5-E3 | 统一真实 / mock / fallback / partial / unavailable 状态展示 | [x] |
| P5-E4 | 前端构建与浏览器验收达到 PASS | [x] |

### P5-F：自动回归与真实报告

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-F1 | 增加真实 RAG 24 问矩阵脚本 | [x] |
| P5-F2 | 增加真实 `knowledge_qa` 24 问脚本 | [x] |
| P5-F3 | 增加 Phase 5 报告敏感信息与证据字段检查 | [x] |
| P5-F4 | 增加 Phase 5 本地真实测试运行说明 | [x] |

### P5-G：最终真实 PASS 门禁

| 任务 | 名称 | 状态 |
| --- | --- | --- |
| P5-G1 | 真实环境与配置 PASS 预检 | [x] |
| P5-G2 | fresh / current-run 上传 P4 语料并确认可检索 | [x] |
| P5-G3 | RAG debug 24 问真实 PASS 报告 | [x] |
| P5-G4 | Wiki 创建、发布、索引、检索、引用真实 PASS 报告 | [ ] |
| P5-G5 | `knowledge_qa` 24 问真实 PASS 报告 | [ ] |
| P5-G6 | 前端中文化与真实状态浏览器 PASS 报告 | [ ] |
| P5-G7 | Phase 5 最终真实 PASS 总结报告 | [ ] |

## 5. 任务详情

### P5-A1：创建 Phase 5 spec 与执行 skill

目标：
创建第五阶段事实源和执行 skill。

范围：
只新增 `PHASE5_SPEC.md` 和 `.github/skills/phase5-rag-wiki-qa-optimization/SKILL.md`；不修改产品代码，不修改 Phase 4 状态。

输出：

```text
PHASE5_SPEC.md
.github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
```

验收标准：
Phase 5 spec 明确 24 问真实 PASS 目标、P5-A 到 P5-G 任务表、真实 PASS 门禁、单任务执行协议；skill 明确以 `PHASE5_SPEC.md` 为事实源，每次只执行一个任务编号并自动本地 commit。

验证方式：

```bash
test -f PHASE5_SPEC.md
test -f .github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
rg -n "P5-A|P5-B|P5-C|P5-D|P5-E|P5-F|P5-G|24 问|真实 PASS|PHASE5_REAL" PHASE5_SPEC.md
rg -n "PHASE5_SPEC|每次只执行一个任务编号|真实 WeKnora|commit|不要 push" .github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
```

状态：[x]

### P5-A2：将 P4-G7 问题清单转成 Phase 5 失败映射表

目标：
把 Phase 4 真实测试总结中的风险和失败项转成 Phase 5 可跟踪修复矩阵。

范围：
只整理文档，不改产品代码。

输出：
`docs/PHASE5_P4G_FAILURE_MAP.md`。

验收标准：
报告至少包含 P4-G1 到 P4-G6 结果、P4Q-017 到 P4Q-019、P4Q-022、P4Q-024、前端英文残留、runtime 状态不一致、对应 P5 任务编号和复测方式。

验证方式：
`test -f docs/PHASE5_P4G_FAILURE_MAP.md`；
`rg -n "P4Q-017|P4Q-019|P4Q-022|P4Q-024|P5-B|P5-C|P5-D|P5-E|复测" docs/PHASE5_P4G_FAILURE_MAP.md`。

状态：[x]

### P5-A3：增加 Phase 4 fixture / 24 问契约检查脚本

目标：
让 Phase 5 每次开发前都能确认固定语料和 24 问没有漂移。

范围：
只增加 fixture contract 检查，不执行真实 WeKnora。

输出：
`backend/scripts/check_phase5_fixture_contract.py`。

验收标准：
脚本校验 manifest、questions、hit matrix 的 corpus id、问题数量、锚点存在性、expected source types、forbidden anchors、Wiki-only 问题、无答案问题和敏感信息扫描；脚本必须明确输出 fixture contract 不是真实 PASS。

验证方式：
`backend/.venv/bin/python backend/scripts/check_phase5_fixture_contract.py`。

状态：[x]

### P5-B1：设计并实现当前验收语料隔离策略

目标：
避免 Phase 4 报告中发现的历史 live 数据污染，让真实验收能锁定 fresh / current-run 语料。

范围：
允许修改 PA 后端和测试脚本；不改 WeKnora 后端。

验收标准：
系统能记录本轮上传的 fixture 文档定位字段，并在 RAG / QA 验收中仅使用这些文档或等价 current-run namespace；如果后端过滤能力不足，PA 层必须二次过滤并输出 warning。

验证方式：
运行新增或相关 smoke，证明当前 run 范围之外的历史材料不会进入 Phase 5 验收结果。

状态：[x]

### P5-B2：稳定 document / wiki / all source 范围过滤

目标：
让 `document`、`wiki`、`all` 三种范围在 RAG API、RAG debug、Agent 检索中语义一致。

范围：
可以修改 RAG schema、service、retriever tool 和相关测试；不把调试参数暴露到正式 QA 页面。

验收标准：
`document` 只返回 `document_chunk`，`wiki` 只返回 `wiki_page`，`all` 可混合返回；不符合范围的 evidence 必须被过滤或明确 warning。

验证方式：
focused backend smoke 覆盖三种 source 范围和空结果场景。

状态：[x]

### P5-B3：优化 answer-bearing chunk 排名与 debug 诊断

目标：
提升精确事实题和条款定位题的 answer-bearing chunk 排名，而不是只命中包含锚点的宽泛 chunk。

范围：
允许改 PA 检索后处理、normalize、debug metadata 和报告字段；不重写 WeKnora 检索服务。

验收标准：
P4Q-001 到 P4Q-012 的 expected anchors 在合理 rank 范围内，并且 debug 输出能说明 rank、score semantics、matched metadata 或等价诊断字段。

验证方式：
RAG debug smoke 和真实 RAG 矩阵报告记录 rank、score、source_type、trace_id。

状态：[x]

### P5-B4：固化 `TEST-DISTRACTOR-001` 干扰材料回归哨兵

目标：
让干扰材料成为长期回归检查，防止政策问题错误引用活动排期材料。

范围：
可增加检索后过滤、评分降级或 QA 证据策略；不得简单删除干扰材料。

验收标准：
P4Q-022 不得引用 `TEST-DISTRACTOR-001`；P4Q-023 仍能命中该材料并说明它不能作为政策依据。

验证方式：
fixture smoke 和真实 RAG / QA 脚本分别覆盖 P4Q-022、P4Q-023。

状态：[x]

### P5-B5：真实 RAG 24 问矩阵达到 PASS

目标：
真实运行 P4Q-001 到 P4Q-024 的 RAG debug 矩阵，并全部 PASS。

范围：
只记录真实 RAG evidence，不生成最终 QA 回答。

输出：
`docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md`。

验收标准：
24 问全部 PASS；报告记录 expected anchors、actual anchors、source_type、rank、trace_id、evidence_id、chunk_id、wiki_page_id、是否误召回干扰材料。

验证方式：
`test -f docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md`；
`rg -n "P4Q-001|P4Q-024|PASS|source_type|trace_id|TEST-DISTRACTOR-001|PHASE5_REAL" docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md`。

状态：[x]

### P5-C1：完善 published Wiki 索引字段覆盖

目标：
确保 published Wiki 的 title、summary、content、source_refs、metadata 等字段进入可检索内容。

范围：
可修改 Wiki service、sync payload、index text 构造和测试。

验收标准：
发布后的 Wiki 页面能通过标题、摘要、正文、关联材料和常见误区等自然语言线索检索。

验证方式：
Wiki smoke 覆盖 publish、index / retrievable、search、read、retrieve。

状态：[x]

### P5-C2：修复 P4Q-017 到 P4Q-019 Wiki-only 自然语言召回

目标：
让三个官方 Wiki-only 问题真实命中 `TEST-WIKI-001` 对应 published Wiki evidence。

范围：
只修 Wiki retrieval，不把文档 chunk 伪装成 Wiki evidence。

验收标准：
P4Q-017、P4Q-018、P4Q-019 均返回 `source=weknora_api`、`source_type=wiki_page`、`wiki_page_id` 或等价定位字段。

验证方式：
真实 Wiki-only 检索脚本或报告覆盖三个问题。

状态：[x]

### P5-C3：稳定 Wiki evidence 与 citation traceability

目标：
确保 Wiki citation 能定位到 Wiki 页面，而不是只显示普通文档来源。

范围：
可修改 citation builder、locator、Wiki page read/search 映射和前端展示。

验收标准：
Wiki citation 包含 `evidence_id`、`source_type=wiki_page`、`wiki_page_id`，前端可定位到 Wiki 页面。

验证方式：
后端 citation smoke 和前端引用定位检查。

状态：[x]

### P5-C4：真实 Wiki 闭环复测达到 PASS

目标：
重新执行 Wiki 创建、发布、索引、检索、引用闭环，并达到 PASS。

输出：
`docs/PHASE5_REAL_WIKI_PASS_REPORT.md`。

验收标准：
报告覆盖 draft、published、indexed / retrievable、Wiki-only retrieve、citation locate 和 P4Q-017 到 P4Q-019 PASS。

验证方式：
`test -f docs/PHASE5_REAL_WIKI_PASS_REPORT.md`；
`rg -n "P4Q-017|P4Q-019|source_type=wiki_page|wiki_page_id|PASS|PHASE5_REAL" docs/PHASE5_REAL_WIKI_PASS_REPORT.md`。

状态：[x]

### P5-D1：增加 `retrieval_scope` 最小接口链路

目标：
为正式 `knowledge_qa` 增加简单来源选择。

范围：
允许修改 API schema、frontend API type、AgentRequest、analysis service 和持久化输入记录；不暴露高级 debug 参数。

验收标准：
`retrieval_scope` 支持 `all`、`document`、`wiki`；默认 `all`；非法值被拒绝；请求进入 `knowledge_qa` workflow 并写入 task input。

验证方式：
后端 schema / analysis smoke 覆盖默认值和三种合法值。

状态：[x]

### P5-D2：让 `knowledge_qa` 支持当前语料范围与 source_type 策略

目标：
让 `knowledge_qa` 在真实验收时只使用当前语料，并按 retrieval_scope 选择证据类型。

范围：
可修改 `KnowledgeQaWorkflow`、retriever filters、evidence policy 和测试脚本。

验收标准：
document-only、wiki-only 和 all-source 问题的 citations 与问题集 expected source types 一致；范围不匹配 evidence 不得进入最终引用。

验证方式：
fixture smoke 与真实 QA 脚本覆盖 P4Q-001、P4Q-013、P4Q-017、P4Q-019。

状态：[x]

### P5-D3：修复无答案拒答与引用支撑规则

目标：
让无答案题明确拒答，并避免把 searched context 当作支持证据。

范围：
可修改 prompt、grounded markdown、citation policy、faithfulness checker 或报告脚本。

验收标准：
P4Q-020、P4Q-021 输出依据不足，不编造真实监管要求或真实客户名称；引用只用于说明检索过的材料不足，不能包装成支持结论。

验证方式：
QA fixture smoke 和真实 QA 报告覆盖两个无答案问题。

状态：[x]

### P5-D4：修复干扰排除与新旧版本冲突回答策略

目标：
修复 P4Q-022 和 P4Q-024 的信任关键问题。

范围：
可修改 prompt、evidence policy、retrieval post-process 或答案模板。

验收标准：
P4Q-022 引用新版政策，不引用活动排期作为政策依据；P4Q-024 同时引用旧版和新版，并明确现在优先新版三个工作日规则。

验证方式：
QA fixture smoke 和真实 QA 报告覆盖 P4Q-022、P4Q-024。

状态：[x]

### P5-D5：真实 `knowledge_qa` 24 问达到 PASS

目标：
真实运行 P4Q-001 到 P4Q-024 的 `knowledge_qa`，并全部 PASS。

输出：
`docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md`。

验收标准：
24 问全部 PASS；报告逐题记录回答要点、引用数量、source_type、evidence_id、chunk_id、wiki_page_id、拒答判断、干扰排除和版本冲突判断。

验证方式：
`test -f docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md`；
`rg -n "P4Q-001|P4Q-024|knowledge_qa|PASS|依据不足|TEST-DISTRACTOR-001|新版|PHASE5_REAL" docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md`。

状态：[x]

### P5-E1：修复核心页面残留英文术语

目标：
完成 Phase 4 报告中发现的前端中文化缺口。

范围：
覆盖首页、资料库、RAG 调试页、Wiki 页、知识问答页、历史页。

验收标准：
用户可见文案中不再出现 Phase 4 报告列出的英文残留；保留代码字段、debug raw metadata 或开发者专用字段时必须只出现在调试区域。

验证方式：
`rg` 扫描残留英文关键词，并运行 frontend build。

状态：[x]

### P5-E2：在知识问答页加入简单知识来源选择

目标：
让普通用户能选择全部知识、仅文档、仅 Wiki，而不接触高级 RAG 参数。

范围：
只改知识问答页面和 API payload 绑定。

验收标准：
页面显示中文来源选项；选择值进入 `retrieval_scope`；默认全部知识。

验证方式：
frontend build；浏览器检查 payload 或后端记录。

状态：[x]

### P5-E3：统一真实 / mock / fallback / partial / unavailable 状态展示

目标：
修复 runtime 状态不一致导致的前端信任问题。

范围：
可修改状态服务、前端状态卡片和文案；不隐藏真实不可用状态。

验收标准：
页面明确区分真实可用、mock、fallback、部分可用、不可用、索引中、可检索；不能把 partial 包装成 ready。

验证方式：
后端状态 smoke、frontend build、浏览器文字证据。

状态：[x]

### P5-E4：前端构建与浏览器验收达到 PASS

目标：
用真实或等价本地环境验收核心页面中文化和状态展示。

输出：
`docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md`。

验收标准：
首页、资料库、RAG 调试、Wiki、知识问答、历史页均有文字证据或截图摘要；无阻塞英文残留；状态展示真实。

验证方式：
`test -f docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md`；
`rg -n "首页|资料库|RAG 调试|Wiki|知识问答|历史|PASS|PHASE5_REAL" docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md`。

状态：[x]

### P5-F1：增加真实 RAG 24 问矩阵脚本

目标：
把 RAG 24 问真实执行从人工操作转成可重复脚本。

范围：
脚本可调用 PA 后端或内部 service，但必须走 PA Adapter，不直接绕到 raw WeKnora。

验收标准：
脚本读取 `questions.json`，按 retrieval_scope 和 expected source types 执行，输出逐题结果；非 PASS 返回非零退出码。

验证方式：
运行脚本的 dry / fixture-safe 模式和真实模式说明。

状态：[x]

### P5-F2：增加真实 `knowledge_qa` 24 问脚本

目标：
把 QA 24 问真实执行转成可重复脚本。

范围：
脚本必须走 `run_analysis()` 或等价 PA workflow，不直接调用模型或 WeKnora。

验收标准：
脚本逐题检查答案要点、引用类型、拒答、干扰排除、版本冲突；非 PASS 返回非零退出码。

验证方式：
运行脚本的 dry / fixture-safe 模式和真实模式说明。

状态：[x]

### P5-F3：增加 Phase 5 报告敏感信息与证据字段检查

目标：
避免真实报告提交敏感内容，同时确保报告包含足够证据字段。

范围：
增加 checker，不改产品逻辑。

验收标准：
checker 扫描 Phase 5 报告中的密钥、私有地址、上传目录、数据库、日志原文风险；同时检查 PASS 报告必须包含 source、source_type、evidence_id、chunk_id、wiki_page_id、trace_id 等适用字段。

验证方式：
运行 checker 覆盖已存在或 fixture 生成的报告样例。

状态：[x]

### P5-F4：增加 Phase 5 本地真实测试运行说明

目标：
让后续 agent 或开发者能重复启动后端、前端和真实测试脚本。

输出：
`docs/PHASE5_REAL_TEST_RUNBOOK.md`。

验收标准：
说明包含后端、前端、fixture 上传、Wiki 发布、RAG 24 问、QA 24 问、前端浏览器验收、报告检查和禁止提交项；不记录任何密钥或真实地址。

验证方式：
`test -f docs/PHASE5_REAL_TEST_RUNBOOK.md`；
`rg -n "后端|前端|24 问|Wiki|RAG|knowledge_qa|报告|禁止提交" docs/PHASE5_REAL_TEST_RUNBOOK.md`。

状态：[x]

### P5-G1：真实环境与配置 PASS 预检

目标：
确认最终门禁环境具备真实 PASS 条件。

输出：
`docs/PHASE5_REAL_ENV_PASS_REPORT.md`。

验收标准：
报告明确 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`、PA backend、frontend、WeKnora connection、model gateway 和 embedding provider 均满足真实测试；任一关键项失败则任务不能标 `[x]`。

验证方式：
`test -f docs/PHASE5_REAL_ENV_PASS_REPORT.md`；
`rg -n "MOCK_MODE=false|KNOWLEDGE_BACKEND=weknora_api|PASS|PHASE5_REAL" docs/PHASE5_REAL_ENV_PASS_REPORT.md`。

状态：[x]

### P5-G2：fresh / current-run 上传 P4 语料并确认可检索

目标：
在最终门禁中上传或确认当前 run 的 9 份 P4 fixture 文档，并隔离历史材料。

输出：
`docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md`。

验收标准：
9 份文档全部 indexed / retrievable；报告记录每份文档的锚点、脱敏定位字段、source、source_type、检索证据和 current-run 范围。

验证方式：
`test -f docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md`；
`rg -n "TEST-RAG-001|TEST-RAG-007|TEST-WIKI-001|TEST-DISTRACTOR-001|PASS|current-run|PHASE5_REAL" docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md`。

状态：[x]

### P5-G3：RAG debug 24 问真实 PASS 报告

目标：
最终门禁中证明 RAG 24 问全部 PASS。

输出：
`docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md`。

验收标准：
同 P5-B5；任何 PARTIAL、FAIL、BLOCKED 都不能标 `[x]`。

验证方式：
同 P5-B5。

状态：[x]

### P5-G4：Wiki 创建、发布、索引、检索、引用真实 PASS 报告

目标：
最终门禁中证明 Wiki 闭环和 Wiki-only 问题全部 PASS。

输出：
`docs/PHASE5_REAL_WIKI_PASS_REPORT.md`。

验收标准：
同 P5-C4；任何 PARTIAL、FAIL、BLOCKED 都不能标 `[x]`。

验证方式：
同 P5-C4。

状态：[ ]

### P5-G5：`knowledge_qa` 24 问真实 PASS 报告

目标：
最终门禁中证明 `knowledge_qa` 24 问全部 PASS。

输出：
`docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md`。

验收标准：
同 P5-D5；任何 PARTIAL、FAIL、BLOCKED 都不能标 `[x]`。

验证方式：
同 P5-D5。

状态：[ ]

### P5-G6：前端中文化与真实状态浏览器 PASS 报告

目标：
最终门禁中证明核心页面中文化和状态展示全部 PASS。

输出：
`docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md`。

验收标准：
同 P5-E4；任何阻塞英文残留、状态误导或浏览器不可验收都不能标 `[x]`。

验证方式：
同 P5-E4。

状态：[ ]

### P5-G7：Phase 5 最终真实 PASS 总结报告

目标：
汇总 P5-G1 到 P5-G6，形成 Phase 5 最终真实 PASS 结论。

输出：
`docs/PHASE5_REAL_PASS_REPORT.md`。

验收标准：
只有在 P5-G1 到 P5-G6 均为 PASS 且报告存在时，才能创建 PASS 总结并标 `[x]`；报告必须明确 24 问 RAG PASS、24 问 `knowledge_qa` PASS、Wiki PASS、前端 PASS 和配置 PASS。若任一前置项不是 PASS，只能写阻塞草稿，不能标 `[x]`。

验证方式：
`test -f docs/PHASE5_REAL_PASS_REPORT.md`；
`rg -n "P5-G1|P5-G6|24 问|RAG|Wiki|knowledge_qa|前端|真实 PASS|PHASE5_REAL" docs/PHASE5_REAL_PASS_REPORT.md`。

状态：[ ]

## 6. 阶段验收标准

Phase 5 最小规划验收：

1. `PHASE5_SPEC.md` 存在。
2. `.github/skills/phase5-rag-wiki-qa-optimization/SKILL.md` 存在。
3. P5-A 到 P5-G 任务表完整。
4. 已验证完成的任务状态为 `[x]`，未执行的开发任务保持 `[ ]`。
5. spec 明确复用 Phase 4 语料和 24 问。
6. spec 明确最终真实 PASS 门禁，且不能用 PARTIAL 报告收口。

Phase 5 最终验收：

1. P5-G1 到 P5-G7 均为 `[x]`。
2. 所有 P5-G 报告结论均为 PASS。
3. 真实测试使用 `MOCK_MODE=false`、`KNOWLEDGE_BACKEND=weknora_api`。
4. RAG 24 问全部 PASS。
5. `knowledge_qa` 24 问全部 PASS。
6. Wiki-only 问题 P4Q-017 到 P4Q-019 全部 PASS。
7. 干扰排除问题 P4Q-022、P4Q-023 全部 PASS。
8. 版本冲突问题 P4Q-024 PASS。
9. 前端中文化与真实状态展示 PASS。
10. 报告不包含真实资料、密钥、上传文件、数据库、日志或未脱敏输出。

## 7. 任务执行协议

AI 开发工具每次只执行一个任务编号。

默认执行流程：

```text
读取 PHASE5_SPEC.md
-> 读取 .github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
-> 运行 git status --short 和 git log --oneline -3
-> 定位一个未完成任务编号
-> 开始前说明任务编号、计划修改文件、验证方式
-> 实现或编写对应文档
-> 运行验收
-> 验收通过后更新 PHASE5_SPEC.md 任务状态
-> 运行 git safety checks
-> 本地 commit
-> 汇报结果，不 push
```

选任务规则：

1. 如果用户指定任务编号，执行该任务编号。
2. 如果用户只说“继续”，选择编号最靠前且未完成的任务。
3. 不跳过 P5-A；P5-A 全部完成后再进入 P5-B。
4. P5-G 只有在 P5-A 到 P5-F 完成后执行。
5. 一次只完成一个任务编号，不跨任务顺手修复。

提交规则：

1. 只提交当前任务相关文件。
2. 不提交 `.env`、上传文件、数据库、日志、构建产物、依赖目录、缓存目录。
3. 不 push，除非用户明确要求。
4. 如果发现无关 dirty changes，保持不动并在回复中说明。
5. 如果发现敏感文件将被提交，停止并报告。
