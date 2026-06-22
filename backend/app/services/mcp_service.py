from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_mcp_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    service_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = {
        "schema_version": "wf-p2-01",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["services"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP visibility",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    overview["source"] = "weknora_api"
    backend = _weknora_backend(settings)
    optional_blockers: list[str] = []

    try:
        services = backend.list_mcp_services()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"services: {exc.error_code}"
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

    if not safe_services:
        overview["surfaces"]["tools"] = {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
        overview["surfaces"]["resources"] = {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
        overview["surfaces"]["approval"] = {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
        overview["surfaces"]["mutations"] = _mcp_mutation_backlog()
        overview["status"] = "live"
        return overview

    tools_by_service = []
    resources_by_service = []
    approvals_by_service = []
    for service in enabled_services[:service_limit]:
        service_id = str(service["id"])
        service_name = str(service.get("name") or service_id)
        try:
            tools = backend.get_mcp_service_tools(service_id)
            tools_by_service.append(
                {
                    "service_id": service_id,
                    "service_name": service_name,
                    "count": len(tools),
                    "approval_required_count": sum(
                        1 for tool in tools if tool.get("require_approval")
                    ),
                    "sample_tools": tools[:5],
                }
            )
        except KnowledgeBackendUnavailableError as exc:
            blocker = f"tools:{service_id}: {exc.error_code}"
            optional_blockers.append(blocker)
            overview["warnings"].append(f"partial: {blocker}")

        try:
            resources = backend.get_mcp_service_resources(service_id)
            resources_by_service.append(
                {
                    "service_id": service_id,
                    "service_name": service_name,
                    "count": len(resources),
                    "sample_resources": resources[:5],
                }
            )
        except KnowledgeBackendUnavailableError as exc:
            blocker = f"resources:{service_id}: {exc.error_code}"
            optional_blockers.append(blocker)
            overview["warnings"].append(f"partial: {blocker}")

        try:
            approvals = backend.list_mcp_tool_approvals(service_id)
            approvals_by_service.append(
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
        except KnowledgeBackendUnavailableError as exc:
            blocker = f"approval:{service_id}: {exc.error_code}"
            optional_blockers.append(blocker)
            overview["warnings"].append(f"partial: {blocker}")

    overview["surfaces"]["tools"] = {
        "status": "partial" if any(item.startswith("tools:") for item in optional_blockers) else "live",
        "service_count": len(tools_by_service),
        "count": sum(item["count"] for item in tools_by_service),
        "items": tools_by_service,
    }
    overview["surfaces"]["resources"] = {
        "status": "partial"
        if any(item.startswith("resources:") for item in optional_blockers)
        else "live",
        "service_count": len(resources_by_service),
        "count": sum(item["count"] for item in resources_by_service),
        "items": resources_by_service,
    }
    overview["surfaces"]["approval"] = {
        "status": "partial"
        if any(item.startswith("approval:") for item in optional_blockers)
        else "live",
        "service_count": len(approvals_by_service),
        "count": sum(item["count"] for item in approvals_by_service),
        "approval_required_count": sum(
            item["approval_required_count"] for item in approvals_by_service
        ),
        "items": approvals_by_service,
    }
    overview["surfaces"]["mutations"] = _mcp_mutation_backlog()
    overview["status"] = "partial" if optional_blockers else "live"
    return overview


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


def _mcp_mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "service CRUD",
            "credential forms",
            "tool execution",
            "approval mutation",
        ],
        "reason": "WF-P2-01 exposes read-only MCP visibility only.",
    }
