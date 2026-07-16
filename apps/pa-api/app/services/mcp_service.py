from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.config import get_settings
from app.models import GeneratedOutput
from app.models import GenerationTask
from app.models import NativeMutationAudit
from app.services.conversation_service import add_message
from app.services.conversation_service import create_conversation
from app.services.conversation_service import get_conversation
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
MCP_EXECUTION_CONFIRM_TOKEN = "EXECUTE_NATIVE_MCP_TOOL"
MCP_EXECUTION_CONFIRM_TOKEN_ID = "native_mcp_tool_execution"
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
    overview["surfaces"]["prompts"] = _mcp_prompts_probe_surface(safe_services)
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
    response["surfaces"]["prompts"] = _mcp_prompts_probe_surface([service])
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
                "prompt_count": 0,
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
        "prompt_count": int(result.get("prompt_count") or 0),
        "sample_tools": result.get("sample_tools") if isinstance(result.get("sample_tools"), list) else [],
        "sample_resources": (
            result.get("sample_resources")
            if isinstance(result.get("sample_resources"), list)
            else []
        ),
        "sample_prompts": (
            result.get("sample_prompts")
            if isinstance(result.get("sample_prompts"), list)
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
    response["surfaces"]["prompts"] = {
        "status": "live" if success else "partial",
        "count": int(result.get("prompt_count") or 0),
        "sample_prompts": result.get("sample_prompts") if isinstance(result.get("sample_prompts"), list) else [],
        "read_endpoint": "/api/mcp/native/services/{service_id}/prompts/{prompt_name}/read",
    }
    response["surfaces"]["tool_execution"] = _mcp_tool_execution_blocker_surface(
        reason="no_live_mcp_tool_available"
        if int(result.get("tool_count") or 0) <= 0
        else "pa_confirmed_mcp_tool_execution_workflow_missing",
    )
    return response


def read_native_mcp_prompt(
    *,
    service_id: str,
    prompt_name: str,
    arguments: dict[str, Any] | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnid-p3-03-mcp-prompt-read"
    response["management_mode"] = "confirmed_mcp_prompt_read"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["prompt_read"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP prompt read",
        }
        return response

    service_id = str(service_id or "").strip()
    prompt_name = str(prompt_name or "").strip()
    if not service_id or not prompt_name:
        response["surfaces"]["prompt_read"] = {
            "status": "blocked",
            "reason": "service_id and prompt_name are required",
        }
        return response

    if confirm_token != MCP_TEST_CONFIRM_TOKEN:
        response["surfaces"]["prompt_read"] = {
            "status": "blocked",
            "reason": "confirmation_required_before_external_mcp_prompt_read",
            "confirm_token": MCP_TEST_CONFIRM_TOKEN,
            "confirm_token_id": "native_mcp_prompt_read",
        }
        return response

    backend = _weknora_backend(settings)
    safe_arguments = arguments if isinstance(arguments, dict) else {}
    try:
        prompts = backend.get_mcp_service_prompts(service_id)
        prompt = backend.read_mcp_prompt(
            service_id,
            prompt_name,
            arguments={str(key): str(value) for key, value in safe_arguments.items()},
        )
    except KnowledgeBackendUnavailableError as exc:
        response["status"] = "partial"
        response["surfaces"]["prompt_read"] = {
            "status": "partial",
            "success": False,
            "reason": f"native_mcp_prompt_read: {_error_code(exc)}",
        }
        response["warnings"].append(f"partial: native_mcp_prompt_read: {_error_code(exc)}")
        return response

    response["status"] = "live"
    response["surfaces"]["prompts"] = {
        "status": "live",
        "count": len(prompts),
        "sample_prompts": prompts[:5],
    }
    response["surfaces"]["prompt_read"] = {
        "status": "live",
        "success": True,
        "prompt": prompt,
        "message_count": int(prompt.get("message_count") or 0),
    }
    return response


def set_native_mcp_tool_approval(
    *,
    session: Session,
    service_id: str,
    tool_name: str,
    require_approval: bool,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnid-p3-02-mcp-tool-approval"
    response["management_mode"] = "confirmed_mcp_tool_execution"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["approval_policy"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP tool approval",
        }
        return response

    service_id = str(service_id or "").strip()
    tool_name = str(tool_name or "").strip()
    if not service_id or not tool_name:
        response["surfaces"]["approval_policy"] = {
            "status": "blocked",
            "reason": "service_id and tool_name are required",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=MCP_EXECUTION_CONFIRM_TOKEN,
            token_id=MCP_EXECUTION_CONFIRM_TOKEN_ID,
            action="weknora_mcp_tool_approval_set",
        )
    except NativeConfirmationError:
        response["surfaces"]["approval_policy"] = _mcp_execution_blocked_surface(
            "approval_policy",
            "confirmation_required_before_native_mcp_tool_execution",
        )
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="mcp",
        operation="weknora_mcp_tool_approval_set",
        target_type="mcp_tool",
        target_id=f"{service_id}:{tool_name}",
        status="started",
        confirmation=confirmation,
        request_summary={
            "service_id": service_id,
            "tool_name": tool_name,
            "require_approval": bool(require_approval),
        },
    )
    session.commit()

    backend = _weknora_backend(settings)
    try:
        result = backend.set_mcp_tool_approval(service_id, tool_name, require_approval)
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"success": False, "tool_name": tool_name},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"]["approval_policy"] = {
            "status": "partial",
            "success": False,
            "reason": f"native_mcp_tool_approval: {_error_code(exc)}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        return response

    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={
            "success": True,
            "tool_name": tool_name,
            "require_approval": bool(require_approval),
        },
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"]["approval_policy"] = {
        "status": "live",
        "success": True,
        "result": result,
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def execute_native_mcp_tool(
    *,
    session: Session,
    service_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    approval_decision: str | None = None,
    conversation_id: str | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnid-p3-02-mcp-tool-execution"
    response["management_mode"] = "confirmed_mcp_tool_execution"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["tool_execution"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native MCP tool execution",
        }
        return response

    service_id = str(service_id or "").strip()
    tool_name = str(tool_name or "").strip()
    approval_decision = str(approval_decision or "").strip().lower() or None
    if not service_id or not tool_name:
        response["surfaces"]["tool_execution"] = {
            "status": "blocked",
            "reason": "service_id and tool_name are required",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=MCP_EXECUTION_CONFIRM_TOKEN,
            token_id=MCP_EXECUTION_CONFIRM_TOKEN_ID,
            action="weknora_mcp_tool_execute",
        )
    except NativeConfirmationError:
        response["surfaces"]["tool_execution"] = _mcp_execution_blocked_surface(
            "tool_execution",
            "confirmation_required_before_native_mcp_tool_execution",
        )
        return response

    safe_arguments = arguments if isinstance(arguments, dict) else {}
    audit = record_native_mutation_audit(
        session=session,
        capability="mcp",
        operation="weknora_mcp_tool_execute",
        target_type="mcp_tool",
        target_id=f"{service_id}:{tool_name}",
        status="started",
        confirmation=confirmation,
        request_summary={
            "service_id": service_id,
            "tool_name": tool_name,
            "argument_keys": sorted(str(key) for key in safe_arguments.keys()),
            "approval_decision": approval_decision,
        },
    )
    session.commit()

    backend = _weknora_backend(settings)
    try:
        result = backend.execute_mcp_tool(
            service_id,
            tool_name,
            arguments=safe_arguments,
            approval_decision=approval_decision,
        )
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"success": False, "tool_name": tool_name},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"]["tool_execution"] = {
            "status": "partial",
            "success": False,
            "reason": f"native_mcp_tool_execute: {_error_code(exc)}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        return response

    conversation, output = _record_mcp_execution_history(
        session=session,
        conversation_id=conversation_id,
        service_id=service_id,
        tool_name=tool_name,
        approval_decision=approval_decision,
        result=result,
        audit=audit,
    )
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if result.get("success") else "failed",
        response_summary=_mcp_execution_response_summary(result, output.id),
        error_message=str(result.get("error") or "") or None,
    )
    session.commit()
    response["status"] = "live" if result.get("success") else "partial"
    response["surfaces"]["tool_execution"] = {
        "status": "live" if result.get("success") else "partial",
        "success": bool(result.get("success")),
        "result": _public_mcp_execution_result(result),
        "history": {
            "conversation_id": conversation.id,
            "output_id": output.id,
            "task_type": output.task_type,
        },
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
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


def _mcp_execution_blocked_surface(surface: str, reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "surface": surface,
        "success": False,
        "reason": reason,
        "confirm_token": MCP_EXECUTION_CONFIRM_TOKEN,
        "confirm_token_id": MCP_EXECUTION_CONFIRM_TOKEN_ID,
    }


def _record_mcp_execution_history(
    *,
    session: Session,
    conversation_id: str | None,
    service_id: str,
    tool_name: str,
    approval_decision: str | None,
    result: dict[str, Any],
    audit: NativeMutationAudit,
) -> tuple[Any, GeneratedOutput]:
    conversation = get_conversation(session, conversation_id) if conversation_id else None
    if conversation is None:
        conversation, _ = create_conversation(
            session=session,
            title=f"MCP tool: {tool_name}",
            summary="Native MCP tool execution evidence",
            default_task_type="native_mcp_tool_execution",
        )

    add_message(
        session=session,
        conversation=conversation,
        role="user",
        content=(
            f"MCP tool execution request: service={service_id}, tool={tool_name}, "
            f"approval_decision={approval_decision or 'none'}"
        ),
        metadata_json=json.dumps(
            {
                "source": "pa_mcp_execution",
                "service_id": service_id,
                "tool_name": tool_name,
                "approval_decision": approval_decision,
                "audit_id": audit.id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    summary = _mcp_execution_markdown(result)
    add_message(
        session=session,
        conversation=conversation,
        role="assistant",
        content=summary,
        metadata_json=json.dumps(
            {
                "source": "weknora_native_mcp_tool_execution",
                "service_id": service_id,
                "tool_name": tool_name,
                "success": bool(result.get("success")),
                "executed": bool(result.get("executed")),
                "rejected": bool(result.get("rejected")),
                "audit_id": audit.id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    task = GenerationTask(
        conversation_id=conversation.id,
        task_type="native_mcp_tool_execution",
        title=f"MCP {tool_name}",
        input_json=json.dumps(
            {
                "service_id": service_id,
                "tool_name": tool_name,
                "approval_decision": approval_decision,
                "audit_id": audit.id,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        status="completed" if result.get("success") else "failed",
        current_step="completed",
        progress=100,
        error_message=str(result.get("error") or "") or None,
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    output = GeneratedOutput(
        task_id=task.id,
        conversation_id=conversation.id,
        task_type="native_mcp_tool_execution",
        title=f"MCP tool execution: {tool_name}",
        content_markdown=summary,
        content_json=json.dumps(_public_mcp_execution_result(result), ensure_ascii=False, sort_keys=True),
        warnings_json=json.dumps([], ensure_ascii=False),
        status="completed" if result.get("success") else "failed",
    )
    session.add(output)
    session.commit()
    session.refresh(output)
    return conversation, output


def _mcp_execution_markdown(result: dict[str, Any]) -> str:
    status = "rejected" if result.get("rejected") else "executed" if result.get("executed") else "blocked"
    output = str(result.get("output") or result.get("message") or result.get("error") or "")
    lines = [
        f"status: {status}",
        f"service: {result.get('service_name') or result.get('service_id') or 'unknown'}",
        f"tool: {result.get('tool_name') or 'unknown'}",
        f"approval_required: {str(bool(result.get('approval_required'))).lower()}",
        f"approval_decision: {result.get('approval_decision') or 'none'}",
    ]
    if output:
        lines.append(f"summary: {_shorten(output, 300)}")
    return "\n".join(lines)


def _mcp_execution_response_summary(result: dict[str, Any], output_id: str) -> dict[str, Any]:
    return {
        "success": bool(result.get("success")),
        "service_id": result.get("service_id"),
        "tool_name": result.get("tool_name"),
        "approval_required": bool(result.get("approval_required")),
        "approval_decision": result.get("approval_decision"),
        "executed": bool(result.get("executed")),
        "rejected": bool(result.get("rejected")),
        "output_id": output_id,
    }


def _public_mcp_execution_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": bool(result.get("success")),
        "service_id": result.get("service_id"),
        "service_name": result.get("service_name"),
        "tool_name": result.get("tool_name"),
        "approval_required": bool(result.get("approval_required")),
        "approval_decision": result.get("approval_decision"),
        "executed": bool(result.get("executed")),
        "rejected": bool(result.get("rejected")),
        "message": _shorten(str(result.get("message") or ""), 240),
        "output": _shorten(str(result.get("output") or ""), 500),
        "output_chars": int(result.get("output_chars") or 0),
        "content_item_count": int(result.get("content_item_count") or 0),
        "error": _shorten(str(result.get("error") or ""), 240),
        "source": result.get("source") or "weknora_api",
    }


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


def _mcp_prompts_probe_surface(services: list[dict[str, Any]]) -> dict[str, Any]:
    if not services:
        return {
            "status": "backlog",
            "reason": "no native MCP services are configured",
            "count": 0,
        }
    return {
        "status": "blocked",
        "reason": "confirmation_required_before_external_mcp_prompt_read",
        "count": 0,
        "native_endpoint": "/api/v1/mcp-services/{id}/prompts",
        "native_read_endpoint": "/api/v1/mcp-services/{id}/prompts/{prompt_name}/read",
        "safe_test_endpoint": "/api/mcp/native/services/{service_id}/test",
        "read_endpoint": "/api/mcp/native/services/{service_id}/prompts/{prompt_name}/read",
        "confirm_token": MCP_TEST_CONFIRM_TOKEN,
    }


def _mcp_tool_execution_blocker_surface(
    *, reason: str = "confirmation_required_before_native_mcp_tool_execution",
) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "count": 0,
        "confirmation_required": True,
        "audit_required": True,
        "history_required": True,
        "confirm_token": MCP_EXECUTION_CONFIRM_TOKEN,
        "confirm_token_id": MCP_EXECUTION_CONFIRM_TOKEN_ID,
        "endpoint": "/api/mcp/native/services/{service_id}/tools/{tool_name}/execute",
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


def _shorten(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)] + "..."


def _error_code(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or exc.__class__.__name__)
