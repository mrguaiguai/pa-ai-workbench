# PA 智能工作台 PRODUCT_SPEC

> 版本：0.1
>
> 本文件是产品规格摘要，详细设计母版见仓库根目录 `PA_AI_WORKBENCH_PRODUCT_SPEC.md`。
>
> AI 开发时优先读取 `DEV_SPEC.md`，需要理解产品背景时再读取本文件。

## 1. 产品定位

PA 智能工作台是面向金融公共事务团队的内部 AI 工作台。

它不是 WeKnora 的子产品，也不是通用聊天机器人。WeKnora 仅作为底层知识能力来源与源码参考。

第一版服务一个约 8 人的小型金融 PA 团队，优先追求：

- 功能闭环完整。
- 模块边界清晰。
- 结果可追溯。
- 后续易迭代。

## 2. 核心场景

第一版聚焦 4 个场景：

1. 知识问答：围绕部门资料库提问，回答必须带来源引用。
2. 政策分析：基于资料生成政策背景、核心要求、影响、风险和建议。
3. 历史案例：轻量复盘类似案例，输出背景、时间线、动作和经验教训。
4. Wiki 沉淀：搜索和查看 Wiki 页面，为长期知识资产预留模块。

## 3. 第一版范围

必须做：

- 资料上传与资料库管理。
- 知识问答。
- 政策分析。
- Wiki 浏览/搜索。
- 任务进度展示。
- 本地数据库保存记录。
- Agent 会话级多轮记忆。

轻量做：

- 历史案例复盘。
- 生成结果历史。
- Skill 系统雏形。
- WeKnora API backend 雏形。

暂不做：

- Word 导出。
- 用户反馈评分。
- 复杂权限。
- 审批流。
- Wiki 图谱。
- 完整多 Agent Supervisor。

## 4. 产品模块

前端主模块：

```text
/
  工作台首页

/library
  资料库

/analysis
  智能分析台
  - 知识问答
  - 政策分析
  - 历史案例

/wiki
  Wiki 知识库

/history
  生成历史
```

## 5. 架构原则

```text
Frontend
-> Backend API
-> Agent Runtime
-> Knowledge Engine
-> mock / weknora_api / extracted backend
```

关键规则：

- 前端只调用后端。
- 后端只通过 Orchestrator 调 Agent。
- Agent 只通过 Knowledge Engine 获取证据。
- Knowledge Engine 不暴露 WeKnora 原始响应。
- mock backend 必须可用。

## 6. Agent 原则

Agent 层按 Runtime 架构设计，不写成单个 prompt 函数。

核心模块：

- AgentOrchestrator。
- AgentRuntime。
- ContextManager。
- MemoryManager。
- SkillRegistry。
- ToolRegistry。
- PolicyGuard。
- EventBus。
- AgentProfile。
- Workflow。

第一版内置 workflow：

- knowledge_qa。
- policy_analysis。
- case_review。

后续可扩展：

- risk_review。
- talking_points。
- meeting_minutes。
- wiki_synthesis。
- wiki_fixer。
- briefing_draft。

## 7. 记忆要求

第一版必须支持会话级多轮记忆：

- 创建会话。
- 保存 user / assistant 消息。
- Agent 读取最近 N 条上下文。
- 支持连续追问。
- 刷新页面后仍能查看历史会话。

暂不做长期跨会话记忆和向量化记忆，但要预留接口。

## 8. 安全要求

- 不提交真实 `.env`。
- 不提交上传资料。
- 不提交 API Key。
- 不在日志里输出长段敏感原文。
- mock 数据必须标记 source=mock。
- 无证据时返回依据不足，不编造来源。

