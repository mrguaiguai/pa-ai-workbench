from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


MCP_TEST_CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE"


def native_mcp_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    service_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = _base_response(settings)
    overview["management_mode"] = "safe_read_confirmed_test"
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["services"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP management",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    backend = _weknora_backend(settings)
    try:
        services = backend.list_mcp_services()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"services: {_error_code(exc)}"
        overview["surfaces"]["services"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    safe_services = [
        service for service in services if isinstance(service, dict) and service.get("id")
    ]
    enabled_services = [service for service in safe_services if service.get("enabled")]
    overview["surfaces"]["services"] = {
        "status": "live",
        "count": len(safe_services),
        "enabled_count": len(enabled_services),
        "builtin_count": sum(1 for service in safe_services if service.get("is_builtin")),
        "items": safe_services[:service_limit],
    }
    overview["surfaces"]["service_read"] = _service_read_surface(safe_services)
    overview["surfaces"]["tools"] = _external_probe_surface(
        safe_services,
        name="tools",
        native_endpoint="/api/v1/mcp-services/{id}/tools",
    )
    overview["surfaces"]["resources"] = _external_probe_surface(
        safe_services,
        name="resources",
        native_endpoint="/api/v1/mcp-services/{id}/resources",
    )
    overview["surfaces"]["approval"] = _approval_overview_surface(
        backend,
        enabled_services[:service_limit],
    )
    overview["surfaces"]["safe_test"] = _safe_test_overview_surface(safe_services)
    overview["surfaces"]["mutations"] = _mcp_mutation_backlog()
    overview["status"] = "partial"
    return overview


def native_mcp_service_detail(service_id: str) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnx-p2-02-service"
    response["management_mode"] = "safe_read_confirmed_test"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["service_read"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP management",
        }
        return response

    service_id = str(service_id or "").strip()
    if not service_id:
        response["surfaces"]["service_read"] = {
            "status": "blocked",
            "reason": "service_id is required",
        }
        return response

    backend = _weknora_backend(settings)
    try:
        service = backend.get_mcp_service(service_id)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["service_read"] = {
            "status": "blocked",
            "reason": f"service_read: {_error_code(exc)}",
        }
        response["warnings"].append(f"blocked: service_read: {_error_code(exc)}")
        return response

    response["surfaces"]["service_read"] = {
        "status": "live",
        "count": 1,
        "item": service,
    }
    response["surfaces"]["tools"] = _external_probe_surface(
        [service],
        name="tools",
        native_endpoint="/api/v1/mcp-services/{id}/tools",
    )
    response["surfaces"]["resources"] = _external_probe_surface(
        [service],
        name="resources",
        native_endpoint="/api/v1/mcp-services/{id}/resources",
    )
    response["surfaces"]["approval"] = _approval_detail_surface(backend, service_id)
    response["surfaces"]["safe_test"] = {
        "status": "blocked",
        "reason": "confirmation_required_before_external_mcp_probe",
        "confirm_token": MCP_TEST_CONFIRM_TOKEN,
        "endpoint": f"/api/mcp/native/services/{service_id}/test",
    }
    response["surfaces"]["mutations"] = _mcp_mutation_backlog()
    response["status"] = "partial"
    return response


def test_native_mcp_service(service_id: str, confirm_token: str | None) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnx-p2-02-test"
    response["management_mode"] = "safe_read_confirmed_test"
    response["surfaces"]["mutations"] = _mcp_mutation_backlog()
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["safe_test"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP management",
        }
        return response

    service_id = str(service_id or "").strip()
    if not service_id:
        response["surfaces"]["safe_test"] = {
            "status": "blocked",
            "reason": "service_id is required",
        }
        return response
    if confirm_token != MCP_TEST_CONFIRM_TOKEN:
        response["surfaces"]["safe_test"] = {
            "status": "blocked",
            "reason": "confirmation_required_before_external_mcp_probe",
            "confirm_token": MCP_TEST_CONFIRM_TOKEN,
        }
        return response

    backend = _weknora_backend(settings)
    try:
        result = backend.test_mcp_service(service_id)
    except KnowledgeBackendUnavailableError as exc:
        response["status"] = "partial"
        response["surfaces"]["safe_test"] = {
            "status": "partial",
            "reason": f"native_test: {_error_code(exc)}",
            "success": False,
            "tool_count": 0,
            "resource_count": 0,
        }
        response["warnings"].append(f"partial: native_test: {_error_code(exc)}")
        return response

    success = bool(result.get("success"))
    response["status"] = "live" if success else "partial"
    response["surfaces"]["safe_test"] = {
        "status": "live" if success else "partial",
        "success": success,
        "tool_count": int(result.get("tool_count") or 0),
        "resource_count": int(result.get("resource_count") or 0),
        "sample_tools": result.get("sample_tools") if isinstance(result.get("sample_tools"), list) else [],
        "sample_resources": (
            result.get("sample_resources")
            if isinstance(result.get("sample_resources"), list)
            else []
        ),
    }
    response["surfaces"]["tools"] = {
        "status": "live" if success else "partial",
        "count": int(result.get("tool_count") or 0),
    }
    response["surfaces"]["resources"] = {
        "status": "live" if success else "partial",
        "count": int(result.get("resource_count") or 0),
    }
    return response


def _base_response(settings: Settings) -> dict[str, Any]:
    return {
        "schema_version": "wnx-p2-02",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _weknora_backend(settings: Settings) -> WeKnoraApiBackend:
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _service_read_surface(services: list[dict[str, Any]]) -> dict[str, Any]:
    if not services:
        return {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
    return {
        "status": "live",
        "count": len(services),
        "endpoint": "/api/mcp/native/services/{service_id}",
    }


def _external_probe_surface(
    services: list[dict[str, Any]],
    *,
    name: str,
    native_endpoint: str,
) -> dict[str, Any]:
    if not services:
        return {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
    return {
        "status": "blocked",
        "reason": "external_mcp_connection_requires_confirmed_test",
        "count": 0,
        "surface": name,
        "native_endpoint": native_endpoint,
        "safe_test_endpoint": "/api/mcp/native/services/{service_id}/test",
    }


def _approval_overview_surface(
    backend: WeKnoraApiBackend,
    services: list[dict[str, Any]],
) -> dict[str, Any]:
    if not services:
        return {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
            "approval_required_count": 0,
        }

    items: list[dict[str, Any]] = []
    blockers: list[str] = []
    for service in services:
        service_id = str(service.get("id") or "")
        service_name = str(service.get("name") or service_id)
        if not service_id:
            continue
        try:
            approvals = backend.list_mcp_tool_approvals(service_id)
        except KnowledgeBackendUnavailableError as exc:
            blockers.append(f"approval:{service_id}: {_error_code(exc)}")
            continue
        items.append(
            {
                "service_id": service_id,
                "service_name": service_name,
                "count": len(approvals),
                "approval_required_count": sum(
                    1 for approval in approvals if approval.get("require_approval")
                ),
                "sample_approvals": approvals[:5],
            }
        )
    return {
        "status": "partial" if blockers else "live",
        "service_count": len(items),
        "count": sum(item["count"] for item in items),
        "approval_required_count": sum(item["approval_required_count"] for item in items),
        "items": items,
        "blockers": blockers[:5],
    }


def _approval_detail_surface(backend: WeKnoraApiBackend, service_id: str) -> dict[str, Any]:
    try:
        approvals = backend.list_mcp_tool_approvals(service_id)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "partial",
            "reason": f"approval: {_error_code(exc)}",
            "count": 0,
            "approval_required_count": 0,
        }
    return {
        "status": "live",
        "count": len(approvals),
        "approval_required_count": sum(
            1 for approval in approvals if approval.get("require_approval")
        ),
        "sample_approvals": approvals[:5],
    }


def _safe_test_overview_surface(services: list[dict[str, Any]]) -> dict[str, Any]:
    if not services:
        return {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
    return {
        "status": "blocked",
        "reason": "confirmation_required_before_external_mcp_probe",
        "confirm_token": MCP_TEST_CONFIRM_TOKEN,
        "endpoint": "/api/mcp/native/services/{service_id}/test",
    }


def _mcp_mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "service create/update/delete",
            "credential forms",
            "tool execution",
            "approval mutation",
        ],
        "reason": (
            "WNX-P2-02 exposes safe read and confirmation-gated tests only; "
            "mutation/execution requires a separate approval and audit design."
        ),
    }


def _error_code(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or exc.__class__.__name__)
