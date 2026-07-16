# WeKnora Native Data Source Connector Live Report

> Task: `WNX-P2-05`
>
> Date: 2026-06-23
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live API/browser evidence with read-only coverage.

## Scope

`WNX-P2-05` adds a safe PA surface for WeKnora native data source connector
management. PA now reads the native connector type catalog and active-KB data
source list through the shared WeKnora adapter, exposes sanitized connector
status in `/api/data-sources/native/overview`, and renders the status in the
Capability Center.

The current WeKnora runtime has no configured data source for the active KB, so
this task does not claim live sync, resources, validation, pause, or resume
workflow PASS. Those controls are present as confirmation-gated or backlog
surfaces, but no external connector probe or sync task was triggered.

## Native Source Audit

| Area | Source | Finding |
| --- | --- | --- |
| Route registration | `internal/router/router.go` | `GET /api/v1/datasource/types`, `GET /api/v1/datasource`, `GET /api/v1/datasource/:id`, and sync-log reads are Viewer+; create/update/delete, credential validation, resources, sync, pause, and resume are Admin+. |
| Handler behavior | `internal/handler/datasource.go`, `internal/handler/datasource_credentials.go` | Handler enforces tenant/KB ownership. Data source responses use DTOs that strip credential maps; credential replacement is isolated behind a dedicated credentials subresource. |
| Service rules | `internal/application/service/datasource_service.go` | Validate/resources call connector implementations; manual sync creates a sync log and enqueues an async task; pause/resume mutate scheduler state. |
| Types | `internal/types/datasource.go` | `DataSource.Config` can hold connector credentials and settings; sync logs can hold error/result details. PA exposes only counts, statuses, configured booleans, and safe indexes. |
| Connector registry | `internal/datasource/connector.go` | Native catalog includes 12 connector types with auth mode and capability metadata; PA keeps this as catalog visibility, not credential setup PASS. |

## PA Surface

Endpoints:

```text
GET /api/data-sources/native/overview?limit=10
GET /api/data-sources/native/sources/by-index/{data_source_index}
POST /api/data-sources/native/sources/by-index/{data_source_index}/sync
POST /api/data-sources/native/sources/by-index/{data_source_index}/pause
POST /api/data-sources/native/sources/by-index/{data_source_index}/resume
```

Key behavior:

- Overview schema is `wnx-p2-05`, `masked=true`, and `management_mode=safe_read_confirmed_sync`.
- Connector type catalog exposes safe type/name/auth/capability counts only.
- Data source list uses PA `safe_index` links instead of raw native data source IDs.
- Sync, pause, and resume return `blocked` unless the caller provides an explicit confirmation phrase.
- Resource listing, credential validation, connector CRUD, raw sync-log details, credential forms, and deletion-sync controls remain backlog or blocked.

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_management.py --browser
```

Sanitized output:

```text
WeKnora native data source connector management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- coverage_state: read-only
- connector_types: status=live count=12
- data_sources: status=live count=0 credentials_configured=0
- connector_read: backlog detail=not_configured
- resources: backlog
- validation: backlog
- sync_control: overview=backlog blocked_path=backlog confirmed_path=not_requested
- mutations: backlog
- browser: Capability Center rendered data source connector readiness
```

Browser validation:

- Chrome headless loads the Capability Center through the temporary frontend.
- The `Data sources / connectors` group renders from `/api/data-sources/native/overview`.
- Summary fields include `connector_type_count` and `sync_control_status`.

## Evidence Classification

| Surface | Result | Evidence |
| --- | --- | --- |
| Connector types | live | Native catalog returned 12 connector types. |
| Data source list | live/read-only | Native list call succeeded for the active KB and returned 0 configured data sources. |
| Connector detail | backlog | No configured connector exists for a detail read. |
| Sync logs | backlog | No configured connector exists for sync-log reads. |
| Resources | backlog | No configured connector exists; external resource listing would require connector credentials and privacy review. |
| Validation | backlog | Raw credential validation is not exposed from PA in this task. |
| Sync/pause/resume | backlog | No configured connector exists; controls are confirmation-gated and not executed. |
| Mutations | backlog | Connector CRUD, credential forms, raw logs, and deletion-sync controls remain outside this safe slice. |

## PASS Statement

`WNX-P2-05` passes as a safe read-only connector visibility slice. PA can read
the WeKnora native connector catalog and active-KB data source list through live
API and browser validation, without leaking credentials, raw connector config,
external resource names, sync-log error text, or raw payloads.

Coverage moves Data sources/connectors from `backlog` to `read-only`, raising
the ledger from `10.50 / 15 = 70.0%` to `10.75 / 15 = 71.7%`. Promotion to
`live-partial` remains blocked/backlog until a sanitized configured connector
exists and resources/validation/sync controls can be validated safely.
