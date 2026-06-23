# WeKnora Native Data Source Configured Connector Smoke Report

Date: 2026-06-23

Task: `WNX-P3-05`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: live API/browser evidence, blocked evidence, backlog evidence.

## Scope

`WNX-P3-05` attempts the Data sources/connectors score move from `read-only` to
`live-partial`.

The required PASS condition is a safe configured connector workflow:

- at least one configured native data source exists for the active KB;
- PA reads connector detail through a safe index, not a raw native id;
- PA reads sanitized sync-log summaries;
- resources and validation are either safely summarized or explicitly blocked
  without leaking private resource names or credentials;
- sync/pause/resume controls are confirmation-gated and, if executed, return
  sanitized status only; and
- no raw credentials, raw connector config, private endpoints, raw sync logs,
  local DB contents, or provider payloads are printed or committed.

## Native Source Audit

Inspected native source files:

- `internal/router/router.go`
- `internal/handler/datasource.go`
- `internal/handler/datasource_credentials.go`
- `internal/application/service/datasource_service.go`
- `internal/types/datasource.go`
- `internal/datasource/connector.go`

Findings:

- Native connector type and data source list/read routes are Viewer+.
- Native credential validation, resources, sync, pause, resume, credentials,
  create, update, and delete routes are Admin+.
- Native resources and validation call external connector implementations.
- Native manual sync creates a sync log and enqueues an async sync task that can
  mutate KB content.
- Native sync logs can contain error/result details, so PA must expose only
  sanitized counts/statuses.

## PA Surface Audit

Inspected PA files:

- `knowledge_engine/backends/weknora_api_backend.py`
- `backend/app/services/data_source_service.py`
- `backend/app/api/data_source.py`
- `backend/scripts/check_weknora_native_data_source_management.py`

Findings:

- PA exposes masked connector overview at
  `/api/data-sources/native/overview`.
- PA exposes configured data source detail through `safe_index` links rather
  than raw native ids.
- PA exposes only safe connector type, data source status, configured booleans,
  resource counts, and sync-log summary fields.
- PA blocks resources/validation by default because they can call external
  systems and reveal private names or credential state.
- PA blocks sync/pause/resume unless the caller provides an explicit
  confirmation token.

No PA workflow upgrade is justified in this task because the current runtime
has no configured data source to validate.

## Live Validation

Command:

```text
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

The smoke passes as a safe read-only visibility check. It does not satisfy the
configured connector workflow PASS condition.

## Coverage Impact

`Data sources/connectors` remains `read-only`.

Coverage remains:

```text
11.25 / 15 = 75.0%
```

The attempted score move is not accepted:

```text
Data sources/connectors read-only -> live-partial: blocked
score gain: +0.00
```

## Required Next Step

To unblock this group, an operator must configure a safe native data source in
WeKnora for the active KB without exposing credentials to PA reports or Codex
output. A later task can then rerun the configured connector smoke and validate
only sanitized detail, resource/validation status, sync/pause/resume control,
and sync-log summaries.

Until that configured connector exists and live validation passes, this group
must stay `read-only`, and the Native Expansion final PASS remains blocked at
`75.0%`.
