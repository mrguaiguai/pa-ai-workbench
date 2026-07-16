# Phase 3 M3 Backend Capability Matrix

This document defines the backend capability and fallback boundary before M3 adds
more fallback implementations. It is intentionally policy-only: it must not
contain WeKnora endpoints, service tokens, workspace IDs, KB IDs, document paths,
or raw WeKnora responses.

## Capability Status

| Status | Meaning |
| --- | --- |
| supported | The backend can serve the PA contract as release evidence. |
| partial | The backend can serve a local or fixture path but is not release evidence. |
| unsupported | The backend must fail or report unavailable for this capability. |
| dev-only | The backend is allowed for local/demo/test use and must not count as release evidence. |

## Matrix

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

## Fallback Decision Table

| Mode | Selected backend | Backend availability | Decision | Release evidence |
| --- | --- | --- | --- | --- |
| dev/test with `MOCK_MODE=true` | mock | available | allow explicit mock | no |
| dev/test with `MOCK_MODE=true` | weknora_api | configured | use WeKnora | yes only if live gates pass |
| dev/test with `MOCK_MODE=true` | weknora_api | missing config/unavailable | may fallback to mock for local continuity, report as mock/dev-only | no |
| dev/test with `MOCK_MODE=true` | extracted | explicitly selected | use extracted | no |
| dev/test with `MOCK_MODE=true` | unknown | unsupported | may fallback to mock for local continuity, report as mock/dev-only | no |
| release/pilot/staging/intranet or `MOCK_MODE=false` | weknora_api | configured and healthy | use WeKnora | yes only if live gates pass |
| release/pilot/staging/intranet or `MOCK_MODE=false` | weknora_api | missing config/unavailable | fail closed; do not fallback mock | no |
| release/pilot/staging/intranet or `MOCK_MODE=false` | unknown | unsupported | fail closed; do not fallback mock | no |
| release/pilot/staging/intranet or `MOCK_MODE=false` | mock | explicitly selected | report mock/dev-only and not release eligible | no |
| release/pilot/staging/intranet or `MOCK_MODE=false` | extracted | explicitly selected | report partial/extracted and not release eligible | no |

## Citation Trace Rule

Real citations require a stable trace. A citation may be marked as
`source=weknora_api` only when it includes enough trace data to locate the source:

- `evidence_id`;
- `source_type`;
- `chunk_id` plus `document_id` or `external_doc_id` for document chunks;
- `wiki_page_id` for wiki pages.

If any required trace is missing, the system must fail closed or mark the result
as non-real fallback evidence. It must not silently relabel mock, extracted,
keyword-only, or partial evidence as WeKnora release evidence.

## Status API

`GET /api/status` exposes a sanitized `backend_capabilities` object:

- `active_backend`, `selected_backend`, `environment`, `strict_fallback_mode`;
- per-backend `matrix` and active-backend `capabilities`;
- `fallback_policy`, including `silent_mock_fallback_allowed`,
  `extracted_fallback=explicit-only`, and
  `citation_trace_required_for_real_citation=true`;
- `release_eligible` for the selected backend.

The status payload must not expose service tokens, endpoint URLs, workspace IDs,
KB IDs, raw WeKnora health bodies, long excerpts, or real document content.
