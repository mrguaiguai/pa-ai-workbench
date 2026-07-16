---
name: auto-coder
description: Spec-driven development skill for PA AI Workbench. Use when the user says "auto code", "自动开发", "执行任务", "开发 A1", "继续下一个任务", or wants AI to implement one task from DEV_SPEC.md.
---

# Auto Coder

This skill implements PA AI Workbench by reading `docs/archive/legacy-product/DEV_SPEC.md` and executing one task at a time.

## Core Rule

Always treat `docs/archive/legacy-product/DEV_SPEC.md` as the source of truth.

Do not modify `platform/weknora` unless the user explicitly requests it.

## Pipeline

```text
Read Spec
-> Pick Task
-> Plan Files
-> Implement
-> Validate
-> Update Progress
-> Report
```

## Step 1: Read Spec

Read:

```text
docs/archive/legacy-product/DEV_SPEC.md
```

If product context is needed, read:

```text
PRODUCT_SPEC.md
```

Do not read the full root-level product spec unless needed for clarification.

## Step 2: Pick Task

If the user specifies a task ID, execute that task.

Examples:

```text
执行 A1
auto code D3
开发 E4
```

If the user says "next" or "继续下一个任务", pick the first task with status `[ ]`.

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
   - Agent -> Knowledge Engine tools
   - Knowledge Engine -> mock / weknora_api / extracted backend
3. Use mock fallback when external services are unavailable.
4. Do not hardcode API keys.
5. Do not log sensitive document content.
6. Do not introduce Word export, feedback, complex auth, or approval flow in MVP unless the task explicitly asks for it.

## Step 5: Validate

Run the validation command listed in `DEV_SPEC.md` for the task.

If validation fails:

```text
Diagnose -> Fix -> Re-run
```

Maximum 3 fix rounds.

If still failing after 3 rounds, stop and report:

```text
Failed task:
Commands run:
Error summary:
Likely cause:
Recommended next step:
```

## Step 6: Update Progress

If validation passes, update `docs/archive/legacy-product/DEV_SPEC.md` task status:

```text
[ ] -> [x]
```

Do not mark a task complete without running its validation.

## Step 7: Report

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
```

## Git Safety

Do not commit automatically.

Before suggesting a commit, run or ask the user to run:

```bash
git status --short
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
```
