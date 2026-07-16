# WeKnora Native Document Lifecycle Live Report

> Task: `WNX-P1-02`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-02` is PASS for internal production document lifecycle.

PA now routes file, URL, and manual document ingestion through WeKnora native
knowledge APIs, keeps PA-owned business records and status events, exposes
native status spans, proxies preview/download through the PA BFF without
leaking credentials, and provides safe recovery controls in the Library page.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds URL/manual ingestion, spans, preview/download proxy reads, reparse, cancel, and delete helpers through the shared native client. |
| PA Backend BFF | `/api/documents/url`, `/api/documents/manual` | Creates PA business records and submits URL/manual ingestion to native WeKnora. |
| PA Backend BFF | `/api/documents/{id}/spans` | Returns sanitized native processing stages/spans metadata. |
| PA Backend BFF | `/api/documents/{id}/preview`, `/api/documents/{id}/download` | Proxies native file bytes without exposing service token or private upstream URL. |
| PA Backend BFF | `/api/documents/{id}/native-reparse`, `/cancel-processing`, `DELETE /api/documents/{id}` | Submits safe native lifecycle controls and records PA processing events. |
| PA Frontend Shell | Library page | Adds file/URL/manual ingestion modes, native preview/download, reparse, cancel, delete, spans summary, and chunk locator links. |
| Validation/Ops | `backend/scripts/check_weknora_native_document_lifecycle.py` | Runs live API/browser validation with temporary DB/uploads and sanitized output. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_document_lifecycle.py --browser
```

Sanitized output:

```text
WeKnora native document lifecycle
- decision: PASS
- evidence_type: live_api
- file: uploaded indexed chunks=1 preview=live download=live
- manual: ingestion=live
- url: ingestion=live
- lifecycle: reparse=live cancel=safe-control delete=live-submitted
- spans: source=weknora_api parse_status=completed current_stage=not_running
- status: final_file_status=indexed
- browser: Library DOM rendered lifecycle workflow
```

Evidence boundaries:

- The script starts a temporary PA backend, temporary Vite frontend, temporary
  SQLite database, and temporary upload directory.
- The file fixture is sanitized Markdown created by the smoke runner and is
  processed by live PA + live WeKnora.
- URL ingestion uses a unique public URL query to avoid duplicate-document
  collisions; no local/private URL is used.
- Manual ingestion sends sanitized Markdown content through the native manual
  knowledge endpoint; the report does not print the raw body.
- Preview/download validation checks byte availability only and does not print
  file contents.
- Delete validation confirms native delete task submission; it does not claim
  the asynchronous worker has completed physical deletion.
- Cancel validation is a safe control: when the document is already terminal,
  PA records a skipped safe-control event instead of issuing an unsafe or
  impossible native cancel.
- The script does not print service tokens, environment-file values, private endpoints,
  raw upstream payloads, raw file bodies, provider payloads, chunks, vectors,
  screenshots, database files, or upload paths.

## Coverage Impact

The `Document lifecycle` group moves from `live-partial` to `live-full`.

Current coverage becomes:

```text
7.00 / 15 = 46.7%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- Native delete is asynchronous; PA marks the lifecycle task as submitted and
  keeps status truthful until later refresh confirms final state.
- Cancel is only available while native processing is active; terminal-state
  documents show a safe skipped control rather than a false cancel PASS.
- Destructive chunk mutation remains outside this task and belongs to
  `WNX-P1-03`.
