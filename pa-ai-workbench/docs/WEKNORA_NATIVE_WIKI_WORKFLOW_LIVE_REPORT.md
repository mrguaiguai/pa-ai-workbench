# WeKnora Native Wiki Workflow Live Report

> Task: `WNX-P1-06`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P1-06` is PASS for the native Wiki workflow slice.

PA now exposes a dedicated native Wiki BFF for pages, search, read, index, log,
graph, stats, lint, issues, and confirmation-gated mutations. The live smoke
created, updated, read, searched, and soft-deleted a temporary native Wiki page
through WeKnora native APIs. The browser workflow renders the native Wiki status
panel and confirmed mutation controls in the Wiki page.

## Implemented Surface

| Layer | File / endpoint | Result |
| --- | --- | --- |
| WeKnora Native Adapter | `knowledge_engine/backends/weknora_api_backend.py` | Adds safe wrappers for native Wiki log, delete, rebuild-links, auto-fix, and issue status updates. |
| PA Backend BFF | `/api/wiki/native/pages`, `/api/wiki/native/page`, `/api/wiki/native/search` | Lists, searches, reads, creates, updates, and soft-deletes native Wiki pages. |
| PA Backend BFF | `/api/wiki/native/index`, `/log`, `/graph`, `/stats`, `/lint`, `/issues` | Exposes safe native Wiki operational status without raw page content or provider payloads. |
| PA Backend BFF | `/api/wiki/native/rebuild-links`, `/auto-fix`, `/issues/{issue_id}/status` | Requires exact confirmation tokens before global maintenance or issue mutations. |
| PA Status Center | `/api/native/status` | Marks Native Wiki as live when WeKnora core config is present and points the next action to cross-workflow history/citation unification. |
| PA Frontend Shell | Wiki page | Adds a Native workflow panel with live counts/status and confirmation-protected mutation controls. |
| Validation | `backend/scripts/check_weknora_native_wiki_workflow.py` | Runs current-run live workflow smoke with a temporary native Wiki page. |

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_wiki_workflow.py
```

Sanitized output:

```text
WeKnora native Wiki workflow smoke passed (live)
- PA endpoint: /api/wiki/native
- overview status/mutations: live/live
- pages status/count: weknora_api/8
- search count: 1
- read traceable: True
- index groups/entries: 5/24
- log entries: 8
- graph nodes/edges: 30/220
- stats total_pages: 382
- lint issue_count: 2313
- issues count: 0
- mutation cycle: create/update/delete
```

Browser evidence:

```text
url: http://127.0.0.1:5174/#/wiki
viewport: 390x844
Native panel: visible
workflow: live
core surfaces: read/search/index live
mutations: live
buttons: rebuild, auto-fix, delete present
failed API responses: none
```

Evidence boundaries:

- The smoke starts a temporary PA backend and calls real PA BFF endpoints backed
  by real WeKnora native APIs.
- The mutation PASS is scoped to a temporary Wiki page created by the smoke; it
  does not mutate existing production Wiki pages.
- The report and smoke output do not print service tokens, raw Wiki page
  content, provider payloads, chunks, `.env` values, logs, or private keys.
- Lint status is treated as Wiki health evidence, not citation evidence.

## Mutation Boundary

Safe native page create/update/delete is live with exact confirmation tokens.
Global maintenance actions are exposed only behind explicit confirmation:

- `REBUILD_NATIVE_WIKI_LINKS`
- `AUTO_FIX_NATIVE_WIKI`
- `UPDATE_NATIVE_WIKI_ISSUE_STATUS`

The live PASS does not depend on executing global auto-fix/rebuild on an
existing production Wiki. Those controls remain operator-confirmed workflows
and must not be automated from status-only surfaces.

## Coverage Impact

The `Native Wiki` group moves from `live-partial` to `live-full` because PA now
has live pages/search/read, index/log/graph/stats/lint/issues, browser workflow,
and a validated safe create/update/delete mutation cycle.

Current coverage becomes:

```text
9.25 / 15 = 61.7%
```

The final 80% target remains unchanged at:

```text
12.00 / 15 = 80.0%
```

## Remaining Risks

- Native Wiki issue-status update needs live issue fixture data before it can be
  called safely in an automated smoke.
- Global rebuild-links and auto-fix require operator confirmation and should
  stay out of automatic status refreshes.
- Cross-workflow history/citation unification remains `WNX-P1-07`; this task
  proves Wiki page locator fields, not all downstream native citation flows.
