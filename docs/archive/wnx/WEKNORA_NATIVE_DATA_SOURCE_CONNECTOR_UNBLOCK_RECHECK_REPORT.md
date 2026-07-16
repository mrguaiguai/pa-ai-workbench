# WeKnora Native Data Source Connector Unblock Recheck Report

Date: 2026-06-23

Task: `WNX-P3-09`

Branch: `weknora-first-mvp`

Decision: `BLOCKED`

Evidence type: native source audit, live API/browser evidence, blocked evidence,
backlog evidence.

## Scope

`WNX-P3-09` rechecks the remaining score-moving path after `WNX-P3-08`.
AgentQA/custom Agent is now `live-full`, so the only remaining path to the
`12.00 / 15 = 80.0%` threshold is Data sources/connectors:

```text
Data sources/connectors read-only -> live-partial: +0.25
```

The task does not create connector credentials, does not print raw connector
configuration, does not inspect local databases, and does not run sync against
an unreviewed external system.

## Native Source Audit

Inspected native files:

```text
internal/router/router.go
internal/handler/datasource.go
internal/handler/datasource_credentials.go
internal/application/service/datasource_service.go
internal/types/datasource.go
internal/datasource/connector.go
internal/datasource/README.md
internal/container/container.go
internal/datasource/connector/notion/connector.go
internal/datasource/connector/yuque/connector.go
```

Findings:

- native data source list/read and sync-log reads are Viewer+;
- create/update/delete, credential validation, resources, validate,
  sync/pause/resume, and credential subresource are Admin+;
- connector metadata lists 12 connector types, including catalog-only types;
- the live connector registry is wired to implemented Feishu, Notion, and Yuque
  connectors;
- those implemented connectors require real external credentials and live
  external API validation before a data source can be safely configured;
- manual sync creates a sync log and enqueues a native sync task that can mutate
  the target knowledge base;
- sync history summaries and resource listings can contain external names,
  URLs, or error details, so PA must keep output summarized.

`auth_type=none` catalog entries such as RSS or Web Crawler are not implemented
and registered in the current native connector registry, so they cannot be used
as a real configured connector PASS.

## PA Surface Audit

Inspected PA files:

```text
knowledge_engine/backends/weknora_api_backend.py
backend/app/services/data_source_service.py
backend/app/api/data_source.py
backend/scripts/check_weknora_native_data_source_management.py
```

The current PA surface remains appropriate for safe visibility:

- connector type catalog is sanitized;
- configured data source list uses `safe_index` rather than raw native ids;
- sync-log output is reduced to status/count/timestamp presence fields;
- resources and validation stay blocked/backlog by default;
- sync/pause/resume require explicit confirmation tokens;
- no raw credentials, raw config, private endpoints, resource names, or raw
  sync-log bodies are printed.

No PA code change is justified while the live runtime has no configured native
data source.

## Live Validation

Command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_management.py --browser
```

Sanitized current-run output:

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

This is a valid current-run read-only smoke. It is not a configured connector
workflow PASS.

## Why This Cannot Be Forced Locally

The following shortcuts are explicitly rejected:

- creating a fake local connector service and treating it as live external
  evidence;
- inserting a data source row directly into the database;
- using connector catalog metadata as proof that a connector implementation is
  configured;
- treating a blocked sync confirmation path as successful sync evidence;
- printing or committing credentials, raw config, resource names, or raw sync
  logs.

Those routes would violate the WNX PASS boundary and would overstate coverage.

## Coverage Impact

`Data sources/connectors` remains `read-only`.

Current coverage remains:

```text
11.75 / 15 = 78.3%
```

Target remains:

```text
12.00 / 15 = 80.0%
```

Score gain from this task:

```text
+0.00
```

## Required Next Step

An operator must configure a real safe Feishu, Notion, or Yuque data source in
WeKnora for the active KB without exposing credentials to Codex output or PA
reports. After that, a new WNX task can validate only sanitized evidence:

- configured data source count greater than 0;
- safe-index detail read;
- sync-log summary read;
- resources/validation summarized or safely blocked;
- confirmation-gated sync/pause/resume with restored state;
- no raw credential/config/resource/log/private endpoint output.

Until that exists, the internal production final PASS remains blocked below
80.0%.
