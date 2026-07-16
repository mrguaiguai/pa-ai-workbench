# WNFC-P3-03 Parser And Storage Diagnostics Evidence

Task: WNFC-P3-03
Date: 2026-06-24
Decision: PASS
Evidence type: live api/browser

## Scope

WNFC-P3-03 requires parser and storage diagnostics to be real, not only
configured. This task completes the model/embedding/rerank/parser scored group
by proving:

- Native parser engine availability check runs through WeKnora.
- Native storage engine active check runs through WeKnora.
- PA status surfaces show parser/storage counts without secret fields.
- A sanitized sample markdown document is actually parsed, indexed, chunked, and
  cleaned up through the PA-to-WeKnora document path.
- Existing Capability Center status UI renders parser/storage diagnostics.

## Native Source Audit

WeKnora already exposes the required native routes:

- `internal/router/router.go`
  - `GET /api/v1/system/parser-engines` is Viewer-gated.
  - `POST /api/v1/system/parser-engines/check` is Admin-gated.
  - `GET /api/v1/system/storage-engine-status` is Viewer-gated.
  - `POST /api/v1/system/storage-engine-check` is Admin-gated.
- `internal/handler/system.go`
  - `ListParserEngines` merges locally registered engines with DocReader
    discovered engines.
  - `CheckParserEngines` runs parser availability checks with current override
    config without saving it.
  - `GetStorageEngineStatus` reports allowed and available storage engines.
  - `CheckStorageEngine` actively tests one selected storage provider and
    sanitizes storage connectivity errors.
- `internal/infrastructure/docparser/engine_registry.go`
  - registers `builtin`, `simple`, `weknoracloud`, `mineru`, and
    `mineru_cloud` parser engines.
  - marks `simple` available without external services and `builtin`
    available when DocReader is connected.
- `internal/types/docparser.go`
  - defines `ParserEngineInfo`, `ReadRequest`, `ReadResult`, and parsed chunk
    structures used by the document pipeline.
- `internal/types/knowledgebase.go`
  - defines storage provider config, provider inference, and provider schemes.

No native Go source change was needed for this task. PA-only configured status
would not be enough, so the smoke combines native active diagnostics with a real
sample document parse/index path.

## Changes

PA changes:

- `backend/app/api/native_status.py`
  - Raises `/api/native/status` `limit` ceiling from 10 to 20 so all WNFC
    capability groups, including model/parser, can be rendered in the status
    center.
- `backend/app/services/native_status_service.py`
  - Aligns the internal native status item limit with the API ceiling.
- `backend/scripts/check_weknora_native_parser_storage_diagnostics.py`
  - Calls native parser-engine active check.
  - Calls native local storage active check.
  - Starts a temporary PA backend and reads `/api/model/native/overview`.
  - Uploads a sanitized markdown sample document to the current native KB.
  - Waits until the PA/WeKnora document reaches `indexed`.
  - Verifies native spans and non-empty chunks.
  - Deletes the temporary PA/native document.
  - Optionally starts the frontend and verifies Capability Center parser/storage
    status UI with `--browser`.
- `frontend/src/pages/CapabilityCenterPage.tsx`
  - Requests enough native status groups for the model/parser card to render.
  - Prioritizes `parser_engine_count` and `storage_engine_count` in the
    model/parser capability card summary.
- `backend/scripts/check_weknora_native_full_completion_acceptance.py`
  - Adds this report to the WNFC evidence inventory.

No native Go file was changed, so no Go test or Docker rebuild is required for
this task.

## Validation Evidence

Python compile:

```bash
backend/.venv/bin/python -m py_compile \
  backend/app/api/native_status.py \
  backend/app/services/native_status_service.py \
  backend/scripts/check_weknora_native_parser_storage_diagnostics.py \
  backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS.

Frontend typecheck:

```bash
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  ./node_modules/typescript/bin/tsc --noEmit
```

Result: PASS.

Live PA/WeKnora parser/storage diagnostics smoke:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_parser_storage_diagnostics.py
```

Current-run output:

```text
WeKnora native parser/storage diagnostics
- decision: PASS
- evidence_type: live api
- parser_check: engines=7 available=4 connected=true
- storage_check: provider=local ok=true message=本地存储无需检测
- pa_overview: parser_engines=7 parser_available=4 storage_engines=7 storage_available=2
- sample_parse: status=indexed parse_status=completed chunks=1 spans_source=weknora_api
- cleanup: document_delete=delete
- output: sanitized
```

Live browser/status UI evidence:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_parser_storage_diagnostics.py --browser
```

Result: PASS. The existing Capability Center renders:

- `Model / embedding / rerank / parser`
- `parser_engine_count`
- `storage_engine_count`
- `/api/model/native/overview`

WNFC acceptance checker:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_acceptance.py
```

Result: PASS in in-progress mode.

Diff hygiene:

```bash
git diff --check
```

Result: PASS in the PA workbench repository and the outer WeKnora repository.

## Sensitive Data Handling

- No API key, service token, raw DocReader address, raw provider payload, raw
  sample document content, storage endpoint, or credential value is present in
  this report.
- The script rejects secret-shaped fields in PA overview payloads.
- Output is limited to counts, booleans, status labels, and bounded sanitized
  messages.
- The temporary sample document contains only synthetic WNFC validation text and
  is deleted after validation.

## Status Impact

WNFC-P3-03 is `[x]` complete.

With WNFC-P3-01, WNFC-P3-02, and WNFC-P3-03 complete, the
Model/embedding/rerank/parser group reaches WNFC `full-complete`. Aggregate WNFC
score increases from `11.50 / 14 = 82.1%` to `12.00 / 14 = 85.7%`.
