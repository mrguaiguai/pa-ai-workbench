# WNFC-P4-03 Native Skill Management Evidence

Task: WNFC-P4-03
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser plus audit proof

## Scope

WNFC-P4-03 requires native skills list/read/create/update/delete/test flows to
pass through PA or record exact native blockers. This task now completes the
safe native skill management scope:

- Native skill list is live through PA and WeKnora.
- Native skill read/detail is live through `GET /api/v1/skills/{name}`.
- Native skill create/update/delete is live for managed `SKILL.md` files.
- Native skill test is live as non-executing metadata/file validation.
- PA gates create/update/delete/test with `CONFIRM_NATIVE_SKILL_MUTATION`.
- PA records `NativeMutationAudit` for create/update/test/delete.
- Capability Center renders live skill management status.

The implementation intentionally does not upload arbitrary resource files or
execute skill scripts. The native test route returns `execution_performed=false`
and reports file/script counts only.

## Native Source Changes

Native Go changes:

- `internal/agent/skills/skill.go`
  - Adds managed skill mutation input, safe file summaries, and non-executing
    test result types.
- `internal/types/interfaces/skill.go`
  - Extends `SkillService` with create/update/delete/test methods.
- `internal/application/service/skill_service.go`
  - Implements managed `SKILL.md` create/update/delete under the configured
    preloaded skills directory.
  - Validates skill metadata through the existing skill parser.
  - Prevents path traversal and rejects rename attempts.
  - Implements non-executing skill tests that report validation status,
    instruction presence/length, file count, script count, and sandbox status.
- `internal/handler/skill_handler.go`
  - Adds read/create/update/delete/test HTTP handlers.
  - The test handler returns `execution_performed=false`.
- `internal/router/router.go`
  - Registers Viewer+ list/read routes and Admin+ create/update/delete/test
    routes.
- `internal/application/service/skill_service_test.go`
  - Covers managed skill create/list/test/update/delete and rename rejection.

Why native source was needed:

- PA-only skill CRUD would have been fake because old WeKnora exposed only
  `GET /api/v1/skills`.
- The native service owns skill discovery/loading, path safety, and runtime
  route authorization.
- PA can only truthfully audit and surface the workflow after native routes
  exist.

## PA Changes

PA changes:

- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds safe adapters for native skill read/create/update/delete/test.
  - Redacts raw `instructions` from PA-facing summaries.
- `backend/app/services/organization_service.py`
  - Surfaces skill read/management/test readiness.
  - Adds confirmation-gated skill create/update/delete/test BFF flows.
  - Records `NativeMutationAudit` for skill create/update/test/delete.
- `backend/app/api/organization.py`
  - Adds `/api/organization/native/skills...` endpoints.
- `backend/app/services/native_status_service.py`
  - Adds skill management scope/status fields to the status center summary.
- `frontend/src/pages/CapabilityCenterPage.tsx`
  - Renders skill read, management, scope, test, and mutation status.
- `backend/scripts/check_weknora_native_skill_management_blocker.py`
  - Replaces the old blocker smoke with live API/browser plus audit proof.

## Current-Run Evidence

Native Go validation:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/app -w /app golang:1.26.0 \
  go test ./internal/application/service -run TestSkillServiceManagedLifecycle -count=1
```

Result: PASS.

Native handler/router compile validation:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/app -w /app golang:1.26.0 \
  go test ./internal/handler ./internal/router -run TestSkill -count=1
```

Result: PASS.

Docker runtime:

```bash
docker compose build app
docker compose up -d app
curl -fsS http://127.0.0.1:8080/health
```

Result: PASS, `{"status":"ok"}`.

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  knowledge_engine/backends/weknora_api_backend.py \
  backend/app/services/organization_service.py \
  backend/app/services/native_status_service.py \
  backend/app/api/organization.py \
  backend/scripts/check_weknora_native_skill_management_blocker.py
```

Result: PASS.

Live PA/WeKnora/browser smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_skill_management_blocker.py --browser
```

Current-run output:

```text
WeKnora native skill management
- decision: PASS
- evidence_type: live api/browser plus audit proof
- skills: list=live read=live create=live update=live delete=live test=live
- test_scope: metadata/file validation only; execution_performed=false
- audit: create/update/test/delete succeeded
- browser: Capability Center rendered skill management live/status proof
- output: sanitized
```

The smoke proves:

- PA can reach native skill list/read through WeKnora.
- Wrong confirmation token blocks skill create.
- Correct token creates a temporary managed skill.
- PA reads the temporary skill through the native read route with safe summary.
- PA updates the temporary skill through the native update route.
- PA tests the temporary skill through the native non-executing test route.
- PA deletes the temporary skill and cleans up validation data.
- Audit events exist for create/update/test/delete.
- Capability Center renders live skill management status.

## Sensitive Data Handling

- No service token, API key, raw skill instructions, raw skill file content,
  script body, script output, local DB content, provider payload, or prompt
  payload is present in this report.
- PA surfaces only skill names, booleans, counts, status labels, and sanitized
  audit metadata.
- Native test does not execute scripts.

## Status Impact

WNFC-P4-03 is `[x]` complete.

The broader FAQ/tags/favorites/skills scored group moves from `live-partial`
to `live-full`. Aggregate WNFC score moves from `13.50 / 14 = 96.4%` to
`14.00 / 14 = 100.0%`.

Final readiness is still not complete because WNFC-P6-02 must produce and
verify the final completion report.
