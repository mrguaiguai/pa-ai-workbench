# WeKnora Native RSS Data Source Connector Live Report

Date: 2026-06-24

Task: `WNX-P3-10`

Branch: `weknora-first-mvp`

Decision: `PASS`

Evidence type: live API/browser evidence, native Docker runtime evidence,
checker execution evidence, partial evidence, backlog evidence.

## Summary

`WNX-P3-10` unblocks the remaining Data sources/connectors coverage gap with a
real no-credential RSS/Atom connector path. The native runtime now registers an
implemented `rss` connector, PA can configure a safe RSS data source through the
native API, and the PA data source smoke validates sanitized detail, resources,
validation, sync, pause, resume, sync-log summary, and browser status without
printing raw config, credentials, native IDs, resource names, raw logs, or feed
URLs.

This moves Data sources/connectors from `read-only` to `live-partial`, adding
`+0.25` and bringing total coverage to:

```text
12.00 / 15 = 80.0%
```

## Native Changes

Implemented a native RSS connector under the WeKnora source tree:

```text
internal/datasource/connector/rss/connector.go
internal/datasource/connector/rss/connector_test.go
internal/container/container.go
```

The connector:

- implements the existing `datasource.Connector` interface;
- uses WeKnora's SSRF-safe HTTP client and URL validation;
- accepts no credentials;
- parses RSS and Atom feeds with standard library XML parsing;
- exposes one configured feed resource;
- converts feed entries to markdown `FetchedItem` content for the real native
  sync ingestion path.

Native validation:

```text
go test ./internal/datasource ./internal/datasource/connector/rss ./internal/types
```

Result:

```text
ok github.com/Tencent/WeKnora/internal/datasource
ok github.com/Tencent/WeKnora/internal/datasource/connector/rss
ok github.com/Tencent/WeKnora/internal/types
```

Runtime validation:

```text
docker compose -f docker-compose.yml build app
docker compose -f docker-compose.yml up -d --no-deps --force-recreate app
curl -fsS http://127.0.0.1:8080/health
```

Result:

```text
app image build: PASS
app recreate: PASS
health: {"status":"ok"}
```

The broader `go test ./internal/container` was attempted with a bare
`golang:1.26.0` image and failed because that image lacked `sqlite3.h`.
The production Dockerfile build is the authoritative runtime compile check for
this stage because it installs `libsqlite3-dev` and successfully compiled
`./cmd/server`.

## PA Changes

PA now has minimal safe RSS data source support:

```text
knowledge_engine/backends/weknora_api_backend.py
backend/app/services/data_source_service.py
backend/scripts/configure_weknora_native_rss_data_source.py
backend/scripts/check_weknora_native_data_source_management.py
```

The adapter adds safe helpers for:

- creating an RSS data source with empty credentials;
- validating a data source connection as connected/blocked only;
- summarizing resources as count/type counts only.

The BFF keeps generic connector CRUD and credential forms in backlog. It runs
resources and validation probes only for RSS, because RSS is no-credential and
the response is reduced to sanitized counts.

## Live Configuration Evidence

Command:

```text
backend/.venv/bin/python backend/scripts/configure_weknora_native_rss_data_source.py
```

Sanitized output:

```text
WeKnora native RSS data source configured
- decision: PASS
- evidence_type: live_api_current_run
- connector_registered: true
- rss_source: created
- data_sources: count=1 rss_count=1
- validation: status=connected connected=true
- resources: status=live count=1
```

The script does not print service tokens, native data source IDs, raw config,
resource names, raw logs, feed URLs, private endpoints, or provider payloads.

## Live PA Smoke Evidence

Command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_management.py --allow-confirmed-sync --browser
```

Sanitized output:

```text
WeKnora native data source connector management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- coverage_state: live-partial
- connector_types: status=live count=12
- data_sources: status=live count=1 credentials_configured=0
- connector_read: live detail=live
- resources: blocked
- validation: blocked
- sync_control: overview=blocked blocked_path=blocked confirmed_path=live
- pause_resume: pause=live resume=live
- mutations: backlog
- browser: Capability Center rendered data source connector readiness
```

The overview still blocks generic resources/validation by default. The
safe-index detail path validates RSS resources and validation live as sanitized
count/connected surfaces, and the confirmed control path verifies sync,
pause, and resume while restoring the source to active state.

## Coverage Decision

Data sources/connectors now qualifies as `live-partial`:

- connector catalog/list visibility is live;
- one no-credential configured RSS data source exists in the live runtime;
- detail and sync-log summary are readable through PA;
- RSS resources and validation are proven live in sanitized detail;
- sync, pause, and resume require confirmation and pass;
- browser Capability Center renders the current data source status.

Remaining backlog:

- generic connector CRUD;
- credential forms;
- raw credential validation;
- raw resource listing;
- raw sync-log details;
- deletion-sync controls;
- credential-bearing Feishu/Notion/Yuque setup.

No mock connector, fixture-only data source, direct DB row injection, cached
report, static UI, raw config, or raw sync log is used as PASS evidence.
