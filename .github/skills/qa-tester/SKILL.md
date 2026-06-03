---
name: qa-tester
description: QA and smoke-test skill for PA AI Workbench. Use when the user says "run QA", "测试", "验收", "跑测试", "test and fix", or asks to verify completed DEV_SPEC tasks.
---

# QA Tester

This skill verifies PA AI Workbench implementation against `pa-ai-workbench/DEV_SPEC.md`.

## Core Rule

Do not mark anything as passed unless a command was run and its output proves the expected behavior.

No inference-only pass.

## Pipeline

```text
Read DEV_SPEC
-> Pick Scope
-> Run One Test
-> Verify Output
-> Fix if Needed
-> Re-run
-> Report
```

## Step 1: Read Spec

Read:

```text
pa-ai-workbench/DEV_SPEC.md
```

Scope can be:

```text
task id: A1, B2, D9
stage: A, B, C, D, E, F
all completed tasks
```

If the user does not specify scope, test the most recently completed task if known; otherwise test all `[x]` tasks.

## Step 2: Test Rules

Run tests strictly one command at a time.

For each command, record:

```text
command
exit status
key stdout/stderr evidence
pass/fail
```

Never run destructive commands.

Never use real sensitive documents.

Use mock data or temporary files under:

```text
pa-ai-workbench/tmp/
```

## Step 3: Validation Commands by Area

### Backend

Use these when backend files changed:

```bash
cd pa-ai-workbench/backend
python -m compileall app
```

If dependencies are installed and server can run:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then test:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
```

### Knowledge Engine

Use:

```bash
cd pa-ai-workbench
python -m compileall knowledge_engine
python -c "from knowledge_engine.factory import create_knowledge_engine; print(create_knowledge_engine().health())"
```

### Agent

Use:

```bash
cd pa-ai-workbench
python -m compileall agent
python -c "from agent.orchestrator import AgentOrchestrator; print('orchestrator import ok')"
```

If D9 is implemented, test through backend:

```bash
curl -X POST http://127.0.0.1:8000/api/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"task_type":"knowledge_qa","query_or_topic":"测试问题"}'
```

### Frontend

Use:

```bash
cd pa-ai-workbench/frontend
npm run build
```

If dev server is needed:

```bash
npm run dev
```

### Git Safety

Use:

```bash
git status --short
```

Fail if output includes:

```text
.env
uploads/
data/
logs/
node_modules/
dist/
```

## Step 4: Fix Policy

If a test fails:

1. Identify whether it is code, config, missing dependency, or test command issue.
2. Apply the smallest safe fix.
3. Re-run the same command.
4. Stop after 3 failed fix rounds.

Do not expand product scope while fixing.

## Step 5: Report Format

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

## Required Checks Before Final PASS

For Day 1 MVP:

```text
backend /health works
Knowledge Engine mock works
Agent imports work
frontend builds or starts
git status has no sensitive files
```

For Day 3 MVP:

```text
documents API works
conversation memory works
analysis API supports knowledge_qa / policy_analysis / case_review
wiki search/read works
history works
frontend build passes
mock fallback visible
git safety check passes
```

