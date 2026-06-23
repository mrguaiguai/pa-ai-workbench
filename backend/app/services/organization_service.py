from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_workbench_organization_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = {
        "schema_version": "wnx-p2-06",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "management_mode": "safe_read_with_mutation_backlog",
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["tags"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native organization features",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    backend = _weknora_backend(settings)
    overview["surfaces"]["tags"] = _tag_surface(backend, settings, item_limit)
    overview["surfaces"]["faq"] = _faq_surface(backend, settings, item_limit)
    overview["surfaces"]["favorites"] = _favorites_surface(backend)
    overview["surfaces"]["skills"] = _skills_surface(backend, item_limit)
    overview["surfaces"]["mutations"] = _mutation_backlog()

    live_surfaces = [
        surface
        for name, surface in overview["surfaces"].items()
        if name != "mutations" and surface.get("status") == "live"
    ]
    if live_surfaces:
        overview["status"] = "partial"
    else:
        overview["status"] = "blocked"
        overview["warnings"].append("blocked: no organization read surface was validated live")
    return overview


def _tag_surface(backend: WeKnoraApiBackend, settings: Settings, limit: int) -> dict[str, Any]:
    if not settings.weknora_default_kb_id:
        return {"status": "blocked", "reason": "active default KB is not configured"}
    try:
        tags = backend.list_knowledge_base_tags(settings.weknora_default_kb_id, limit=limit)
    except KnowledgeBackendUnavailableError as exc:
        return {"status": "blocked", "reason": f"tags: {_error_code(exc)}"}
    return {
        "status": "live",
        "count": len(tags),
        "used_count": sum(
            1
            for tag in tags
            if int(tag.get("knowledge_count") or 0) > 0 or int(tag.get("chunk_count") or 0) > 0
        ),
        "items": [
            {
                "name": tag.get("name"),
                "color_configured": bool(tag.get("color")),
                "knowledge_count": tag.get("knowledge_count"),
                "chunk_count": tag.get("chunk_count"),
            }
            for tag in tags[:limit]
        ],
    }


def _faq_surface(backend: WeKnoraApiBackend, settings: Settings, limit: int) -> dict[str, Any]:
    if not settings.weknora_default_kb_id:
        return {"status": "blocked", "reason": "active default KB is not configured"}
    try:
        entries = backend.list_faq_entries(settings.weknora_default_kb_id, limit=limit)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "blocked",
            "reason": f"faq_entries: {_error_code(exc)}",
            "readiness": "requires FAQ-type KB or readable FAQ entries",
        }
    return {
        "status": "live",
        "count": len(entries),
        "enabled_count": sum(1 for entry in entries if entry.get("enabled")),
        "recommended_count": sum(1 for entry in entries if entry.get("recommended")),
        "answer_count": sum(int(entry.get("answer_count") or 0) for entry in entries),
        "items": entries[:limit],
    }


def _favorites_surface(backend: WeKnoraApiBackend) -> dict[str, Any]:
    surfaces: dict[str, Any] = {"status": "live", "resource_types": {}}
    total = 0
    blocked: list[str] = []
    for resource_type in ("kb", "agent"):
        try:
            favorites = backend.list_user_favorites(resource_type)
        except KnowledgeBackendUnavailableError as exc:
            surfaces["resource_types"][resource_type] = {
                "status": "blocked",
                "reason": f"favorites_{resource_type}: {_error_code(exc)}",
            }
            blocked.append(resource_type)
            continue
        total += len(favorites)
        surfaces["resource_types"][resource_type] = {
            "status": "live",
            "count": len(favorites),
        }
    surfaces["count"] = total
    if blocked and len(blocked) == 2:
        surfaces["status"] = "blocked"
        surfaces["reason"] = "favorites require user-scoped auth context"
    elif blocked:
        surfaces["status"] = "partial"
        surfaces["blocked_types"] = blocked
    return surfaces


def _skills_surface(backend: WeKnoraApiBackend, limit: int) -> dict[str, Any]:
    try:
        result = backend.list_skills()
    except KnowledgeBackendUnavailableError as exc:
        return {"status": "blocked", "reason": f"skills: {_error_code(exc)}"}
    skills = result.get("skills") if isinstance(result.get("skills"), list) else []
    return {
        "status": "live",
        "count": len(skills),
        "skills_available": bool(result.get("skills_available")),
        "items": skills[:limit],
    }


def _mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "FAQ create/update/delete/import",
            "tag create/update/delete",
            "favorite add/remove",
            "skill upload/enable/execute",
            "PA-owned taxonomy system",
        ],
        "reason": (
            "WNX-P2-06 validates safe native organization visibility first. "
            "Mutation flows need dedicated confirmation, ownership, and audit design."
        ),
    }


def _error_code(exc: KnowledgeBackendUnavailableError) -> str:
    return str(getattr(exc, "error_code", None) or "native_unavailable")


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
