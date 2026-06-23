from __future__ import annotations

from typing import Any

from app.services.data_source_service import native_data_source_overview
from app.config import Settings
from app.config import get_settings
from app.services.mcp_service import native_mcp_overview
from app.services.model_config_service import native_model_config_overview
from app.services.model_status_service import get_model_status
from app.services.runtime_status_service import get_weknora_status
from app.services.vector_store_service import native_vector_store_overview
from app.services.web_search_service import native_web_search_overview
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CAPABILITY_ORDER = [
    "system_health_status_deployment",
    "workspace_knowledge_base",
    "document_lifecycle",
    "chunk_management",
    "knowledge_search_rag",
    "knowledge_chat_session_chat",
    "agentqa_custom_agent",
    "native_wiki",
    "mcp",
    "web_search",
    "vector_store",
    "model_embedding_rerank_parser",
    "data_sources_connectors",
    "faq_tags_favorites_skills",
    "history_citation_product_shell",
]


def native_status_center(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    groups: dict[str, dict[str, Any]] = {}

    weknora_status = _call("weknora_status", lambda: get_weknora_status(settings))
    model_status = _call("model_status", lambda: get_model_status(settings))
    mcp_overview = _call("mcp", lambda: native_mcp_overview(limit=item_limit))
    web_search_overview = _call(
        "web_search",
        lambda: native_web_search_overview(limit=item_limit),
    )
    vector_store_overview = _call(
        "vector_store",
        lambda: native_vector_store_overview(limit=item_limit),
    )
    model_config_overview = _call(
        "model_config",
        lambda: native_model_config_overview(limit=item_limit),
    )
    data_source_overview = _call(
        "data_source",
        lambda: native_data_source_overview(limit=item_limit),
    )

    groups["system_health_status_deployment"] = _system_group(settings, weknora_status)
    groups["workspace_knowledge_base"] = _workspace_group(settings, weknora_status)
    groups["document_lifecycle"] = _baseline_group(
        capability_id="document_lifecycle",
        label="Document lifecycle",
        status="partial",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/documents",
        next_action="WNX-P1-02",
        summary={
            "live_status_surface": True,
            "known_gaps": [
                "URL/manual ingestion",
                "preview/download",
                "delete/reparse/cancel",
                "status spans",
            ],
        },
    )
    groups["chunk_management"] = _baseline_group(
        capability_id="chunk_management",
        label="Chunk management",
        status="partial",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/documents/{id}/chunks",
        next_action="WNX-P1-03",
        summary={
            "live_status_surface": True,
            "mutation_status": "backlog",
        },
    )
    groups["knowledge_search_rag"] = _baseline_group(
        capability_id="knowledge_search_rag",
        label="Knowledge-search / RAG",
        status="live",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/rag/debug",
        next_action="WNX-P1-04",
        summary={
            "native_search_adapter": "available",
            "citation_required": True,
        },
    )
    groups["knowledge_chat_session_chat"] = _baseline_group(
        capability_id="knowledge_chat_session_chat",
        label="Knowledge-chat / session chat",
        status="backlog",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/v1/knowledge-chat/{session_id}",
        next_action="WNX-P1-04",
        summary={"pa_path": "not_integrated"},
    )
    groups["agentqa_custom_agent"] = _baseline_group(
        capability_id="agentqa_custom_agent",
        label="AgentQA / custom Agent",
        status="partial",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/v1/agent-chat/{session_id}",
        next_action="WNX-P1-05",
        summary={
            "answer_history_path": "available",
            "citation_status": "blocked_until_traceable_references",
        },
    )
    groups["native_wiki"] = _baseline_group(
        capability_id="native_wiki",
        label="Native Wiki",
        status="live" if _weknora_core_configured(settings) else "blocked",
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/wiki/native/overview",
        next_action="WNX-P1-07",
        summary={
            "workflow_surfaces": "pages_search_read_index_log_graph_stats_lint_issues",
            "mutation_status": "confirmation_required",
            "global_maintenance": "operator_confirmed_only",
        },
    )
    groups["mcp"] = _overview_group(
        capability_id="mcp",
        label="MCP",
        overview=mcp_overview,
        configured=_mcp_configured(mcp_overview),
        source_endpoint="/api/mcp/native/overview",
        native_endpoint="/api/v1/mcp-services",
        next_action="WNX-P2-02",
        summary=_mcp_summary(mcp_overview),
    )
    groups["web_search"] = _overview_group(
        capability_id="web_search",
        label="Web search",
        overview=web_search_overview,
        configured=_web_search_configured(web_search_overview),
        source_endpoint="/api/web-search/native/overview",
        native_endpoint="/api/v1/web-search-providers",
        next_action="WNX-P2-03",
        summary=_web_search_summary(web_search_overview),
    )
    groups["vector_store"] = _overview_group(
        capability_id="vector_store",
        label="Vector store",
        overview=vector_store_overview,
        configured=_vector_store_configured(vector_store_overview),
        source_endpoint="/api/vector-stores/native/overview",
        native_endpoint="/api/v1/vector-stores",
        next_action="WNX-P2-04",
        summary=_vector_store_summary(vector_store_overview),
    )
    groups["model_embedding_rerank_parser"] = _model_group(
        settings,
        model_status,
        model_config_overview,
    )
    groups["data_sources_connectors"] = _overview_group(
        capability_id="data_sources_connectors",
        label="Data sources / connectors",
        overview=data_source_overview,
        configured=_data_source_configured(data_source_overview),
        source_endpoint="/api/data-sources/native/overview",
        native_endpoint="/api/v1/datasource",
        next_action="WNX-P2-05",
        summary=_data_source_summary(data_source_overview),
    )
    groups["faq_tags_favorites_skills"] = _baseline_group(
        capability_id="faq_tags_favorites_skills",
        label="FAQ / tags / favorites / skills",
        status="backlog",
        configured=False,
        source_endpoint=(
            "/api/v1/knowledge-bases/{kb_id}/faq, "
            "/api/v1/knowledge-bases/{kb_id}/tags, "
            "/api/v1/user/favorites, /api/v1/skills"
        ),
        next_action="WNX-P2-06",
        summary={
            "safe_read_endpoints_exist": True,
            "pa_workbench_workflow": "not_integrated",
        },
    )
    groups["history_citation_product_shell"] = _baseline_group(
        capability_id="history_citation_product_shell",
        label="History / citation / product shell",
        status="partial",
        configured=True,
        source_endpoint="/api/history, /api/citations/locate",
        next_action="WNX-P1-07",
        summary={
            "pa_owned": True,
            "native_workflow_unification": "incomplete",
        },
    )

    ordered_groups = {key: groups[key] for key in CAPABILITY_ORDER}
    return {
        "schema_version": "wnx-p0-02",
        "source": "pa_backend_bff",
        "status": _aggregate_status(ordered_groups),
        "evidence_type": "live_api",
        "configured": _weknora_core_configured(settings),
        "masked": True,
        "config": _masked_config(settings),
        "groups": ordered_groups,
        "group_count": len(ordered_groups),
        "warnings": _warnings(ordered_groups),
        "next_action": "WNX-P0-03",
    }


def _system_group(settings: Settings, weknora_status: dict[str, Any]) -> dict[str, Any]:
    if weknora_status.get("error"):
        status = "blocked"
        summary = {"reason": weknora_status["error"]}
    else:
        payload = weknora_status.get("value")
        connected = bool(getattr(payload, "connected", False))
        status = "live" if connected and not settings.mock_mode else "blocked"
        summary = {
            "pa_health": "ok",
            "weknora_connected": connected,
            "weknora_health_status": getattr(payload, "health_status", None),
            "mock_mode": settings.mock_mode,
        }
    return _group(
        capability_id="system_health_status_deployment",
        label="System health / status / deployment",
        status=status,
        configured=_weknora_core_configured(settings),
        source_endpoint="/api/status",
        native_endpoint="/health",
        next_action="WNX-P0-05",
        summary=summary,
    )


def _workspace_group(settings: Settings, weknora_status: dict[str, Any]) -> dict[str, Any]:
    payload = weknora_status.get("value")
    mapping = getattr(payload, "kb_mapping", {}) if payload is not None else {}
    mapping_status = str(mapping.get("status") or "").strip()
    if weknora_status.get("error"):
        status = "blocked"
        summary = {"reason": weknora_status["error"]}
    else:
        status = "live" if mapping_status == "validated" else mapping_status or "blocked"
        if status == "configured":
            status = "partial"
        summary = {
            "mapping_status": mapping_status or None,
            "validated": bool(mapping.get("validated")),
            "selection_source": mapping.get("selection_source"),
            "default_used": mapping.get("default_used"),
            "mapping_configured": bool(mapping.get("mapping_configured")),
            "management_endpoint": "/api/knowledge-bases/native/overview",
            "unsafe_mutations": "backlog_until_confirmation_and_audit_trail",
        }
    return _group(
        capability_id="workspace_knowledge_base",
        label="Workspace / knowledge base",
        status=status,
        configured=bool(settings.weknora_workspace_id and settings.weknora_default_kb_id),
        source_endpoint="/api/knowledge-bases/native/overview",
        native_endpoint=(
            "/api/v1/tenants/{workspace_id}, /api/v1/knowledge-bases, "
            "/api/v1/knowledge-bases/{kb_id}, /api/v1/knowledge-bases/{kb_id}/tags"
        ),
        next_action="WNX-P3-02",
        summary=summary,
    )


def _model_group(
    settings: Settings,
    model_status: dict[str, Any],
    model_config_overview: dict[str, Any],
) -> dict[str, Any]:
    if model_config_overview.get("error"):
        status = "blocked"
        summary = {"reason": model_config_overview["error"]}
        configured = False
    elif model_config_overview.get("value"):
        overview = model_config_overview["value"]
        surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
        summary = _model_config_summary(overview)
        configured = surfaces.get("pa_runtime", {}).get("status") == "live"
        status = str(overview.get("status") or "blocked")
    elif model_status.get("error"):
        status = "blocked"
        summary = {"reason": model_status["error"]}
        configured = False
    else:
        payload = model_status["value"]
        chat = payload.chat
        embedding = payload.embedding
        configured = bool(payload.configured and not chat.mock and not embedding.mock)
        status = "live" if configured else "blocked"
        summary = {
            "pa_chat": {
                "provider": chat.provider,
                "model": chat.model,
                "configured": chat.configured,
                "mock": chat.mock,
            },
            "pa_embedding": {
                "provider": embedding.provider,
                "model": embedding.model,
                "configured": embedding.configured,
                "mock": embedding.mock,
                "dimension": embedding.dimension,
            },
            "native_model_catalog": "backlog",
            "native_parser_engines": "backlog",
            "native_rerank_remote_check": "blocked_admin_only",
        }
    return _group(
        capability_id="model_embedding_rerank_parser",
        label="Model / embedding / rerank / parser",
        status=status,
        configured=configured,
        source_endpoint="/api/model/native/overview",
        native_endpoint=(
            "/api/v1/models, /api/v1/models/providers, "
            "/api/v1/system/parser-engines, /api/v1/system/storage-engine-status"
        ),
        next_action="WNX-P3-02",
        summary=summary,
    )


def _overview_group(
    *,
    capability_id: str,
    label: str,
    overview: dict[str, Any],
    configured: bool,
    source_endpoint: str,
    native_endpoint: str,
    next_action: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    if overview.get("error"):
        status = "blocked"
        summary = {"reason": overview["error"], **summary}
    else:
        status = _normalize_status(str(overview.get("value", {}).get("status") or "blocked"))
    return _group(
        capability_id=capability_id,
        label=label,
        status=status,
        configured=configured,
        source_endpoint=source_endpoint,
        native_endpoint=native_endpoint,
        next_action=next_action,
        summary=summary,
    )


def _baseline_group(
    *,
    capability_id: str,
    label: str,
    status: str,
    configured: bool,
    source_endpoint: str,
    next_action: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return _group(
        capability_id=capability_id,
        label=label,
        status=status,
        configured=configured,
        source_endpoint=source_endpoint,
        native_endpoint=None,
        next_action=next_action,
        summary={**summary, "status_source": "wnx_status_center_baseline"},
    )


def _group(
    *,
    capability_id: str,
    label: str,
    status: str,
    configured: bool,
    source_endpoint: str,
    native_endpoint: str | None,
    next_action: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    normalized_status = _normalize_status(status)
    return {
        "id": capability_id,
        "label": label,
        "status": normalized_status,
        "configured": bool(configured),
        "masked": True,
        "source_endpoint": source_endpoint,
        "native_endpoint": native_endpoint,
        "next_action": next_action,
        "summary": summary,
    }


def _masked_config(settings: Settings) -> dict[str, Any]:
    backend = WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
        retry_attempts=0,
    )
    return {
        "knowledge_backend": settings.knowledge_backend,
        "mock_mode": settings.mock_mode,
        "weknora": backend.native_client_status(),
        "chat_model": {
            "provider": settings.chat_model_provider,
            "configured": bool(settings.chat_model_base_url and settings.chat_model_name),
            "api_key_configured": bool(settings.chat_model_api_key),
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "configured": bool(
                settings.embedding_base_url
                and settings.embedding_model_name
                and settings.embedding_dimension > 0
            ),
            "api_key_configured": bool(settings.embedding_api_key),
            "dimension": settings.embedding_dimension,
        },
    }


def _call(label: str, func) -> dict[str, Any]:
    try:
        return {"value": func()}
    except Exception as exc:  # noqa: BLE001
        return {"error": _public_error(label, exc)}


def _mcp_summary(overview: dict[str, Any]) -> dict[str, Any]:
    value = overview.get("value") or {}
    surfaces = _surfaces(value)
    services = surfaces.get("services", {})
    tools = surfaces.get("tools", {})
    resources = surfaces.get("resources", {})
    approval = surfaces.get("approval", {})
    service_read = surfaces.get("service_read", {})
    safe_test = surfaces.get("safe_test", {})
    mutations = surfaces.get("mutations", {})
    return {
        "services_count": int(services.get("count") or 0),
        "safe_test_status": safe_test.get("status"),
        "service_read_status": service_read.get("status"),
        "mutations_status": mutations.get("status"),
        "services_status": services.get("status"),
        "enabled_count": int(services.get("enabled_count") or 0),
        "tools_status": tools.get("status"),
        "tools_count": int(tools.get("count") or 0),
        "resources_status": resources.get("status"),
        "resources_count": int(resources.get("count") or 0),
        "approval_status": approval.get("status"),
        "approval_count": int(approval.get("count") or 0),
    }


def _web_search_summary(overview: dict[str, Any]) -> dict[str, Any]:
    value = overview.get("value") or {}
    surfaces = _surfaces(value)
    provider_types = surfaces.get("provider_types", {})
    providers = surfaces.get("configured_providers", {})
    provider_read = surfaces.get("provider_read", {})
    provider_test = surfaces.get("provider_test", {})
    agentqa = surfaces.get("agentqa_dependency", {})
    mutations = surfaces.get("mutations", {})
    return {
        "provider_type_count": int(provider_types.get("count") or 0),
        "provider_test_status": provider_test.get("status"),
        "provider_read_status": provider_read.get("status"),
        "agentqa_dependency_status": agentqa.get("status"),
        "provider_types_status": provider_types.get("status"),
        "configured_provider_count": int(providers.get("count") or 0),
        "default_provider_count": int(providers.get("default_count") or 0),
        "credentials_configured_count": int(providers.get("credentials_configured_count") or 0),
        "ready_provider_count": int(providers.get("ready_provider_count") or 0),
        "mutations_status": mutations.get("status"),
    }


def _vector_store_summary(overview: dict[str, Any]) -> dict[str, Any]:
    value = overview.get("value") or {}
    surfaces = _surfaces(value)
    store_types = surfaces.get("store_types", {})
    stores = surfaces.get("stores", {})
    store_read = surfaces.get("store_read", {})
    store_test = surfaces.get("store_test", {})
    kb_binding = surfaces.get("kb_binding", {})
    embedding = surfaces.get("embedding", {})
    mutations = surfaces.get("mutations", {})
    return {
        "store_read_status": store_read.get("status"),
        "store_test_status": store_test.get("status"),
        "store_types_status": store_types.get("status"),
        "store_type_count": int(store_types.get("count") or 0),
        "stores_status": stores.get("status"),
        "stores_count": int(stores.get("count") or 0),
        "env_count": int(stores.get("env_count") or 0),
        "user_count": int(stores.get("user_count") or 0),
        "kb_binding_status": kb_binding.get("binding_status") or kb_binding.get("status"),
        "kb_binding_source": kb_binding.get("binding_source"),
        "embedding_status": embedding.get("status"),
        "embedding_provider": embedding.get("provider"),
        "embedding_mock": embedding.get("mock"),
        "mutations_status": mutations.get("status"),
    }


def _data_source_summary(overview: dict[str, Any]) -> dict[str, Any]:
    value = overview.get("value") or {}
    surfaces = _surfaces(value)
    connector_types = surfaces.get("connector_types", {})
    data_sources = surfaces.get("data_sources", {})
    connector_read = surfaces.get("connector_read", {})
    sync_logs = surfaces.get("sync_logs", {})
    resources = surfaces.get("resources", {})
    validation = surfaces.get("validation", {})
    sync_control = surfaces.get("sync_control", {})
    mutations = surfaces.get("mutations", {})
    return {
        "connector_type_count": int(connector_types.get("count") or 0),
        "data_source_count": int(data_sources.get("count") or 0),
        "sync_control_status": sync_control.get("status"),
        "resources_status": resources.get("status"),
        "connector_type_status": connector_types.get("status"),
        "data_sources_status": data_sources.get("status"),
        "connector_read_status": connector_read.get("status"),
        "sync_logs_status": sync_logs.get("status"),
        "validation_status": validation.get("status"),
        "credential_required_count": int(connector_types.get("credential_required_count") or 0),
        "credential_configured_count": int(data_sources.get("credential_configured_count") or 0),
        "scheduled_count": int(data_sources.get("scheduled_count") or 0),
        "mutations_status": mutations.get("status"),
    }


def _model_config_summary(overview: dict[str, Any]) -> dict[str, Any]:
    surfaces = _surfaces(overview)
    provider_catalog = surfaces.get("provider_catalog", {})
    model_catalog = surfaces.get("model_catalog", {})
    parser_engines = surfaces.get("parser_engines", {})
    storage_engines = surfaces.get("storage_engines", {})
    pa_runtime = surfaces.get("pa_runtime", {})
    admin_tests = surfaces.get("admin_tests", {})
    return {
        "provider_count": int(provider_catalog.get("count") or 0),
        "model_count": int(model_catalog.get("count") or 0),
        "parser_engine_count": int(parser_engines.get("count") or 0),
        "storage_engine_count": int(storage_engines.get("count") or 0),
        "chat_provider": pa_runtime.get("chat_provider"),
        "embedding_provider": pa_runtime.get("embedding_provider"),
        "embedding_dimension": pa_runtime.get("embedding_dimension"),
        "admin_tests": admin_tests.get("status"),
    }


def _mcp_configured(overview: dict[str, Any]) -> bool:
    services = _surfaces(overview.get("value") or {}).get("services", {})
    return int(services.get("count") or 0) > 0


def _web_search_configured(overview: dict[str, Any]) -> bool:
    providers = _surfaces(overview.get("value") or {}).get("configured_providers", {})
    return int(providers.get("count") or 0) > 0


def _vector_store_configured(overview: dict[str, Any]) -> bool:
    stores = _surfaces(overview.get("value") or {}).get("stores", {})
    return int(stores.get("count") or 0) > 0


def _data_source_configured(overview: dict[str, Any]) -> bool:
    data_sources = _surfaces(overview.get("value") or {}).get("data_sources", {})
    return int(data_sources.get("count") or 0) > 0


def _surfaces(value: dict[str, Any]) -> dict[str, Any]:
    surfaces = value.get("surfaces") if isinstance(value, dict) else {}
    return surfaces if isinstance(surfaces, dict) else {}


def _weknora_core_configured(settings: Settings) -> bool:
    return bool(
        settings.knowledge_backend == "weknora_api"
        and settings.weknora_base_url
        and settings.weknora_service_token
        and settings.weknora_workspace_id
        and settings.weknora_default_kb_id
    )


def _aggregate_status(groups: dict[str, dict[str, Any]]) -> str:
    statuses = {str(group.get("status") or "") for group in groups.values()}
    if "blocked" in statuses:
        return "partial"
    if "partial" in statuses or "backlog" in statuses:
        return "partial"
    return "live"


def _warnings(groups: dict[str, dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for capability_id, group in groups.items():
        status = group.get("status")
        if status in {"blocked", "backlog"}:
            warnings.append(f"{capability_id}: {status}")
    return warnings


def _normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"live", "partial", "blocked", "backlog"}:
        return normalized
    if normalized in {"validated", "connected", "ok", "healthy", "ready"}:
        return "live"
    if normalized in {"configured", "configured_unknown", "optional", "optional_unconfigured"}:
        return "partial"
    return "blocked"


def _public_error(label: str, exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in (
        "Authorization",
        "Bearer",
        "api_key",
        "service_token",
        "password",
        "secret",
        "token",
    ):
        text = text.replace(marker, "[redacted]")
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return f"{label}: {text}"


__all__ = ["native_status_center"]
