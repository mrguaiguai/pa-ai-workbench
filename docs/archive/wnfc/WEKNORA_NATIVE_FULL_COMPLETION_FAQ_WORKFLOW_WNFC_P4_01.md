# WNFC-P4-01 FAQ Full Workflow Evidence

Task: WNFC-P4-01
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser plus audit proof

## Scope

WNFC-P4-01 requires the native FAQ workflow to work through PA with real
WeKnora capability, not mock or fixture-only data. This task validates:

- FAQ list and read.
- FAQ create, update, import, and delete through confirmation-gated PA BFF.
- FAQ search through native WeKnora.
- FAQ import progress through native WeKnora.
- `NativeMutationAudit` for FAQ mutations.
- Capability Center browser proof for the FAQ status surface.

The current default KB is a document KB, not a FAQ KB. The smoke therefore
creates an isolated validation FAQ KB, drives the workflow through PA, then
deletes the validation KB in cleanup. The validation KB is visible during the
smoke because native `is_temporary=true` KBs are hidden from list APIs and would
not allow browser/status proof.

## Native Source Audit

WeKnora already exposes the required native FAQ routes:

- `internal/router/router.go`
  - `GET /api/v1/knowledge-bases/:id/faq/entries`
  - `GET /api/v1/knowledge-bases/:id/faq/entries/export`
  - `GET /api/v1/knowledge-bases/:id/faq/entries/:entry_id`
  - `POST /api/v1/knowledge-bases/:id/faq/entries`
  - `POST /api/v1/knowledge-bases/:id/faq/entry`
  - `PUT /api/v1/knowledge-bases/:id/faq/entries/:entry_id`
  - `DELETE /api/v1/knowledge-bases/:id/faq/entries`
  - `POST /api/v1/knowledge-bases/:id/faq/search`
  - `GET /api/v1/faq/import/progress/:task_id`
- `internal/handler/faq.go`
  - Implements list, create, update, delete, search, export, batch upsert, and
    import progress handlers.
  - Routes are Viewer+ for reads/search and owner/admin write-gated for
    mutations.
- `internal/application/service/knowledge_faq.go`
  - Validates that the target KB is `type=faq`.
  - Creates FAQ chunks, writes FAQ metadata, indexes FAQ content, supports
    search, and converts chunks back to FAQ entries.
- `internal/types/faq.go`
  - Defines `FAQEntry`, `FAQEntryPayload`, `FAQBatchUpsertPayload`,
    `FAQSearchRequest`, and `FAQImportProgress`.

No native Go source change was needed. Source audit did reveal one required
runtime precondition: a newly created FAQ KB must have a valid
`embedding_model_id`, because FAQ create immediately indexes the entry.

## Changes

PA changes:

- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds safe adapter methods for temporary validation FAQ KB creation,
    KB cleanup, FAQ list/read/create/update/delete/search/import/progress.
  - Validation FAQ KB creation inherits the active default KB embedding/summary
    model IDs so native FAQ indexing can run.
  - FAQ entries are returned as safe summaries with counts and status flags;
    raw question and answer text are not surfaced.
- `backend/app/services/organization_service.py`
  - Adds FAQ workflow BFF functions.
  - Adds `CONFIRM_NATIVE_FAQ_MUTATION` confirmation gating for create, update,
    import, and delete.
  - Records `NativeMutationAudit` for FAQ mutations.
  - Upgrades FAQ overview to discover a visible FAQ KB instead of only testing
    the default document KB.
- `backend/app/api/organization.py`
  - Adds PA FAQ endpoints under `/api/organization/native/faq/...`.
- `frontend/src/pages/CapabilityCenterPage.tsx`
  - Prioritizes `faq_status` and `faq_count` in the organization capability
    card summary.
- `backend/scripts/check_weknora_native_faq_workflow.py`
  - Runs the full current-run FAQ workflow through PA and native WeKnora.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to the WNFC evidence inventory.

## Current-Run Evidence

Live PA/WeKnora/browser/audit smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_faq_workflow.py --browser
```

Current-run output:

```text
WeKnora native FAQ full workflow
- decision: PASS
- evidence_type: live api/browser plus audit proof
- faq_kb: temporary=true cleanup=scheduled
- workflow: create=live read=live update=live search=live import_progress=live delete=live
- audit: create/update/import/delete succeeded
- browser: Capability Center rendered FAQ status
- output: sanitized
```

The smoke proves:

- A validation FAQ KB can be created with real native model configuration.
- FAQ create is blocked without the confirmation token.
- FAQ create/read/update/search/import-progress/delete all run through PA BFF
  against native WeKnora.
- FAQ create/update/import/delete audits are present and succeeded.
- The audit API does not expose the raw confirmation token.
- Capability Center renders `faq_status: live`.
- Validation data is cleaned up after the evidence is captured.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  knowledge_engine/backends/weknora_api_backend.py \
  backend/app/services/organization_service.py \
  backend/app/api/organization.py \
  backend/scripts/check_weknora_native_faq_workflow.py \
  backend/scripts/check_weknora_native_full_completion_acceptance.py
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

- No service token, API key, raw question text, raw answer text, raw chunk
  content, provider payload, local DB path, or raw upstream response is present
  in this report.
- FAQ API responses expose counts, booleans, status labels, and entry ids needed
  for mutation continuity; they do not echo questions or answers.
- Audit summaries record action and counts only, not question or answer bodies.
- The smoke rejects secret-shaped fields and raw WNFC validation text in PA
  responses.

## Status Impact

WNFC-P4-01 is `[x]` complete.

The FAQ slice is now live-full, but the broader FAQ/tags/favorites/skills
scored group remains `live-partial` until WNFC-P4-02 and WNFC-P4-03 close tag,
favorite, and native skill mutation workflows. Aggregate WNFC score remains
`12.00 / 14 = 85.7%`.
