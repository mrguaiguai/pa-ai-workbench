---
name: phase3-agent-designer
description: Agent workflow design and implementation skill for PA AI Workbench phase 3. Use when the user asks to execute PHASE3_SPEC Agent evidence workflow tasks, CitationChecker tasks, QA/policy/case prompts, Wiki draft workflows, or evidence-insufficient behavior.
---

# Phase 3 Agent Designer

This skill designs and implements PA Agent workflows for phase 3.

## Core Rule

Agent workflows must consume PA-standard evidence from `KnowledgeBackend`, not raw WeKnora responses.

M1 Agent scope is fixed evidence workflows:

```text
knowledge_qa
policy_analysis
case_review
wiki_draft_from_output
```

Do not introduce complex autonomous tool-calling, multi-agent supervisor, external actions, or code execution in M1.

## Read First

Read:

```text
pa-ai-workbench/PHASE3_SPEC.md
```

Then inspect relevant files:

```text
pa-ai-workbench/agent/orchestrator.py
pa-ai-workbench/agent/runtime.py
pa-ai-workbench/agent/agents/
pa-ai-workbench/agent/tools/
pa-ai-workbench/agent/schemas.py
pa-ai-workbench/knowledge_engine/schemas.py
pa-ai-workbench/backend/app/services/analysis_service.py
pa-ai-workbench/backend/app/services/generation_service.py
```

## Responsibilities

- Keep Agent workflows stable and evidence-grounded.
- Ensure QA, policy, and case workflows work with `source=weknora_api`.
- Strengthen CitationChecker and citation persistence.
- Generate Wiki drafts only from traceable outputs/citations.
- Return clear insufficient-evidence warnings.
- Keep ModelGateway as the only Chat model path.

## Evidence Rules

For non-mock citations:

```text
evidence_id required
source_type required
document_chunk requires chunk_id and document/external_doc id
wiki_page requires wiki_page_id or external wiki id
title and text required
```

If evidence is missing, the Agent must say evidence is insufficient instead of inventing facts.

## Workflow

```text
Read PHASE3_SPEC
-> Pick one P3-M1-D task
-> Inspect current workflow/tool code
-> Plan files
-> Implement the smallest workflow change
-> Add/adjust tests or smoke
-> Validate
-> Update task status only if validation passes
-> Run git safety checks
-> Commit task-scoped files automatically
-> Report
```

## Validation

Use relevant checks:

```bash
cd pa-ai-workbench && python -m compileall agent knowledge_engine backend/app
cd pa-ai-workbench/backend && python scripts/smoke_weknora_agent_m1.py
cd pa-ai-workbench/backend && python scripts/smoke_agent_l4.py
git status --short
git status --ignored --short
```

M1 WeKnora Agent pass requires non-mock citations. Existing L4 mock/extracted smoke is useful regression coverage but not M1 release proof.

## Auto Commit

After validation passes, automatically create one task-level commit.

Rules:

1. Commit only files related to the current Agent task.
2. Include the task id in the commit message.
3. Use `feat:` for workflow/tool changes, `test:` for smoke/validation-only tasks, and `docs:` for prompt/spec-only tasks.
4. Do not push unless the user explicitly asks.
5. If unrelated changes are present, leave them unstaged and mention them.
6. If sensitive files are present, stop before commit and report the blocker.

Example:

```bash
git commit -m "feat: complete P3-M1-D2 qa weknora evidence workflow"
```

## Guardrails

- Do not bypass `ModelGateway`.
- Do not bypass `RetrieverTool` / `KnowledgeBackend`.
- Do not store full sensitive source material in memory summaries.
- Do not weaken citation validation to make tests pass.
- Do not make prompts depend on WeKnora-specific field names.
- Do not push automatically.

## Report Format

```text
Completed:
- P3-...

Agent behavior:
- ...

Files changed:
- ...

Validation:
- command: result

Remaining risks:
- ...

Git:
- commit hash or blocked reason
```
