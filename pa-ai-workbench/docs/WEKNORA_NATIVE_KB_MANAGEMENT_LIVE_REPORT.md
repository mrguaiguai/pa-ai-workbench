# WeKnora Native KB Management Live Report

> Task: `WNX-P1-01`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-01` is PASS for internal production knowledge-base management.

PA now exposes a BFF-owned knowledge-base management path that can list native
WeKnora knowledge bases, read/validate the active KB, save a PA-owned active
selection snapshot, show safe tag metadata, and render the selection workflow
in the Library page. Unsafe write mutations remain backlog until confirmation
and audit-trail controls exist.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds safe `list_knowledge_bases` and `list_knowledge_base_tags` methods through the shared native client. |
| PA Backend BFF | `/api/knowledge-bases/native/overview` | Returns masked live KB overview, active selection, list/read/tag surfaces, and mutation backlog. |
| PA Backend BFF | `/api/knowledge-bases/native/active` | Validates the requested KB through native read, then saves a PA business snapshot. |
| PA Business DB | `knowledge_base_selection_snapshots` | Stores only workspace/KB selection snapshot and safe summary metadata; no chunks, vectors, credentials, or raw provider payloads. |
| Document Upload | `/api/documents` form field `knowledge_base_id` | Uploads can target the selected active KB; when omitted, PA falls back to the latest PA snapshot, then configured default. |
| PA Frontend Shell | Library page | Renders active KB, upload target selector, KB count, vector binding status, and active-selection action state. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_kb_management.py --browser
```

Sanitized output:

```text
WeKnora native KB management
- decision: PASS
- evidence_type: live_api
- api: list_total=1 active_snapshot=saved
- tags: status=live count=1
- mutations: create/update/delete/pin/tag write flows remain backlog
- browser: Library DOM rendered KB selector
```

Evidence boundaries:

- The script starts a temporary PA backend and temporary Vite frontend.
- The backend uses a temporary SQLite database, so validation proves PA DB
  snapshot behavior without modifying or committing the local production DB.
- The script calls real PA BFF endpoints backed by real WeKnora native APIs.
- Headless Chrome reads the rendered Library DOM through Chrome DevTools
  Protocol and checks the KB selector text.
- The script does not print KB ids, service tokens, private endpoints, raw
  upstream payloads, `.env` values, chunks, vectors, or provider data.

## Mutation Boundary

Native routes exist for create, update, delete, pin, and tag mutations, but PA
does not expose production-destructive controls in this task. The BFF and
report keep these as backlog:

- KB create/update/delete requires confirmation and audit trail.
- Pin/tag mutations require a dedicated confirmation UX.
- PA must not mutate production KBs from a status-only surface.

This is a safe blocker/backlog boundary, not a hidden PASS.

## Coverage Impact

The `Workspace/knowledge-base management` group moves from `live-partial`
to `live-full` because list/read, active selection, PA DB snapshot, upload
targeting, safe tag visibility, browser workflow, and explicit mutation backlog
are now validated in the current WNX run.

Current coverage becomes:

```text
6.50 / 15 = 43.3%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- Destructive KB mutations remain backlog until a confirmation and audit-trail
  design is added.
- This task validates Library selection and upload target propagation, not full
  document lifecycle recovery. That remains `WNX-P1-02`.
- The status center can summarize the new BFF endpoint, but final internal
  production coverage must still be recomputed by `WNX-P3-02`.
