# WNFC-P5-04 Wiki Global Maintenance Evidence

Task: `WNFC-P5-04: Wiki global maintenance closure`

Decision: `[x]` complete

Evidence type: live API plus audit proof

## Scope

WNFC-P5-04 covers native Wiki global maintenance:

- rebuild-links
- auto-fix
- create a controlled persisted Wiki issue
- issue-status mutation

The fix keeps PA as the BFF and audit owner, while adding one controlled native
exception: a real owner/admin native route to create a persisted
`wiki_page_issues` row for a Wiki KB. The validation no longer manufactures a
fake issue or updates a database row directly.

## Native Source Patch

- `internal/router/router.go`
  - Adds `POST /api/v1/knowledgebase/:kb_id/wiki/issues` guarded by
    `OwnedWikiKBOrAdmin`.
- `internal/handler/wiki_page.go`
  - Adds `CreateIssue`, validates the Wiki KB, trims and bounds public fields,
    accepts only `pending`, `ignored`, or `resolved`, and writes through
    `wikiService.CreateIssue`.
  - Updates issue status with `UpdateIssueStatusForKB` so `kb_id` and `issue_id`
    must match.
- `internal/types/interfaces/wiki_page.go`
  - Adds `UpdateIssueStatusForKB` to service and repository contracts.
- `internal/application/service/wiki_page.go`
  - Adds the KB-scoped issue status service method.
- `internal/application/repository/wiki_page.go`
  - Adds KB-scoped issue status update and returns not found when no matching
    issue row exists.

## PA Changes

- `knowledge_engine/backends/weknora_api_backend.py`
  - Adds `create_wiki_issue` for native `POST /wiki/issues`.
- `backend/app/schemas.py`
  - Adds `NativeWikiIssueCreateRequest`.
- `backend/app/services/wiki_service.py`
  - Adds confirmation token `CREATE_NATIVE_WIKI_ISSUE`.
  - Records `NativeMutationAudit` operation `weknora_wiki_create_issue`.
  - Keeps existing audit operations for rebuild-links, auto-fix, and
    issue-status.
- `backend/app/api/wiki.py`
  - Adds `POST /api/wiki/native/issues`.
  - Converts native backend failures to sanitized HTTP 503 responses.
- `backend/scripts/check_weknora_native_wiki_global_maintenance.py`
  - Creates an isolated temporary wiki-enabled KB.
  - Creates a temporary Wiki page.
  - Proves bad-token rejection.
  - Runs rebuild-links and auto-fix with confirmation/audit.
  - Creates a real native Wiki issue through PA BFF.
  - Resolves that issue through the native status route and verifies audit.

No MCP service work was added or counted.

## Validation Evidence

Commands:

```text
pa-ai-workbench/backend/.venv/bin/python -m py_compile pa-ai-workbench/backend/app/api/wiki.py pa-ai-workbench/backend/app/schemas.py pa-ai-workbench/backend/app/services/wiki_service.py pa-ai-workbench/backend/scripts/check_weknora_native_wiki_global_maintenance.py pa-ai-workbench/knowledge_engine/backends/weknora_api_backend.py
```

```text
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -w /workspace golang:1.26.0 go test ./internal/types ./internal/application/repository ./internal/application/service ./internal/handler ./internal/router
```

```text
docker compose build app
```

```text
docker compose up -d --no-deps app
```

```text
pa-ai-workbench/backend/.venv/bin/python pa-ai-workbench/backend/scripts/check_weknora_native_wiki_global_maintenance.py
```

Go focused test output:

```text
ok  	github.com/Tencent/WeKnora/internal/types	0.473s
ok  	github.com/Tencent/WeKnora/internal/application/repository	0.457s
ok  	github.com/Tencent/WeKnora/internal/application/service	1.409s
ok  	github.com/Tencent/WeKnora/internal/handler	0.264s
ok  	github.com/Tencent/WeKnora/internal/router	0.266s
```

Live smoke output:

```text
WeKnora native Wiki global maintenance closure
- decision: PASS
- evidence_type: live api plus audit proof
- rebuild_links: live audit=succeeded
- auto_fix: live audit=succeeded
- create_issue: live audit=succeeded
- issue_status: live audit=succeeded
- output: sanitized
```

The live runtime was rebuilt from current native source and `WeKnora-app` was
recreated from the freshly built app image so the new native route was actually
available on port 8080. The validation used a temporary native Wiki KB and
deleted it at the end of the run.

## Status

`WNFC-P5-04` is `[x]` complete.

Native Wiki remains `live-full`, and the previous issue-status blocker is
closed by a real native route plus PA confirmation/audit proof. Remaining WNFC
final readiness work is `WNFC-P6-02`.
