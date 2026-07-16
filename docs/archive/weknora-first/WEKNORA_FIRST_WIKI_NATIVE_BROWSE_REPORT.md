# WeKnora-First Native Wiki Browse Report

> Task: `WF-P1-02`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live PA API + live WeKnora native Wiki API.

## Scope

`WF-P1-02` adds a read-only PA API slice over WeKnora native Wiki browse/search,
read, index, stats, graph, lint, and issue-list surfaces. PA remains the product
wrapper and returns sanitized counts, ids, slugs, status, and traceability
fields. It does not rebuild WeKnora Wiki admin or mutate native Wiki state.

## Native Source And PA Mapping

| Area | Native source | PA decision |
| --- | --- | --- |
| List pages | `GET /api/v1/knowledgebase/{kb_id}/wiki/pages` | Expose via PA native overview as sanitized page summaries. |
| Search pages | `GET /api/v1/knowledgebase/{kb_id}/wiki/search` | Keep existing PA search behavior and include native search in overview. |
| Read page | `GET /api/v1/knowledgebase/{kb_id}/wiki/pages/{slug}` | Preserve `source_type=wiki_page`, `wiki_page_id`, and `evidence_id`. |
| Index view | `GET /api/v1/knowledgebase/{kb_id}/wiki/index` | Expose group and entry counts with sanitized entries. |
| Stats | `GET /api/v1/knowledgebase/{kb_id}/wiki/stats` | Expose aggregate counts and readiness fields. |
| Graph | `GET /api/v1/knowledgebase/{kb_id}/wiki/graph` | Expose read-only node/edge counts and graph meta. |
| Lint | `GET /api/v1/knowledgebase/{kb_id}/wiki/lint` | Expose read-only health and issue counts. |
| Issues | `GET /api/v1/knowledgebase/{kb_id}/wiki/issues` | Expose read-only issue count and safe issue fields. |
| Mutations | `POST /rebuild-links`, `POST /auto-fix`, issue status update | Marked backlog for this task. |

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_wiki_native_browse_live.py
```

Result summary:

```text
WeKnora native Wiki browse smoke passed (live)
- PA endpoint: /api/wiki/native/overview
- knowledge base: 29adf20a-91db-45b5-9df1-6c608f802e8d
- overview status: live
- pages status/count/total: live/5/355
- search status/count: live/5
- read status/slug: live/concept/rag-debug
- read traceable: True
- index status/groups/entries: live/5/15
- stats status/total_pages: live/355
- graph status/nodes: live/5
- lint status/issues: live/2261
- issues status/count: live/0
- mutations status: backlog
```

What this proves:

- PA exposed a current HTTP API endpoint for native Wiki overview.
- The endpoint called real WeKnora native Wiki surfaces, not mock or cached data.
- Core browse/search/read/index/stats surfaces returned live data.
- Native graph, lint, and issues were surfaced as read-only status.
- Native Wiki read preserved traceability with `source_type`, `wiki_page_id`, and
  `evidence_id`.
- Mutation/admin surfaces remain backlog and are not counted as live PASS.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Used for PA `/api/wiki/native/overview` and native WeKnora Wiki read-only endpoints. |
| fixture-only | Not used as PASS evidence. |
| mock | Not used; mock evidence is not PASS. |
| cached | Not used; old reports and cached page state are not PASS. |
| partial | No partial core surface in this run; future native failures should be labeled per-surface. |
| blocked | No blocker for read-only browse/search/read/index/stats in this run. |
| backlog | Native Wiki mutations and admin workflows remain backlog. |

## Citation And Locator Contract

The read path keeps native Wiki evidence traceable:

- `source_type=wiki_page`
- `wiki_page_id` is present
- `evidence_id` is present and uses the PA citation contract
- raw page content is not printed in the smoke output or report

PA does not invent `wiki_page_id`, `source_refs`, or citation locators. If a
future native response lacks identifiers, the overview must mark that surface
blocked or partial instead of creating fake evidence.

## PASS Statement

`WF-P1-02` is complete for the read-only native Wiki browse/search/read/index
slice. PA now exposes a sanitized native Wiki overview API backed by live WeKnora
Wiki endpoints, while graph/lint/issues are read-only and mutations remain
explicit backlog.
