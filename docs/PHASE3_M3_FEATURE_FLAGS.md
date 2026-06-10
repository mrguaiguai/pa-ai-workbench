# Phase 3 M3 Backend Feature Flags

This document defines the standard capability schema used by UI and Agent code.
It is derived from the backend capability matrix and must not contain endpoint
URLs, tokens, workspace IDs, KB IDs, raw WeKnora responses, long excerpts, or
real document content.

## API

`GET /api/capabilities` returns the same sanitized object embedded in
`GET /api/status.backend_capabilities`.

Required top-level fields:

| Field | Purpose |
| --- | --- |
| `active_backend` | Backend used for capability decisions. |
| `selected_backend` | Configured backend value after normalization. |
| `capabilities` | Capability-to-status map. |
| `matrix` | Full mock / weknora_api / extracted matrix. |
| `parity_summary` | Short status page summary. |
| `feature_flags` | UI and Agent gating schema. |

## Feature Flag Schema

`feature_flags.schema_version` is `p3-m3-a3`.

UI flags:

| Flag | Source capability | Rule |
| --- | --- | --- |
| `can_upload_documents` | `document_upload` | true when not `unsupported`. |
| `can_view_document_chunks` | `document_chunks` | true when not `unsupported`. |
| `can_retrieve` | `rag_retrieve` | true when not `unsupported`. |
| `can_debug_retrieve` | `rag_debug` | true when not `unsupported`. |
| `can_search_wiki` | `wiki_search` | true when not `unsupported`. |
| `can_read_wiki` | `wiki_read` | true when not `unsupported`. |
| `can_create_update_publish_wiki` | `wiki_create_update_publish` | true only when `supported`. |
| `can_recover_status` | `status_recovery` | true when not `unsupported`. |
| `can_use_real_citations` | `citation_trace` + `real_data_source` | true only for release-eligible real source. |
| `can_count_release_evidence` | `real_data_source` | true only for release-eligible real source. |

Agent flags:

| Flag | Rule |
| --- | --- |
| `can_retrieve` | Agent retrieve tool may call backend retrieve. |
| `can_read_wiki` | Agent Wiki read tool may call backend Wiki read. |
| `can_publish_wiki` | Agent may publish Wiki only when the capability is `supported`. |
| `must_not_call` | List of unsupported capabilities that Agent tools must block. |
| `requires_citation_trace_for_real_citation` | Real citations require stable trace fields. |

## Probes

`feature_flags.probes` contains one entry per capability:

| Probe field | Meaning |
| --- | --- |
| `status` | `supported`, `partial`, `unsupported`, or `dev-only`. |
| `available` | false only for `unsupported`. |
| `release_evidence` | true only for supported WeKnora release candidates. |
| `ui_policy` | `show`, `show_with_badge`, `disable_write_action`, or `hide_or_disable`. |
| `agent_policy` | `allow`, `allow_non_release`, `fallback_only`, or `block`. |

## UI Usage

Frontend pages must gate actions by `feature_flags.ui`, not backend names.

- RAG debug submit is enabled only when `can_debug_retrieve=true`.
- Wiki create/edit/save/publish is enabled only when
  `can_create_update_publish_wiki=true`.
- Wiki status refresh/recovery is enabled only when `can_recover_status=true`.
- Unsupported actions must be hidden or disabled, never sent and then treated as
  success.

## Agent Usage

Agent tools must gate calls by `feature_flags.agent` or the shared
`AgentCapabilityGuard`.

- Retrieve requires `rag_retrieve` to be available.
- Wiki read requires `wiki_read` to be available.
- Unsupported capabilities raise `AgentCapabilityError` before calling the
  backend.
- Partial/dev-only results can support local workflows but cannot be counted as
  release evidence or real WeKnora citations.
