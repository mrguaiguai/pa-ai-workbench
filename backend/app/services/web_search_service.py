from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_web_search_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = {
        "schema_version": "wf-p2-02",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["provider_types"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native web search visibility",
        }
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("backlog")
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    overview["source"] = "weknora_api"
    backend = _weknora_backend(settings)
    try:
        provider_types = backend.list_web_search_provider_types()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"provider_types: {exc.error_code}"
        overview["surfaces"]["provider_types"] = {"status": "blocked", "reason": blocker}
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("blocked")
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    try:
        configured_providers = backend.list_web_search_providers()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"configured_providers: {exc.error_code}"
        overview["surfaces"]["configured_providers"] = {
            "status": "blocked",
            "reason": blocker,
        }
        overview["surfaces"]["provider_types"] = _provider_type_surface(
            provider_types,
            item_limit,
        )
        overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency("blocked")
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    default_count = sum(1 for provider in configured_providers if provider.get("is_default"))
    configured_credentials = sum(
        1 for provider in configured_providers if provider.get("credentials_configured")
    )
    overview["surfaces"]["provider_types"] = _provider_type_surface(provider_types, item_limit)
    overview["surfaces"]["configured_providers"] = {
        "status": "live",
        "count": len(configured_providers),
        "default_count": default_count,
        "credentials_configured_count": configured_credentials,
        "items": configured_providers[:item_limit],
    }
    overview["surfaces"]["agentqa_dependency"] = _agentqa_dependency(
        "optional" if configured_providers else "optional_unconfigured",
    )
    overview["surfaces"]["mutations"] = _web_search_mutation_backlog()
    overview["status"] = "live"
    return overview


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


def _agentqa_dependency(status: str) -> dict[str, Any]:
    reasons = {
        "optional": "native AgentQA can use web search when enabled and a provider is selected",
        "optional_unconfigured": (
            "native AgentQA exposes web_search_enabled, but no provider is configured"
        ),
        "blocked": "provider readiness could not be queried safely",
        "backlog": "native web search readiness requires weknora_api backend",
    }
    return {
        "status": status,
        "required_for_agentqa": False,
        "optional_for_agentqa": status in {"optional", "optional_unconfigured"},
        "reason": reasons.get(status, "web search requirement is not proven"),
    }


def _web_search_mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "provider CRUD",
            "credential forms",
            "connection tests",
            "raw web search debugging",
            "PA-owned web search orchestration",
        ],
        "reason": "WF-P2-02 exposes read-only web search provider visibility only.",
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
