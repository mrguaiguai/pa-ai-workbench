# WeKnora Native Capability Center Browser Report

Date: 2026-06-23

Task: `WNX-P0-03`

Branch: `weknora-first-mvp`

## Scope

This report validates the PA capability center frontend shell against the live
PA BFF native status endpoint. The page is not a static capability board: it
loads `/api/native/status`, renders the returned capability groups, and keeps
`live`, `partial`, `blocked`, and `backlog` states visible.

## Runtime

- Backend: temporary PA backend on `http://127.0.0.1:8023`.
- Frontend: temporary Vite frontend on `http://127.0.0.1:5174`.
- Browser: local Chrome headless through Playwright.
- API source: `/api/native/status`.
- API schema: `wnx-p0-02`.
- API source label: `pa_backend_bff`.
- API evidence type: `live_api`.
- API masking: `masked=true`.
- CORS note: `5173` was already in use locally, so the temporary backend process
  was started with local `5174` allowed for browser validation. No committed
  CORS configuration was changed.

## Live API Evidence

Sanitized status summary:

```text
schema_version: wnx-p0-02
source: pa_backend_bff
evidence_type: live_api
masked: true
group_count: 15
status_counts: live=7, partial=5, blocked=0, backlog=3
```

The frontend consumes this live response through `apiClient.getNativeStatusCenter`
and renders `Object.values(groups)` from the backend payload. No mock data,
fixture data, cached report, or static status card is used as PASS evidence.

## Browser Matrix

| Viewport | Result | Evidence |
| --- | --- | --- |
| Desktop `1440x900` | PASS | Title visible; `wnx-p0-02`, `pa_backend_bff`, `live_api`, `masked`, `15 groups`, and all status buckets visible; 15 capability cards rendered; no horizontal overflow; no suspicious secret-like text. |
| Mobile `390x844` | PASS | Same live markers and 15 capability cards visible; mobile navigation and capability cards fit without horizontal overflow; no suspicious secret-like text. |

Observed status counters in both viewports:

```text
live: 7
partial: 5
blocked: 0
backlog: 3
```

The `blocked` bucket is intentionally visible even when the live count is `0`;
the page must not hide a zero-count state because future native blockers need a
stable operator surface.

## UI Safety Checks

- Long native capability ids and endpoint paths wrap within capability cards.
- Mobile navigation fits after adding the capability center route.
- The page shows `partial` and `backlog` as first-class states instead of
  converting them into healthy/green status.
- Masked config rows show status booleans/provider labels only; no credential
  values or provider payloads are rendered.
- No screenshots were created or committed.

## Validation Commands

```text
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node frontend/node_modules/typescript/bin/tsc -p frontend/tsconfig.json --noEmit
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/vite/bin/vite.js build
Chrome/Playwright DOM validation for http://127.0.0.1:5174/#/capabilities
```

## PASS Decision

`WNX-P0-03` is PASS with `live browser evidence backed by live API response`.
This task adds a truthful PA frontend capability center shell. It does not
upgrade read-only capability coverage to workflow `live-full`, and it does not
claim that backlog or zero-count blocked groups are implemented workflows.
