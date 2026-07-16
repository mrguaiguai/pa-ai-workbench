# WNFC-P2-01 MCP CRUD and Credentials Evidence

Task: WNFC-P2-01
Date: 2026-06-24
Decision: PASS
Evidence type: live api plus audit proof

## Scope

This task verifies PA-first access to WeKnora native MCP service CRUD and the
native MCP credentials subresource.

Included:

- PA BFF creates a temporary native MCP service through `POST /api/v1/mcp-services`.
- PA BFF reads the created native MCP service through the existing service detail path.
- PA BFF updates the service through `PUT /api/v1/mcp-services/{id}`.
- PA BFF writes credential metadata through `PUT /api/v1/mcp-services/{id}/credentials`.
- PA BFF clears credential metadata through `DELETE /api/v1/mcp-services/{id}/credentials/{field}`.
- PA BFF deletes the temporary service through `DELETE /api/v1/mcp-services/{id}`.
- Every mutation requires `confirm_token` and writes a `NativeMutationAudit` event.
- PA responses expose only masked service and credential metadata.

Excluded from this task:

- MCP resource/tool/prompt discovery. That remains WNFC-P2-02.
- MCP tool execution. That remains WNFC-P2-03.
- Treating a configured service URL as tested. No external MCP probe was claimed.

## Native Audit

Native WeKnora already provides the required service-level and credential-level
surfaces:

- `POST /api/v1/mcp-services`
- `GET /api/v1/mcp-services`
- `GET /api/v1/mcp-services/{id}`
- `PUT /api/v1/mcp-services/{id}`
- `DELETE /api/v1/mcp-services/{id}`
- `PUT /api/v1/mcp-services/{id}/credentials`
- `DELETE /api/v1/mcp-services/{id}/credentials/{field}`

Native response DTOs omit raw MCP secret fields and return credential presence
metadata only. The main update path intentionally ignores secret values; PA uses
the dedicated credentials subresource for credential writes.

## PA Implementation

Changed files:

- `knowledge_engine/backends/weknora_api_backend.py`
  - Added native MCP create/update/delete adapter methods.
  - Added native MCP credentials update/clear adapter methods.
  - Kept public service and credential responses safe and masked.
- `backend/app/services/mcp_service.py`
  - Added confirmation-gated MCP CRUD and credential mutation service functions.
  - Added `NativeMutationAudit` recording for create/update/delete/credential update/credential clear.
  - Kept MCP tool/resource execution outside P2-01.
- `backend/app/api/mcp.py`
  - Added PA BFF endpoints for native MCP create/update/delete and credential update/clear.
- `backend/scripts/check_weknora_native_mcp_crud_credentials.py`
  - Added current-run live smoke for P2-01.
- `backend/scripts/check_weknora_native_mcp_management.py`
  - Updated the existing MCP readiness smoke so mutation status can reflect the new partial CRUD/credential completion.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Added this report to the WNFC report inventory.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_mcp_crud_credentials.py
```

Current-run output:

```text
WeKnora native MCP CRUD and credentials
- decision: PASS
- evidence_type: live api plus audit proof
- service_crud: create=live read=live update=live delete=live
- credentials: update=masked_live clear=live
- audit: mcp mutation events recorded
- cleanup: temporary native MCP service deleted
```

The smoke starts a temporary PA backend, calls the live WeKnora native API
through the PA BFF, creates a temporary MCP service, updates it, writes and
clears a credential field, deletes the service, and verifies the temporary
service is absent from the final PA overview.

## Masking and Audit Proof

The live smoke checks:

- Create/update/delete responses contain no raw native URL, headers, auth
  config, env vars, stdio config, or credential payload.
- Credential update response reports masked metadata only.
- Service detail reports configured credential counts without returning the raw
  credential.
- `/api/native-audit/events?capability=mcp&limit=20` contains succeeded events
  for:
  - `weknora_mcp_service_create`
  - `weknora_mcp_service_update`
  - `weknora_mcp_credentials_update`
  - `weknora_mcp_credentials_clear`
  - `weknora_mcp_service_delete`
- Audit API output does not return raw credential material.

## Remaining Blockers

WNFC-P2-01 does not complete MCP as a capability group. The following remain
open:

- WNFC-P2-02: real configured MCP service resources/tools/prompts list and read.
- WNFC-P2-03: approval-gated real MCP tool execution with timeout, audit, and
  history.
- WNFC-P1-01: credential-bearing connector setup remains blocked by missing
  real Notion/Yuque/Feishu credentials and accessible workspace.

Aggregate WNFC score remains `11.50 / 14 = 82.1%` because MCP is still
`live-partial` until P2-02 and P2-03 are complete.
