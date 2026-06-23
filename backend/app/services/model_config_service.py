from __future__ import annotations

from collections import Counter
from typing import Any

from app.config import Settings
from app.config import get_settings
from app.services.model_status_service import get_model_status
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_model_config_overview(limit: int = 10) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 20), 1)
    overview: dict[str, Any] = {
        "schema_version": "wnx-p2-01",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }
    overview["surfaces"]["pa_runtime"] = _pa_runtime_surface(settings)
    overview["surfaces"]["admin_tests"] = _admin_test_surface()
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["provider_catalog"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native model config visibility",
        }
        overview["surfaces"]["model_catalog"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native model config visibility",
        }
        overview["surfaces"]["parser_engines"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native parser visibility",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    overview["source"] = "weknora_api"
    backend = _weknora_backend(settings)
    providers: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    parser_payload: dict[str, Any] = {}
    storage_payload: dict[str, Any] = {}

    try:
        providers = backend.list_model_providers()
        overview["surfaces"]["provider_catalog"] = _provider_catalog_surface(providers, item_limit)
    except KnowledgeBackendUnavailableError as exc:
        _block_surface(overview, "provider_catalog", exc)

    try:
        models = backend.list_models()
        overview["surfaces"]["model_catalog"] = _model_catalog_surface(models, item_limit)
    except KnowledgeBackendUnavailableError as exc:
        _block_surface(overview, "model_catalog", exc)

    try:
        parser_payload = backend.list_parser_engines()
        overview["surfaces"]["parser_engines"] = _parser_engine_surface(parser_payload, item_limit)
    except KnowledgeBackendUnavailableError as exc:
        _block_surface(overview, "parser_engines", exc)

    try:
        storage_payload = backend.get_storage_engine_status()
        overview["surfaces"]["storage_engines"] = _storage_engine_surface(storage_payload, item_limit)
    except KnowledgeBackendUnavailableError as exc:
        _block_surface(overview, "storage_engines", exc)

    live_read_surfaces = [
        name
        for name in ("provider_catalog", "model_catalog", "parser_engines", "storage_engines")
        if overview["surfaces"].get(name, {}).get("status") == "live"
    ]
    runtime_status = overview["surfaces"]["pa_runtime"].get("status")
    if live_read_surfaces and runtime_status == "live":
        overview["status"] = "partial"
    elif live_read_surfaces:
        overview["status"] = "partial"
        overview["warnings"].append("partial: PA chat/embedding runtime is not fully configured")
    else:
        overview["status"] = "blocked"
    overview["summary"] = {
        "provider_count": len(providers),
        "model_count": len(models),
        "parser_engine_count": len(parser_payload.get("engines") or []),
        "storage_engine_count": len(storage_payload.get("engines") or []),
        "admin_tests": "blocked_admin_only",
    }
    return overview


def _pa_runtime_surface(settings: Settings) -> dict[str, Any]:
    status = get_model_status(settings)
    chat_ready = bool(status.chat.configured and not status.chat.mock)
    embedding_ready = bool(status.embedding.configured and not status.embedding.mock)
    return {
        "status": "live" if chat_ready and embedding_ready else "blocked",
        "chat_provider": status.chat.provider,
        "chat_model": status.chat.model,
        "chat_configured": status.chat.configured,
        "chat_mock": status.chat.mock,
        "chat_api_key_configured": status.chat.api_key_configured,
        "embedding_provider": status.embedding.provider,
        "embedding_model": status.embedding.model,
        "embedding_configured": status.embedding.configured,
        "embedding_mock": status.embedding.mock,
        "embedding_api_key_configured": status.embedding.api_key_configured,
        "embedding_dimension": status.embedding.dimension,
    }


def _provider_catalog_surface(providers: list[dict[str, Any]], item_limit: int) -> dict[str, Any]:
    type_counts: Counter[str] = Counter()
    for provider in providers:
        for model_type in provider.get("model_types") or []:
            type_counts[str(model_type)] += 1
    return {
        "status": "live",
        "count": len(providers),
        "model_type_counts": dict(sorted(type_counts.items())),
        "items": providers[:item_limit],
    }


def _model_catalog_surface(models: list[dict[str, Any]], item_limit: int) -> dict[str, Any]:
    type_counts = Counter(str(model.get("type") or "unknown") for model in models)
    source_counts = Counter(str(model.get("source") or "unknown") for model in models)
    status_counts = Counter(str(model.get("status") or "unknown") for model in models)
    return {
        "status": "live",
        "count": len(models),
        "type_counts": dict(sorted(type_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "default_count": sum(1 for model in models if model.get("is_default")),
        "builtin_count": sum(1 for model in models if model.get("is_builtin")),
        "credential_field_count": sum(int(model.get("credential_field_count") or 0) for model in models),
        "configured_credential_field_count": sum(
            int(model.get("configured_credential_field_count") or 0)
            for model in models
        ),
        "items": models[:item_limit],
    }


def _parser_engine_surface(payload: dict[str, Any], item_limit: int) -> dict[str, Any]:
    engines = payload.get("engines")
    engines = engines if isinstance(engines, list) else []
    available = [engine for engine in engines if engine.get("available")]
    return {
        "status": "live",
        "count": len(engines),
        "available_count": len(available),
        "unavailable_count": len(engines) - len(available),
        "docreader_connected": bool(payload.get("connected")),
        "docreader_addr_configured": bool(payload.get("docreader_addr_configured")),
        "docreader_transport": payload.get("docreader_transport"),
        "items": engines[:item_limit],
    }


def _storage_engine_surface(payload: dict[str, Any], item_limit: int) -> dict[str, Any]:
    engines = payload.get("engines")
    engines = engines if isinstance(engines, list) else []
    return {
        "status": "live",
        "count": len(engines),
        "allowed_count": sum(1 for engine in engines if engine.get("allowed")),
        "available_count": sum(1 for engine in engines if engine.get("available")),
        "allowed_provider_count": int(payload.get("allowed_provider_count") or 0),
        "minio_env_available": bool(payload.get("minio_env_available")),
        "items": engines[:item_limit],
    }


def _admin_test_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "WeKnora remote, embedding, rerank, parser, and storage check endpoints are Admin-only and may use stored credentials or trigger remote probes.",
        "remote_model_check": "blocked_admin_only",
        "embedding_test": "blocked_admin_only",
        "rerank_check": "blocked_admin_only",
        "parser_engine_check": "blocked_admin_only",
        "storage_engine_check": "blocked_admin_only",
    }


def _block_surface(overview: dict[str, Any], surface_name: str, exc: KnowledgeBackendUnavailableError) -> None:
    reason = f"{surface_name}: {exc.error_code}"
    overview["surfaces"][surface_name] = {"status": "blocked", "reason": reason}
    overview["warnings"].append(f"blocked: {reason}")


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


__all__ = ["native_model_config_overview"]
