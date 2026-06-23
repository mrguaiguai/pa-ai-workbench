---
name: phase5-rag-wiki-qa-optimization
description: Planning and execution skill for PA AI Workbench Phase 5 RAG, Wiki, knowledge_qa quality repair, retrieval_scope, current-run corpus isolation, 24-question regression, frontend Chinese terminology, and real WeKnora PASS gates. Use when the user asks to design, update, execute, validate, or continue PHASE5_SPEC tasks without expanding into new corpus design, complex Agent workflows, export, permissions, graph, or long-term memory scope.
---

# Phase 5 RAG Wiki QA Optimization

This skill maintains and executes the fifth-stage source of truth:

```text
pa-ai-workbench/PHASE5_SPEC.md
```

## Core Rule

Treat `PHASE5_SPEC.md` as the Phase 5 source of truth.

Phase 5 direction:

```text
Reuse Phase 4 synthetic sanitized corpus and 24 questions
-> Convert P4-G PARTIAL / FAIL items into fixable regression tasks
-> Repair RAG current-run isolation, source filtering, ranking, and distractor suppression
-> Repair Wiki natural-language recall and Wiki citation traceability
-> Repair knowledge_qa evidence quality, refusal, distractor handling, and version conflict answers
-> Finish frontend Chinese terminology and real-state display
-> Prove final real WeKnora 24-question PASS
```

Do not implement product code while using this skill unless the user explicitly asks to execute one numbered `PHASE5_SPEC.md` task.

## Read First

Always read:

```text
pa-ai-workbench/PHASE5_SPEC.md
```

Read for context when needed:

```text
pa-ai-workbench/PHASE4_SPEC.md
pa-ai-workbench/docs/PHASE4_REAL_TEST_SUMMARY.md
pa-ai-workbench/backend/fixtures/phase4_rag_wiki_qa/manifest.json
pa-ai-workbench/backend/fixtures/phase4_rag_wiki_qa/questions.json
pa-ai-workbench/backend/fixtures/phase4_rag_wiki_qa/hit_matrix.md
pa-ai-workbench/frontend/src/pages/RagDebugPage.tsx
pa-ai-workbench/frontend/src/pages/AnalysisPage.tsx
pa-ai-workbench/frontend/src/pages/WikiPage.tsx
pa-ai-workbench/backend/app/api/rag.py
pa-ai-workbench/backend/app/services/analysis_service.py
pa-ai-workbench/agent/agents/qa_agent.py
```

Read only the files relevant to the selected task.

## Responsibilities

- Maintain Phase 5 scope for RAG, Wiki, `knowledge_qa`, frontend Chinese terminology, 24-question regression, and real PASS reports.
- Reuse `backend/fixtures/phase4_rag_wiki_qa/`; do not design a new corpus unless a future task explicitly says so.
- Keep `knowledge_qa` as the only重点 Agent workflow for this phase.
- Keep `policy_analysis` and `case_review` unchanged unless explicitly tasked.
- Keep official QA simple: question, simple knowledge source selection, answer, citations, and insufficient-evidence notice.
- Keep advanced retrieval controls on the RAG debug page.
- Preserve PA product boundaries: frontend and Agent must use PA APIs / PA Adapter, not raw WeKnora APIs.
- Separate fixture, offline, local live, and real WeKnora validation evidence.
- Never count mock, fixture-only, old cache, historical upload leakage, or fallback evidence as final PASS.
- Final P5-G tasks require `MOCK_MODE=false`, `KNOWLEDGE_BACKEND=weknora_api`, and PASS reports.

## Task Status

Use:

```text
[ ] not started
[~] in progress
[x] completed
```

Do not mark `[x]` without validation evidence.

For P5-G final gate tasks, do not mark `[x]` for PARTIAL, FAIL, or BLOCKED. Phase 5 final gate is stricter than Phase 4 reporting.

## Workflow

```text
Read PHASE5_SPEC
-> Run git status --short and git log --oneline -3
-> Identify one P5 task id
-> State task id, planned file edits, and validation method before editing
-> Implement only that task
-> Run validation
-> Update PHASE5_SPEC task status only if validation passes
-> Run git safety checks
-> Commit task related files automatically
-> Report changes, validation, risks, and next recommended task
```

If the user asks for broad Phase 5 work without a task id, select the first unfinished task in `PHASE5_SPEC.md`.

Do not skip P5-A. Only move to P5-B after P5-A is complete. Only move to P5-G after P5-A through P5-F are complete.

## Validation

Choose the relevant subset:

```bash
test -f PHASE5_SPEC.md
test -f .github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
rg -n "P5-A|P5-B|P5-C|P5-D|P5-E|P5-F|P5-G|24 问|真实 PASS|PHASE5_REAL" PHASE5_SPEC.md
rg -n "PHASE5_SPEC|每次只执行一个任务编号|真实 WeKnora|commit|不要 push" .github/skills/phase5-rag-wiki-qa-optimization/SKILL.md
git status --short
git status --ignored --short
```

For backend tasks, add focused checks such as:

```bash
backend/.venv/bin/python -m compileall backend/app agent knowledge_engine
backend/.venv/bin/python backend/scripts/check_phase5_fixture_contract.py
```

For frontend tasks, add:

```bash
cd frontend && npm run build
```

For final real PASS tasks, use the Phase 5 real scripts and reports defined in `PHASE5_SPEC.md`.

## Real PASS Rules

P5-G tasks are final gate tasks. They must use synthetic sanitized materials, but the tested ability must be real PA backend + PA Adapter + WeKnora.

Pass requirements:

```text
MOCK_MODE=false
KNOWLEDGE_BACKEND=weknora_api
source=weknora_api
RAG evidence comes from the current real retrieve run
Wiki evidence proves draft -> publish -> indexed/retrievable -> retrieve -> citation
knowledge_qa uses real evidence and traceable non-mock citations
24 RAG questions PASS
24 knowledge_qa questions PASS
frontend build and browser acceptance PASS
```

Required final report files:

```text
P5-G1 -> docs/PHASE5_REAL_ENV_PASS_REPORT.md
P5-G2 -> docs/PHASE5_REAL_UPLOAD_INDEX_PASS_REPORT.md
P5-G3 -> docs/PHASE5_REAL_RAG_24Q_PASS_REPORT.md
P5-G4 -> docs/PHASE5_REAL_WIKI_PASS_REPORT.md
P5-G5 -> docs/PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md
P5-G6 -> docs/PHASE5_REAL_FRONTEND_PASS_REPORT.md
P5-G7 -> docs/PHASE5_REAL_PASS_REPORT.md
```

Do not mark a P5-G task `[x]` unless its report exists and contains PASS.

## Test Corpus Rules

Use the Phase 4 synthetic sanitized corpus:

```text
backend/fixtures/phase4_rag_wiki_qa/
```

Never commit:

```text
real company names
real people
real customers
real projects
private addresses
real policy numbers
API keys
authorization secrets
uploads
databases
logs
unredacted prompts or provider outputs
```

## Auto Commit

After validation passes, automatically create one commit for the selected task.

Rules:

1. Commit only files related to the current task.
2. Include the task id when the task is an implementation task.
3. Use `docs:` for spec/planning/report tasks, `feat:` for product behavior, `test:` for smoke/fixtures, and `chore:` for acceptance/checker work.
4. Do not push unless the user explicitly asks.
5. If unrelated changes are present, leave them unstaged and mention them.
6. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "docs: complete P5-A2 failure map"
git commit -m "feat: complete P5-D1 retrieval scope"
git commit -m "test: complete P5-F1 real rag matrix script"
```

## Guardrails

- Do not implement multiple Phase 5 task ids in one turn.
- Do not mark tasks complete with only prose when a command or concrete artifact is required.
- Do not expose raw WeKnora fields in normal user-facing QA.
- Do not make debug controls part of the default knowledge QA page.
- Do not let fallback evidence use `source=weknora_api`.
- Do not create or commit real test documents.
- Do not mark P5-G final gate tasks complete with mock, fixture-only, static-only, local fallback, stale cache, old report evidence, or PARTIAL results.
- Do not push automatically.

## Report Format

```text
Completed:
- P5-...

Files changed:
- ...

Validation:
- command: result

Acceptance evidence:
- fixture / offline / local live / real WeKnora live / not applicable

Real capability evidence:
- source / source_type / evidence_id / chunk_id / wiki_page_id / trace_id

Risks:
- ...

Next:
- ...
```
