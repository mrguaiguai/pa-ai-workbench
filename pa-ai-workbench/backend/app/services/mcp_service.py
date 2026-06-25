from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.config import get_settings
from app.models import NativeMutationAudit
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import confirmation_surface
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


MCP_TEST_CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE"
MCP_MUTATION_CONFIRM_TOKEN = "CONFIRM_NATIVE_MCP_MUTATION"
MCP_MUTATION_CONFIRM_TOKEN_ID = "native_mcp_mutation"
MCP_MUTATION_ACTIONS = {
    "create": "weknora_mcp_service_create",
    "update": "weknora_mcp_service_update",
    "delete": "weknora_mcp_service_delete",
    "credentials_update": "weknora_mcp_credentials_update",
    "credentials_clear": "weknora_mcp_credentials_clear",
}


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
    overview["surfaces"]["prompts"] = _mcp_prompts_blocker_surface()
    overview["surfaces"]["approval"] = _approval_overview_surface(
        backend,
        enabled_services[:service_limit],
    )
    overview["surfaces"]["safe_test"] = _safe_test_overview_surface(safe_services)
    overview["surfaces"]["tool_execution"] = _mcp_tool_execution_blocker_surface()
    overview["surfaces"]["mutations"] = _mcp_mutation_surface()
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
    response["surfaces"]["prompts"] = _mcp_prompts_blocker_surface()
    response["surfaces"]["approval"] = _approval_detail_surface(backend, service_id)
    response["surfaces"]["safe_test"] = {
        "status": "blocked",
        "reason": "confirmation_required_before_external_mcp_probe",
        "confirm_token": MCP_TEST_CONFIRM_TOKEN,
        "endpoint": f"/api/mcp/native/services/{service_id}/test",
    }
    response["surfaces"]["tool_execution"] = _mcp_tool_execution_blocker_surface()
    response["surfaces"]["mutations"] = _mcp_mutation_surface()
    response["status"] = "partial"
    return response


def test_native_mcp_service(service_id: str, confirm_token: str | None) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnx-p2-02-test"
    response["management_mode"] = "safe_read_confirmed_test"
    response["surfaces"]["mutations"] = _mcp_mutation_surface()
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
        "reason": result.get("reason") if not success else None,
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
    response["surfaces"]["prompts"] = _mcp_prompts_blocker_surface()
    response["surfaces"]["tool_execution"] = _mcp_tool_execution_blocker_surface(
        reason="no_live_mcp_tool_available"
        if int(result.get("tool_count") or 0) <= 0
        else "pa_confirmed_mcp_tool_execution_workflow_missing",
    )
    return response


def create_native_mcp_service(
    *,
    session: Session,
    name: str,
    transport_type: str,
    url: str | None = None,
    description: str = "",
    enabled: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_mcp_service(
        session=session,
        action="create",
        confirm_token=confirm_token,
        service_id=None,
        payload={
            "name": name,
            "transport_type": transport_type,
            "url": url,
            "description": description,
            "enabled": enabled,
        },
    )


def update_native_mcp_service(
    *,
    session: Session,
    service_id: str,
    name: str | None = None,
    description: str | None = None,
    enabled: bool | None = None,
    transport_type: str | None = None,
    url: str | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_mcp_service(
        session=session,
        action="update",
        confirm_token=confirm_token,
        service_id=service_id,
        payload={
            "name": name,
            "description": description,
            "enabled": enabled,
            "transport_type": transport_type,
            "url": url,
        },
    )


def delete_native_mcp_service(
    *,
    session: Session,
    service_id: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_mcp_service(
        session=session,
        action="delete",
        confirm_token=confirm_token,
        service_id=service_id,
        payload={},
    )


def update_native_mcp_credentials(
    *,
    session: Session,
    service_id: str,
    api_key: str | None = None,
    token: str | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_mcp_service(
        session=session,
        action="credentials_update",
        confirm_token=confirm_token,
        service_id=service_id,
        payload={
            "api_key_provided": bool(api_key),
            "token_provided": bool(token),
            "_api_key": api_key,
            "_token": token,
        },
    )


def clear_native_mcp_credential(
    *,
    session: Session,
    service_id: str,
    field: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_mcp_service(
        session=session,
        action="credentials_clear",
        confirm_token=confirm_token,
        service_id=service_id,
        payload={"field": field},
    )


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


def _mutate_native_mcp_service(
    *,
    session: Session,
    action: str,
    confirm_token: str | None,
    service_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnfc-p2-01-mcp-mutation"
    response["management_mode"] = "confirmed_mcp_crud_credentials"
    response["surfaces"]["mutations"] = _mcp_mutation_surface()
    action_name = MCP_MUTATION_ACTIONS.get(action, f"weknora_mcp_{action}")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["mutation"] = {
            "status": "backlog",
            "action": action,
            "reason": "weknora_api backend is required for native MCP mutations",
        }
        return response

    service_id = str(service_id or "").strip()
    if action != "create" and not service_id:
        response["surfaces"]["mutation"] = {
            "status": "blocked",
            "action": action,
            "success": False,
            "reason": "service_id is required",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=MCP_MUTATION_CONFIRM_TOKEN,
            token_id=MCP_MUTATION_CONFIRM_TOKEN_ID,
            action=action_name,
        )
    except NativeConfirmationError:
        response["surfaces"]["mutation"] = _mcp_mutation_blocked_surface(action)
        response["warnings"].append(f"blocked: MCP {action} requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    audit = record_native_mutation_audit(
        session=session,
        capability="mcp",
        operation=action_name,
        target_type="mcp_service",
        target_id=service_id or None,
        status="started",
        confirmation=confirmation,
        request_summary=_mcp_request_summary(action, service_id, payload),
    )
    session.commit()
    try:
        result = _perform_mcp_mutation(backend, action, service_id, payload)
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": action, "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"]["mutation"] = {
            "status": "partial",
            "action": action,
            "success": False,
            "reason": f"native_mcp_{action}: {_error_code(exc)}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: native_mcp_{action}: {_error_code(exc)}")
        return response

    if action == "create":
        audit.target_id = str(result.get("id") or "")
    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary=_mcp_response_summary(action, result),
    )
    session.commit()
    response["status"] = "partial"
    response["surfaces"]["mutation"] = {
        "status": "live",
        "action": action,
        "success": True,
        "result": result,
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _perform_mcp_mutation(
    backend: WeKnoraApiBackend,
    action: str,
    service_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if action == "create":
        return backend.create_mcp_service(
            name=str(payload.get("name") or "").strip(),
            description=str(payload.get("description") or "").strip(),
            enabled=bool(payload.get("enabled")),
            transport_type=str(payload.get("transport_type") or "").strip(),
            url=_optional_text(payload.get("url")),
        )
    if action == "update":
        return backend.update_mcp_service(
            service_id,
            name=_optional_text(payload.get("name")),
            description=_optional_text(payload.get("description")),
            enabled=payload.get("enabled") if isinstance(payload.get("enabled"), bool) else None,
            transport_type=_optional_text(payload.get("transport_type")),
            url=_optional_text(payload.get("url")),
        )
    if action == "delete":
        return backend.delete_mcp_service(service_id)
    if action == "credentials_update":
        return backend.update_mcp_service_credentials(
            service_id,
            api_key=_optional_text(payload.get("_api_key")),
            token=_optional_text(payload.get("_token")),
        )
    if action == "credentials_clear":
        return backend.clear_mcp_service_credential(
            service_id,
            str(payload.get("field") or "").strip(),
        )
    raise ValueError(f"unsupported MCP mutation action: {action}")


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


def _mcp_prompts_blocker_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "native_mcp_prompt_api_missing",
        "count": 0,
        "native_endpoint": None,
        "required_native_surface": (
            "MCP prompts list/read route or native client support is required "
            "before PA can expose prompts truthfully."
        ),
    }


def _mcp_tool_execution_blocker_surface(
    *, reason: str = "requires_live_mcp_tool_and_confirmed_execution_path",
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "count": 0,
        "confirmation_required": True,
        "audit_required": True,
        "history_required": True,
        "required_evidence": (
            "A real initialized MCP service must expose at least one low-risk "
            "tool, and PA must prove confirmation-gated execution with timeout, "
            "NativeMutationAudit/history, and masked output."
        ),
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


def _mcp_mutation_surface() -> dict[str, Any]:
    return {
        "status": "partial",
        "items": [
            "service create/update/delete live with confirm_token and NativeMutationAudit",
            "credential update/clear live with masked metadata only",
            "tool execution remains separate approval-gated work",
        ],
        "reason": (
            "WNFC-P2-01 enables MCP service CRUD and credentials; "
            "tool/resource execution is handled by WNFC-P2-02/P2-03."
        ),
        "confirm_token_id": MCP_MUTATION_CONFIRM_TOKEN_ID,
        "confirmation": confirmation_surface(
            token_id=MCP_MUTATION_CONFIRM_TOKEN_ID,
            confirm_token=MCP_MUTATION_CONFIRM_TOKEN,
            reason="native MCP CRUD and credential mutations require explicit operator confirmation",
        ),
    }


def _mcp_mutation_blocked_surface(action: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "action": action,
        "success": False,
        "reason": "confirmation_required_before_native_mcp_mutation",
        "confirmation": confirmation_surface(
            token_id=MCP_MUTATION_CONFIRM_TOKEN_ID,
            confirm_token=MCP_MUTATION_CONFIRM_TOKEN,
            reason="native MCP CRUD and credential mutations require explicit operator confirmation",
        ),
    }


def _mcp_request_summary(action: str, service_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "service_id": service_id,
        "name": payload.get("name"),
        "enabled": payload.get("enabled"),
        "transport_type": payload.get("transport_type"),
        "url_configured": bool(payload.get("url")),
        "credential_field_count": int(bool(payload.get("api_key_provided")))
        + int(bool(payload.get("token_provided"))),
        "field": payload.get("field"),
    }


def _mcp_response_summary(action: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "success": True,
        "service": _public_mcp_service_item(result) if action in {"create", "update"} else None,
        "credential_status": _public_mcp_credential_item(result)
        if action in {"credentials_update", "credentials_clear"}
        else None,
        "deleted": bool(result.get("status") == "deleted") if action == "delete" else None,
    }


def _public_mcp_service_item(service: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": service.get("id"),
        "name": service.get("name"),
        "enabled": bool(service.get("enabled")),
        "transport_type": service.get("transport_type"),
        "is_builtin": bool(service.get("is_builtin")),
        "credential_field_count": int(service.get("credential_field_count") or 0),
        "configured_credential_field_count": int(service.get("configured_credential_field_count") or 0),
        "credentials_configured": bool(service.get("credentials_configured")),
        "source": service.get("source") or "weknora_api",
    }


def _public_mcp_credential_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "masked": True,
        "field_count": int(item.get("field_count") or 0),
        "configured_field_count": int(item.get("configured_field_count") or 0),
        "credentials_configured": bool(item.get("credentials_configured")),
        "cleared": bool(item.get("cleared")),
        "field": item.get("field"),
        "source": item.get("source") or "weknora_api",
    }


def _audit_surface(audit: NativeMutationAudit) -> dict[str, Any]:
    return {
        "id": audit.id,
        "capability": audit.capability,
        "operation": audit.operation,
        "target_type": audit.target_type,
        "target_id": audit.target_id,
        "source": audit.source,
        "status": audit.status,
        "confirmation_required": audit.confirmation_required,
        "confirmation_method": audit.confirmation_method,
        "confirm_token_id": audit.confirm_token_id,
        "created_at": audit.created_at.isoformat(),
    }


def _confirmation_read(confirmation: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": bool(confirmation.get("required", True)),
        "method": confirmation.get("method"),
        "token_id": confirmation.get("token_id"),
    }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _error_code(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or exc.__class__.__name__)
