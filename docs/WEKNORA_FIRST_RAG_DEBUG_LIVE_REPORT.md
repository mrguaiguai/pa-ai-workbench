# WeKnora-First RAG Debug Live Report

> Task: `WF-P0-03`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live PA RAG debug API handler path + live WeKnora native search.

## Scope

`WF-P0-03` keeps PA RAG debug as a thin WeKnora-first adapter. PA owns the debug response shape, traceability, redaction, warnings, rank display, and evidence contract. WeKnora owns native retrieval through `/api/v1/knowledge-search`.

This is live evidence, not fixture-only proof. Fixture smokes are regression guards for redaction and parameter validation only.

## Native Source And PA Mapping

| Area | Native / PA source | Finding | Decision |
| --- | --- | --- | --- |
| Native route | `internal/router/router.go` | `POST /api/v1/knowledge-search` routes to `SearchKnowledge`. | Use as PA RAG debug retrieval source. |
| Native search types | `internal/types/search.go`, `internal/types/retriever.go` | `SearchResult` carries `id`, `knowledge_id`, `knowledge_base_id`, `score`, `match_type`, chunk offsets, matched content, metadata, and retriever score semantics. | Map to PA `Evidence` and debug metadata. |
| Native retrieval service | `internal/application/service/knowledgebase_search*.go` | Hybrid search fans out across stores, fuses/deduplicates results, and preserves result order before enrichment. | Preserve native rank separately from PA display rank. |
| PA adapter | `knowledge_engine/backends/weknora_api_backend.py` | PA calls `/api/v1/knowledge-search` and maps native results to `source=weknora_api`, `source_type`, `evidence_id`, `chunk_id`, `external_doc_id`, score, and metadata. | Added native endpoint/rank metadata for debug traceability. |
| PA debug API | `backend/app/api/rag.py` | PA returns redacted debug items with `rank`, `source_type`, `evidence_id`, ids, score, and safe metadata. | Added native endpoint/rank/evidence metadata to allowlist and normalized `requested_source_type`. |

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_debug_live.py
```

Result:

```text
WeKnora RAG debug live smoke passed
- base URL: http://127.0.0.1:8080
- knowledge base: 29adf20a-91db-45b5-9df1-6c608f802e8d
- external doc id: 257afb30-83f8-4f32-ba4e-a216d319a7fd
- indexed status: indexed
- trace id: d052f2baf9464df49bc376bdd8de6737
- evidence id: document_chunk:7caecfe8-619e-44e2-930d-814fb3e29fb7
- chunk id: 7caecfe8-619e-44e2-930d-814fb3e29fb7
- source: weknora_api
- source type: document_chunk
- rank: 1
- native rank: 1
- debug trace stages: hybrid,rerank,threshold
```

What this proves:

- A current sanitized document was uploaded to live WeKnora and reached `indexed`.
- PA RAG debug retrieved evidence scoped to the current `external_doc_id`.
- Debug evidence preserved `source=weknora_api`, `source_type=document_chunk`, `evidence_id`, native `chunk_id`, and `external_doc_id`.
- PA debug output includes display `rank`, native result rank, and trace stages.
- The debug path exposes safe metadata only and does not print tokens, provider payloads, raw document body text, or raw native response bodies.

## Fixture Evidence

Commands:

```bash
backend/.venv/bin/python backend/scripts/smoke_rag_debug_api_m2.py
backend/.venv/bin/python backend/scripts/smoke_rag_debug_params_m2.py
```

Result summary:

- RAG debug API fixture smoke passed.
- RAG debug parameter fixture smoke passed.
- Fixture coverage verifies redaction, source type normalization, safe metadata allowlist, validation rejection for unsupported filters, and no raw response/token leakage.

Fixture evidence is not live capability PASS. It only supports the live debug evidence above.

## Current Contract

| Field | WF-P0-03 expectation | Live result |
| --- | --- | --- |
| `source` | `weknora_api` | PASS |
| `source_type` | `document_chunk` or `wiki_page`; this live slice validates `document_chunk`. | PASS |
| `evidence_id` | Required for PA citation/debug traceability. | PASS |
| Native ids | `external_doc_id` and `chunk_id` when source type is `document_chunk`. | PASS |
| `rank` | PA display rank after PA filtering/ranking. | PASS |
| Native rank | Native WeKnora result order before PA filtering/ranking. | PASS |
| `trace` | Debug stages show hybrid/rerank/threshold posture. | PASS |
| `partial` / `blocked` labels | Required when native search or fields are unavailable. | Not triggered in the live PASS run. |

## Blocked And Backlog Decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Core PA RAG debug -> WeKnora native search | Completed | Live debug smoke proves current PA debug path calls native search and returns traceable evidence. |
| RAG debug redaction and parameter validation | Completed as fixture guard | Existing fixture smokes now match the current handler path and protect safe output behavior. |
| Advanced hybrid/rerank controls | Backlog for this task | Trace stages are visible; deeper native parameter semantics remain reserved unless a later task scopes them. |
| Browser RAG debug page | Backlog for this task | No frontend files changed; browser validation belongs to frontend/status polish unless the UI is edited. |

## PASS Statement

`WF-P0-03` is PASS with live PA + live WeKnora evidence. The current run used PA's RAG debug API handler path, real WeKnora native `/api/v1/knowledge-search`, current uploaded evidence, and non-mock runtime posture. This PASS is not fixture-only and does not rely on old reports, cached evidence ids, mock backend, or static UI.
