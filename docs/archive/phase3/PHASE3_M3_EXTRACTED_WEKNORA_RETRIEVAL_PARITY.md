# Phase 3 M3 Extracted / WeKnora Retrieval Parity

This report records the P3-M3-B2 comparison contract for Python `extracted`
fallback retrieval versus the WeKnora API adapter. It is intentionally based on
sanitized offline fixtures. It does not use live WeKnora credentials, endpoint
URLs, workspace IDs, KB IDs, raw responses, long excerpts, or real PA documents.

## Scope

The regression fixture compares:

- chunk boundaries from local Python parsing/chunking and fixture WeKnora chunk
  previews;
- `top_k` behavior for key queries;
- `source_type` normalization for `document_chunk` evidence;
- score semantics, without assuming scores are on the same scale;
- citation trace fields required by Agent, CitationChecker, and PA API schemas.

## Fixture Result

| Check | extracted | weknora_api fixture | Expected |
| --- | --- | --- | --- |
| data source label | `source=extracted` | `source=weknora_api` | Different and explicit |
| chunk boundaries | local paragraph windows | fixture backend chunk spans | Difference recorded |
| ranking | local vector similarity | fixture WeKnora backend score | Difference recorded, not exact-match asserted |
| score semantics | `local_vector_cosine` | `weknora_rrf_or_backend_score` | Different and explicit |
| citation trace | local document/chunk IDs | fixture WeKnora document/chunk IDs | Both traceable |
| key queries | return evidence | return evidence | Both non-empty |

## Acceptance Notes

P3-M3-B2 does not require extracted fallback to match WeKnora ranking or chunk
boundaries. WeKnora ranking can change with backend settings, rerankers, and KB
state. The durable contract is that differences are quantified and key queries
still return traceable PA `Evidence`.

The smoke script writes an in-memory parity report and asserts:

- extracted fallback never reports `source=weknora_api`;
- WeKnora fixture evidence always reports `source=weknora_api`;
- both backends respect requested `top_k`;
- both backends return `evidence_id`, `source_type`, and citation metadata;
- chunk-count and boundary deltas are recorded;
- score semantics are present for every returned evidence item.

## Live Comparison

Live comparison is optional for this task and was not required for the offline
contract. If live WeKnora is used later, keep the same comparison fields and do
not add real document text, endpoints, tokens, workspace IDs, KB IDs, or raw
responses to this report.
