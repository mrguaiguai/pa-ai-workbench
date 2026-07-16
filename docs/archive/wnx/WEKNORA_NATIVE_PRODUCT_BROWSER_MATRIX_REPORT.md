# WeKnora Native Product Browser Matrix Report

Date: 2026-06-23

Task: `WNX-P3-01`

Branch: `weknora-first-mvp`

## Scope

This report validates the PA internal production UI across the core workbench
routes. The task title says six-page matrix, while the current product shell has
seven routed views in scope: home, library, intelligent analysis, RAG debug,
Wiki, history, and capability/config center.

The validation uses live PA services and live browser evidence. It does not use
mock data, fixture-only data, cached reports, screenshots, or static UI as PASS
evidence.

## Runtime

- Backend: temporary PA backend on a local ephemeral port.
- Frontend: temporary Vite frontend on a local ephemeral port.
- Browser: local Chrome headless through the Chrome DevTools Protocol.
- Database: temporary SQLite database under a throwaway temp directory.
- API source: `/api/native/status`.
- API schema: `wnx-p0-02`.
- API evidence type: `live_api`.
- API masking: `masked=true`.
- Status groups: `15`.

No screenshots, logs, databases, uploads, provider payloads, credentials, or raw
native ids were saved or committed.

## Browser Matrix

| Route | Hash route | Desktop `1440x900` | Mobile `390x844` | Evidence markers |
| --- | --- | --- | --- | --- |
| Home | `#/` | PASS | PASS | Workbench heading, WeKnora status, capability state, `weknora_api`. |
| Library | `#/library` | PASS | PASS | Library heading, active KB selector, upload target, backend-backed KB state. |
| Intelligent analysis | `#/analysis` | PASS | PASS | Analysis heading, analysis flow controls, run action, backend empty-conversation state. |
| RAG debug | `#/rag-debug` | PASS | PASS | RAG debug heading, native knowledge QA panel, trace empty state, question action. |
| Wiki | `#/wiki` | PASS | PASS | Wiki heading, native workflow state, page/read status indicators. |
| History | `#/history` | PASS | PASS | History heading, result panel, warning/evidence filters, evidence state. |
| Capability center | `#/capabilities` | PASS | PASS | Capability heading, `wnx-p0-02`, `pa_backend_bff`, data-source connector group. |

## Live Browser Evidence

Sanitized command output:

```text
WeKnora native product workflow browser matrix
- decision: PASS
- evidence_type: live_browser_evidence
- api: native_status_schema=wnx-p0-02 groups=15
- browser: routes=7 viewport_checks=14
- desktop: pass=7 overflow=0 visible_overlap=0
- mobile: pass=7 overflow=0 visible_overlap=0
```

Each page check verifies:

- route-level product markers are rendered by the live frontend;
- live backend/native status is reachable before browser validation;
- page-specific backend-backed state is visible where the route loads backend
  state on entry;
- `documentElement` and `body` do not horizontally overflow the viewport;
- visible interactive/text elements do not show incoherent overlap;
- secret-shaped values are not rendered in visible page text;
- unsafe evidence claims such as mock/fixture/cache/static UI PASS wording are
  not rendered.

## Validation Commands

```text
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_product_browser_matrix.py
backend/.venv/bin/python backend/scripts/check_weknora_native_product_browser_matrix.py
```

Additional repository validation was run after this report/spec update.

## PASS Decision

`WNX-P3-01` is PASS with `live browser evidence`.

The PASS is limited to the product workflow/browser matrix. It does not upgrade
any capability coverage group, does not claim that backlog controls are
implemented, and does not hide visible partial or blocked native states.
