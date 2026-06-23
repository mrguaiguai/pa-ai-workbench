# WeKnora-First Document Native Path Live Report

> Task: `WF-P0-02`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live PA service/API + live WeKnora native document ingestion; fixture smoke is defensive code-path evidence only.

## Scope

`WF-P0-02` validates the smallest real document path where PA keeps business records and product status, while WeKnora owns native document ingestion, parsing, chunking, embedding, indexing, status, and chunk preview.

This report does not claim fixture-only PASS. The live PASS depends on current PA runtime configuration using `KNOWLEDGE_BACKEND=weknora_api`, non-mock model/embedding configuration, and a real WeKnora knowledge base.

## Code Path Alignment

| PA surface | WF-P0-02 behavior | Native source of truth | Decision |
| --- | --- | --- | --- |
| `create_document` | Saves PA document record, uploads the stored file to WeKnora, persists `external_doc_id`, `knowledge_backend=weknora_api`, and native status. | WeKnora `/api/v1/knowledge-bases/{kb_id}/knowledge/file` through `WeKnoraApiBackend.upload_document`. | PASS live. |
| `parse_document_file` | For WeKnora documents, refreshes native status and returns metadata instead of running PA local parser. | WeKnora document status API. | PASS fixture-guarded. |
| `index_document_chunks` | For WeKnora documents, refreshes native status and counts native chunks instead of PA chunking/embedding/vector indexing. | WeKnora status and chunks APIs. | PASS fixture-guarded and live chunk preview verified. |
| `reindex_document_chunks` / `retry_index_document` | For WeKnora documents, routes recovery to native retry/status refresh instead of rebuilding PA local vectors. | WeKnora native upload/status path using the existing PA record. | PASS fixture-guarded. |
| Document API `/index`, `/reindex`, `/retry-index` | Returns WeKnora-specific messages so the UI/API does not claim PA-local chunk/vector indexing. | PA adapter status plus WeKnora native status. | PASS code-path validated. |

## Live Evidence

### Native Document Service Smoke

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_document_native_live.py
```

Result:

```text
WeKnora native document live smoke passed
- base URL: http://127.0.0.1:8080
- external doc id: e3fa4420-c083-4a2d-b47e-a3c540e6f3fb
- indexed status: indexed
- native chunk count: 1
- upload/status events: 4
```

What this proves:

- PA document service uploaded a sanitized temporary Markdown file into live WeKnora.
- PA persisted the WeKnora native `external_doc_id`.
- WeKnora reached `indexed`.
- PA read chunk preview through the native chunks path.
- PA recorded `weknora_upload` and `weknora_status` events.

The input document was synthetic and contained no private data. The smoke does not print raw document body text, provider payloads, API keys, or service tokens.

### WeKnora Connection Smoke

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_connection.py
```

Result summary:

- Connection PASS against `http://127.0.0.1:8080`.
- Auth PASS for the configured PA smoke account.
- Workspace/knowledge-base binding PASS for the configured PA M1 smoke KB.

### PA Runtime Status

Commands:

```bash
curl -s http://127.0.0.1:8000/api/status
curl -s http://127.0.0.1:8000/api/model/status
```

Result summary:

- `/api/status` reports `knowledge_backend=weknora_api`, `mock_mode=false`, and WeKnora `status=connected`.
- `/api/model/status` reports non-mock chat and embedding providers configured.
- Status output uses configured booleans only and does not expose actual keys.

### Current RAG Adapter Smoke

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_rag_m1.py
```

Result summary:

- Live WeKnora knowledge base id: `29adf20a-91db-45b5-9df1-6c608f802e8d`.
- Live external document id: `a3674886-d5f2-4a87-8f31-bd5bdf09d476`.
- Indexed status: `indexed`.
- Evidence id: `document_chunk:08231ceb-cb1a-4a69-b9de-cb0b9ed11049`.
- Chunk id: `08231ceb-cb1a-4a69-b9de-cb0b9ed11049`.
- Evidence source: `weknora_api`; source type: `document_chunk`.

This is supporting evidence that the current PA adapter can retrieve live WeKnora document chunk evidence. The primary `WF-P0-02` PASS comes from the document service native upload/status/chunk smoke above.

## Fixture Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_document_native_path.py
```

Result:

```text
WeKnora document native path smoke passed (fixture: parse/index avoid local pipeline, reindex uses native retry)
```

This fixture smoke deliberately monkeypatches local parser, embedding, and vector-store paths to raise if called. It proves the WeKnora document code path avoids PA-local parsing, chunking, embedding, and vector indexing when `knowledge_backend=weknora_api`.

This fixture evidence is not live capability PASS by itself. It is a regression guard that supports the live evidence.

## Blocked And Backlog Decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Core PA document upload/status/index path | Completed | Live PA service uploaded to WeKnora, persisted native id, reached `indexed`, and read native chunks. |
| PA-local parser/chunker/vector path for WeKnora documents | Completed as avoided path | Fixture guard fails if the local pipeline is accidentally called. |
| Library frontend browser check | Backlog for this task | No frontend files changed; API/service messages now truthfully avoid claiming PA-local indexing. Browser polish belongs with `WF-P1-04` unless `WF-P0-04` status surfaces require it. |
| Optional native admin UX for chunk/status details | Backlog | Core live document path is proven; deeper native admin controls are outside this P0 slice. |

## PASS Statement

`WF-P0-02` is PASS with live PA + live WeKnora evidence for the document native path. The PASS is not fixture-only: the live smoke exercised PA document service upload, native WeKnora indexing, persisted `external_doc_id`, native status refresh, and native chunk preview.

Fixture evidence is used only to prove PA no longer runs local parser/chunker/embedding/vector indexing for WeKnora documents.
