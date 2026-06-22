from __future__ import annotations

from collections import Counter
from typing import Any

from app.config import Settings
from app.config import get_settings
from app.services.model_status_service import get_model_status
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_vector_store_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = {
        "schema_version": "wf-p2-03",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "surfaces": {},
        "warnings": [],
    }
    overview["surfaces"]["embedding"] = _embedding_surface(settings)
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["store_types"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store visibility",
        }
        overview["surfaces"]["stores"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store visibility",
        }
        overview["surfaces"]["kb_binding"] = {
            "status": "backlog",
            "reason": "active KB binding requires weknora_api backend",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    overview["source"] = "weknora_api"
    backend = _weknora_backend(settings)
    try:
        store_types = backend.list_vector_store_types()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"store_types: {exc.error_code}"
        overview["surfaces"]["store_types"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    try:
        stores = backend.list_vector_stores()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"stores: {exc.error_code}"
        overview["surfaces"]["store_types"] = _store_type_surface(store_types, item_limit)
        overview["surfaces"]["stores"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    overview["surfaces"]["store_types"] = _store_type_surface(store_types, item_limit)
    overview["surfaces"]["stores"] = _stores_surface(stores, item_limit)
    overview["surfaces"]["kb_binding"] = _kb_binding_surface(settings, backend)
    overview["surfaces"]["mutations"] = _vector_store_mutation_backlog()
    overview["status"] = "live"
    return overview


def _store_type_surface(store_types: list[dict], item_limit: int) -> dict[str, Any]:
    return {
        "status": "live",
        "count": len(store_types),
        "connection_field_count": sum(
            int(store_type.get("connection_field_count") or 0)
            for store_type in store_types
        ),
        "sensitive_connection_field_count": sum(
            int(store_type.get("sensitive_connection_field_count") or 0)
            for store_type in store_types
        ),
        "index_field_count": sum(
            int(store_type.get("index_field_count") or 0)
            for store_type in store_types
        ),
        "items": store_types[:item_limit],
    }


def _stores_surface(stores: list[dict], item_limit: int) -> dict[str, Any]:
    source_counts = Counter(str(store.get("source") or "unknown") for store in stores)
    engine_counts = Counter(str(store.get("engine_type") or "unknown") for store in stores)
    return {
        "status": "live",
        "count": len(stores),
        "env_count": source_counts.get("env", 0),
        "user_count": source_counts.get("user", 0),
        "readonly_count": sum(1 for store in stores if store.get("readonly")),
        "engine_counts": dict(sorted(engine_counts.items())),
        "items": stores[:item_limit],
    }


def _kb_binding_surface(settings: Settings, backend: WeKnoraApiBackend) -> dict[str, Any]:
    if not settings.weknora_default_kb_id:
        return {
            "status": "blocked",
            "reason": "active default KB is not configured",
        }
    try:
        kb = backend.get_knowledge_base(settings.weknora_default_kb_id)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "blocked",
            "reason": f"knowledge_base: {exc.error_code}",
        }
    vector_store = kb.get("vector_store")
    if not isinstance(vector_store, dict):
        return {
            "status": "configured_unknown",
            "kb_configured": True,
            "reason": "native KB response did not include vector store display fields",
        }
    status = str(vector_store.get("status") or "").strip() or "unknown"
    source = str(vector_store.get("source") or "").strip() or "unknown"
    return {
        "status": "live" if status == "available" else "blocked",
        "kb_configured": True,
        "kb_id_configured": True,
        "binding_status": status,
        "binding_source": source,
        "engine_type": vector_store.get("engine_type") or None,
        "explicit_binding": bool(vector_store.get("bound")),
    }


def _embedding_surface(settings: Settings) -> dict[str, Any]:
    embedding = get_model_status(settings).embedding
    return {
        "status": "live" if embedding.configured and not embedding.mock else "blocked",
        "provider": embedding.provider,
        "model": embedding.model,
        "configured": embedding.configured,
        "mock": embedding.mock,
        "dimension": embedding.dimension,
    }


def _vector_store_mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "vector store CRUD",
            "connection tests",
            "raw connection config display",
            "PA-owned vector administration",
            "KB rebind mutation",
        ],
        "reason": "WF-P2-03 exposes read-only vector store visibility only.",
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
