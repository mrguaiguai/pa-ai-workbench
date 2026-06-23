# Phase 4 RAG / Wiki / QA 期望命中矩阵

本矩阵对应 `questions.json`。所有材料均为合成脱敏测试文本，不包含真实机构、真实个人、真实客户、真实政策编号、密钥或 token。

| 问题 ID | 类型 | 期望命中锚点 | 推荐范围 | 必须文档引用 | 必须 Wiki 引用 | 应提示依据不足 | 主要检查点 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-001 | 精确事实 | TEST-RAG-001 | document | 是 | 否 | 否 | 旧版普通事项五个工作日，不误用新版 |
| P4Q-002 | 精确事实 | TEST-RAG-002 | document | 是 | 否 | 否 | 新版三个工作日初稿、第四个工作日前复核 |
| P4Q-003 | 精确事实 | TEST-RAG-003 | document | 是 | 否 | 否 | 九十日与一百八十日 |
| P4Q-004 | 精确事实 | TEST-RAG-005 | document | 是 | 否 | 否 | 蓝湾最终稿晚两个工作日 |
| P4Q-005 | 精确事实 | TEST-RAG-007 | document | 是 | 否 | 否 | 上传前检查三件事 |
| P4Q-006 | 条款定位 | TEST-RAG-003 | document | 是 | 否 | 否 | 访问审计字段 |
| P4Q-007 | 条款定位 | TEST-RAG-004 | document | 是 | 否 | 否 | 引用校验事项 |
| P4Q-008 | 条款定位 | TEST-RAG-004 | document | 是 | 否 | 否 | 两个工作日内撤回说明 |
| P4Q-009 | 条款定位 | TEST-RAG-003 | document | 是 | 否 | 否 | 删除前检查命中矩阵 |
| P4Q-010 | 跨文档综合 | TEST-RAG-001, TEST-RAG-002 | all | 是 | 否 | 否 | 旧版/新版时限和附件规则差异 |
| P4Q-011 | 跨文档综合 | TEST-RAG-003, TEST-RAG-004 | all | 是 | 否 | 否 | 访问审计 vs 发布校验 |
| P4Q-012 | 跨文档综合 | TEST-RAG-005, TEST-RAG-002 | all | 是 | 否 | 否 | 蓝湾问题与事项卡片规则 |
| P4Q-013 | 跨文档综合 | TEST-WIKI-001, TEST-RAG-003, TEST-RAG-004 | all | 是 | 是 | 否 | Wiki 与文档混合引用 |
| P4Q-014 | 案例复盘 | TEST-RAG-005 | document | 是 | 否 | 否 | 蓝湾延迟三项因素 |
| P4Q-015 | 案例复盘 | TEST-RAG-006 | document | 是 | 否 | 否 | 北辰错误原因和处置动作 |
| P4Q-016 | 案例复盘 | TEST-RAG-005, TEST-RAG-006 | all | 是 | 否 | 否 | 延迟响应 vs 信息更正 |
| P4Q-017 | Wiki 检索 | TEST-WIKI-001 | wiki | 否 | 是 | 否 | Wiki 专题关联的政策、法规、案例 |
| P4Q-018 | Wiki 检索 | TEST-WIKI-001 | wiki | 否 | 是 | 否 | Wiki 常见误区 |
| P4Q-019 | Wiki 检索 | TEST-WIKI-001 | wiki | 否 | 是 | 否 | `source_type=wiki_page` |
| P4Q-020 | 无答案 | 无 | all | 否 | 否 | 是 | 不编造真实监管部门要求 |
| P4Q-021 | 无答案 | 无 | all | 否 | 否 | 是 | 不编造真实客户名称 |
| P4Q-022 | 干扰排除 | TEST-RAG-002 | all | 是 | 否 | 否 | 不引用 TEST-DISTRACTOR-001 的排版日期 |
| P4Q-023 | 干扰排除 | TEST-DISTRACTOR-001 | document | 是 | 否 | 否 | 活动材料只能回答活动安排，不能当政策依据 |
| P4Q-024 | 新旧版本冲突 | TEST-RAG-001, TEST-RAG-002 | all | 是 | 否 | 否 | 当前应优先新版三个工作日，并说明旧版差异 |

## 使用建议

1. 先逐份上传 `documents/*.md` 并等待索引完成。
2. 用 RAG 调试页分别测试 `document`、`wiki` 和 `all` 来源。
3. Wiki 相关问题需先将 `TEST-WIKI-001` 作为 Wiki 草稿发布并确认可检索。
4. 若无答案问题命中干扰材料，知识问答仍应提示依据不足。
5. 记录每题的 `top_k`、命中锚点、引用来源和人工判断，避免只看最终回答流畅度。
