---
name: phase4-rag-wiki-qa
description: Planning, execution, and real-test reporting skill for PA AI Workbench phase 4 RAG, Wiki, knowledge_qa quality, test corpus, retrieval debug controls, citation/refusal validation, frontend Chinese terminology, and P4-G real capability reports. Use when the user asks to design, update, execute, or verify PHASE4_SPEC tasks without expanding into complex Agent workflows, export, permissions, approval, IM, graph, or long-term memory scope.
---

# Phase 4 RAG Wiki QA

This skill maintains and executes the fourth-stage source of truth:

```text
pa-ai-workbench/PHASE4_SPEC.md
```

## Core Rule

Treat `PHASE4_SPEC.md` as the phase 4 source of truth.

Phase 4 first segment direction:

```text
Synthetic sanitized test corpus
-> RAG / Wiki quality baseline
-> knowledge_qa single-workflow optimization
-> frontend Chinese terminology
-> debug controls separated from normal QA experience
-> real PA / WeKnora capability tests with improvement reports
```

Do not implement product code while using this skill unless the user explicitly asks to execute one numbered `PHASE4_SPEC.md` task.

## Read First

Always read:

```text
pa-ai-workbench/PHASE4_SPEC.md
```

Read for context when needed:

```text
pa-ai-workbench/PHASE3_SPEC.md
pa-ai-workbench/PRODUCT_SPEC.md
pa-ai-workbench/frontend/src/pages/RagDebugPage.tsx
pa-ai-workbench/frontend/src/pages/AnalysisPage.tsx
pa-ai-workbench/frontend/src/pages/WikiPage.tsx
pa-ai-workbench/backend/app/api/rag.py
pa-ai-workbench/backend/app/api/wiki.py
pa-ai-workbench/agent/skills/builtin/knowledge_qa.md
```

Read only the files relevant to the selected task.

## Responsibilities

- Maintain Phase 4 scope for RAG, Wiki, `knowledge_qa`, test corpus, and frontend Chinese terminology.
- Keep `policy_analysis` and `case_review` unchanged unless a future task explicitly brings them into scope.
- Keep official knowledge QA simple: question, optional retrieval source, answer, citations, and insufficient-evidence notice.
- Keep advanced retrieval controls on the RAG / Wiki debug page.
- Separate mock, fixture, local live, and real WeKnora live validation evidence.
- Ensure mock or fixture results are not counted as real RAG / Wiki acceptance.
- For P4-G real-test tasks, require `MOCK_MODE=false`, `KNOWLEDGE_BACKEND=weknora_api`, real PA Adapter evidence, and a report file with test results plus improvement recommendations.
- Preserve PA product boundaries: frontend and Agent must not call raw WeKnora APIs.
- Prevent scope creep into Word/PPT export, complex Agent orchestration, permissions, approval, IM, graph, and long-term memory.

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
Read PHASE4_SPEC
-> Identify one P4 task id
-> State task id, planned file edits, and validation method before editing
-> Implement only that task
-> Run validation
-> Update PHASE4_SPEC task status only if validation passes
-> Run git safety checks
-> Commit task-scoped files automatically
-> Report changes, validation, risks, and next recommended task
```

If the user asks for broad Phase 4 work without a task id, select the first unfinished task in `PHASE4_SPEC.md`.

If P4-A through P4-F are complete and P4-G exists, select the first unfinished P4-G task. Do not treat P4-F checklists or fixture/static checks as proof that P4-G real testing is complete.

## Validation

Choose the relevant subset:

```bash
test -f PHASE4_SPEC.md
rg -n "P4-A|P4-B|P4-C|P4-D|P4-E|P4-F" PHASE4_SPEC.md
rg -n "knowledge_qa|RAG|Wiki|中文化|mock|fixture|真实 WeKnora live" PHASE4_SPEC.md
rg -n "P4-G|真实测试|真实能力|改进建议|PHASE4_REAL" PHASE4_SPEC.md
rg -n "P4-G|real capability|报告|改进建议|MOCK_MODE=false" .github/skills/phase4-rag-wiki-qa/SKILL.md
git status --short
git status --ignored --short
```

For product-code tasks in later turns, add focused checks from the touched subsystem:

```bash
backend/.venv/bin/python -m compileall backend/app agent knowledge_engine
backend/.venv/bin/python backend/scripts/smoke_retrieval_quality_golden_m3.py
backend/.venv/bin/python backend/scripts/smoke_rag_debug_api_m2.py
backend/.venv/bin/python backend/scripts/smoke_wiki_l5.py
cd frontend && npm run build
```

For non-P4-G planning or fixture tasks, if real WeKnora is unavailable, use sanitized fixtures or local checks and clearly report that live acceptance was not run.

For P4-G, real WeKnora unavailability is a BLOCKED or PARTIAL result, not a PASS. Do not replace real capability testing with mock, fixture-only, static checks, old smoke output, keyword fallback, or cached evidence.

## Real Test Reports

P4-G tasks are real capability tests. They must use synthetic sanitized materials, but the tested ability must be real PA backend + PA Adapter + WeKnora.

P4-G pass requirements:

```text
MOCK_MODE=false
KNOWLEDGE_BACKEND=weknora_api
source is not mock or fixture-only
RAG evidence is from the current real retrieve run
Wiki evidence proves draft -> publish -> indexed/retrievable -> retrieve -> citation when applicable
knowledge_qa uses real evidence and traceable non-mock citations
```

Required report files:

```text
P4-G1 -> docs/PHASE4_REAL_ENV_PRECHECK_REPORT.md
P4-G2 -> docs/PHASE4_REAL_UPLOAD_INDEX_REPORT.md
P4-G3 -> docs/PHASE4_REAL_RAG_MATRIX_REPORT.md
P4-G4 -> docs/PHASE4_REAL_WIKI_REPORT.md
P4-G5 -> docs/PHASE4_REAL_KNOWLEDGE_QA_REPORT.md
P4-G6 -> docs/PHASE4_REAL_FRONTEND_REPORT.md
P4-G7 -> docs/PHASE4_REAL_TEST_SUMMARY.md
```

Do not mark a P4-G task `[x]` unless its report exists and includes:

```text
test time
environment
backend source
config summary without tokens
tested fixture documents / Wiki slug / P4Q ids
PASS / PARTIAL / FAIL / BLOCKED result
source, source_type, evidence_id, chunk_id, wiki_page_id, trace_id where applicable
failure or risk diagnosis
improvement recommendations grouped by RAG, Wiki, QA, frontend, and config/ops as applicable
```

## Test Corpus Rules

Use synthetic sanitized materials by default.

The corpus should test RAG / Wiki behavior first, not act as a realistic PA demo script. It may use policy, regulation, case, FAQ, Wiki-topic, distractor, and version-conflict document shapes.

Never commit:

```text
real company names
real people
real customers
real projects
private endpoints
real policy numbers
API keys
service tokens
uploads
databases
logs
unredacted prompts or outputs
```

## Auto Commit

After validation passes, automatically create one task-level commit.

Rules:

1. Commit only files related to the current task.
2. Include the task id in the commit message.
3. Use `docs:` for spec/planning, `feat:` for product behavior, `test:` for smoke/fixtures, and `chore:` for acceptance/checker work.
4. Do not push unless the user explicitly asks.
5. If unrelated changes are present, leave them unstaged and mention them.
6. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "docs: complete P4-A1 test corpus specification"
git commit -m "feat: complete P4-B1 rag debug parameter controls"
git commit -m "test: complete P4-C1 wiki retrieval loop smoke"
```

## Guardrails

- Do not implement multiple Phase 4 task ids in one turn unless the user explicitly requests a planning-only batch.
- Do not mark tasks complete with only prose when a command or concrete artifact is required.
- Do not expose raw WeKnora fields in normal user-facing QA.
- Do not make debug controls part of the default knowledge QA page.
- Do not let fallback evidence use `source=weknora_api`.
- Do not create or commit real test documents unless they are synthetic and sanitized.
- Do not mark P4-G real-test tasks complete with mock, fixture-only, static-only, local fallback, stale cache, or old smoke evidence.
- Do not mark P4-G complete if the report has no test result or no improvement recommendations.
- Do not push automatically.

## Report Format

```text
Completed:
- P4-...

Files changed:
- ...

Validation:
- command: result

Acceptance evidence:
- mock / fixture / local live / real WeKnora live / not applicable

Real capability evidence:
- source / source_type / evidence_id / chunk_id / wiki_page_id / trace_id

Risks:
- ...

Report file:
- docs/PHASE4_REAL_...

Improvement recommendations:
- RAG / Wiki / QA / frontend / config-ops

Blocked by:
- ...

Git:
- commit hash or blocked reason

Next task:
- ...
```
