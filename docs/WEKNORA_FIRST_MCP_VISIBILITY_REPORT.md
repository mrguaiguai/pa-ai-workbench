# WeKnora-First MCP Visibility Report

> Task: `WF-P2-01`
>
> Date: 2026-06-22
>
> Branch: `weknora-first-mvp`
>
> Report marker: `WEKNORA_FIRST`
>
> Result: PASS
>
> Evidence type: live PA API + live WeKnora native read-only MCP visibility.

## Scope

`WF-P2-01` exposes read-only MCP service readiness in PA. PA does not implement
MCP service CRUD, credential forms, tool execution, approval mutation, or
independent MCP orchestration in this task.

The goal is visibility:

- list native MCP service readiness
- show tool/resource/approval availability when safe
- keep credential and execution surfaces blocked/backlog
- avoid leaking URL, headers, env vars, auth config, API keys, tokens, or tool
  input schemas

## Native Source Audit

| Area | Native source | PA decision |
| --- | --- | --- |
| MCP route registration | `internal/router/router.go` | `GET /api/v1/mcp-services`, `/:id/tools`, `/:id/resources`, and `/:id/tool-approvals` are Viewer+ read-only routes. |
| MCP service handler | `internal/handler/mcp_service.go` | List/get use `dto.NewMCPServiceResponse`; create/update/delete/test/credential/approval mutation remain out of PA scope. |
| MCP response DTO | `internal/handler/dto/mcp.go` | DTO omits API key/token values and exposes configured credential booleans; PA further strips URL, headers, env vars, stdio config, auth config, tool schemas, and credential field names. |
| MCP service layer | `internal/application/service/mcp_service.go` | `GetMCPServiceTools` and `GetMCPServiceResources` are read-only but may connect to external MCP services; PA marks failures as partial rather than PASS. |
| MCP types | `internal/types/mcp.go` | Tool/resource/approval DTOs define names/counts and approval flags; PA only surfaces sanitized counts and names. |

## PA Implementation

PA now exposes:

```text
GET /api/mcp/native/overview?limit=5
```

The endpoint returns:

- `status`: `live`, `partial`, `blocked`, or `backlog`
- `services`: live native service list status and safe service metadata
- `tools`: live/partial/backlog tool count by service
- `resources`: live/partial/backlog resource count by service
- `approval`: live/partial/backlog approval count by service
- `mutations`: backlog list for CRUD, credentials, tool execution, and approval mutation

The frontend shared WeKnora-first strip also reads this endpoint and displays an
`MCP native` chip plus service/tool/resource/approval counts.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/smoke_weknora_mcp_visibility_live.py
```

Result summary:

```text
WeKnora MCP visibility smoke passed (live)
- PA endpoint: /api/mcp/native/overview
- overview status: live
- services status/count/enabled: live/0/0
- tools status/count: backlog/0
- resources status/count: backlog/0
- approval status/count/required: backlog/0/0
- mutations status: backlog
- sanitized response: True
```

What this proves:

- PA exposed a current HTTP API endpoint for native MCP visibility.
- The endpoint reached the native WeKnora MCP service list path through the live
  WeKnora API configuration.
- The current tenant has zero configured MCP services, so tool/resource/approval
  availability is truthfully labeled backlog instead of being faked.
- Mutation, credential, approval-write, and tool execution surfaces remain
  backlog.
- The response was checked for forbidden credential-bearing fields.

## Evidence Classification

| Evidence category | Result |
| --- | --- |
| live | Used for PA `/api/mcp/native/overview` and native WeKnora MCP service list. |
| mock | Not used; mock evidence is not PASS. |
| fixture-only | Not used as PASS. |
| cached | Not used as PASS. |
| partial | Allowed only for optional tools/resources/approval probes if a configured MCP service cannot be read safely. Not observed in this run. |
| blocked | Would apply if native read-only MCP endpoints are unavailable or unsafe to expose. Not observed for the service list. |
| backlog | Tools/resources/approval are backlog in this run because no MCP services are configured; CRUD, credentials, tool execution, and approval mutation remain backlog by design. |

## Safety Boundary

PA does not expose these MCP fields:

- service URL
- headers
- env vars
- stdio config
- auth config
- credential field names
- API key
- token
- raw tool input schema

The report and smoke output also avoid private endpoints, provider payloads,
local database paths, logs, caches, and raw secrets.

## PASS Statement

`WF-P2-01` passes for read-only MCP visibility. PA can now show native MCP
readiness through a sanitized API and frontend status strip while keeping
credential management, service mutation, approval mutation, and tool execution
as explicit backlog.
