# Phase 3 M3 Wiki Fallback Sync Strategy

P3-M3-B3 defines the minimum Wiki fallback behavior for explicit
`KNOWLEDGE_BACKEND=extracted`. The fallback is local-only and must never be
reported as WeKnora-retrievable evidence.

## Rules

- Local fallback Wiki pages use `source=extracted` at the KnowledgeBackend
  Adapter boundary.
- PA DB Wiki pages created while the selected backend is `extracted` keep local
  product state and expose `fallback_backend=extracted`.
- Draft pages show `wiki_state=draft` and `wiki_retrievable=false`.
- Published local fallback pages show `wiki_state=sync_pending` and
  `wiki_retrievable=false`.
- `index_wiki_page()` for extracted fallback records local sync state only; it
  must not claim WeKnora indexing or retrievability.
- Conflict tracking is explicit through `sync_conflict_status`; the default is
  `none` until a later sync task detects a conflict.

## Status Fields

| Field | Local fallback value |
| --- | --- |
| `fallback_backend` | `extracted` |
| `fallback_explicit` | `true` |
| `local_wiki_fallback` | `true` for PA DB Wiki fallback |
| `weknora_sync_status` | `not_synced` for drafts, `pending` after publish/update |
| `weknora_index_status` | `not_synced` |
| `weknora_retrievable` | `false` |
| `wiki_state` | `draft` or `sync_pending` |
| `sync_conflict_status` | `none` |

## Non-goals

This task does not implement live WeKnora reconciliation, conflict resolution,
or background sync workers. Those remain separate tasks. The purpose here is to
keep local fallback useful while preserving clear UI and Agent boundaries.
