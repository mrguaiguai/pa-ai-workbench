# Phase 3 M3 Backend Parity Matrix

This parity matrix is the product/testing view of the Phase 3 knowledge backend
boundary. It complements the capability policy in
`docs/PHASE3_M3_BACKEND_CAPABILITY_MATRIX.md` and uses the same status vocabulary:
`supported`, `partial`, `unsupported`, and `dev-only`.

The matrix is intentionally sanitized. It must not include service tokens,
endpoint URLs, workspace IDs, KB IDs, raw WeKnora responses, long excerpts, or
real document content.

## Capability Parity

| Capability | mock | weknora_api | extracted |
| --- | --- | --- | --- |
| document_upload | dev-only | supported | partial |
| document_status | dev-only | supported | partial |
| document_chunks | unsupported | supported | partial |
| rag_retrieve | dev-only | supported | partial |
| rag_debug | dev-only | supported | partial |
| wiki_search | dev-only | supported | partial |
| wiki_read | dev-only | supported | partial |
| wiki_create_update_publish | unsupported | supported | unsupported |
| citation_trace | unsupported | supported | partial |
| status_recovery | dev-only | supported | partial |
| real_data_source | unsupported | supported | unsupported |

## Product Parity

| Area | mock | weknora_api | extracted |
| --- | --- | --- | --- |
| Data fact source | Synthetic in-memory demo data. | WeKnora KB and Wiki through PA adapter. | Local parsed documents, local vectors, optional local Wiki store. |
| Release evidence | Never release evidence. | Release candidate after live gates pass. | Never release evidence. |
| Citation trace | unsupported; citations must not be called real. | supported for document chunks and Wiki pages. | partial; local trace only, not WeKnora trace. |
| Status recovery | dev-only synthetic status. | supported document/Wiki recovery through adapter-safe status checks. | partial local status only. |
| Wiki | dev-only search/read, no create/update/publish. | supported search/read/create/update/publish. | partial search/read when local store exists, no create/update/publish. |
| Retrieve debug | dev-only synthetic trace. | supported sanitized trace, no raw response or long excerpts. | partial local trace, no WeKnora parity guarantee. |
| Quality limits | Demo-only ranking and fixed fixtures. | Depends on live WeKnora, embedding, model, KB binding, and release checks. | Local fallback quality, no hybrid/rerank/live indexing guarantee. |

## Unsupported Behavior

Unsupported capability must not silently succeed:

- `mock.document_chunks` must fail or be absent instead of inventing chunk records.
- `mock.wiki_create_update_publish` must fail or be absent.
- `extracted.wiki_create_update_publish` must fail until a dedicated fallback task
  implements it.
- `real_data_source=unsupported` means the backend must not be counted as
  WeKnora release evidence.

Partial capability must be visibly partial:

- `extracted` may return local chunks, local retrieve results, and local Wiki
  summaries, but these must keep `source=extracted`.
- Partial citation trace can locate local evidence but must not use
  `source=weknora_api`.
- Partial debug output must remain sanitized and must not imply live WeKnora
  readiness.

Dev-only capability must stay out of release pass criteria:

- `mock` is useful for demos, UI development, and fixture checks.
- `mock` can exercise workflow shape but cannot satisfy pilot/release acceptance.
- Release/pilot/staging/intranet mode must not silently fallback to mock.

## Status Page Summary

The Home page runtime status displays a `Capability` card derived from
`GET /api/status.backend_capabilities.parity_summary`:

- selected/active backend;
- release eligibility or fail-closed/dev-only state;
- supported/partial/unsupported capability counts;
- data fact source;
- citation trace, Wiki publish, and retrieve debug status.

The UI summary is intentionally short. Full capability details remain in the
status API and this document.
