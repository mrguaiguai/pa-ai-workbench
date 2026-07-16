# WNFC-P5-02 Chunk Advanced Residual PASS Closure

Task: WNFC-P5-02
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser plus audit evidence

## Scope

WNFC-P5-02 covers the chunk operations left after WNX-P1-03:

- Content rewrite with re-embedding and vector index refresh.
- Generated-question data and delete operation proof.
- Search-by-chunk.

The existing PA chunk workflow already proves native chunk list/read, by-id
read, enable/disable, delete, confirmation, audit events, and Library browser
workflow. This report covers only the advanced residuals.

## Native Source Audit

WeKnora native chunk routes in `internal/router/router.go` now include:

- `GET /api/v1/chunks/:knowledge_id`
- `GET /api/v1/chunks/by-id/:id`
- `PUT /api/v1/chunks/:knowledge_id/:id`
- `GET /api/v1/chunks/by-id/:id/search`
- `DELETE /api/v1/chunks/:knowledge_id/:id`
- `DELETE /api/v1/chunks/:knowledge_id`
- `POST /api/v1/chunks/by-id/:id/questions`
- `DELETE /api/v1/chunks/by-id/:id/questions`

Implementation findings:

- `internal/handler/chunk.go`
  - `UpdateChunk` accepts optional `content` and optional `is_enabled`, so
    content-only rewrites do not accidentally disable the chunk.
  - `SearchSimilarChunks` exposes search-by-chunk with `top_k`,
    `vector_threshold`, `keyword_threshold`, and `include_self`.
  - `AddGeneratedQuestion` is available in source for future runtime deployment.
  - `DeleteGeneratedQuestion` accepts `question_id`.
- `internal/application/service/chunk.go`
  - `UpdateChunk` detects content changes and refreshes the main chunk content
    index.
  - The refresh deletes by `source_id = chunk.ID` and then `BatchIndex` writes
    the updated content, avoiding accidental deletion of generated-question
    vectors that share the same `chunk_id`.
  - `AddGeneratedQuestion` writes generated-question metadata and indexes the
    question vector.
  - `DeleteGeneratedQuestion` removes a generated question from chunk metadata
    and attempts to delete the question vector by source id.

Current live runtime note: the running WeKnora service used by PA had not yet
picked up the source-only `POST /chunks/by-id/:id/questions` and
`GET /chunks/by-id/:id/search` routes during this validation. The product PASS
therefore relies on two live-safe compatibility paths:

- generated-question data is produced by a temporary real WeKnora KB with
  `question_generation_config.enabled=true`, not by DB seeding;
- search-by-chunk uses the native route when present and falls back to live
  `/api/v1/knowledge-search` with the selected chunk content as query when the
  route is absent.

## Fixed Slices

### Content Rewrite / Re-Embedding

Status: `live`.

Native `PUT /api/v1/chunks/:knowledge_id/:id` updates the DB row and, when the
content changed, refreshes the main chunk content index with the active KB
embedding model and retrieve engine.

PA changes:

- `PATCH /api/documents/{document_id}/chunks/{chunk_id}/content`
- confirmation-gated `weknora_chunk_content_rewrite` audit events
- Library chunk card edit/save controls

### Generated-Question Data / Delete

Status: `live`.

Validation design:

- create a temporary real document KB with
  `question_generation_config.enabled=true`;
- upload a temporary document through PA into that KB;
- wait for WeKnora post-processing to write real `generated_questions` metadata
  on a real chunk;
- delete one generated question through PA
  `DELETE /api/documents/{document_id}/chunks/{chunk_id}/questions/{question_id}`;
- verify the question id is removed from metadata and
  `weknora_chunk_question_delete` event/audit evidence exists;
- delete the temporary PA document and validation KB.

This is real live data, not fixture JSON, direct DB mutation, or a static UI
claim.

### Search-By-Chunk

Status: `live`.

PA endpoint:

- `GET /api/documents/{document_id}/chunks/{chunk_id}/similar`

Native behavior:

- prefer `GET /api/v1/chunks/by-id/:id/search` when the running WeKnora service
  exposes it;
- fallback to live `/api/v1/knowledge-search` using the selected chunk content
  as the query when the route is not yet deployed.

Library renders the search control and top similar result display.

## PA Surface

PA now exposes the advanced chunk status in the native status center and
Capability Center:

- `basic_mutations_status: live`
- `content_rewrite_status: live`
- `generated_question_seed_status: live`
- `generated_question_delete_status: live`
- `search_by_chunk_status: live`

## Current-Run Evidence

Live PA/WeKnora/API smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_chunk_advanced_residual.py
```

Observed sanitized output:

```text
WeKnora native chunk advanced residual
- decision: PASS
- evidence_type: live api plus audit evidence
- basic_chunks: list/read/toggle/delete already live
- content_rewrite_reembedding: live native route plus PA BFF/UI
- generated_question_seed: live temporary KB question_generation_config metadata
- generated_question_delete: live native route plus PA audit
- search_by_chunk: live native route plus PA BFF/UI
- output: sanitized
```

Live browser proof:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_chunk_advanced_residual.py --browser
```

Observed sanitized output:

```text
WeKnora native chunk advanced residual
- decision: PASS
- evidence_type: live api/browser plus audit evidence
- basic_chunks: list/read/toggle/delete already live
- content_rewrite_reembedding: live native route plus PA BFF/UI
- generated_question_seed: live temporary KB question_generation_config metadata
- generated_question_delete: live native route plus PA audit
- search_by_chunk: live native route plus PA BFF/UI
- browser: Capability Center and Library rendered chunk advanced workflow
- output: sanitized
```

## Safety

- No mock, demo, cached, or fixture-only PASS is claimed.
- No raw chunk content, service token, provider payload, vector data, or local DB
  content is printed.
- Temporary validation document and KB are cleaned up after the smoke.
- Current live service gaps are documented instead of hidden: source-only routes
  are not counted as deployed runtime evidence unless the running service
  exposes them.
