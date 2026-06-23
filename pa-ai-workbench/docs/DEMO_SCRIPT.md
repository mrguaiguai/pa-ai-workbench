# PA AI Workbench MVP Demo Script

This script is for the Day 3 MVP walkthrough of PA AI Workbench. Use mock data or sanitized sample files only.

## Demo Goal

Show that PA AI Workbench is an independent internal workbench for a financial public affairs team, with a complete MVP loop:

1. Confirm backend and mock knowledge backend are available.
2. Upload or inspect documents in the library.
3. Run knowledge QA with citations.
4. Run policy analysis and case review workflows.
5. Browse Wiki pages from the Knowledge Engine.
6. Review persisted generation history.

## Safety Rules

- Do not use real department materials, client names, non-public policies, credentials, or API keys.
- Do not commit or screen-share `.env`, `backend/data/`, `backend/uploads/`, logs, or local databases.
- Keep `KNOWLEDGE_BACKEND=mock` and `MOCK_MODE=true` unless a sanitized WeKnora API environment has been explicitly prepared.
- When explaining citations, call out `source=mock` as intentional demo fallback behavior.
- If evidence is insufficient, present that as a product safeguard rather than a failure.

## Setup Checklist

Run the backend:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the frontend:

```bash
cd /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Pre-demo smoke checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
```

Expected:

- `/health` returns `ok`.
- `/api/status` shows `knowledge_backend=mock` or the approved demo backend.
- The home page backend badge is ready.
- No real `.env`, uploads, databases, or sensitive files are staged in git.

## Talk Track

### 1. Home

Open `/`.

Say:

> This is PA AI Workbench, an independent product under `pa-ai-workbench/`. It is not a WeKnora sub-product. WeKnora is only one possible Knowledge Engine backend.

Show:

- Backend status badge.
- Metrics for documents, conversations, tasks, and outputs.
- Navigation to Library, Analysis, Wiki, and History.

Success cue:

- The page loads and the backend badge is ready or shows a clear error state.

### 2. Library

Open `/library`.

Say:

> The library is the controlled entry point for PA materials. For the MVP we use local storage plus Knowledge Engine indexing status, and mock fallback keeps the demo available without external services.

Show:

- Document count and indexed count.
- Upload form fields: title, business area, type, source.
- Existing document rows and status badges.

Optional safe upload:

- Use a tiny sanitized text file created only for the demo.
- Avoid real policies, real department documents, client names, or private material.

Success cue:

- A document appears in the list with a tracked status such as `indexed`.

### 3. Knowledge QA

Open `/analysis` and choose `知识问答`.

Use a safe prompt:

```text
请基于资料库说明当前 mock 政策材料的核心要求，并列出依据。
```

Say:

> The analysis page is conversation-based. If no conversation exists, the backend creates one automatically. Each response is persisted with task, output, citations, and conversation messages.

Show:

- Conversation list.
- Message stream.
- Task progress.
- Result panel.
- Citations panel.

Success cue:

- The result contains an answer and at least one citation, or a clear insufficient-evidence warning.

### 4. Policy Analysis

In `/analysis`, choose `政策分析`.

Use a safe prompt:

```text
分析 mock 监管政策对公共事务团队的影响，输出背景、核心要求、风险和建议。
```

Optional fields:

```text
业务域: securities
资料类型: policy
额外要求: 用适合管理层汇报的结构表达
```

Say:

> Policy analysis reuses the same Agent Runtime but routes to a different workflow. The key design point is traceability: recommendations should be grounded in retrieved evidence.

Show:

- Workflow switch.
- Structured output.
- Warnings if evidence is limited.
- Citations and source labels.

Success cue:

- Output includes policy background, requirements, impact, risk, suggestions, and visible citations or warnings.

### 5. Case Review

In `/analysis`, choose `案例复盘`.

Use a safe prompt:

```text
复盘一个 mock 历史案例，说明背景、时间线、动作和经验教训。
```

Say:

> Case review is intentionally lightweight in the MVP. It proves the workflow model can support more PA tasks beyond QA and policy analysis.

Show:

- New assistant response in the same conversation or a new one.
- Persisted messages.
- Case-oriented sections in the result.

Success cue:

- Output includes background, timeline, actions, lessons, and citations or warnings.

### 6. Wiki

Open `/wiki`.

Search:

```text
mock
```

Open a result such as:

```text
Mock 政策观察
```

Say:

> Wiki is the knowledge asset view. In the MVP it reads through the Knowledge Engine contract, so mock and future WeKnora-backed pages share the same frontend shape.

Show:

- Search results.
- Page type and summary.
- Wiki content.
- Citation list and `source=mock`.

Success cue:

- Search returns mock Wiki pages and page details render with citations.

### 7. History

Open `/history`.

Say:

> Every generated output is persisted. History lets the team review what was produced, inspect warnings, and trace citations after the conversation has moved on.

Show:

- Output list.
- Filter by task type or status.
- Result detail.
- Warnings and citations.

Success cue:

- Outputs from the QA, policy analysis, or case review demo appear in history.

## Fallback Paths

- If the backend is unavailable, show the frontend error states and then restart `uvicorn`.
- If external WeKnora is unavailable, keep `KNOWLEDGE_BACKEND=mock`; the mock backend is expected MVP behavior.
- If no citations appear, explain that the system should prefer warnings or insufficient evidence over unsupported claims.
- If upload is skipped, use the built-in mock evidence and Wiki pages for the demo.

## Closing Message

Say:

> The MVP demonstrates the full working loop: materials enter the library, Agent workflows produce traceable outputs, Wiki pages provide a knowledge asset view, and generated history keeps the work auditable. The architecture remains independent from WeKnora while preserving a clean backend adapter path for future integration.

## Post-Demo Checks

After the demo:

```bash
git status --short
git status --ignored --short
```

Confirm:

- No `.env` files are staged.
- No uploads, local databases, logs, `node_modules/`, or `dist/` are staged.
- Any temporary sanitized demo file is deleted or left ignored outside git-tracked scope.
