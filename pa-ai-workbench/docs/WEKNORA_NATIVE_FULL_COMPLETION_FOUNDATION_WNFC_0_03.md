# WNFC-0-03 Credential, Approval, and Audit Foundation

Date: 2026-06-24
Task: `WNFC-0-03: Credential, approval, and audit foundation`
Task type: credential/approval/security foundation plus PA BFF/business
DB/history/audit
Expected PASS evidence type: live API/browser plus audit proof
Current status: complete. Implementation, local validation, and live
API/browser/audit validation passed after explicit operator approval.

## 1. Scope

This task creates the shared PA safety foundation needed before WNFC high-risk
workflows:

- shared confirmation-token validation;
- shared masked/safe summary helpers;
- native mutation audit table;
- native audit BFF;
- one low-risk native mutation path wired through the shared pattern;
- smoke script for live API/browser plus audit validation.

Web Search remains excluded.

## 2. Implemented Foundation

Backend model:

- `backend/app/models.py`
  - Added `NativeMutationAudit`.
  - Stores only safe audit metadata: capability, operation, target type/id,
    source, status, confirmation method, token id, reason, safe request summary,
    safe response summary, sanitized error, and timestamp.
  - Does not store credentials, provider payloads, raw chunks, vectors, or raw
    upstream payloads.

Backend service:

- `backend/app/services/native_audit_service.py`
  - Added shared confirmation validation.
  - Added confirmation phrase id convention.
  - Added masked credential/status helper.
  - Added safe summary redaction for sensitive key and text shapes.
  - Added audit record create/update/list helpers.

Backend BFF:

- `backend/app/api/native_audit.py`
  - Added `GET /api/native-audit/events`.
  - Supports safe filters by capability, operation, target type/id, status, and
    limit.
- `backend/app/main.py`
  - Registered the native audit router.

Low-risk path wired:

- `backend/app/services/document_service.py`
  - `set_native_document_chunk_enabled`.
  - `delete_native_document_chunk`.
  - `delete_native_generated_question`.
  - These paths now accept the shared confirmation-token field and record native
    mutation audits.
  - Existing `confirm: true` remains as legacy compatibility, but the new WNFC
    smoke uses `confirm_token`.
- `backend/app/api/documents.py`
  - Chunk mutation responses now include `audit` and `confirmation`.
- `backend/app/schemas.py`
  - Added `NativeMutationAuditRead`, `NativeMutationAuditListResponse`, and
    `NativeConfirmationRead`.
  - Added optional `confirm_token` to chunk mutation requests.

Frontend:

- `frontend/src/api/client.ts`
  - Chunk toggle/delete now send the shared confirmation phrase through
    `confirm_token`.
  - Added `listNativeAuditEvents`.
  - Added native mutation audit response types.
- `frontend/src/pages/LibraryPage.tsx`
  - Shows a short safe audit status after chunk mutations.

Validation script:

- `backend/scripts/check_weknora_native_foundation.py`
  - Starts temporary PA backend/frontend.
  - Uploads a temporary WeKnora-backed document.
  - Waits for indexing.
  - Toggles one chunk using `confirm_token`.
  - Verifies the action response contains audit and confirmation metadata.
  - Queries `/api/native-audit/events`.
  - Checks the audit BFF does not return the raw confirmation phrase.
  - With `--browser`, verifies the Library chunk workflow renders.

## 3. Validation Completed

Static syntax:

```text
python3 -m py_compile backend/app/models.py backend/app/services/native_audit_service.py backend/app/api/native_audit.py backend/app/services/document_service.py backend/app/api/documents.py backend/app/main.py backend/scripts/check_weknora_native_foundation.py
PASS
```

Local audit-service validation:

```text
PYTHONPATH=backend backend/.venv/bin/python -c "<native audit in-memory sqlite validation>"
native_audit_service local validation PASS
```

Frontend type check:

```text
PATH=/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH ./node_modules/.bin/tsc --noEmit
PASS
```

Sensitive-shaped scan on changed foundation files:

```text
rg -n "SECRET_TEXT_RE|TOKEN\\s*=|API_KEY\\s*=|SERVICE_TOKEN\\s*=|PASSWORD\\s*=|SECRET\\s*=|AUTHORIZATION\\s*=" ...
0 matches
```

## 4. Live Validation

The live validation command was approved by the operator and passed:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/check_weknora_native_foundation.py --browser
```

Output:

```text
WNFC-0-03 native safety foundation
- decision: PASS
- evidence_type: live_api/browser_plus_audit
- confirmation: confirm_token
- audit: operation=weknora_chunk_toggle status=succeeded id=audit_d2abbad0798f
- audit_api: total=1
- masked_summary: raw_confirm_token_absent
- browser: Library DOM rendered native chunk workflow
```

The smoke performed a controlled live write against a temporary WeKnora-backed
document:

- temporary PA backend and frontend started;
- temporary document uploaded to the active WeKnora KB;
- document reached indexed status;
- one native chunk was toggled with `confirm_token`;
- the action response returned audit and confirmation metadata;
- `/api/native-audit/events` returned the mutation audit;
- raw confirmation phrase was absent from audit API output;
- Library browser DOM rendered the native chunk workflow.

## 5. Current Decision

`WNFC-0-03` is complete. The shared safety foundation is implemented and proven
by current live API/browser/audit evidence.
