# WNFC-P4-02 Tags And Favorites Mutations Evidence

Task: WNFC-P4-02
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser plus audit proof

## Scope

WNFC-P4-02 requires native tag and favorite mutations to work through PA with
real WeKnora capability, confirmation gating, audit records, and browser proof.
This task validates:

- Tag list/create/update/delete for a native knowledge base.
- Favorite add/remove/toggle for a native KB resource.
- `NativeMutationAudit` for tag and favorite mutations.
- Capability Center browser proof for tag/favorite mutation readiness.

Favorite update is not a native WeKnora route because a favorite has no mutable
fields. PA exposes a toggle contract that calls the native add/remove routes and
records both operations.

## Native Source Audit

WeKnora already exposes the required native routes:

- `internal/router/router.go`
  - `GET /api/v1/knowledge-bases/:id/tags`
  - `POST /api/v1/knowledge-bases/:id/tags`
  - `PUT /api/v1/knowledge-bases/:id/tags/:tag_id`
  - `DELETE /api/v1/knowledge-bases/:id/tags/:tag_id`
  - `GET /api/v1/user/favorites`
  - `POST /api/v1/user/favorites`
  - `DELETE /api/v1/user/favorites/:type/:id`
- `internal/handler/tag.go`
  - Implements tag list/create/update/delete.
  - Tag reads are Viewer+; tag writes are KB owner/admin/write-gated.
- `internal/application/service/tag.go`
  - Validates KB existence, duplicate tag names, tag updates, and safe deletion
    rules.
- `internal/types/tag.go`
  - Defines `KnowledgeTag`, `KnowledgeTagWithStats`, and usage counts.
- `internal/handler/user_resource_favorite.go`
  - Implements user-scoped favorite list/add/remove.
- `internal/types/user_resource_favorite.go`
  - Defines supported favorite resource types: `kb` and `agent`.

No native Go source change was needed.

## Changes

PA changes:

- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds safe adapter methods for native tag create/update/delete.
  - Adds safe adapter methods for favorite add/remove.
- `backend/app/services/organization_service.py`
  - Adds `CONFIRM_NATIVE_ORGANIZATION_MUTATION`.
  - Adds tag list/create/update/delete BFF functions.
  - Adds favorite toggle BFF function backed by native add/remove.
  - Records `NativeMutationAudit` for tag and favorite mutations.
  - Updates organization mutation readiness to show tag/favorite live and skill
    management still backlog.
- `backend/app/api/organization.py`
  - Adds PA endpoints under `/api/organization/native/tags/...`.
  - Adds `/api/organization/native/favorites/toggle`.
- `backend/app/services/native_status_service.py`
  - Surfaces favorite and mutation readiness in the native status center.
- `frontend/src/pages/CapabilityCenterPage.tsx`
  - Renders tag/favorite mutation readiness in the organization capability
    summary.
- `backend/scripts/check_weknora_native_tags_favorites_workflow.py`
  - Runs the current-run tag/favorite workflow through PA and native WeKnora.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to the WNFC evidence inventory.

## Current-Run Evidence

Live PA/WeKnora/browser/audit smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_tags_favorites_workflow.py --browser
```

Current-run output:

```text
WeKnora native tags and favorites mutations
- decision: PASS
- evidence_type: live api/browser plus audit proof
- tags: create=live update=live delete=live
- favorites: add=live remove=live toggle=live
- audit: tag/favorite mutations succeeded
- browser: Capability Center rendered mutation status
- output: sanitized
```

The smoke proves:

- A validation KB can be created and cleaned up after the run.
- Tag create is blocked without the confirmation token.
- Tag create/update/delete run through PA BFF against native WeKnora.
- Favorite add/remove/toggle run through PA BFF against native WeKnora.
- Tag and favorite audit events are present and succeeded.
- The audit API does not expose the raw confirmation token.
- Capability Center renders `tag_mutations: live` and
  `favorite_mutations: live`.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  knowledge_engine/backends/weknora_api_backend.py \
  backend/app/api/organization.py \
  backend/app/services/organization_service.py \
  backend/app/services/native_status_service.py \
  backend/scripts/check_weknora_native_tags_favorites_workflow.py
```

Result: PASS.

Live API/browser smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_tags_favorites_workflow.py --browser
```

Result: PASS.

## Sensitive Data Handling

- No service token, API key, raw user id, raw provider payload, raw upstream
  response, or local DB content is present in this report.
- Tag and favorite responses expose statuses, counts, booleans, and safe
  mutation continuity ids only.
- Audit summaries record action, target type, and safe booleans only; raw
  confirmation tokens are not exposed.

## Status Impact

WNFC-P4-02 is `[x]` complete.

The tag and favorite mutation slice is live, but the broader
FAQ/tags/favorites/skills scored group remains `live-partial` until WNFC-P4-03
closes native skill management or records an exact native blocker. Aggregate
WNFC score remains `12.00 / 14 = 85.7%`.
