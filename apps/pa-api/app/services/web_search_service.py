from __future__ import annotations

from typing import Any

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
from sqlmodel import Session


WEB_SEARCH_TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"
WEB_SEARCH_MUTATION_CONFIRM_TOKEN = "MUTATE_NATIVE_WEB_SEARCH_PROVIDER"
WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID = "native_web_search_provider_mutation"
WEB_SEARCH_TEST_CONFIRM_TOKEN_ID = "native_web_search_provider_test"
WEB_SEARCH_MUTATION_ACTIONS = {
    "create": "weknora_web_search_provider_create",
    "update": "weknora_web_search_provider_update",
    "delete": "weknora_web_search_provider_delete",
    "credentials_update": "weknora_web_search_credentials_update",
    "credentials_clear": "weknora_web_search_credentials_clear",
    "raw_test": "weknora_web_search_provider_raw_test",
    "saved_test": "weknora_web_search_provider_test",
}


def native_web_search_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = _base_response(settings)
    overview["management_mode"] = "safe_read_confirmed_test"
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["provider_types"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native web search management",
        }
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("backlog")
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    backend = _weknora_backend(settings)
    try:
        provider_types = backend.list_web_search_provider_types()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"provider_types: {_error_code(exc)}"
        overview["surfaces"]["provider_types"] = {"status": "blocked", "reason": blocker}
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("blocked")
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    try:
        configured_providers = backend.list_web_search_providers()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"configured_providers: {_error_code(exc)}"
        overview["surfaces"]["configured_providers"] = {
            "status": "blocked",
            "reason": blocker,
        }
        overview["surfaces"]["provider_types"] = _provider_type_surface(provider_types, item_limit)
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("blocked")
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    ready_count = _ready_provider_count(configured_providers, provider_types)
    overview["surfaces"]["provider_types"] = _provider_type_surface(provider_types, item_limit)
    overview["surfaces"]["configured_providers"] = _configured_provider_surface(
        configured_providers,
        provider_types,
        item_limit,
    )
    overview["surfaces"]["provider_read"] = _provider_read_surface(configured_providers)
    overview["surfaces"]["provider_test"] = _provider_test_surface(configured_providers)
    overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency(
        "provider_configured"
        if ready_count > 0
        else "optional_unconfigured"
        if not configured_providers
        else "blocked_missing_credentials",
    )
    overview["surfaces"]["mutations"] = _web_search_mutation_surface()
    overview["surfaces"]["provider_setup"] = _provider_setup_surface(configured_providers, provider_types)
    overview["status"] = "partial"
    return overview


def native_web_search_provider_detail(provider_id: str) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnx-p2-03-provider"
    response["management_mode"] = "safe_read_confirmed_test"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["provider_read"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native web search management",
        }
        return response

    provider_id = str(provider_id or "").strip()
    if not provider_id:
        response["surfaces"]["provider_read"] = {
            "status": "blocked",
            "reason": "provider_id is required",
        }
        return response

    backend = _weknora_backend(settings)
    try:
        provider = backend.get_web_search_provider(provider_id)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["provider_read"] = {
            "status": "blocked",
            "reason": f"provider_read: {_error_code(exc)}",
        }
        response["warnings"].append(f"blocked: provider_read: {_error_code(exc)}")
        return response

    response["surfaces"]["provider_read"] = {
        "status": "live",
        "count": 1,
        "item": provider,
    }
    response["surfaces"]["provider_test"] = {
        "status": "blocked",
        "reason": "confirmation_required_before_external_web_search_probe",
        "confirm_token": WEB_SEARCH_TEST_CONFIRM_TOKEN,
        "endpoint": f"/api/web-search/native/providers/{provider_id}/test",
    }
    response["surfaces"]["mutations"] = _web_search_mutation_surface()
    response["status"] = "partial"
    return response


def test_native_web_search_provider(
    *,
    session: Session,
    provider_id: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnid-p4-01-saved-test"
    response["management_mode"] = "safe_read_confirmed_test"
    response["surfaces"]["mutations"] = _web_search_mutation_surface()
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["provider_test"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native web search management",
        }
        return response

    provider_id = str(provider_id or "").strip()
    if not provider_id:
        response["surfaces"]["provider_test"] = {
            "status": "blocked",
            "reason": "provider_id is required",
        }
        return response
    if confirm_token != WEB_SEARCH_TEST_CONFIRM_TOKEN:
        response["surfaces"]["provider_test"] = {
            "status": "blocked",
            "reason": "confirmation_required_before_external_web_search_probe",
            "confirm_token": WEB_SEARCH_TEST_CONFIRM_TOKEN,
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=WEB_SEARCH_TEST_CONFIRM_TOKEN,
            token_id=WEB_SEARCH_TEST_CONFIRM_TOKEN_ID,
            action=WEB_SEARCH_MUTATION_ACTIONS["saved_test"],
        )
    except NativeConfirmationError:
        response["surfaces"]["provider_test"] = _provider_test_blocked_surface()
        response["warnings"].append("blocked: web search provider test requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    audit = record_native_mutation_audit(
        session=session,
        capability="web_search",
        operation=WEB_SEARCH_MUTATION_ACTIONS["saved_test"],
        target_type="web_search_provider",
        target_id=provider_id,
        status="started",
        confirmation=confirmation,
        request_summary={"provider_id": provider_id, "saved_provider": True},
    )
    session.commit()
    try:
        result = backend.test_web_search_provider(provider_id)
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"success": False, "saved_provider": True},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"]["provider_test"] = {
            "status": "partial",
            "reason": f"native_test: {_error_code(exc)}",
            "success": False,
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: native_test: {_error_code(exc)}")
        return response

    success = bool(result.get("success"))
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if success else "failed",
        response_summary={"success": success, "saved_provider": True},
    )
    session.commit()
    response["status"] = "live" if success else "partial"
    response["surfaces"]["provider_test"] = {
        "status": "live" if success else "partial",
        "success": success,
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def test_native_web_search_provider_raw(
    *,
    session: Session,
    provider: str,
    parameters: dict[str, Any] | None,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="raw_test",
        confirm_token=confirm_token,
        provider_id=None,
        payload={
            "provider": provider,
            "parameters": parameters or {},
        },
    )


def create_native_web_search_provider(
    *,
    session: Session,
    name: str,
    provider: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    is_default: bool = False,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="create",
        confirm_token=confirm_token,
        provider_id=None,
        payload={
            "name": name,
            "provider": provider,
            "description": description,
            "parameters": parameters or {},
            "is_default": is_default,
        },
    )


def update_native_web_search_provider(
    *,
    session: Session,
    provider_id: str,
    name: str | None = None,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
    is_default: bool | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="update",
        confirm_token=confirm_token,
        provider_id=provider_id,
        payload={
            "name": name,
            "description": description,
            "parameters": parameters,
            "is_default": is_default,
        },
    )


def delete_native_web_search_provider(
    *,
    session: Session,
    provider_id: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="delete",
        confirm_token=confirm_token,
        provider_id=provider_id,
        payload={},
    )


def update_native_web_search_credentials(
    *,
    session: Session,
    provider_id: str,
    api_key: str | None = None,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="credentials_update",
        confirm_token=confirm_token,
        provider_id=provider_id,
        payload={
            "api_key_provided": bool(api_key),
            "_api_key": api_key,
        },
    )


def clear_native_web_search_credential(
    *,
    session: Session,
    provider_id: str,
    field: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    return _mutate_native_web_search_provider(
        session=session,
        action="credentials_clear",
        confirm_token=confirm_token,
        provider_id=provider_id,
        payload={"field": field},
    )


def _base_response(settings: Settings) -> dict[str, Any]:
    return {
        "schema_version": "wnid-p4-01",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _provider_type_surface(provider_types: list[dict], item_limit: int) -> dict[str, Any]:
    return {
        "status": "live",
        "count": len(provider_types),
        "requires_api_key_count": sum(
            1 for provider_type in provider_types if provider_type.get("requires_api_key")
        ),
        "free_count": sum(
            1 for provider_type in provider_types if not provider_type.get("requires_api_key")
        ),
        "requires_base_url_count": sum(
            1 for provider_type in provider_types if provider_type.get("requires_base_url")
        ),
        "items": provider_types[:item_limit],
    }


def _configured_provider_surface(
    configured_providers: list[dict],
    provider_types: list[dict],
    item_limit: int,
) -> dict[str, Any]:
    return {
        "status": "live",
        "count": len(configured_providers),
        "default_count": sum(1 for provider in configured_providers if provider.get("is_default")),
        "credentials_configured_count": sum(
            1 for provider in configured_providers if provider.get("credentials_configured")
        ),
        "ready_provider_count": _ready_provider_count(configured_providers, provider_types),
        "items": configured_providers[:item_limit],
    }


def _provider_setup_surface(configured_providers: list[dict], provider_types: list[dict]) -> dict[str, Any]:
    ready_count = _ready_provider_count(configured_providers, provider_types)
    if ready_count == 0:
        return {
            "status": "blocked",
            "success": False,
            "reason": "no ready native web search provider is configured",
            "recommended_provider": "duckduckgo",
            "requires_api_key": False,
            "confirmation": confirmation_surface(
                token_id=WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID,
                confirm_token=WEB_SEARCH_MUTATION_CONFIRM_TOKEN,
                reason="native Web Search provider setup changes external search configuration",
            ),
        }
    return {
        "status": "live",
        "success": True,
        "ready_provider_count": ready_count,
        "confirmation": confirmation_surface(
            token_id=WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID,
            confirm_token=WEB_SEARCH_MUTATION_CONFIRM_TOKEN,
            reason="native Web Search provider setup changes external search configuration",
        ),
    }


def _provider_read_surface(configured_providers: list[dict]) -> dict[str, Any]:
    if not configured_providers:
        return {
            "status": "backlog",
            "reason": "no native web search providers are configured",
            "count": 0,
        }
    return {
        "status": "live",
        "count": len(configured_providers),
        "endpoint": "/api/web-search/native/providers/{provider_id}",
    }


def _provider_test_surface(configured_providers: list[dict]) -> dict[str, Any]:
    if not configured_providers:
        return {
            "status": "backlog",
            "reason": "no native web search providers are configured",
            "count": 0,
        }
    return {
        "status": "blocked",
        "reason": "confirmation_required_before_external_web_search_probe",
        "confirm_token": WEB_SEARCH_TEST_CONFIRM_TOKEN,
        "confirm_token_id": WEB_SEARCH_TEST_CONFIRM_TOKEN_ID,
        "endpoint": "/api/web-search/native/providers/{provider_id}/test",
    }


def _agentqa_dependency(status: str) -> dict[str, Any]:
    reasons = {
        "provider_configured": (
            "native AgentQA can use web search when enabled and a ready provider is selected"
        ),
        "optional_configured": (
            "native AgentQA can use web search when enabled and a ready provider is selected"
        ),
        "optional_unconfigured": (
            "native AgentQA exposes web_search_enabled, but no provider is configured"
        ),
        "blocked_missing_credentials": (
            "native web search provider exists, but credential readiness is incomplete or untested"
        ),
        "blocked": "provider readiness could not be queried safely",
        "backlog": "native web search readiness requires weknora_api backend",
    }
    return {
        "status": status,
        "required_for_agentqa": False,
        "optional_for_agentqa": status in {"provider_configured", "optional_configured", "optional_unconfigured"},
        "ready_for_agentqa": status in {"provider_configured", "optional_configured"},
        "reason": reasons.get(status, "web search requirement is not proven"),
    }


def _web_search_mutation_surface() -> dict[str, Any]:
    return {
        "status": "live",
        "items": [
            "provider create/update/delete live with confirm_token and NativeMutationAudit",
            "credential update/clear live with masked metadata only",
            "saved/raw provider tests require confirm_token and NativeMutationAudit",
        ],
        "reason": (
            "WNID-P4-01 enables native Web Search provider setup and tests through PA; "
            "AgentQA Web Search answer/reference proof remains WNID-P4-02."
        ),
        "confirm_token_id": WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID,
        "confirmation": confirmation_surface(
            token_id=WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID,
            confirm_token=WEB_SEARCH_MUTATION_CONFIRM_TOKEN,
            reason="native Web Search provider setup changes external search configuration",
        ),
    }


def _mutate_native_web_search_provider(
    *,
    session: Session,
    action: str,
    confirm_token: str | None,
    provider_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnid-p4-01-provider-mutation"
    response["management_mode"] = "confirmed_web_search_provider_setup"
    response["surfaces"]["mutations"] = _web_search_mutation_surface()
    action_name = WEB_SEARCH_MUTATION_ACTIONS.get(action, f"weknora_web_search_{action}")
    token = WEB_SEARCH_TEST_CONFIRM_TOKEN if action == "raw_test" else WEB_SEARCH_MUTATION_CONFIRM_TOKEN
    token_id = WEB_SEARCH_TEST_CONFIRM_TOKEN_ID if action == "raw_test" else WEB_SEARCH_MUTATION_CONFIRM_TOKEN_ID

    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["mutation"] = {
            "status": "backlog",
            "action": action,
            "reason": "weknora_api backend is required for native web search provider setup",
        }
        return response

    provider_id = str(provider_id or "").strip()
    if action not in {"create", "raw_test"} and not provider_id:
        response["surfaces"]["mutation"] = {
            "status": "blocked",
            "action": action,
            "success": False,
            "reason": "provider_id is required",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=token,
            token_id=token_id,
            action=action_name,
        )
    except NativeConfirmationError:
        response["surfaces"]["mutation"] = _web_search_mutation_blocked_surface(action, token, token_id)
        response["warnings"].append(f"blocked: web search provider {action} requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    audit = record_native_mutation_audit(
        session=session,
        capability="web_search",
        operation=action_name,
        target_type="web_search_provider",
        target_id=provider_id or None,
        status="started",
        confirmation=confirmation,
        request_summary=_web_search_request_summary(action, provider_id, payload),
    )
    session.commit()
    try:
        result = _perform_web_search_mutation(backend, action, provider_id, payload)
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
            "reason": f"native_web_search_{action}: {_error_code(exc)}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: native_web_search_{action}: {_error_code(exc)}")
        return response

    if action == "create":
        audit.target_id = str(result.get("id") or "")
    success = bool(result.get("success", True))
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if success else "failed",
        response_summary=_web_search_response_summary(action, result),
    )
    session.commit()
    response["status"] = "live" if success else "partial"
    response["surfaces"]["mutation"] = {
        "status": "live" if success else "partial",
        "action": action,
        "success": success,
        "result": _public_web_search_result(action, result),
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _perform_web_search_mutation(
    backend: WeKnoraApiBackend,
    action: str,
    provider_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if action == "create":
        return backend.create_web_search_provider(
            name=str(payload.get("name") or "").strip(),
            provider=str(payload.get("provider") or "").strip(),
            description=str(payload.get("description") or "").strip(),
            parameters=payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {},
            is_default=bool(payload.get("is_default")),
        )
    if action == "update":
        return backend.update_web_search_provider(
            provider_id,
            name=_optional_text(payload.get("name")),
            description=_optional_text(payload.get("description")),
            parameters=payload.get("parameters") if payload.get("parameters") is not None else None,
            is_default=payload.get("is_default") if isinstance(payload.get("is_default"), bool) else None,
        )
    if action == "delete":
        return backend.delete_web_search_provider(provider_id)
    if action == "credentials_update":
        return backend.update_web_search_provider_credentials(
            provider_id,
            api_key=_optional_text(payload.get("_api_key")),
        )
    if action == "credentials_clear":
        return backend.clear_web_search_provider_credential(
            provider_id,
            str(payload.get("field") or "").strip(),
        )
    if action == "raw_test":
        return backend.test_web_search_provider_raw(
            provider=str(payload.get("provider") or "").strip(),
            parameters=payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {},
        )
    raise ValueError(f"unsupported web search provider action: {action}")


def _web_search_mutation_blocked_surface(action: str, confirm_token: str, token_id: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "action": action,
        "success": False,
        "reason": "confirmation_required_before_native_web_search_provider_setup",
        "confirmation": confirmation_surface(
            token_id=token_id,
            confirm_token=confirm_token,
            reason="native Web Search provider setup and tests require explicit operator confirmation",
        ),
    }


def _provider_test_blocked_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "success": False,
        "reason": "confirmation_required_before_external_web_search_probe",
        "confirmation": confirmation_surface(
            token_id=WEB_SEARCH_TEST_CONFIRM_TOKEN_ID,
            confirm_token=WEB_SEARCH_TEST_CONFIRM_TOKEN,
            reason="provider tests call external Web Search services",
        ),
    }


def _web_search_request_summary(action: str, provider_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    return {
        "action": action,
        "provider_id": provider_id,
        "provider": payload.get("provider"),
        "name": payload.get("name"),
        "is_default": payload.get("is_default"),
        "credential_field_count": int(bool(payload.get("api_key_provided"))),
        "field": payload.get("field"),
        "parameter_status": {
            "engine_id_configured": bool(parameters.get("engine_id")),
            "base_url_configured": bool(parameters.get("base_url")),
            "proxy_url_configured": bool(parameters.get("proxy_url")),
            "extra_config_key_count": len(parameters.get("extra_config"))
            if isinstance(parameters.get("extra_config"), dict)
            else 0,
        },
    }


def _web_search_response_summary(action: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "success": bool(result.get("success", True)),
        "provider": _public_web_search_provider_item(result)
        if action in {"create", "update"}
        else None,
        "credential_status": _public_web_search_credential_item(result)
        if action in {"credentials_update", "credentials_clear"}
        else None,
        "deleted": bool(result.get("status") == "deleted") if action == "delete" else None,
    }


def _public_web_search_result(action: str, result: dict[str, Any]) -> dict[str, Any]:
    if action in {"create", "update"}:
        return _public_web_search_provider_item(result)
    if action in {"credentials_update", "credentials_clear"}:
        return _public_web_search_credential_item(result)
    return {
        "success": bool(result.get("success", False)),
        "source": result.get("source") or "weknora_api",
    }


def _public_web_search_provider_item(provider: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": provider.get("id"),
        "name": provider.get("name"),
        "provider": provider.get("provider"),
        "is_default": bool(provider.get("is_default")),
        "credential_field_count": int(provider.get("credential_field_count") or 0),
        "configured_credential_field_count": int(provider.get("configured_credential_field_count") or 0),
        "credentials_configured": bool(provider.get("credentials_configured")),
        "parameter_status": provider.get("parameter_status") if isinstance(provider.get("parameter_status"), dict) else {},
        "source": provider.get("source") or "weknora_api",
    }


def _public_web_search_credential_item(item: dict[str, Any]) -> dict[str, Any]:
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
    text = str(value or "").strip()
    return text or None


def _ready_provider_count(configured_providers: list[dict], provider_types: list[dict]) -> int:
    type_requirements = {
        str(provider_type.get("id") or ""): bool(provider_type.get("requires_api_key"))
        for provider_type in provider_types
        if isinstance(provider_type, dict)
    }
    ready = 0
    for provider in configured_providers:
        provider_type = str(provider.get("provider") or "")
        if not type_requirements.get(provider_type, True):
            ready += 1
        elif provider.get("credentials_configured"):
            ready += 1
    return ready


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


def _error_code(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or exc.__class__.__name__)
