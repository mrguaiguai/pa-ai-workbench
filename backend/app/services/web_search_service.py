from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


WEB_SEARCH_TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"


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
        "optional_configured"
        if ready_count > 0
        else "optional_unconfigured"
        if not configured_providers
        else "blocked_missing_credentials",
    )
    overview["surfaces"]["mutations"] = _web_search_mutation_backlog()
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
    response["surfaces"]["mutations"] = _web_search_mutation_backlog()
    response["status"] = "partial"
    return response


def test_native_web_search_provider(provider_id: str, confirm_token: str | None) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings)
    response["schema_version"] = "wnx-p2-03-test"
    response["management_mode"] = "safe_read_confirmed_test"
    response["surfaces"]["mutations"] = _web_search_mutation_backlog()
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

    backend = _weknora_backend(settings)
    try:
        result = backend.test_web_search_provider(provider_id)
    except KnowledgeBackendUnavailableError as exc:
        response["status"] = "partial"
        response["surfaces"]["provider_test"] = {
            "status": "partial",
            "reason": f"native_test: {_error_code(exc)}",
            "success": False,
        }
        response["warnings"].append(f"partial: native_test: {_error_code(exc)}")
        return response

    success = bool(result.get("success"))
    response["status"] = "live" if success else "partial"
    response["surfaces"]["provider_test"] = {
        "status": "live" if success else "partial",
        "success": success,
    }
    return response


def _base_response(settings: Settings) -> dict[str, Any]:
    return {
        "schema_version": "wnx-p2-03",
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
        "endpoint": "/api/web-search/native/providers/{provider_id}/test",
    }


def _agentqa_dependency(status: str) -> dict[str, Any]:
    reasons = {
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
        "optional_for_agentqa": status in {"optional_configured", "optional_unconfigured"},
        "ready_for_agentqa": status == "optional_configured",
        "reason": reasons.get(status, "web search requirement is not proven"),
    }


def _web_search_mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "provider create/update/delete",
            "credential forms",
            "raw credential tests",
            "raw web search debugging",
            "PA-owned web search orchestration",
        ],
        "reason": (
            "WNX-P2-03 exposes safe read and confirmation-gated saved-provider "
            "tests only; credential and mutation workflows require a separate "
            "approval and audit design."
        ),
    }


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
