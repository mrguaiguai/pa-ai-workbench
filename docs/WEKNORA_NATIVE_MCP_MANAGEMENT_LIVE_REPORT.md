# WeKnora Native MCP Management Live Report

> Task: `WNX-P2-02`
>
> Date: 2026-06-23
>
> Evidence type: live API/browser evidence.

## Decision

`WNX-P2-02` is PASS for safe live-partial MCP management readiness.

PA now exposes a `wnx-p2-02` MCP management overview backed by WeKnora native
MCP APIs. The current live tenant has no configured MCP services, so service
connection tests, tool/resource probes, and approval reads beyond the empty
list remain explicit backlog for this run. PA does not expose service URLs,
headers, env vars, stdio config, API key/token values, raw tool input schemas,
raw MCP test messages, credential forms, service CRUD, approval mutation, or
tool execution.

## Native Audit

| Area | Source | Result |
| --- | --- | --- |
| Routes | `internal/router/router.go` | `GET /api/v1/mcp-services` and `GET /api/v1/mcp-services/:id` are Viewer+; `POST /:id/test`, service CRUD, credentials, and approval mutation are Admin+. |
| Handler | `internal/handler/mcp_service.go` | List/get responses use a DTO that omits API key/token; native test connects to external MCP infrastructure. |
| Credentials | `internal/handler/mcp_credentials.go` | Credentials are split into a dedicated subresource and never returned as values. |
| Service | `internal/application/service/mcp_service.go` | Tools/resources and test create/use MCP clients, so PA must not call them automatically from status refresh. |
| Types/DTO | `internal/types/mcp.go`, `internal/handler/dto/mcp.go` | Native service DTO may still include non-secret connection details for normal services; PA strips them before display. |

## PA Surfaces

| Surface | PA endpoint | Live result |
| --- | --- | --- |
| Overview | `/api/mcp/native/overview` | `status=partial`, `services.status=live`, `services.count=0`, `safe_test.status=backlog`, `mutations.status=backlog`. |
| Service detail | `/api/mcp/native/services/{service_id}` | Implemented as a sanitized read path; not exercised live because no service is configured. |
| Safe test | `/api/mcp/native/services/{service_id}/test` | Confirmation-gated and not executed in this live run because no service is configured. |
| Capability Center | `/api/native/status`, `/#/capabilities` | MCP group renders `services_count`, `safe_test_status`, `service_read_status`, and `mutations_status`. |

## Validation

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_mcp_management.py --browser
```

Result:

```text
WeKnora native MCP management readiness
- decision: PASS
- evidence_type: live_api+browser_current_run
- services: status=live count=0 enabled=0
- service_read: backlog detail=not_configured
- safe_test: overview=backlog blocked_path=backlog confirmed_path=not_requested
- mutations: backlog
- browser: Capability Center rendered MCP management readiness
```

## Evidence Boundary

Live evidence:

- PA reached WeKnora native MCP service list through `/api/mcp/native/overview`.
- Capability Center rendered the current-run MCP management summary from
  `/api/native/status`.
- Response masking excludes credential values and connection details.

Backlog evidence:

- The tenant has no configured MCP services, so service detail/test,
  tools/resources, and approval reads beyond the empty service list cannot be
  counted as live PASS in this run.
- Service create/update/delete, credential forms, tool execution, and approval
  mutation remain backlog until a separate approval, audit, and rollback design
  is accepted.

Blocked evidence:

- No native runtime blocker was observed for the MCP service list.
- No external MCP test was run without explicit operator confirmation.

## Coverage

MCP moves from `read-only` to `live-partial`:

```text
10.00 / 15 = 66.7%
```

The increase is only `+0.25`; this report does not claim full MCP workflow
coverage because mutation, credential handling, external tool/resource probes,
and tool execution are not safe as automatic PA flows.
