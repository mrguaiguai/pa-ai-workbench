# WNFC-P1-02 Data Source Workflow Evidence

Date: 2026-06-24

Task: `WNFC-P1-02: Data-source resources, validation, sync, logs, delete`

Decision: PASS

Evidence type: `live_api+browser_current_run+audit`

## Scope

This task makes the existing native data-source operational workflow usable
through PA for resources, validation, sync logs, sync, pause, resume, delete,
browser visibility, and audit records.

It does not complete `WNFC-P1-01` credential-bearing connector setup and does
not substitute RSS for a real Notion/Yuque/Feishu credential connector. It also
does not complete `WNFC-P1-03` RAG evidence from synced external source content.
The WNFC aggregate score therefore remains `11.50 / 14 = 82.1%`.

## Native Source Audit

No WeKnora Go source change was required. The existing native routes already
cover the required P1-02 paths:

- `GET /api/v1/datasource/types`
- `GET /api/v1/datasource`
- `GET /api/v1/datasource/:id`
- `DELETE /api/v1/datasource/:id`
- `POST /api/v1/datasource/:id/validate`
- `GET /api/v1/datasource/:id/resources`
- `GET /api/v1/datasource/:id/logs`
- `POST /api/v1/datasource/:id/sync`
- `POST /api/v1/datasource/:id/pause`
- `POST /api/v1/datasource/:id/resume`

Audited native code surfaces:

- `internal/router/router.go`
- `internal/handler/datasource.go`
- `internal/application/service/datasource_service.go`

PA-first was sufficient because WeKnora already exposes the data-source API
surface needed for this task.

## PA Changes

Backend adapter:

- Added `WeKnoraApiBackend.delete_data_source(...)`.
- Kept public responses masked and summarized.

BFF/service:

- Added confirmation-gated delete by safe index.
- Connected sync, pause, resume, and delete to `NativeMutationAudit`.
- Added `delete_control` and more precise `mutations=partial` surfaces.
- Kept raw native ids, config, credentials, raw resources, raw logs, private
  endpoints, and feed URL out of public PA responses.

API:

- Added `DELETE /api/data-sources/native/sources/by-index/{data_source_index}`.
- Added DB session dependency to sync, pause, resume, and delete so audit
  records are persisted.

Frontend:

- Added data-source detail/action client methods.
- Added a Capability Center `Native data source ops` panel with masked
  overview/detail status, resources, validation, sync logs, sync control,
  delete control, and audit-id feedback.
- Added sync, pause, resume, and delete controls through PA BFF only.

Validation:

- Extended `backend/scripts/check_weknora_native_data_source_management.py`
  with `--wnfc-p1-02`.
- The script creates a temporary RSS data source, validates it through PA safe
  indexes, performs confirmed sync/pause/resume/delete, checks native audit
  events, verifies the temporary source is removed, and renders browser DOM
  evidence.

## Current-Run Evidence

Python compile:

```text
backend/.venv/bin/python -m py_compile knowledge_engine/backends/weknora_api_backend.py backend/app/services/data_source_service.py backend/app/api/data_source.py backend/scripts/check_weknora_native_data_source_management.py
PASS
```

Frontend typecheck:

```text
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node ./node_modules/typescript/bin/tsc --noEmit
PASS
```

Live API and browser smoke:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_management.py --wnfc-p1-02 --browser

WeKnora native data source connector management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- coverage_state: live-partial
- connector_types: status=live count=12
- data_sources: status=live count=2 credentials_configured=0
- connector_read: live detail=live
- resources: blocked
- validation: blocked
- sync_control: overview=blocked blocked_path=blocked confirmed_path=live
- pause_resume: pause=live resume=live
- delete: live
- audit: data_source mutation events recorded
- mutations: partial
- browser: Capability Center rendered data source connector readiness
```

Notes on the `resources` and `validation` lines above:

- Overview-level resources/validation remain blocked by design because generic
  connector probes can reveal private external resource names.
- The smoke script asserts the selected temporary RSS detail path has live RSS
  resources and live RSS validation with connected status.

Acceptance harness:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_acceptance.py

WNFC native full completion acceptance check passed
- evidence_type: checker_execution
- mode: in-progress
- reports checked: 5
- task rows: 23
- completed tasks: 4
- unfinished tasks: 19
- current score: 11.50/14 = 82.1%
- target score: 14.00/14 = 100.0%
- web_search: excluded
- final_ready: false
- browser_hooks: WNFC-P6-01 desktop/mobile matrix and WNFC-P6-02 final report hooks present
```

Diff whitespace check:

```text
git diff --check
PASS
```

## Audit Proof

The WNFC smoke checks the persisted audit log at:

```text
GET /api/native-audit/events?capability=data_source&limit=20
```

Required successful operations:

- `weknora_data_source_sync`
- `weknora_data_source_pause`
- `weknora_data_source_resume`
- `weknora_data_source_delete`

Each mutation is confirmation-gated and records a safe target id in the
`data_source_index:{n}` form.

## Browser Proof

The smoke starts the frontend and confirms the Capability Center DOM contains:

- `Data sources / connectors`
- `Native data source ops`
- `resources_status`
- `validation_status`
- `sync_control_status`
- `delete_control_status`
- `native_data_source_delete`
- `/api/data-sources/native/overview`

## Remaining Blockers

`WNFC-P1-01` remains blocked:

- Need one real credential-bearing Notion/Yuque/Feishu connector credential.
- Need an accessible third-party workspace with permission to list resources
  and sync content.
- RSS is no-credential and cannot satisfy that requirement.

`WNFC-P1-03` remains open:

- Need proof that synced external-source content becomes searchable/answerable
  through PA with traceable native evidence.
