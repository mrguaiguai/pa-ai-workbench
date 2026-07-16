---
name: phase2-auto-coder
description: Spec-driven implementation skill for PA AI Workbench phase 2. Use when the user asks to execute a PHASE2_SPEC task, continue phase 2 development, or implement v0.2 RAG/Wiki/Model Gateway work.
---

# Phase 2 Auto Coder

This skill implements PA AI Workbench v0.2 by reading `docs/archive/legacy-product/PHASE2_SPEC.md` and executing one task at a time.

## Core Rule

Always treat `docs/archive/legacy-product/PHASE2_SPEC.md` as the source of truth.

Do not modify `platform/weknora` unless the user explicitly requests it.

## Pipeline

```text
Read PHASE2_SPEC
-> Pick Task
-> Plan Files
-> Implement
-> Validate
-> Update Progress
-> Report
-> Commit/push only when user asks
```

## Step 1: Read Spec

Read:

```text
docs/archive/legacy-product/PHASE2_SPEC.md
```

If baseline context is needed, read:

```text
docs/archive/legacy-product/DEV_SPEC.md
PRODUCT_SPEC.md
```

## Step 2: Pick Task

If the user specifies a task ID, execute that task.

Examples:

```text
执行 G3
开发 H2
继续 K4
```

If the user says "继续下一个任务", pick the first task with status `[ ]`.

Task status markers:

```text
[ ] not started
[~] in progress
[x] completed
```

## Step 3: Plan Files

Before editing, report:

```text
Task: <ID + name>
Planned files:
- file 1
- file 2
Validation:
- command 1
- command 2
```

Keep the plan short.

## Step 4: Implement

Rules:

1. Keep PA applications under `apps/` and PA packages under `packages/`.
2. Preserve module boundaries:
   - frontend -> backend API
   - backend -> AgentOrchestrator
   - Agent -> ModelGateway / Tools / Knowledge Engine
   - Knowledge Engine -> extracted / mock / weknora_api backend
3. Do not bypass ModelGateway for Chat API calls.
4. Do not bypass EmbeddingProvider for embedding calls.
5. Do not hardcode API keys.
6. Do not log sensitive document content.
7. Preserve mock fallback.
8. Do not introduce RBAC, approval flow, Word export, graph visualization, or complex multi-agent work unless the task explicitly asks for it.

## Step 5: Validate

Run validation relevant to the task.

General commands:

```bash
cd apps/pa-api && python -m compileall app
cd . && python -m compileall agent knowledge_engine
cd apps/pa-web && npm run build
git status --short
```

Run only the relevant subset for the task.

If validation fails:

```text
Diagnose -> Fix -> Re-run
```

Maximum 3 fix rounds.

## Step 6: Update Progress

If validation passes, update `docs/archive/legacy-product/PHASE2_SPEC.md` task status:

```text
[ ] -> [x]
```

Do not mark a task complete without validation.

## Step 7: Git Safety

Commit and push only if the user asks.

Before staging, run:

```bash
git status --short
git status --ignored --short
```

Never stage or commit:

```text
.env
uploads/
data/
logs/
node_modules/
dist/
API keys
sensitive documents
real department materials
```

Stage only relevant files when possible.

## Step 8: Report

Final report format:

```text
Completed: <task id + name>
Files changed:
- ...
Validation:
- command: result
Notes:
- ...
Next task:
- ...
Git:
- committed/pushed or not requested
```
