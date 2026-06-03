---
name: phase2-qa-tester
description: QA and smoke-test skill for PA AI Workbench phase 2. Use when the user asks to test v0.2, verify real RAG, check Wiki workflow, or validate PHASE2_SPEC tasks.
---

# Phase 2 QA Tester

This skill verifies PA AI Workbench v0.2 against `pa-ai-workbench/PHASE2_SPEC.md`.

## Core Rule

Do not mark anything as passed unless a command was run and its output proves the expected behavior.

No inference-only pass.

## Pipeline

```text
Read PHASE2_SPEC
-> Pick Scope
-> Run One Test
-> Verify Output
-> Fix if Needed
-> Re-run
-> Report
```

## Test Scope

Scope can be:

```text
task id: G3, H9, I4
stage: G, H, I, J, K, L
all completed phase2 tasks
```

If the user does not specify scope, test the most recently completed task if known; otherwise test all `[x]` tasks in `PHASE2_SPEC.md`.

## Core Checks

### Model Gateway

```bash
cd pa-ai-workbench
python -m compileall agent
```

If API is running:

```bash
curl http://127.0.0.1:8000/api/model/status
```

### Embedding / Knowledge Engine

```bash
cd pa-ai-workbench
python -m compileall knowledge_engine
```

### Backend

```bash
cd pa-ai-workbench/backend
python -m compileall app
```

If server is running:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
```

### RAG

Use only sanitized or temporary sample text.

Expected checks:

```text
document upload
parse/chunk/index
retrieve returns evidence
citations link to chunk/wiki
```

### Wiki

Expected checks:

```text
create draft
edit page
publish page
retrieve wiki evidence
```

### Frontend

```bash
cd pa-ai-workbench/frontend
npm run build
```

### Git Safety

```bash
git status --short
git status --ignored --short
```

Fail if staged files include:

```text
.env
uploads/
data/
logs/
node_modules/
dist/
*.db
*.sqlite
real documents
API keys
```

## Fix Policy

If a test fails:

1. Identify whether it is code, config, dependency, or test command issue.
2. Apply the smallest safe fix.
3. Re-run the same command.
4. Stop after 3 failed fix rounds.

Do not expand product scope while fixing.

## Report Format

```text
QA Scope:
- ...

Commands run:
- command: result + key output

Fixes applied:
- ...

Result:
- PASS / FAIL

Remaining risks:
- ...
```

