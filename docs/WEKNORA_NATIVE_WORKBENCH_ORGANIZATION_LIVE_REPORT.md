# WeKnora Native Workbench Organization Live Report

> Task: `WNX-P2-06`
>
> Date: 2026-06-23
>
> Branch: `weknora-first-mvp`
>
> Evidence type: live API/browser evidence.

## Scope

`WNX-P2-06` adds safe PA visibility for WeKnora native workbench organization
features: knowledge-base tags, FAQ readiness, user favorites, and preloaded
Agent skills. PA exposes a masked overview at `/api/organization/native/overview`
and renders the resulting capability state in the Capability Center.

This is a safe live-partial slice. It proves native read/list organization
surfaces are reachable through PA, while FAQ mutations, tag mutations, favorite
toggle writes, skill upload/enable/execute, and PA-owned taxonomy expansion
remain backlog.

## Native Source Audit

| Area | Source | Finding |
| --- | --- | --- |
| Route registration | `internal/router/router.go` | FAQ list/read/search/export and import-progress reads are Viewer+; FAQ create/update/delete/import/display mutations are owner/admin write flows. Tags list is Viewer+ and tag writes are owner/admin/contributor flows. Favorites list/add/remove are Viewer+ but user-scoped. Skills currently expose read-only `GET /api/v1/skills` as Viewer+. |
| FAQ handler/types | `internal/handler/faq.go`, `internal/types/faq.go` | FAQ entries contain question/answer bodies and chunk ids, so PA strips content and exposes only counts/status/readiness. |
| Tag handler/types | `internal/handler/tag.go`, `internal/types/tag.go` | Tags are KB-scoped organization metadata with usage counts; PA exposes safe name/color/count summaries only. |
| Favorite handler/types | `internal/handler/user_resource_favorite.go`, `internal/types/user_resource_favorite.go` | Favorites are user+tenant scoped navigation aids for `kb` and `agent`; PA reads counts but does not toggle favorites in this task. |
| Skill handler/service | `internal/handler/skill_handler.go`, `internal/types/interfaces/skill.go` | Native skill list is read-only; upload/enable/execute would need a separate sandbox and approval design. |

## PA Surface

Endpoints:

```text
GET /api/organization/native/overview?limit=10
GET /api/native/status?limit=5
```

Key behavior:

- Overview schema is `wnx-p2-06`, `masked=true`, and `management_mode=safe_read_with_mutation_backlog`.
- Tags expose counts and non-sensitive display metadata only.
- Skills expose name and description-presence only, plus `skills_available`.
- FAQ strips question/answer bodies and is allowed to be `blocked` when the active KB is not suitable for FAQ listing.
- Favorites expose only resource type and count.
- Mutations remain backlog.

## Live Validation

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_organization.py --browser
```

Sanitized output:

```text
WeKnora native workbench organization readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- tags: status=live count=1
- skills: status=live count=5 available=True
- faq: status=blocked count=0
- favorites: status=live count=0
- mutations: backlog
- browser: Capability Center rendered organization readiness
```

Browser validation:

- Chrome headless loads the Capability Center through the temporary frontend.
- The `FAQ / tags / favorites / skills` group renders from `/api/organization/native/overview`.
- Summary fields include `skills_count` and `tags_status`.

## Evidence Classification

| Surface | Result | Evidence |
| --- | --- | --- |
| Tags | live | Active KB tag list returned 1 safe tag summary. |
| Skills | live | Native skill list returned 5 preloaded skills and sandbox availability. |
| Favorites | live | User-scoped favorite lists returned 0 entries without exposing user or resource ids. |
| FAQ | blocked | Current active KB did not provide a safe FAQ entry PASS; PA records the surface as blocked instead of fabricating FAQ evidence. |
| Mutations | backlog | FAQ/tag/favorite/skill writes remain outside this safe read slice. |

## PASS Statement

`WNX-P2-06` passes as `live-partial`: PA calls real WeKnora native organization
APIs, exposes safe tags/skills/favorites status, renders the Capability Center
workflow, and keeps blocked/backlog areas explicit. Coverage moves
FAQ/tags/favorites/skills from `backlog` to `live-partial`, raising the ledger
from `10.75 / 15 = 71.7%` to `11.25 / 15 = 75.0%`.
