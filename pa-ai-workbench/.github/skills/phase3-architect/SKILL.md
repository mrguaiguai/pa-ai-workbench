---
name: phase3-architect
description: Architecture and specification maintenance skill for PA AI Workbench phase 3. Use when the user asks to design, revise, split, audit, or update PHASE3_SPEC tasks, M1/M2/M3 scope, real LLM productization, WeKnora reuse boundaries, or phase3 skill-driven planning without implementing product code.
---

# Phase 3 Architect

This skill maintains the third-stage source of truth:

```text
pa-ai-workbench/PHASE3_SPEC.md
```

## Core Rule

Treat `PHASE3_SPEC.md` as the phase 3 source of truth.

Phase 3 direction:

```text
Reuse WeKnora backend RAG/Wiki capability
-> Keep PA frontend, backend API, and Agent layer independent
-> Expose WeKnora only through PA KnowledgeBackend Adapter
-> Make M2/M3 release readiness depend on real DeepSeek + DashScope + WeKnora gates
-> Deliver M3 as a locally runnable real product, not a mock/demo flow
```

Do not implement product code while using this skill unless the user explicitly switches from spec design to a numbered implementation task.

## Read First

Always read:

```text
pa-ai-workbench/PHASE3_SPEC.md
```

Read for context when needed:

```text
pa-ai-workbench/PHASE2_SPEC.md
pa-ai-workbench/DEV_SPEC.md
pa-ai-workbench/PRODUCT_SPEC.md
../DEV_SPEC_副本.md
```

Use `../DEV_SPEC_副本.md` only as a structure/style reference. Do not copy unrelated product goals from it into phase 3.

## Responsibilities

- Maintain M1/M2/M3 scope.
- Add or refine phase 3 tasks.
- Keep tasks executable with target, scope, input, output, acceptance, validation, risk, and status.
- Preserve the decision that M1 uses WeKnora as RAG/Wiki fact source.
- Preserve the decision that M2/M3 require real DeepSeek Chat, WeKnora DeepSeek KnowledgeQA, and DashScope Embedding for release.
- Keep three-week launch framed as M1, not the whole phase.
- Keep the PA product boundary independent from WeKnora UI and raw API shape.
- Require new M2/M3 tasks to state real-model validation, release checker impact, fallback boundaries, and secret-safety rules.
- Keep mock/extracted fallback documented as dev-only or explicit fallback unless a task is specifically testing fallback behavior.

## Task Status

Use:

```text
[ ] not started
[~] in progress
[x] completed
```

Do not mark `[x]` without validation evidence.

## Workflow

```text
Read PHASE3_SPEC
-> Identify requested scope or task
-> Revise spec only
-> Check consistency with M1/M2/M3 boundaries
-> Validate document structure
-> Update task status only if validation passes
-> Run git safety checks
-> Commit task-scoped files automatically
-> Report changes and next recommended task
```

## Validation

Run relevant checks:

```bash
test -f PHASE3_SPEC.md
rg -n "P3-M1|P3-M2|P3-M3|KnowledgeBackend Adapter|WeKnora|DeepSeek|DashScope|check_m2|check_m3" PHASE3_SPEC.md
git status --short
git status --ignored --short
```

## Auto Commit

After validation passes, automatically create one task-level commit.

Rules:

1. Commit only files related to the current task.
2. Include the task id in the commit message.
3. Do not push unless the user explicitly asks.
4. If unrelated changes are present, leave them unstaged and mention them.
5. If sensitive files are present, stop before commit and report the blocker.

Recommended message:

```bash
git commit -m "docs: complete P3-M1-A1 weknora deployment audit"
```

## Guardrails

- Do not move phase 3 back to Python-first RAG/Wiki replication unless the user explicitly changes strategy.
- Do not make PA frontend or Agent depend on WeKnora raw response fields.
- Do not turn M1 into full production RBAC, IM, graph, approval flow, or export scope.
- Do not let M2/M3 READY rely on mock chat, mock RAG, keyword-only retrieve, old chunks, or fallback Wiki draft.
- Do not add secrets, real documents, uploads, databases, or logs.
- Do not push automatically.

## Report Format

```text
Updated:
- ...

Spec decisions:
- ...

Validation:
- command: result

Git:
- commit hash or blocked reason

Next task:
- ...
```
