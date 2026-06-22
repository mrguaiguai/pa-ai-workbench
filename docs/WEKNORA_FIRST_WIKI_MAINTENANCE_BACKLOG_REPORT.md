# WeKnora-First Wiki Maintenance Backlog Report

> Task: `WF-P2-04`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: BACKLOG
>
> Evidence type: backlog with native source audit.

## Scope

`WF-P2-04` covers advanced Wiki maintenance: lint details, issue management,
graph filtering, auto-fix, link rebuild, and maintenance scheduling. This task
does not run or expose native Wiki mutations from PA. The safe sprint decision
is to keep mutation actions backlog while preserving the read-only visibility
already exposed by `WF-P1-02`.

## Native Source Audit

| Area | Native source inspected | Observed shape | PA sprint decision |
| --- | --- | --- | --- |
| Graph | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go`, `internal/types/wiki_page.go` | `GET /api/v1/knowledgebase/{kb_id}/wiki/graph`; viewer route; overview and ego modes; HTTP handler clamps limit and depth. | Keep read-only status visible through the existing native Wiki overview; richer graph exploration remains backlog or native admin. |
| Stats | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/types/wiki_page.go` | `GET /api/v1/knowledgebase/{kb_id}/wiki/stats`; viewer route; aggregate counts including pending issues. | Keep read-only readiness/counts. |
| Lint | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_lint.go` | `GET /api/v1/knowledgebase/{kb_id}/wiki/lint`; viewer route; service walks pages in bounded batches and returns health score/issues. | Keep read-only health visibility; do not treat route existence as a live PASS for maintenance workflow. |
| Issues | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go`, `internal/types/wiki_page.go` | `GET /api/v1/knowledgebase/{kb_id}/wiki/issues`; viewer route; returns issue records with status and suspected knowledge ids. | Keep sanitized read-only issue counts/fields; issue triage workflow remains backlog. |
| Issue status mutation | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go` | `PUT /api/v1/knowledgebase/{kb_id}/wiki/issues/{issue_id}/status`; owned-KB/admin route; mutates issue state. | Backlog. PA needs a separate safety task before exposing this. |
| Link rebuild | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_page.go` | `POST /api/v1/knowledgebase/{kb_id}/wiki/rebuild-links`; owned-KB/admin route; rebuilds link references. | Backlog. Do not trigger from PA in this sprint. |
| Auto-fix | `internal/router/router.go`, `internal/handler/wiki_page.go`, `internal/application/service/wiki_lint.go` | `POST /api/v1/knowledgebase/{kb_id}/wiki/auto-fix`; owned-KB/admin route; can update page content, metadata, archived status, source refs, and then rebuild links. | Backlog. Requires explicit mutation UX, audit trail, preview, and rollback design before PA exposure. |

## Current PA State From Prior Sprint Slice

`WF-P1-02` already exposed read-only native Wiki visibility through PA:

- native browse/search/read/index/stats/graph/lint/issues are represented as
  sanitized read-only status in the Wiki native overview;
- native Wiki mutations are labeled backlog;
- citation fields remain traceable for native Wiki read paths;
- no raw Wiki content is required for the visibility report.

This report does not reuse the prior live result as a new PASS. It records why
advanced maintenance remains backlog after source inspection.

## Backlog Decision

`WF-P2-04` remains `[b]`.

Reasons:

- The useful read-only slice is already covered by `WF-P1-02`.
- The remaining advanced actions are native mutations or maintenance workflows.
- `auto-fix` can modify Wiki page content, archive sparse pages, update
  metadata/source refs, delete pages in stale-ref cases, and rebuild links.
- `rebuild-links` and issue status updates require product controls that PA
  does not yet define: preview, confirmation, audit trail, permission display,
  per-action result review, and recovery path.
- Building a PA-native graph/lint/auto-fix engine would violate the
  WeKnora-first rule because WeKnora already owns these native capabilities.

## Allowed Future Slice

A future explicit `WF-*` task may safely start with one of these narrow scopes:

- show native-admin jump targets for Wiki maintenance;
- add a read-only issue-detail panel using sanitized issue fields only;
- add graph filter controls over the existing read-only native graph endpoint;
- design an auto-fix preview-only flow that calls no mutation endpoint;
- add a mutation safety design document before any PA-triggered maintenance
  action is implemented.

## Not Done

- No `POST /wiki/auto-fix` call was made.
- No `POST /wiki/rebuild-links` call was made.
- No `PUT /wiki/issues/{issue_id}/status` call was made.
- No PA backend or frontend code was changed.
- No live PASS is claimed for advanced Wiki maintenance mutations.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Not claimed for this task. |
| source audit | Used to identify read-only and mutation boundaries. |
| fixture-only | Not used as PASS evidence. |
| mock | Not used. |
| cached | Not used. |
| partial | Not used as completion evidence. |
| blocked | Not blocked by runtime; intentionally deferred by sprint scope. |
| backlog | Advanced Wiki maintenance mutation and broad admin workflows remain backlog. |

## Conclusion

`WF-P2-04` is closed as backlog for this sprint. PA should continue to consume
WeKnora's native read-only Wiki visibility and should not expose advanced
maintenance mutations until a separate safety-focused task defines preview,
audit, permission, and recovery behavior.
