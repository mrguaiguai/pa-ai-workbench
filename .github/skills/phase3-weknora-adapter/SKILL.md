---
name: phase3-weknora-adapter
description: Implementation skill for PA AI Workbench phase 3 WeKnora backend integration. Use when the user asks to execute PHASE3_SPEC WeKnora deployment, RAG adapter, Wiki adapter, runtime preflight, capability matrix, Document/Evidence/Citation/WikiPage mapping, or adapter contract-test tasks.
---

# Phase 3 WeKnora Adapter

This skill implements phase 3 tasks that connect PA AI Workbench to WeKnora backend RAG/Wiki capability.

For M2/M3, this skill also owns the WeKnora side of real runtime readiness:
DeepSeek KnowledgeQA, DashScope Embedding, KB `embedding_model_id`, vector dimension,
DocReader, Redis, vector store, capability reporting, and fallback boundaries.

## Core Rule

All WeKnora calls must pass through PA backend and PA KnowledgeBackend Adapter.

Allowed path:

```text
PA Frontend
-> PA FastAPI Backend
-> PA KnowledgeBackend Adapter
-> WeKnora Backend
```

Forbidden path:

```text
PA Frontend or PA Agent
-> raw WeKnora API / raw WeKnora response
```

## Read First

Read:

```text
docs/archive/legacy-product/PHASE3_SPEC.md
```

Then read only the relevant code/docs:

```text
packages/knowledge-engine/packages/knowledge-engine/knowledge_engine/backends/weknora_api_backend.py
packages/knowledge-engine/packages/knowledge-engine/knowledge_engine/base.py
packages/knowledge-engine/packages/knowledge-engine/knowledge_engine/schemas.py
apps/pa-api/app/api/
apps/pa-api/app/services/
docs/swagger.yaml
client/
internal/handler/
internal/application/service/
```

## Responsibilities

- Implement `weknora_api` backend as the M1 primary RAG/Wiki backend.
- Map WeKnora document status to PA status.
- Map WeKnora search results to PA `Evidence`.
- Map WeKnora Wiki responses to PA `WikiPage` / `WikiPageSummary`.
- Preserve PA API contracts for frontend.
- Add contract tests or smoke scripts for each adapter task.
- Keep mock backend available for local development, but do not use mock as M1 pass evidence.
- Add M2/M3 preflight gates for KnowledgeQA, Embedding, KB binding, DocReader, Redis, and vector store.
- Surface capability matrix data without leaking endpoints, tokens, or raw WeKnora internals.
- Keep extracted/mock fallback explicit and dev-only unless a fallback task is being validated.
- Verify multi-KB/workspace mapping does not mix document, wiki, or retrieve facts.

## Standard Output Shapes

Adapter output must use PA schemas:

```text
KnowledgeDocument
Evidence
WikiPage
WikiPageSummary
Citation metadata
DocumentStatus
```

Non-mock evidence must include:

```text
evidence_id
source_type: document_chunk | wiki_page
source=weknora_api
chunk_id or wiki_page_id
document_id or external_doc_id when source_type=document_chunk
title
text
score or score metadata
```

## Workflow

```text
Read PHASE3_SPEC
-> Pick one P3-M1/M2/M3 WeKnora or adapter task
-> Inspect WeKnora API/source for that capability
-> Plan files
-> Implement adapter mapping
-> Add focused validation
-> Run validation
-> Update task status only if validation passes
-> Run git safety checks
-> Commit task-scoped files automatically
-> Report
```

## Validation

Choose the relevant subset:

```bash
python -m compileall apps/pa-api/app packages/agent-runtime/agent packages/knowledge-engine/knowledge_engine
cd apps/pa-api && python scripts/smoke_weknora_connection.py
cd apps/pa-api && python scripts/smoke_weknora_rag_m1.py
cd apps/pa-api && python scripts/smoke_weknora_wiki_m1.py
cd apps/pa-api && python scripts/check_m2_preflight.py
cd apps/pa-api && python scripts/check_m2_release.py
cd apps/pa-api && python scripts/check_m3_local_product.py
git status --short
git status --ignored --short
```

If real WeKnora is unavailable, use recorded sanitized fixtures for contract tests and clearly report that live smoke was not run.

For M2/M3 release readiness, sanitized fixtures are not enough. Real gates must prove
DeepSeek KnowledgeQA, DashScope Embedding, KB `embedding_model_id`, vector dimension,
and live WeKnora RAG/Wiki behavior.

## Auto Commit

After validation passes, automatically create one task-level commit.

Rules:

1. Commit only files related to the current task.
2. Include the task id in the commit message.
3. Use `feat:` for adapter implementation, `docs:` for audit maps, and `test:` for smoke/contract tests.
4. Do not push unless the user explicitly asks.
5. If unrelated changes are present, leave them unstaged and mention them.
6. If sensitive files are present, stop before commit and report the blocker.

Examples:

```bash
git commit -m "docs: complete P3-M1-B1 weknora rag api map"
git commit -m "feat: complete P3-M1-B3 weknora retrieve adapter"
```

## Guardrails

- Do not hardcode WeKnora tokens, endpoints, workspace IDs, or real document paths.
- Do not log full prompts, full documents, long chunks, or secrets.
- Do not expose WeKnora raw errors directly to frontend.
- Do not make Agent workflows import WeKnora-specific client code.
- Do not mark M1 tasks complete with only mock/extracted backend evidence.
- Do not mark M2/M3 tasks complete if real model or embedding gates are missing.
- Do not let fallback evidence use `source=weknora_api`.
- Do not push automatically.

## Report Format

```text
Completed:
- P3-...

Files changed:
- ...

Validation:
- command: result

WeKnora capability:
- live / fixture / blocked

Risks:
- ...

Git:
- commit hash or blocked reason

Next task:
- ...
```
