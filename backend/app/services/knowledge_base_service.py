from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app.config import Settings
from app.config import get_settings
from app.models import KnowledgeBaseSelectionSnapshot
from app.models import utc_now
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError


def native_knowledge_base_overview(session: Session, limit: int = 20) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 100), 1)
    overview: dict[str, Any] = {
        "schema_version": "wnx-p1-01",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "evidence_type": "live_api",
        "masked": True,
        "workspace_id_configured": bool(settings.weknora_workspace_id),
        "default_kb_configured": bool(settings.weknora_default_kb_id),
        "active_selection": None,
        "items": [],
        "total": 0,
        "surfaces": {},
        "warnings": [],
        "next_action": "WNX-P1-02",
    }
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        overview["surfaces"] = _backlog_surfaces()
        return overview

    backend = _weknora_backend(settings)
    try:
        kbs = backend.list_knowledge_bases()
    except KnowledgeBackendUnavailableError as exc:
        overview["surfaces"]["list"] = {"status": "blocked", "reason": exc.error_code}
        overview["warnings"].append(f"blocked: list knowledge bases failed ({exc.error_code})")
        return overview

    active = _active_selection(session, backend, settings, kbs)
    overview["items"] = kbs[:item_limit]
    overview["total"] = len(kbs)
    overview["active_selection"] = active
    overview["surfaces"] = {
        "list": {
            "status": "live",
            "count": len(kbs),
            "temporary_count": sum(1 for item in kbs if item.get("is_temporary")),
            "pinned_count": sum(1 for item in kbs if item.get("is_pinned")),
        },
        "read": {
            "status": "live" if active and active.get("validated") else "blocked",
            "kb_id": active.get("kb_id") if active else None,
            "selection_source": active.get("selection_source") if active else None,
        },
        "active_selection": {
            "status": "live" if active else "blocked",
            "snapshot_saved": bool(active and active.get("selection_source") == "pa_active_selection"),
        },
        "tags": _tags_surface(backend, active, item_limit),
        "mutations": _mutation_backlog(),
    }
    overview["status"] = "live" if active else "partial"
    return overview


def select_active_knowledge_base(session: Session, kb_id: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.knowledge_backend != "weknora_api":
        raise KnowledgeBackendUnavailableError("weknora_api backend is required for KB selection")
    backend = _weknora_backend(settings)
    kb = backend.get_knowledge_base(kb_id)
    snapshot = _save_selection_snapshot(
        session=session,
        workspace_id=settings.weknora_workspace_id or None,
        kb=kb,
        selection_source="pa_active_selection",
        mapping_name=None,
    )
    tags = _safe_tags(backend, kb.get("id"), limit=20)
    return {
        "schema_version": "wnx-p1-01",
        "status": "live",
        "evidence_type": "live_api",
        "source": "pa_backend_bff",
        "active_selection": _snapshot_to_selection(snapshot, kb=kb, validated=True),
        "tags": tags,
        "mutation_backlog": _mutation_backlog()["items"],
    }


def active_knowledge_base_id(session: Session) -> str | None:
    snapshot = _latest_selection_snapshot(session)
    if snapshot and snapshot.status == "active":
        return snapshot.kb_id
    return None


def _active_selection(
    session: Session,
    backend: WeKnoraApiBackend,
    settings: Settings,
    kbs: list[dict],
) -> dict[str, Any] | None:
    snapshot = _latest_selection_snapshot(session)
    if snapshot and snapshot.status == "active":
        matching = next((item for item in kbs if item.get("id") == snapshot.kb_id), None)
        if matching is not None:
            return _snapshot_to_selection(snapshot, kb=matching, validated=True)

    try:
        target = backend.active_kb_target()
        kb = backend.get_knowledge_base(str(target.get("kb_id") or settings.weknora_default_kb_id))
    except KnowledgeBackendUnavailableError:
        return None

    return {
        "workspace_id": target.get("workspace_id") or settings.weknora_workspace_id or None,
        "kb_id": kb.get("id") or target.get("kb_id"),
        "name": kb.get("name"),
        "type": kb.get("type"),
        "selection_source": target.get("selection_source") or "default",
        "mapping_name": target.get("mapping_name"),
        "default_used": bool(target.get("default_used")),
        "validated": True,
        "snapshot_saved": False,
        "source": "weknora_api",
        "vector_store": kb.get("vector_store"),
    }


def _save_selection_snapshot(
    *,
    session: Session,
    workspace_id: str | None,
    kb: dict[str, Any],
    selection_source: str,
    mapping_name: str | None,
) -> KnowledgeBaseSelectionSnapshot:
    snapshot = KnowledgeBaseSelectionSnapshot(
        workspace_id=workspace_id,
        kb_id=str(kb.get("id") or ""),
        selection_source=selection_source,
        mapping_name=mapping_name,
        name=kb.get("name"),
        type=kb.get("type"),
        source="weknora_api",
        status="active",
        metadata_json=json.dumps(
            {
                "knowledge_count": kb.get("knowledge_count"),
                "chunk_count": kb.get("chunk_count"),
                "is_processing": kb.get("is_processing"),
                "vector_store": kb.get("vector_store"),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def _latest_selection_snapshot(session: Session) -> KnowledgeBaseSelectionSnapshot | None:
    statement = (
        select(KnowledgeBaseSelectionSnapshot)
        .order_by(KnowledgeBaseSelectionSnapshot.created_at.desc())
        .limit(1)
    )
    return session.exec(statement).first()


def _snapshot_to_selection(
    snapshot: KnowledgeBaseSelectionSnapshot,
    *,
    kb: dict[str, Any],
    validated: bool,
) -> dict[str, Any]:
    return {
        "workspace_id": snapshot.workspace_id,
        "kb_id": snapshot.kb_id,
        "name": kb.get("name") or snapshot.name,
        "type": kb.get("type") or snapshot.type,
        "selection_source": snapshot.selection_source,
        "mapping_name": snapshot.mapping_name,
        "default_used": False,
        "validated": validated,
        "snapshot_saved": True,
        "source": snapshot.source,
        "vector_store": kb.get("vector_store"),
        "created_at": snapshot.created_at.isoformat(),
    }


def _tags_surface(
    backend: WeKnoraApiBackend,
    active: dict[str, Any] | None,
    limit: int,
) -> dict[str, Any]:
    if not active or not active.get("kb_id"):
        return {"status": "blocked", "reason": "active KB is unavailable"}
    tags = _safe_tags(backend, active.get("kb_id"), limit=limit)
    return {
        "status": "live",
        "count": len(tags),
        "items": tags[:limit],
        "mutation_status": "backlog",
    }


def _safe_tags(backend: WeKnoraApiBackend, kb_id: object, limit: int) -> list[dict]:
    try:
        return backend.list_knowledge_base_tags(str(kb_id or ""), limit=limit)
    except KnowledgeBackendUnavailableError:
        return []


def _mutation_backlog() -> dict[str, Any]:
    return {
        "status": "backlog",
        "items": [
            "KB create/update/delete requires confirmation and audit trail",
            "pin/tag mutations require a dedicated confirmation UX",
            "PA must not mutate production KBs from a status-only surface",
        ],
    }


def _backlog_surfaces() -> dict[str, Any]:
    return {
        "list": {"status": "backlog"},
        "read": {"status": "backlog"},
        "active_selection": {"status": "backlog"},
        "tags": {"status": "backlog"},
        "mutations": _mutation_backlog(),
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
