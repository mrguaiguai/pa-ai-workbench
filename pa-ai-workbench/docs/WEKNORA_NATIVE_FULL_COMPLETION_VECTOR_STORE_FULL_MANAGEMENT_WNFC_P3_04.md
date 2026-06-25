# WNFC-P3-04 Vector-Store Full Management Evidence

Task: WNFC-P3-04
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser plus docker runtime plus audit proof

## Scope

WNFC-P3-04 asks for native vector-store full management: safe native test,
CRUD/rebind where native ownership allows, embedding compatibility, audit, and
browser proof.

This task proves the real native/PA vector-store management lane:

- PA reads native vector-store type/list/detail through WeKnora.
- PA proves the active KB is bound to a live vector store.
- PA proves embedding compatibility for the active KB/vector-store lane.
- PA performs a confirmation-gated native saved/env store connectivity test.
- PA performs a confirmation-gated raw Qdrant connection test.
- PA creates a saved user-owned Qdrant vector store through native WeKnora.
- PA updates the saved user store display name through native WeKnora.
- PA tests the saved user store by safe index through native WeKnora.
- PA deletes the temporary saved user store through native WeKnora.
- PA records `NativeMutationAudit` for every external probe and mutation.
- Capability Center renders vector-store live status.

Native WeKnora still makes `knowledge_base.vector_store_id` immutable after
creation. PA therefore treats KB rebind as `native_immutable` rather than
pretending a rebind mutation exists.

## Native Source Audit

WeKnora already exposes vector-store management routes:

- `internal/router/router.go`
  - `GET /api/v1/vector-stores/types`
  - `GET /api/v1/vector-stores`
  - `POST /api/v1/vector-stores`
  - `GET /api/v1/vector-stores/:id`
  - `PUT /api/v1/vector-stores/:id`
  - `DELETE /api/v1/vector-stores/:id`
  - `POST /api/v1/vector-stores/:id/test`
  - `POST /api/v1/vector-stores/test`
- `internal/handler/vectorstore.go`
  - List/detail responses use `types.NewVectorStoreResponse`, which masks
    stored/env connection config.
  - Env stores are read-only and cannot be updated or deleted.
  - Raw test/create accepts connection config and probes external systems.
  - Update is name-only for saved user stores.
- `internal/application/service/vectorstore.go`
  - Create validates connection/index config and actively tests the connection
    before saving.
  - Delete refuses stores that still have active KB bindings.
  - Env stores are derived from `RETRIEVE_DRIVER` and cached for resolution.
- `docs/api/knowledge-base.md`
  - `vector_store_id` is set at KB creation time and cannot be changed by the
    update endpoint.

No native Go source change was needed. WeKnora already exposes the required
native CRUD/test API for vector-store management. PA now wires that API through
confirmation-gated BFF endpoints with audit and sanitized responses.

## Changes

PA changes:

- `backend/app/services/vector_store_service.py`
  - Adds `embedding_compatibility`.
  - Adds confirmation-gated raw test, create, update-name, and guarded delete
    paths for native vector stores.
  - Wraps confirmed saved/env store tests with `NativeMutationAudit`.
  - Wraps raw test/create/update/delete with `NativeMutationAudit`.
  - Returns only safe store summaries and safe index targets.
- `backend/app/api/vector_store.py`
  - Exposes PA BFF routes for native raw test, create, update, delete, and
    saved/env test.
- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds native vector-store raw-test/create/update/delete adapter methods.
- `frontend/src/pages/CapabilityCenterPage.tsx`
  - Prioritizes vector-store `store_read_status`, `store_test_status`,
    `mutations_status`, and `embedding_status` in the native capability card.
- `backend/scripts/check_weknora_native_vector_store_full_management.py`
  - Starts temporary PA backend/frontend services.
  - Reads vector-store overview/detail through PA.
  - Verifies embedding compatibility and active KB vector-store binding.
  - Verifies unconfirmed test is blocked.
  - Runs a confirmed native saved/env vector-store connectivity test.
  - Runs confirmed raw Qdrant test.
  - Creates, updates, tests, and deletes a temporary saved Qdrant user store.
  - Verifies `NativeMutationAudit` and audit API output.
  - Verifies Capability Center browser evidence.
- `backend/scripts/check_weknora_native_vector_store_management.py`
  - Keeps the earlier WNX smoke compatible with the stricter WNFC blocker
    classification.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this blocker report to the WNFC evidence inventory.

## Current-Run Evidence

Live PA/WeKnora/browser/audit smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_vector_store_full_management.py --browser
```

Current-run output:

```text
WeKnora native vector-store full management
- decision: PASS
- evidence_type: live api/browser plus docker runtime plus audit proof
- store_types: status=live count=7
- stores: status=live count=1 env=1 user=0
- safe_test: confirmed=live audit=succeeded
- raw_test: confirmed=live engine=qdrant
- user_store_crud: create=live update=live test=live delete=live
- embedding_compatibility: status=live dimension=1024 kb_source=env
- native_immutable: kb_rebind
- browser: Capability Center rendered vector-store live/status proof
- output: sanitized
```

Current recheck without browser:

```text
WeKnora native vector-store full management
- decision: PASS
- evidence_type: live api plus docker runtime plus audit proof
- store_types: status=live count=7
- stores: status=live count=1 env=1 user=0
- safe_test: confirmed=live audit=succeeded
- raw_test: confirmed=live engine=qdrant
- user_store_crud: create=live update=live test=live delete=live
- embedding_compatibility: status=live dimension=1024 kb_source=env
- native_immutable: kb_rebind
- output: sanitized
```

The smoke proves:

- Native vector-store catalog is live.
- Current runtime starts with one read-only `env` store and zero persisted user
  stores.
- Existing saved/env store test works with explicit confirmation.
- A local disposable Qdrant Docker runtime is reachable from the WeKnora app
  container.
- Raw Qdrant test works with explicit confirmation.
- Native saved user-store create/update/test/delete works through PA BFF.
- `NativeMutationAudit` records `weknora_vector_store_test` as `succeeded`.
- `NativeMutationAudit` records raw test, create, update, and delete as
  `succeeded`.
- Audit API returns token id only and not the raw confirmation token.
- Capability Center shows the vector-store card with live mutation status.
- The temporary saved user store is deleted before the smoke exits.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  backend/app/api/vector_store.py \
  backend/app/services/vector_store_service.py \
  backend/scripts/check_weknora_native_vector_store_full_management.py \
  backend/scripts/check_weknora_native_vector_store_management.py \
  knowledge_engine/backends/weknora_api_backend.py
```

Result: PASS.

Frontend typecheck:

```bash
cd frontend
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  ./node_modules/typescript/bin/tsc --noEmit
```

Result: PASS.

WNFC acceptance checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS in in-progress mode. `final_ready=false` remains expected.

Diff hygiene:

```bash
git diff --check
```

Result: PASS in the PA workbench repository and the outer WeKnora repository.

## Sensitive Data Handling

- No service token, API key, raw native store id, DSN, host, port, username,
  password, database name, collection name, index name, connection config, or
  provider payload appears in this report.
- PA responses expose safe index values instead of raw vector-store ids.
- The confirmed test response and audit API are checked for secret-shaped fields
  and raw confirmation-token leakage.
- Output is limited to statuses, counts, dimensions, and blocker labels.

## Status Impact

WNFC-P3-04 is `[x]` complete.

The vector-store scored group moves to WNFC `live-full`. Aggregate WNFC score
is now `13.50 / 14 = 96.4%`. Final WNFC readiness remains blocked by other
in-scope non-Web-Search tasks.
