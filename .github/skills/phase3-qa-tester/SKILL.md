---
name: phase3-qa-tester
description: QA and smoke-test skill for PA AI Workbench phase 3. Use when the user asks to test PHASE3_SPEC tasks, verify WeKnora RAG/Wiki integration, validate non-mock citations, run M1/M2/M3 smoke tests, or check frontend/backend behavior.
---

# Phase 3 QA Tester

This skill verifies phase 3 tasks against `PHASE3_SPEC.md`.

## Core Rule

Do not mark anything as passed unless a command or live/manual check proves the expected behavior.

No inference-only pass.

For M1, mock/extracted success is not enough. M1 RAG/Wiki/Agent pass requires WeKnora-backed evidence or an explicit fixture-only contract-test result marked as non-release proof.

## Read First

Read:

```text
pa-ai-workbench/PHASE3_SPEC.md
```

Read task-specific docs or scripts only as needed:

```text
pa-ai-workbench/docs/PHASE3_WEKNORA_DEPLOYMENT_MAP.md
pa-ai-workbench/docs/PHASE3_WEKNORA_API_MAP.md
pa-ai-workbench/backend/scripts/
pa-ai-workbench/frontend/package.json
```

## Test Scopes

Scope can be:

```text
single task: P3-M1-B3
milestone: M1, M2, M3
module: WeKnora RAG, Wiki, Agent, Frontend, Release
```

If the user does not specify scope, test the latest completed or in-progress phase 3 task.

## M1 Required Checks

M1 must prove:

- WeKnora backend is reachable.
- PA uses service account configuration.
- Upload/index uses WeKnora, not mock.
- Retrieve returns `source=weknora_api`.
- Agent citations are non-mock and traceable.
- Wiki draft/publish/retrieve works.
- Frontend build passes.
- Release safety checks pass.

## Commands

Choose relevant commands:

```bash
cd pa-ai-workbench && python -m compileall backend/app agent knowledge_engine
cd pa-ai-workbench/backend && python scripts/smoke_weknora_connection.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_rag_m1.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_agent_m1.py
cd pa-ai-workbench/backend && python scripts/smoke_weknora_wiki_m1.py
cd pa-ai-workbench/frontend && npm run build
cd pa-ai-workbench && git status --short
cd pa-ai-workbench && git status --ignored --short
```

Existing phase 2 regression checks may also be useful:

```bash
cd pa-ai-workbench/backend && python scripts/smoke_backend_l3.py
cd pa-ai-workbench/backend && python scripts/smoke_agent_l4.py
cd pa-ai-workbench/backend && python scripts/smoke_wiki_l5.py
```

## Failure Policy

If a test fails:

1. Identify whether the issue is code, config, dependency, WeKnora availability, test data, or test expectation.
2. Apply the smallest safe fix only if the user requested QA with fixes.
3. Re-run the same command.
4. Stop after 3 failed fix rounds.

Do not expand product scope while fixing.

## Auto Commit

If QA creates or updates task-related test scripts, fixtures, docs, or spec statuses, and validation passes, automatically create one task-level commit.

Rules:

1. Commit only files related to the QA scope.
2. Include the task id or milestone in the commit message.
3. Use `test:` for smoke/tests and `docs:` for QA reports/checklists.
4. Do not push unless the user explicitly asks.
5. If QA only runs tests and changes no files, do not create an empty commit.
6. If unrelated changes are present, leave them unstaged and mention them.
7. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "test: complete P3-M1-F1 weknora rag smoke"
git commit -m "docs: complete P3-M1-F5 release checklist"
```

## Sensitive Data Rules

Use only sanitized files.

Fail the release check if git includes:

```text
.env
uploads/
data/
logs/
*.db
*.sqlite
API keys
service tokens
real department documents
private model endpoints in committed files
```

## Report Format

```text
QA Scope:
- ...

Commands run:
- command: PASS/FAIL + key output

Evidence:
- source=weknora_api / mock / fixture-only

Fixes applied:
- ...

Result:
- PASS / FAIL / BLOCKED

Remaining risks:
- ...

Git:
- commit hash, no changes, or blocked reason
```
