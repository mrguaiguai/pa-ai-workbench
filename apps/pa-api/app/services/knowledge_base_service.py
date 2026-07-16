from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app.config import Settings
from app.config import get_settings
from app.models import KnowledgeBaseSelectionSnapshot
from app.models import utc_now
from app.models import NativeMutationAudit
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError

CONFIRM_KB_MUTATION_TOKEN = "CONFIRM_NATIVE_KB_MUTATION"
CONFIRM_KB_MUTATION_TOKEN_ID = "native_knowledge_base_mutation"


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
        "mutations": _mutation_surface(),
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
        "mutation_backlog": [],
        "mutation_status": _mutation_surface(),
    }


def create_native_knowledge_base(
    *,
    session: Session,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_knowledge_base(
        session=session,
        action="create",
        confirm_token=confirm_token,
        target_type="knowledge_base",
        target_id=None,
        request_summary=_kb_request_summary("create", payload=payload),
        mutate=lambda backend: {
            "knowledge_base": backend.create_knowledge_base(**_kb_create_payload(payload)),
        },
    )


def update_native_knowledge_base(
    *,
    session: Session,
    kb_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_knowledge_base(
        session=session,
        action="update",
        confirm_token=confirm_token,
        target_type="knowledge_base",
        target_id=_safe_public_id(kb_id),
        request_summary=_kb_request_summary("update", kb_id=kb_id, payload=payload),
        mutate=lambda backend: {
            "knowledge_base": backend.update_knowledge_base(
                kb_id,
                name=str(payload.get("name") or "").strip(),
                description=payload.get("description"),
            ),
        },
    )


def delete_native_knowledge_base(
    *,
    session: Session,
    kb_id: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_knowledge_base(
        session=session,
        action="delete",
        confirm_token=confirm_token,
        target_type="knowledge_base",
        target_id=_safe_public_id(kb_id),
        request_summary={"action": "delete", "kb_id_present": bool(str(kb_id or "").strip())},
        mutate=lambda backend: {
            "deleted": bool(backend.delete_knowledge_base(kb_id).get("success")),
        },
    )


def toggle_native_knowledge_base_pin(
    *,
    session: Session,
    kb_id: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_knowledge_base(
        session=session,
        action="pin_toggle",
        confirm_token=confirm_token,
        target_type="knowledge_base_pin",
        target_id=_safe_public_id(kb_id),
        request_summary={"action": "pin_toggle", "kb_id_present": bool(str(kb_id or "").strip())},
        mutate=lambda backend: {
            "knowledge_base": backend.toggle_knowledge_base_pin(kb_id),
        },
    )


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
        "mutation_status": "live",
    }


def _safe_tags(backend: WeKnoraApiBackend, kb_id: object, limit: int) -> list[dict]:
    try:
        return backend.list_knowledge_base_tags(str(kb_id or ""), limit=limit)
    except KnowledgeBackendUnavailableError:
        return []


def _mutation_surface() -> dict[str, Any]:
    return {
        "status": "live",
        "kb_mutations": "live",
        "pin_mutations": "live",
        "tag_mutations": "live",
        "confirm_token_required": CONFIRM_KB_MUTATION_TOKEN,
        "confirm_token_id": CONFIRM_KB_MUTATION_TOKEN_ID,
        "items": [
            "KB create/update/delete",
            "KB pin toggle",
            "tag create/update/delete via organization surface",
        ],
    }


def _backlog_surfaces() -> dict[str, Any]:
    return {
        "list": {"status": "backlog"},
        "read": {"status": "backlog"},
        "active_selection": {"status": "backlog"},
        "tags": {"status": "backlog"},
        "mutations": _mutation_surface(),
    }


def _mutate_knowledge_base(
    *,
    session: Session,
    action: str,
    confirm_token: str | None,
    target_type: str,
    target_id: str | None,
    request_summary: dict[str, Any],
    mutate: Any,
) -> dict[str, Any]:
    settings = get_settings()
    response = _kb_response(settings, f"wnfc-p5-01-kb-{action}")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"][action] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_KB_MUTATION_TOKEN,
            token_id=CONFIRM_KB_MUTATION_TOKEN_ID,
            action=f"native knowledge base {action}",
        )
    except NativeConfirmationError:
        response["surfaces"][action] = _kb_confirmation_blocked(action)
        response["warnings"].append(f"blocked: native knowledge base {action} requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="knowledge_base",
        operation=f"weknora_kb_{action}",
        target_type=target_type,
        target_id=target_id,
        status="started",
        confirmation=confirmation,
        request_summary=request_summary,
    )
    session.commit()

    try:
        result = mutate(_weknora_backend(settings))
    except (KnowledgeBackendUnavailableError, ValueError) as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": action, "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"][action] = {"status": "partial", "reason": f"kb_{action}: {_error_code_from_exception(exc)}"}
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: kb_{action}: {_error_code_from_exception(exc)}")
        return response

    surface = {"status": "live", **_kb_result_surface(result)}
    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={"action": action, "success": True, **_kb_surface_summary(surface)},
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"][action] = surface
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _kb_response(settings: Settings, schema_version: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _kb_create_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("knowledge base name is required")
    return {
        "name": name[:128],
        "description": str(payload.get("description") or "").strip()[:500],
        "kb_type": str(payload.get("type") or "document").strip()[:32] or "document",
        "is_temporary": bool(payload.get("is_temporary")),
    }


def _kb_request_summary(action: str, *, payload: dict[str, Any], kb_id: str | None = None) -> dict[str, Any]:
    return {
        "action": action,
        "kb_id_present": bool(str(kb_id or "").strip()),
        "name_present": bool(str(payload.get("name") or "").strip()),
        "description_present": bool(str(payload.get("description") or "").strip()),
        "type": str(payload.get("type") or "document").strip()[:32],
        "is_temporary": bool(payload.get("is_temporary")),
    }


def _kb_result_surface(result: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    kb = result.get("knowledge_base") if isinstance(result.get("knowledge_base"), dict) else None
    if kb:
        safe["knowledge_base"] = _public_kb(kb)
    if "deleted" in result:
        safe["deleted"] = bool(result.get("deleted"))
    return safe


def _kb_surface_summary(surface: dict[str, Any]) -> dict[str, Any]:
    kb = surface.get("knowledge_base") if isinstance(surface.get("knowledge_base"), dict) else {}
    return {
        "status": surface.get("status"),
        "deleted": surface.get("deleted"),
        "kb_id_present": bool(kb.get("id")),
        "is_pinned": kb.get("is_pinned"),
        "type": kb.get("type"),
    }


def _public_kb(kb: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": kb.get("id"),
        "name": kb.get("name"),
        "description_present": bool(kb.get("description")),
        "type": kb.get("type"),
        "is_temporary": bool(kb.get("is_temporary")),
        "is_pinned": bool(kb.get("is_pinned")),
        "knowledge_count": kb.get("knowledge_count"),
        "chunk_count": kb.get("chunk_count"),
        "source": kb.get("source") or "weknora_api",
    }


def _kb_confirmation_blocked(action: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": f"confirm_token={CONFIRM_KB_MUTATION_TOKEN} is required",
        "action": action,
        "confirm_token_id": CONFIRM_KB_MUTATION_TOKEN_ID,
    }


def _audit_surface(audit: NativeMutationAudit) -> dict[str, Any]:
    return {
        "id": audit.id,
        "capability": audit.capability,
        "operation": audit.operation,
        "target_type": audit.target_type,
        "target_id": audit.target_id,
        "status": audit.status,
        "confirm_token_id": audit.confirm_token_id,
    }


def _confirmation_read(confirmation: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": bool(confirmation.get("required")),
        "method": confirmation.get("method"),
        "token_id": confirmation.get("token_id"),
    }


def _safe_public_id(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= 12:
        return text
    return f"{text[:6]}...{text[-4:]}"


def _error_code_from_exception(exc: Exception) -> str:
    if isinstance(exc, KnowledgeBackendUnavailableError):
        return exc.error_code
    return exc.__class__.__name__


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
