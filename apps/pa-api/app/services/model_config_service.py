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
        overview["surfaces"]["config_source"] = _config_source_surface(models)
        overview["surfaces"]["pa_bridge_alignment"] = _pa_bridge_alignment_surface(
            overview["surfaces"]["pa_runtime"],
            models,
        )
    except KnowledgeBackendUnavailableError as exc:
        _block_surface(overview, "model_catalog", exc)
        _block_surface(overview, "config_source", exc)
        _block_surface(overview, "pa_bridge_alignment", exc)

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
        "yaml_managed_model_count": int(
            overview["surfaces"].get("config_source", {}).get("yaml_managed_count") or 0
        ),
        "pa_bridge_alignment": overview["surfaces"].get("pa_bridge_alignment", {}).get("status"),
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
        "yaml_managed_count": sum(1 for model in models if model.get("managed_by") == "yaml"),
        "items": models[:item_limit],
    }


def _config_source_surface(models: list[dict[str, Any]]) -> dict[str, Any]:
    yaml_models = [
        model
        for model in models
        if model.get("is_builtin") and model.get("managed_by") == "yaml"
    ]
    type_counts = Counter(str(model.get("type") or "unknown") for model in yaml_models)
    required_types = ("KnowledgeQA", "Embedding")
    missing_required_types = [
        model_type
        for model_type in required_types
        if int(type_counts.get(model_type) or 0) == 0
    ]
    recommended_missing_types = [
        model_type
        for model_type in ("Rerank",)
        if int(type_counts.get(model_type) or 0) == 0
    ]
    if not yaml_models:
        status = "blocked"
        reason = (
            "no native model rows are marked is_builtin=true and managed_by=yaml; "
            "config/builtin_models.yaml or BUILTIN_MODELS_CONFIG is not proven as source of truth"
        )
    elif missing_required_types:
        status = "partial"
        reason = "yaml-managed model config is present but missing required model types"
    else:
        status = "live"
        reason = "yaml-managed built-in model config is the native source of truth"
    return {
        "status": status,
        "source": "config/builtin_models.yaml_or_BUILTIN_MODELS_CONFIG",
        "reason": reason,
        "yaml_managed_count": len(yaml_models),
        "type_counts": dict(sorted(type_counts.items())),
        "required_types": list(required_types),
        "missing_required_types": missing_required_types,
        "recommended_missing_types": recommended_missing_types,
        "default_yaml_count": sum(1 for model in yaml_models if model.get("is_default")),
    }


def _pa_bridge_alignment_surface(
    pa_runtime: dict[str, Any],
    models: list[dict[str, Any]],
) -> dict[str, Any]:
    yaml_models = [
        model
        for model in models
        if model.get("is_builtin") and model.get("managed_by") == "yaml"
    ]
    checks = {
        "chat": _runtime_model_alignment(
            runtime_model=pa_runtime.get("chat_model"),
            runtime_provider=pa_runtime.get("chat_provider"),
            model_type="KnowledgeQA",
            yaml_models=yaml_models,
        ),
        "embedding": _runtime_model_alignment(
            runtime_model=pa_runtime.get("embedding_model"),
            runtime_provider=pa_runtime.get("embedding_provider"),
            model_type="Embedding",
            yaml_models=yaml_models,
        ),
    }
    blocked = [
        name
        for name, check in checks.items()
        if check.get("status") == "blocked"
    ]
    partial = [
        name
        for name, check in checks.items()
        if check.get("status") == "partial"
    ]
    runtime_live = pa_runtime.get("status") == "live"
    if not runtime_live:
        status = "blocked"
        reason = "PA chat/embedding env bridge is not live-configured"
    elif blocked:
        status = "blocked"
        reason = "PA env bridge cannot be aligned because native YAML-managed models are missing"
    elif partial:
        status = "partial"
        reason = "PA env bridge is live but differs from native YAML-managed defaults"
    else:
        status = "live"
        reason = "PA env bridge is live and aligned with native YAML-managed model config"
    return {
        "status": status,
        "reason": reason,
        "source": "pa_env_bridge_to_native_builtin_models",
        "checks": checks,
    }


def _runtime_model_alignment(
    *,
    runtime_model: str | None,
    runtime_provider: str | None,
    model_type: str,
    yaml_models: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = [
        model
        for model in yaml_models
        if str(model.get("type") or "") == model_type
    ]
    if not candidates:
        return {
            "status": "blocked",
            "model_type": model_type,
            "candidate_count": 0,
            "reason": "no YAML-managed native model candidate",
        }
    runtime_name = _norm(runtime_model)
    runtime_provider_norm = _norm(runtime_provider)
    default_candidates = [model for model in candidates if model.get("is_default")]
    comparable = default_candidates or candidates
    name_match = any(_norm(model.get("name")) == runtime_name for model in comparable)
    provider_match = any(_norm(model.get("provider")) == runtime_provider_norm for model in comparable)
    if name_match and provider_match:
        status = "live"
        reason = "runtime model name and provider match native YAML-managed config"
    elif name_match:
        status = "partial"
        reason = "runtime model name matches but provider differs or is unavailable"
    else:
        status = "partial"
        reason = "runtime model name differs from native YAML-managed config"
    return {
        "status": status,
        "model_type": model_type,
        "candidate_count": len(candidates),
        "default_candidate_count": len(default_candidates),
        "name_match": name_match,
        "provider_match": provider_match,
        "reason": reason,
    }


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


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
