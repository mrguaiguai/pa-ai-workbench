---
name: phase3-release-checker
description: Release readiness and safety-check skill for PA AI Workbench phase 3. Use when the user asks to prepare or verify M1 internal pilot launch, check WeKnora configuration, ensure mock is disabled, inspect git safety, or create/update release checklists.
---

# Phase 3 Release Checker

This skill checks whether a phase 3 M1 internal pilot is safe to run.

## Core Rule

M1 release readiness requires real WeKnora-backed RAG/Wiki capability.

Do not approve release if:

```text
KNOWLEDGE_BACKEND != weknora_api
MOCK_MODE=true
WeKnora auth/health fails
non-mock citation smoke fails
sensitive files are tracked or staged
```

## Read First

Read:

```text
pa-ai-workbench/PHASE3_SPEC.md
```

Then inspect as needed:

```text
pa-ai-workbench/backend/.env.example
pa-ai-workbench/backend/app/config.py
pa-ai-workbench/README.md
pa-ai-workbench/docs/
pa-ai-workbench/backend/scripts/
```

Do not read or print real `.env` values unless the user explicitly asks and it is necessary; never echo secrets in the final report.

## Responsibilities

- Verify M1 release checklist.
- Check WeKnora connection, auth, workspace/kb availability.
- Check mock mode and backend mode.
- Check RAG/Agent/Wiki smoke outputs.
- Check frontend build.
- Check git tracked/ignored sensitive files.
- Create or update `docs/PHASE3_M1_RELEASE_CHECKLIST.md` when requested by a task.

## Release Checklist

Required:

- WeKnora backend reachable.
- Service account configured through environment.
- `KNOWLEDGE_BACKEND=weknora_api`.
- `MOCK_MODE=false`.
- RAG smoke returns `source=weknora_api`.
- Agent smoke saves non-mock citations.
- Wiki smoke proves publish -> retrieve.
- Frontend build passes.
- No secrets or real documents in git.
- README or release docs explain startup and rollback.

## Commands

Use relevant checks:

```bash
cd pa-ai-workbench && git status --short
cd pa-ai-workbench && git status --ignored --short
cd pa-ai-workbench && python -m compileall backend/app agent knowledge_engine
cd pa-ai-workbench/backend && python scripts/smoke_weknora_connection.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_rag_m1.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_agent_m1.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_wiki_m1.py
cd pa-ai-workbench/frontend && npm run build
```

If scripts do not exist yet, report the missing release gate and fail readiness rather than silently passing.

## Auto Commit

If release checking creates or updates release docs, checklists, scripts, or spec statuses, and all relevant checks pass, automatically create one task-level commit.

Rules:

1. Commit only release-checker task files.
2. Include the task id in the commit message when available.
3. Use `docs:` for checklist/docs and `test:` for release smoke scripts.
4. Do not push unless the user explicitly asks.
5. If the release decision is `NOT READY` or `BLOCKED`, do not commit status as completed.
6. If unrelated changes are present, leave them unstaged and mention them.
7. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "docs: complete P3-M1-F5 release checklist"
git commit -m "test: complete P3-M1-F2 weknora wiki smoke"
```

## Guardrails

- Do not commit or print `.env`.
- Do not stage generated data, uploads, db files, logs, node_modules, or dist.
- Do not count mock smoke tests as release proof.
- Do not approve if WeKnora is unreachable unless the release target is explicitly changed away from M1 internal pilot.
- Do not push automatically.

## Report Format

```text
Release Scope:
- M1 internal pilot

Checks:
- WeKnora health: PASS/FAIL
- Config mode: PASS/FAIL
- RAG smoke: PASS/FAIL
- Agent smoke: PASS/FAIL
- Wiki smoke: PASS/FAIL
- Frontend build: PASS/FAIL
- Git safety: PASS/FAIL

Decision:
- READY / NOT READY / BLOCKED

Blocking issues:
- ...

Git:
- commit hash, no changes, or blocked reason

Next action:
- ...
```
