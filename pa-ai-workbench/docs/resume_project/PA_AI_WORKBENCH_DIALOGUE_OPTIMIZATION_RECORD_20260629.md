# PA AI Workbench 智能对话优化开发记录

> 日期：2026-06-29
>
> 范围：本次对话内的智能对话产品瘦身、主入口调整、智能分析冻结、知识库选择融合、界面整体化与文案优化。
>
> 口径：PA AI Workbench 是独立产品；WeKnora 提供底层 RAG、Wiki、AgentQA、MCP、Web Search 等原生能力。本文记录 PA 产品层的界面、BFF、能力封装、验证与同步改动，不把 PA 写成从零重写 WeKnora 底层能力。

## 1. 背景与目标

本轮优化的起点，是用户认为原有 `#/dialogue` 更像“能力验收控制台”，主界面同时暴露策略编辑、MCP、Web Search、调试细节、建议问题和多种 Agent 能力，日常使用显得臃肿。

新的产品目标是把智能对话收敛成 GPT/ima 式日常对话界面：

- 用户默认看到会话列表、消息流、输入框、Agent 选择、知识库选择和必要引用入口。
- 调试、策略、MCP、Web Search、审计等能力保留，但退出主路径。
- 数据分析 Agent、自定义 Agent、Wiki 修订等暂时冻结或隐藏，不删除后端能力。
- 智能推理 Agent 先复用 WeKnora 已支持的 `multi_turn_enabled` 与 `history_turns`，不在本阶段接入长期记忆。
- 主入口从旧功能宫格切换到智能对话，让 `#/` 直接进入对话。

## 2. 关键决策记录

| 议题 | 决策 | 原因 |
| --- | --- | --- |
| 智能对话定位 | 从验收控制台改成日常聊天工作区 | 降低认知负担，符合用户对 GPT/ima 式界面的预期 |
| WeKnora 模板参考 | 只融合布局思路，不显示 WeKnora 品牌内容 | 产品是 PA AI Workbench，不能生搬硬套上游截图 |
| 首页 | 取消旧功能页体验，由智能对话取代首页 | 智能对话中已能跳转资料库、检索、Wiki 等页面 |
| 推荐问题 | 从主界面移除 | 避免空会话区域变成大面板，减少干扰 |
| 智能分析 | 主导航冻结，直接路由显示冻结提示 | 后端能力保留，前端不再作为独立主功能暴露 |
| 数据分析/自定义 Agent | 普通 Agent 选择器隐藏 | 当前阶段不用，避免用户误触高复杂度能力 |
| 知识库选择 | 融合到输入区工具栏，第一版单选 | 让对话时能明确选择知识库，同时避免多选范围过重 |
| 回答类型 | 输入区加入普通问答、政策分析、案例复盘 | 把部分智能分析能力轻量融合到对话里 |
| 空状态文案 | 去掉大标题和配置说明，改为输入框 placeholder | 页面更像即时对话工作区，不像启动页 |

## 3. 实施变更总览

### 3.1 路由与主导航

- `#/` 直接渲染 `DialoguePage`。
- `#/dialogue` 保留为兼容别名。
- 对话路由隐藏外层 topbar 与 page heading，使智能对话成为整页主工作区。
- 旧首页功能宫格不再作为默认入口。
- `#/analysis` 改为冻结提示，引导回智能对话。

### 3.2 智能对话页面瘦身

- 主界面仅保留快速问答、智能推理、Wiki 问答等可用对话 Agent。
- 隐藏数据分析、自定义 Agent、Wiki 修订等当前阶段不适合作为普通入口的能力。
- 删除推荐问题区域、默认问题 chips、suggested questions 拉取与刷新逻辑。
- 引用、工具过程、warnings 和运行详情进入可折叠详情区域。
- 高级文档范围保留为折叠输入，不再把内部 ID 放在主路径上。

### 3.3 知识库选择与回答类型

- 输入区工具栏新增知识库单选器，数据来自 `getNativeKnowledgeBaseOverview()`。
- 默认选中当前 active KB。
- 发起 Quick Q&A 或 AgentQA 时传入 `knowledge_base_ids: [selectedKbId]`。
- 不自动修改全局 active KB，避免一次对话选择影响全局状态。
- 新增回答类型：普通问答、政策分析、案例复盘。
- 政策分析与案例复盘默认走智能推理 Agent，复用 AgentQA/native session。

### 3.4 BFF 与请求体

- `/api/analysis/native-agentqa` 支持可选 `answer_mode`。
- `/api/rag/knowledge-chat` 支持可选 `answer_mode`。
- BFF 根据 `answer_mode` 生成适合分析模式的 effective query。
- PA 历史中仍保存用户原始输入，不把内部增强后的 query 当成用户原话。

### 3.5 界面整体化

- 将对话页外层和内层卡片的视觉割裂移除。
- 对话路由下：
  - 不渲染外层顶部栏。
  - 不渲染页面标题区。
  - page surface padding 设为 0。
  - dialogue shell 去掉边框、圆角和阴影。
- 桌面与移动端均验证无横向溢出。

### 3.6 空状态文案优化

用户指出空会话中心的大标题“开始一次资料库对话”以及“知识库 · Agent · 回答类型”参数说明不适合继续展示。

最终处理：

- 移除空状态主视觉大标题。
- 移除空状态参数说明。
- 输入框 placeholder 改为 `向知识库提问`。

这样表达更轻，不把内部状态当成页面主标题，也更接近日常对话产品。

## 4. 主要文件改动

| 文件 | 改动摘要 |
| --- | --- |
| `frontend/src/App.tsx` | 将 `/` 和 `/dialogue` 指向智能对话；对话路由隐藏外层 topbar/page heading；Analysis 路由冻结 |
| `frontend/src/pages/DialoguePage.tsx` | 重构对话主体验；过滤可见 Agent；移除推荐问题；加入知识库选择、回答类型、详情抽屉和 WeKnora 风格融合布局 |
| `frontend/src/styles.css` | 新增整体化对话布局、输入区、侧栏、详情抽屉、移动端响应式样式；移除空状态标题样式 |
| `frontend/src/api/client.ts` | 增加 `answer_mode`、知识库选择等前端请求字段支持 |
| `backend/app/api/analysis.py` | AgentQA 请求支持 `answer_mode`，保持历史保存用户原始输入 |
| `backend/app/api/rag.py` | knowledge-chat 请求支持 `answer_mode` |
| `backend/app/schemas.py` | 增加/扩展相关 schema 字段 |
| `backend/app/services/native_agent_service.py` | 支持分析模式 query 构造与智能推理多轮能力复用 |
| `backend/app/services/native_chat_service.py` | 支持知识库范围与回答类型透传 |
| `knowledge_engine/backends/weknora_api_backend.py` | 对接 WeKnora API 的相关参数适配 |
| `.gitignore` | 外层新增 `.pnpm-store/` 忽略规则，避免提交依赖缓存 |

## 5. 验证记录

本轮前端与浏览器验证均围绕真实页面进行，不用静态截图当作 PASS。

| 验证项 | 结果 |
| --- | --- |
| `tsc --noEmit` | 通过 |
| `vite build` | 通过 |
| `#/` 桌面端 | 进入智能对话，无旧首页功能宫格，无外层 topbar/page heading，无横向溢出 |
| `#/dialogue` 移动端 | 进入智能对话，无横向溢出 |
| `#/library` 回归 | 仍保留原页面标题与顶部导航，非对话页面不受影响 |
| 空状态文案 | “开始一次资料库对话”和参数说明均不存在，placeholder 为“向知识库提问” |
| 智能分析冻结 | 主导航不再作为核心入口；直开 `#/analysis` 显示冻结提示 |

## 6. 当前产品状态

当前智能对话已经从“能力验收控制台”收敛为日常主入口：

- 首页即对话。
- 左侧是产品导航与近期会话。
- 中间是消息流与输入框。
- 输入框可选择知识库、回答类型和 Agent。
- 细节、引用、工具过程放在详情区域。
- 推荐问题退出主界面。
- 智能分析页暂时冻结，其分析能力以回答类型方式进入对话。

这使产品主路径更清晰：用户先提问，再根据需要选择知识库或回答类型，而不是先理解一堆内部能力面板。

## 7. 后续优化建议

下一阶段更适合继续做三类优化：

1. 输入区密度与控件表达：减少按钮文字，统一 icon tooltip，保持低干扰。
2. 对话历史体验：支持更自然的会话命名、置顶、删除和搜索。
3. 引用查看体验：点击回答中的引用后，在右侧详情区聚焦对应 document/wiki/web evidence。

长期记忆、复杂策略编辑、自定义 Agent、数据分析完整页，可以作为后续二期能力重新评估，不建议现在回到主界面。
