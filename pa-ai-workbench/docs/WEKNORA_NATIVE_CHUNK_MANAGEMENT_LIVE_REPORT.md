# WeKnora Native Chunk Management Live Report

> Task: `WNX-P1-03`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-03` is PASS for safe internal production chunk management.

PA now exposes document-scoped chunk inspection and selected safe native chunk
operations through the PA BFF. The live PASS covers chunk list, chunk by-id,
enable/disable, delete with confirmation, PA audit events, and the Library
browser chunk detail workflow. It does not count chunk status as answer
citation evidence.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds chunk by-id, update/toggle, delete, and generated-question delete helpers through the shared native client. |
| PA Backend BFF | `GET /api/documents/{id}/chunks/{chunk_id}` | Reads native chunk detail only within the owning PA document scope. |
| PA Backend BFF | `PATCH /api/documents/{id}/chunks/{chunk_id}/enabled` | Requires confirmation, toggles native chunk enabled state, and records PA audit events. |
| PA Backend BFF | `DELETE /api/documents/{id}/chunks/{chunk_id}` | Requires confirmation, deletes the native chunk, and records PA audit events. |
| PA Backend BFF | `DELETE /api/documents/{id}/chunks/{chunk_id}/questions/{question_id}` | Available only with confirmation and existing generated-question metadata; not live-claimed in this smoke because no generated question data was produced. |
| PA Frontend Shell | Library page | Shows enabled state, generated-question count, chunk by-id refresh, enable/disable, delete confirmation, and chunk locator links. |
| Validation/Ops | `backend/scripts/check_weknora_native_chunk_management.py` | Runs live API/browser validation with temporary DB/uploads and sanitized output. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_chunk_management.py --browser
```

Sanitized output:

```text
WeKnora native chunk management
- decision: PASS
- evidence_type: live_api
- chunks: before=1 after_delete=0
- by_id: live
- toggle: disabled=live enabled=live audit=recorded
- delete: live-with-confirmation audit=recorded
- generated_questions: backlog_no_generated_question_data_in_smoke
- content_update: backlog_pending_reembed_safety
- search_by_chunk: backlog_native_route_not_found
- browser: Library DOM rendered chunk detail workflow
```

Evidence boundaries:

- The script starts temporary PA backend/frontend services, a temporary SQLite
  database, and a temporary upload directory.
- The document fixture is sanitized Markdown created by the smoke runner and is
  processed by live PA + live WeKnora.
- The mutation smoke operates on that temporary test document only.
- Toggle and delete require explicit PA confirmation and create
  `DocumentProcessingEvent` audit rows.
- The report does not print service tokens, environment-file values, private
  endpoints, raw upstream payloads, raw chunk text, vectors, screenshots,
  database files, upload paths, or provider payloads.

## Coverage Impact

The `Chunk management` group moves from `read-only` to `live-full` for safe
PA-scoped operations.

Current coverage becomes:

```text
7.75 / 15 = 51.7%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- Content rewrite remains backlog because the inspected native service updates
  chunk content directly and this task did not prove re-embedding safety.
- Generated-question delete remains backlog for PASS because the live smoke did
  not produce generated-question metadata to delete.
- Search-by-chunk remains backlog because no dedicated native route was found
  during this task's route/handler/service audit.
- Chunk enabled/disabled state is operational status only; it is not citation
  evidence unless tied to a real answer and retrievable source evidence.
