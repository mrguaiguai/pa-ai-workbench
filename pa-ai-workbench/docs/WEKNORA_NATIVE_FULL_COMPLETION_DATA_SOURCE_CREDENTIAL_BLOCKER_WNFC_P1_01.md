# WNFC-P1-01 Data-Source Connector Credential Setup Scope Report

Date: 2026-06-24
Task: `WNFC-P1-01: Data-source connector credential setup`
Task type: WeKnora native capability access plus credential/approval/security
Evidence type: excluded evidence
Status: excluded by explicit user scope decision. No credential-bearing
connector PASS is claimed or required for WNFC 100%.

## 1. Scope

`WNFC-P1-01` originally required at least one credential-bearing native
data-source connector to be configured live with masked storage/status. On
2026-06-24, the user explicitly removed this credential-bearing connector setup
slice from the WNFC 100% scope.

This report preserves the original blocker audit for traceability, but the
current decision is `[b]`: Notion/Yuque/Feishu credential setup is not required
for final readiness. This task did not create a mock connector, fixture
credential, demo workspace, or fake configured state.

## 2. Native Source Audit

Native WeKnora already exposes the needed PA-first credential setup path:

- `internal/router/router.go`
  - `GET /api/v1/datasource/types`
  - `POST /api/v1/datasource/validate-credentials`
  - `POST /api/v1/datasource`
  - `GET /api/v1/datasource`
  - `GET /api/v1/datasource/:id`
  - `PUT /api/v1/datasource/:id`
  - `DELETE /api/v1/datasource/:id`
  - `PUT /api/v1/datasource/:id/credentials`
  - `DELETE /api/v1/datasource/:id/credentials/:field`
  - `POST /api/v1/datasource/:id/validate`
  - `GET /api/v1/datasource/:id/resources`
  - `POST /api/v1/datasource/:id/sync`
  - `POST /api/v1/datasource/:id/pause`
  - `POST /api/v1/datasource/:id/resume`
  - `GET /api/v1/datasource/:id/logs`
  - `GET /api/v1/datasource/logs/:log_id`
- `internal/handler/datasource_credentials.go`
  - data-source credentials are an atomic `credentials` map;
  - PUT returns only configured metadata, not raw credential values;
  - DELETE clears the logical `credentials` field.
- `internal/application/service/datasource_service.go`
  - `UpdateDataSourceCredentials` injects the credential map into the encrypted
    native config and runs live connector validation before saving.
- `internal/types/datasource.go`
  - `DataSourceConfig` owns connector credentials and resource IDs;
  - comments state secret values are not returned through API response DTOs.
- `internal/datasource/connector.go`
  - registered real connectors include Feishu, Notion, Yuque, and RSS;
  - metadata-only connector types outside those registrations cannot count
    without a native connector implementation.

Credential-bearing registered connector requirements:

- Notion: `api_key` internal integration token. The integration must have access
  to at least one page or database.
- Yuque: `api_token`; optional `base_url` only for private/enterprise Yuque.
  The token must access at least one namespace/book/repo.
- Feishu/Lark: `app_id` and `app_secret`. The app must have document/wiki/drive
  permissions and access to at least one workspace/wiki space.

## 3. PA Surface Audit

PA currently has safe read/sync surfaces, but not a credential-bearing connector
setup workflow:

- `knowledge_engine/backends/weknora_api_backend.py`
  - lists connector types;
  - lists native data sources;
  - reads data-source detail by native id;
  - creates only RSS data sources through a helper;
  - validates, lists resources, reads sync logs, syncs, pauses, and resumes
    existing sources.
- `backend/app/api/data_source.py`
  - exposes overview, detail by safe index, and confirmed sync/pause/resume.
- `backend/app/services/data_source_service.py`
  - keeps connector create/update/delete, credential forms, raw credential
    validation, external resource listing, raw logs, and deletion-sync controls
    in backlog.
- Existing smoke:
  - `backend/scripts/check_weknora_native_data_source_management.py` validates
    the current safe read/sync surface without printing secrets.

PA-first implementation remains possible if this slice is reopened later and
real credentials are supplied. A Go native exception is not needed for Notion,
Yuque, or Feishu credential setup.

## 4. Current Live Evidence

Masked env-key check:

```text
Checked key names only in:
- /Users/mac/Downloads/WeKnora-main/.env
- /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/.env
- /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/backend/.env

Matching Feishu/Notion/Yuque/DataSource/Connector credential keys: 0
```

Live data-source smoke:

```text
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/check_weknora_native_data_source_management.py
```

Output:

```text
WeKnora native data source connector management readiness
- decision: PASS
- evidence_type: live_api
- coverage_state: live-partial
- connector_types: status=live count=12
- data_sources: status=live count=1 credentials_configured=0
- connector_read: live detail=live
- resources: blocked
- validation: blocked
- sync_control: overview=blocked blocked_path=blocked confirmed_path=not_requested
- pause_resume: pause=not_requested resume=not_requested
- mutations: backlog
```

The one current data source is enough for the earlier RSS live-partial WNX
evidence and, after the user scope decision, the completed `WNFC-P1-02` and
`WNFC-P1-03` RSS workflows define the in-scope data-source WNFC target.
`credentials_configured=0` remains true but no longer blocks WNFC final
readiness.

## 5. Historical Blocker Request

This request is no longer active for WNFC 100%. If the slice is reopened later,
provide one real credential-bearing connector path. Choose one:

1. Notion
   - required credential: internal integration token for `api_key`;
   - required workspace permission: share at least one page or database with
     the integration;
   - expected config handoff: provide via a local secret file or environment
     variables that are not committed, then tell Codex the key names only.
2. Yuque
   - required credential: personal/team `api_token`;
   - required workspace permission: at least one accessible namespace/book/repo;
   - optional: `base_url` for private/enterprise Yuque.
3. Feishu/Lark
   - required credentials: `app_id` and `app_secret`;
   - required permissions: document/wiki/drive export and download permissions;
   - required workspace: at least one accessible workspace/wiki space.

Minimal access level: read-only access to one small test page/database/book/wiki
space is enough for `WNFC-P1-01`; later `WNFC-P1-02` and `WNFC-P1-03` will need
resource selection, sync, and RAG evidence.

If credentials are supplied in a later reopened scope, validation will run:

1. PA masked credential presence check without printing values.
2. Native `POST /api/v1/datasource/validate-credentials`.
3. Native data-source create or credential update through PA BFF.
4. Masked status proof that exactly one credential-bearing connector is
   configured.
5. Sensitive scan proving no raw credential values were written to docs, code,
   output, or PA business DB.

## 6. Current Decision

`WNFC-P1-01` is `[b]` by explicit user decision. It is not counted as an
unfinished or blocking task for WNFC 100%.

No credential-bearing connector PASS is claimed. No Web Search work was
performed. The in-scope data-source group is covered by the existing RSS
workflow evidence in `WNFC-P1-02` and `WNFC-P1-03`.
