---
name: phase2-rag-auditor
description: Audit WeKnora RAG/Wiki source code for PA AI Workbench phase 2. Use when the user asks to execute G1, audit WeKnora RAG source, plan extraction, or create the source map.
---

# Phase 2 RAG Auditor

This skill executes the source-audit part of PA AI Workbench v0.2.

## Core Rule

Always treat `pa-ai-workbench/PHASE2_SPEC.md` as the source of truth.

Do not write product implementation code while auditing.

Do not modify WeKnora source files outside `pa-ai-workbench/`.

## Scope

Read WeKnora source modules listed in `PHASE2_SPEC.md`, especially:

```text
internal/infrastructure/chunker/
internal/application/service/retriever/
internal/application/service/chat_pipeline/
internal/application/service/knowledge_process.go
internal/application/service/knowledge_post_process.go
internal/application/service/knowledgebase_search*.go
internal/application/service/wiki_ingest*.go
internal/application/service/wiki_page.go
internal/types/chunk.go
internal/types/retriever.go
internal/types/retrieval_config.go
internal/types/wiki_page.go
internal/models/embedding/
```

## Required Output

Create or update:

```text
pa-ai-workbench/docs/WEKNORA_RAG_SOURCE_MAP.md
```

The source map must include:

- Source module path.
- Responsibility.
- Key structs/functions/interfaces.
- Dependencies.
- Extraction decision: reference / Python rewrite / service wrapper / skip.
- Target PA Workbench module.
- Risks and notes.
- License / attribution note.

## Pipeline

```text
Read PHASE2_SPEC
-> Inspect source modules
-> Build module map
-> Decide extraction strategy
-> Write source map
-> Validate file exists and is useful
-> Update G1 status in PHASE2_SPEC only if complete
-> Report
```

## Validation

Run:

```bash
test -f pa-ai-workbench/docs/WEKNORA_RAG_SOURCE_MAP.md
rg -n "Chunker|Retriever|Wiki|Embedding|Citation|Extraction decision" pa-ai-workbench/docs/WEKNORA_RAG_SOURCE_MAP.md
git status --short
```

## Report Format

```text
Completed: G1 WeKnora RAG/Wiki source audit
Files changed:
- ...
Audit highlights:
- ...
Validation:
- ...
Next task:
- G2 ...
```

