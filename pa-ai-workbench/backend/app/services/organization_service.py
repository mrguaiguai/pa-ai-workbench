from __future__ import annotations

from typing import Any

from app.config import Settings
from app.config import get_settings
from app.models import NativeMutationAudit
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from sqlmodel import Session


CONFIRM_FAQ_MUTATION_TOKEN = "CONFIRM_NATIVE_FAQ_MUTATION"
CONFIRM_FAQ_MUTATION_TOKEN_ID = "native_faq_mutation"
CONFIRM_ORGANIZATION_MUTATION_TOKEN = "CONFIRM_NATIVE_ORGANIZATION_MUTATION"
CONFIRM_ORGANIZATION_MUTATION_TOKEN_ID = "native_organization_mutation"
CONFIRM_NATIVE_SKILL_MUTATION_TOKEN = "CONFIRM_NATIVE_SKILL_MUTATION"
CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID = "native_skill_mutation"


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
    overview["surfaces"]["mutations"] = _organization_mutation_surface()

    non_mutation_surfaces = [
        surface
        for name, surface in overview["surfaces"].items()
        if name != "mutations"
    ]
    live_surfaces = [surface for surface in non_mutation_surfaces if surface.get("status") == "live"]
    mutations = overview["surfaces"].get("mutations", {})
    if non_mutation_surfaces and len(live_surfaces) == len(non_mutation_surfaces) and mutations.get("status") == "live":
        overview["status"] = "live"
    elif live_surfaces:
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
    kb_id, selection = _faq_kb_target(backend, settings)
    if not kb_id:
        return {
            "status": "blocked",
            "reason": "faq_kb_missing",
            "readiness": "requires FAQ-type KB",
        }
    try:
        entries = backend.list_faq_entries(kb_id, limit=limit)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "blocked",
            "reason": f"faq_entries: {_error_code(exc)}",
            "readiness": "requires FAQ-type KB or readable FAQ entries",
        }
    return {
        "status": "live",
        "count": len(entries),
        "kb_selection": selection,
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
    read_probe: dict[str, Any] = {}
    if skills:
        first_name = str(skills[0].get("name") or "").strip()
        if first_name:
            try:
                read_probe = backend.get_skill(first_name)
            except KnowledgeBackendUnavailableError as exc:
                read_probe = {"status": "blocked", "reason": f"skill_read: {_error_code(exc)}"}
    return {
        "status": "live",
        "count": len(skills),
        "skills_available": bool(result.get("skills_available")),
        "read_status": "live" if not read_probe.get("reason") else "blocked",
        "read_probe": read_probe,
        "management_status": "live",
        "management_scope": "managed_skill_md_only",
        "test_status": "confirmation_required",
        "script_upload_status": "not_supported",
        "execution_test_status": "not_supported",
        "confirm_token_required": CONFIRM_NATIVE_SKILL_MUTATION_TOKEN,
        "confirm_token_id": CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID,
        "items": skills[:limit],
    }


def _organization_mutation_surface() -> dict[str, Any]:
    return {
        "status": "live",
        "tag_mutations": "live",
        "favorite_mutations": "live",
        "skill_mutations": "live",
        "confirm_token_required": CONFIRM_ORGANIZATION_MUTATION_TOKEN,
        "confirm_token_id": CONFIRM_ORGANIZATION_MUTATION_TOKEN_ID,
        "items": [
            "tag create/update/delete",
            "favorite add/remove/toggle",
            "skill create/read/update/delete/test",
        ],
        "open_items": ["skill script/resource upload and execution test remain intentionally unsupported"],
        "reason": "Native skill management is live for SKILL.md lifecycle with confirmation and audit; arbitrary script upload/execution is out of this safe contract.",
    }


def native_tags(kb_id: str, limit: int = 10) -> dict[str, Any]:
    settings = get_settings()
    response = _organization_response(settings, "wnfc-p4-02-tags-list")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["tags"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        tags = _weknora_backend(settings).list_knowledge_base_tags(kb_id, limit=limit)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["tags"] = {"status": "blocked", "reason": f"tags: {_error_code(exc)}"}
        response["warnings"].append(f"blocked: tags: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["tags"] = _tags_surface(tags)
    return response


def create_native_tag(
    *,
    session: Session,
    kb_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="tag",
        action="create",
        confirm_token=confirm_token,
        target_type="knowledge_tag",
        target_id=f"kb:{_safe_public_id(kb_id)}",
        request_summary=_tag_request_summary("create", payload=payload),
        mutate=lambda backend: {
            "tag": backend.create_knowledge_base_tag(kb_id, _tag_payload(payload)),
        },
    )


def update_native_tag(
    *,
    session: Session,
    kb_id: str,
    tag_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="tag",
        action="update",
        confirm_token=confirm_token,
        target_type="knowledge_tag",
        target_id=_safe_public_id(tag_id),
        request_summary=_tag_request_summary("update", payload=payload, tag_id=tag_id),
        mutate=lambda backend: {
            "tag": backend.update_knowledge_base_tag(kb_id, tag_id, _tag_update_payload(payload)),
        },
    )


def delete_native_tag(
    *,
    session: Session,
    kb_id: str,
    tag_id: str,
    force: bool,
    content_only: bool,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="tag",
        action="delete",
        confirm_token=confirm_token,
        target_type="knowledge_tag",
        target_id=_safe_public_id(tag_id),
        request_summary={
            "action": "delete",
            "tag_id_present": bool(str(tag_id or "").strip()),
            "force": bool(force),
            "content_only": bool(content_only),
        },
        mutate=lambda backend: {
            "deleted": bool(
                backend.delete_knowledge_base_tag(
                    kb_id,
                    tag_id,
                    force=force,
                    content_only=content_only,
                ).get("success")
            ),
        },
    )


def toggle_native_favorite(
    *,
    session: Session,
    resource_type: str,
    resource_id: str,
    favorited: bool,
    confirm_token: str | None,
) -> dict[str, Any]:
    action = "favorite_add" if favorited else "favorite_remove"
    return _mutate_organization(
        session=session,
        capability="favorite",
        action=action,
        confirm_token=confirm_token,
        target_type=f"favorite_{str(resource_type or '').strip()}",
        target_id=_safe_public_id(resource_id),
        request_summary={
            "action": action,
            "resource_type": str(resource_type or "").strip(),
            "resource_id_present": bool(str(resource_id or "").strip()),
            "favorited": bool(favorited),
        },
        mutate=lambda backend: {
            "favorited": bool(favorited),
            "resource_type": str(resource_type or "").strip(),
            "resource_id_present": bool(str(resource_id or "").strip()),
            "result": (
                backend.add_user_favorite(resource_type, resource_id)
                if favorited
                else backend.remove_user_favorite(resource_type, resource_id)
            ).get("success"),
        },
    )


def native_skill(name: str) -> dict[str, Any]:
    settings = get_settings()
    response = _organization_response(settings, "wnfc-p4-03-skill-read")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["skill_read"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        skill = _weknora_backend(settings).get_skill(name)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["skill_read"] = {"status": "blocked", "reason": f"skill_read: {_error_code(exc)}"}
        response["warnings"].append(f"blocked: skill_read: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["skill_read"] = {"status": "live", "skill": _public_skill(skill)}
    return response


def create_native_skill(
    *,
    session: Session,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="skill",
        action="create",
        confirm_token=confirm_token,
        target_type="skill",
        target_id=_safe_public_id(payload.get("name")),
        request_summary=_skill_request_summary("create", payload=payload),
        mutate=lambda backend: {"skill": backend.create_skill(_skill_payload(payload))},
        expected_token=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN,
        token_id=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID,
    )


def update_native_skill(
    *,
    session: Session,
    name: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="skill",
        action="update",
        confirm_token=confirm_token,
        target_type="skill",
        target_id=_safe_public_id(name),
        request_summary=_skill_request_summary("update", name=name, payload=payload),
        mutate=lambda backend: {"skill": backend.update_skill(name, _skill_payload(payload, default_name=name))},
        expected_token=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN,
        token_id=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID,
    )


def delete_native_skill(
    *,
    session: Session,
    name: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="skill",
        action="delete",
        confirm_token=confirm_token,
        target_type="skill",
        target_id=_safe_public_id(name),
        request_summary=_skill_request_summary("delete", name=name),
        mutate=lambda backend: backend.delete_skill(name),
        expected_token=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN,
        token_id=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID,
    )


def test_native_skill(
    *,
    session: Session,
    name: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_organization(
        session=session,
        capability="skill",
        action="test",
        confirm_token=confirm_token,
        target_type="skill",
        target_id=_safe_public_id(name),
        request_summary=_skill_request_summary("test", name=name),
        mutate=lambda backend: {"skill_test": backend.test_skill(name)},
        expected_token=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN,
        token_id=CONFIRM_NATIVE_SKILL_MUTATION_TOKEN_ID,
    )


def native_faq_entries(kb_id: str, limit: int = 10) -> dict[str, Any]:
    settings = get_settings()
    response = _faq_response(settings, "wnfc-p4-01-faq-list")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["entries"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        entries = _weknora_backend(settings).list_faq_entries(
            kb_id,
            limit=limit,
            include_internal_refs=True,
        )
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["entries"] = {"status": "blocked", "reason": f"faq_entries: {_error_code(exc)}"}
        response["warnings"].append(f"blocked: faq_entries: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["entries"] = _faq_entries_surface(entries)
    return response


def native_faq_entry(kb_id: str, entry_id: int) -> dict[str, Any]:
    settings = get_settings()
    response = _faq_response(settings, "wnfc-p4-01-faq-read")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["entry_read"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        entry = _weknora_backend(settings).get_faq_entry(kb_id, entry_id)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["entry_read"] = {"status": "blocked", "reason": f"faq_read: {_error_code(exc)}"}
        response["warnings"].append(f"blocked: faq_read: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["entry_read"] = {"status": "live", "entry": _public_faq_entry(entry)}
    return response


def create_native_faq_entry(
    *,
    session: Session,
    kb_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_faq(
        session=session,
        kb_id=kb_id,
        action="create",
        confirm_token=confirm_token,
        payload=_faq_entry_payload(payload),
    )


def update_native_faq_entry(
    *,
    session: Session,
    kb_id: str,
    entry_id: int,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_faq(
        session=session,
        kb_id=kb_id,
        action="update",
        confirm_token=confirm_token,
        entry_id=entry_id,
        payload=_faq_entry_payload(payload),
    )


def delete_native_faq_entries(
    *,
    session: Session,
    kb_id: str,
    entry_ids: list[int],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_faq(
        session=session,
        kb_id=kb_id,
        action="delete",
        confirm_token=confirm_token,
        entry_ids=entry_ids,
    )


def search_native_faq_entries(kb_id: str, query_text: str, match_count: int = 5) -> dict[str, Any]:
    settings = get_settings()
    response = _faq_response(settings, "wnfc-p4-01-faq-search")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["search"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        entries = _weknora_backend(settings).search_faq_entries(kb_id, query_text, match_count=match_count)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["search"] = {"status": "blocked", "reason": f"faq_search: {_error_code(exc)}"}
        response["warnings"].append(f"blocked: faq_search: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["search"] = _faq_entries_surface(entries, surface_name="search")
    return response


def import_native_faq_entries(
    *,
    session: Session,
    kb_id: str,
    entries: list[dict[str, Any]],
    dry_run: bool,
    confirm_token: str | None,
) -> dict[str, Any]:
    payload = {
        "entries": [_faq_entry_payload(entry) for entry in entries],
        "dry_run": bool(dry_run),
    }
    return _mutate_faq(
        session=session,
        kb_id=kb_id,
        action="import",
        confirm_token=confirm_token,
        payload=payload,
    )


def native_faq_import_progress(task_id: str) -> dict[str, Any]:
    settings = get_settings()
    response = _faq_response(settings, "wnfc-p4-01-faq-import-progress")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["import_progress"] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        progress = _weknora_backend(settings).get_faq_import_progress(task_id)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["import_progress"] = {
            "status": "blocked",
            "reason": f"faq_import_progress: {_error_code(exc)}",
        }
        response["warnings"].append(f"blocked: faq_import_progress: {_error_code(exc)}")
        return response
    response["status"] = "live"
    response["surfaces"]["import_progress"] = {
        "status": "live",
        "import_status": progress.get("status"),
        "task_id_present": progress.get("task_id_present"),
        "progress": progress.get("progress"),
        "total": progress.get("total"),
        "processed": progress.get("processed"),
        "success_count": progress.get("success_count"),
        "failed_count": progress.get("failed_count"),
        "dry_run": progress.get("dry_run"),
    }
    return response


def _mutate_faq(
    *,
    session: Session,
    kb_id: str,
    action: str,
    confirm_token: str | None,
    entry_id: int | None = None,
    entry_ids: list[int] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _faq_response(settings, f"wnfc-p4-01-faq-{action}")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"][action] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_FAQ_MUTATION_TOKEN,
            token_id=CONFIRM_FAQ_MUTATION_TOKEN_ID,
            action=f"native FAQ {action}",
        )
    except NativeConfirmationError:
        response["surfaces"][action] = _faq_confirmation_blocked(action)
        response["warnings"].append(f"blocked: native FAQ {action} requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="faq",
        operation=f"weknora_faq_{action}",
        target_type="faq_entry",
        target_id=_faq_target_id(action, entry_id=entry_id, entry_ids=entry_ids),
        status="started",
        confirmation=confirmation,
        request_summary=_faq_request_summary(action, payload=payload, entry_id=entry_id, entry_ids=entry_ids),
    )
    session.commit()

    backend = _weknora_backend(settings)
    try:
        if action == "create":
            result = backend.create_faq_entry(kb_id, payload or {})
            surface = {"status": "live", "entry": _public_faq_entry(result)}
        elif action == "update":
            result = backend.update_faq_entry(kb_id, int(entry_id or 0), payload or {})
            surface = {"status": "live", "entry": _public_faq_entry(result)}
        elif action == "delete":
            result = backend.delete_faq_entries(kb_id, entry_ids or [])
            surface = {"status": "live", "deleted_count": int(result.get("deleted_count") or 0)}
        elif action == "import":
            result = backend.upsert_faq_entries(
                kb_id,
                list((payload or {}).get("entries") or []),
                dry_run=bool((payload or {}).get("dry_run")),
            )
            surface = {
                "status": "live",
                "task_id_present": bool(result.get("task_id")),
                "task_id": result.get("task_id"),
            }
        else:
            raise KnowledgeBackendUnavailableError(
                "unsupported FAQ action",
                error_code="faq_action_unsupported",
                operation="faq_mutation",
            )
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": action, "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"][action] = {"status": "partial", "reason": f"faq_{action}: {_error_code(exc)}"}
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: faq_{action}: {_error_code(exc)}")
        return response

    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={"action": action, "success": True, **_faq_surface_summary(surface)},
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"][action] = surface
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _mutate_organization(
    *,
    session: Session,
    capability: str,
    action: str,
    confirm_token: str | None,
    target_type: str,
    target_id: str | None,
    request_summary: dict[str, Any],
    mutate: Any,
    expected_token: str = CONFIRM_ORGANIZATION_MUTATION_TOKEN,
    token_id: str = CONFIRM_ORGANIZATION_MUTATION_TOKEN_ID,
) -> dict[str, Any]:
    settings = get_settings()
    response = _organization_response(settings, f"wnfc-p4-02-{capability}-{action}")
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"][action] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=expected_token,
            token_id=token_id,
            action=f"native organization {action}",
        )
    except NativeConfirmationError:
        response["surfaces"][action] = _organization_confirmation_blocked(
            action,
            confirm_token=expected_token,
            token_id=token_id,
        )
        response["warnings"].append(f"blocked: native organization {action} requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability=capability,
        operation=f"weknora_{capability}_{action}",
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
        response["surfaces"][action] = {"status": "partial", "reason": f"{capability}_{action}: {_error_code_from_exception(exc)}"}
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: {capability}_{action}: {_error_code_from_exception(exc)}")
        return response

    surface = {"status": "live", **_organization_result_surface(result)}
    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={"action": action, "success": True, **_organization_surface_summary(surface)},
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"][action] = surface
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _organization_response(settings: Settings, schema_version: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _faq_response(settings: Settings, schema_version: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _tag_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("tag name is required")
    return {
        "name": name[:128],
        "color": _safe_color(payload.get("color")),
        "sort_order": int(payload.get("sort_order") or 0),
    }


def _tag_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("tag name is required")
        result["name"] = name[:128]
    if "color" in payload:
        result["color"] = _safe_color(payload.get("color"))
    if "sort_order" in payload:
        result["sort_order"] = int(payload.get("sort_order") or 0)
    if not result:
        raise ValueError("tag update payload is empty")
    return result


def _safe_color(value: Any) -> str:
    color = str(value or "").strip()
    if not color:
        return ""
    if len(color) > 32:
        raise ValueError("tag color is too long")
    return color


def _tag_request_summary(
    action: str,
    *,
    payload: dict[str, Any],
    tag_id: str | None = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "tag_id_present": bool(tag_id),
        "name_present": bool(str(payload.get("name") or "").strip()),
        "color_configured": bool(str(payload.get("color") or "").strip()),
        "sort_order": int(payload.get("sort_order") or 0),
    }


def _tags_surface(tags: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "live",
        "count": len(tags),
        "used_count": sum(
            1
            for tag in tags
            if int(tag.get("knowledge_count") or 0) > 0 or int(tag.get("chunk_count") or 0) > 0
        ),
        "items": [_public_tag(tag) for tag in tags[:10]],
    }


def _public_tag(tag: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag_id": tag.get("id") or tag.get("tag_id"),
        "seq_id": tag.get("seq_id"),
        "name_present": bool(tag.get("name")),
        "color_configured": bool(tag.get("color")),
        "sort_order": tag.get("sort_order"),
        "knowledge_count": tag.get("knowledge_count"),
        "chunk_count": tag.get("chunk_count"),
    }


def _organization_result_surface(result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(result)
    if isinstance(safe.get("tag"), dict):
        safe["tag"] = _public_tag(safe["tag"])
    if isinstance(safe.get("skill"), dict):
        safe["skill"] = _public_skill(safe["skill"])
    if isinstance(safe.get("skill_test"), dict):
        safe["skill_test"] = _public_skill_test(safe["skill_test"])
    return safe


def _organization_surface_summary(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface_status": surface.get("status"),
        "tag_present": bool(surface.get("tag")),
        "deleted": bool(surface.get("deleted")),
        "favorited": surface.get("favorited"),
        "resource_type": surface.get("resource_type"),
        "resource_id_present": bool(surface.get("resource_id_present")),
        "skill_present": bool(surface.get("skill")),
        "skill_test_present": bool(surface.get("skill_test")),
    }


def _organization_confirmation_blocked(action: str, *, confirm_token: str, token_id: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "action": action,
        "confirm_token_required": confirm_token,
        "confirm_token_id": token_id,
    }


def _safe_public_id(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:120]


def _skill_payload(payload: dict[str, Any], default_name: str | None = None) -> dict[str, Any]:
    name = str(payload.get("name") or default_name or "").strip()
    description = str(payload.get("description") or "").strip()
    instructions = str(payload.get("instructions") or "").strip()
    if not name:
        raise ValueError("skill name is required")
    if not description:
        raise ValueError("skill description is required")
    if not instructions:
        raise ValueError("skill instructions are required")
    return {
        "name": name,
        "description": description,
        "instructions": instructions,
    }


def _skill_request_summary(action: str, *, name: str | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    instructions = str(payload.get("instructions") or "")
    return {
        "action": action,
        "name_present": bool(str(payload.get("name") or name or "").strip()),
        "description_present": bool(str(payload.get("description") or "").strip()),
        "instructions_present": bool(instructions.strip()),
        "instructions_char_count": len(instructions),
        "managed_scope": "skill_md_only",
    }


def _public_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": skill.get("name"),
        "description_present": bool(skill.get("description_present")),
        "instructions_present": bool(skill.get("instructions_present")),
        "instructions_char_count": skill.get("instructions_char_count"),
        "file_count": skill.get("file_count"),
        "script_count": skill.get("script_count"),
        "file_count_present": bool(skill.get("file_count") is not None),
        "source": skill.get("source"),
    }


def _public_skill_test(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": result.get("name"),
        "valid": bool(result.get("valid")),
        "instructions_present": bool(result.get("instructions_present")),
        "instructions_char_count": result.get("instructions_char_count"),
        "file_count": result.get("file_count"),
        "script_count": result.get("script_count"),
        "sandbox_available": bool(result.get("sandbox_available")),
        "execution_performed": bool(result.get("execution_performed")),
        "source": result.get("source"),
    }


def _error_code_from_exception(exc: Exception) -> str:
    if isinstance(exc, KnowledgeBackendUnavailableError):
        return _error_code(exc)
    return exc.__class__.__name__


def _faq_entry_payload(payload: dict[str, Any]) -> dict[str, Any]:
    standard_question = str(payload.get("standard_question") or "").strip()
    if not standard_question:
        raise ValueError("standard_question is required")
    answers = _string_list(payload.get("answers"))
    if not answers:
        raise ValueError("answers are required")
    return {
        "standard_question": standard_question,
        "similar_questions": _string_list(payload.get("similar_questions")),
        "negative_questions": _string_list(payload.get("negative_questions")),
        "answers": answers,
        "answer_strategy": str(payload.get("answer_strategy") or "all"),
        "tag_name": str(payload.get("tag_name") or "").strip(),
        "is_enabled": bool(payload.get("is_enabled", True)),
        "is_recommended": bool(payload.get("is_recommended", False)),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _faq_entries_surface(entries: list[dict], surface_name: str = "entries") -> dict[str, Any]:
    return {
        "status": "live",
        "count": len(entries),
        "surface": surface_name,
        "enabled_count": sum(1 for entry in entries if entry.get("enabled")),
        "recommended_count": sum(1 for entry in entries if entry.get("recommended")),
        "answer_count": sum(int(entry.get("answer_count") or 0) for entry in entries),
        "items": [_public_faq_entry(entry) for entry in entries[:10]],
    }


def _public_faq_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": entry.get("_native_entry_id"),
        "id_present": bool(entry.get("id_present")),
        "knowledge_id_present": bool(entry.get("knowledge_id_present")),
        "knowledge_base_id_present": bool(entry.get("knowledge_base_id_present")),
        "tag_configured": bool(entry.get("tag_configured")),
        "enabled": bool(entry.get("enabled")),
        "recommended": bool(entry.get("recommended")),
        "similar_question_count": int(entry.get("similar_question_count") or 0),
        "negative_question_count": int(entry.get("negative_question_count") or 0),
        "answer_count": int(entry.get("answer_count") or 0),
        "chunk_type": entry.get("chunk_type"),
    }


def _faq_confirmation_blocked(action: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "action": action,
        "confirm_token_required": CONFIRM_FAQ_MUTATION_TOKEN,
        "confirm_token_id": CONFIRM_FAQ_MUTATION_TOKEN_ID,
    }


def _faq_target_id(action: str, *, entry_id: int | None, entry_ids: list[int] | None) -> str:
    if entry_id is not None:
        return f"faq_entry:{entry_id}"
    if entry_ids:
        return f"faq_entries:{len(entry_ids)}"
    return f"faq_{action}"


def _faq_request_summary(
    action: str,
    *,
    payload: dict[str, Any] | None,
    entry_id: int | None,
    entry_ids: list[int] | None,
) -> dict[str, Any]:
    entries = (payload or {}).get("entries")
    return {
        "action": action,
        "entry_id_present": entry_id is not None,
        "entry_count": len(entries) if isinstance(entries, list) else 1 if payload else len(entry_ids or []),
        "answer_count": len((payload or {}).get("answers") or []) if isinstance(payload, dict) else 0,
        "dry_run": bool((payload or {}).get("dry_run")) if isinstance(payload, dict) else False,
    }


def _faq_surface_summary(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface_status": surface.get("status"),
        "entry_present": bool(surface.get("entry")),
        "deleted_count": surface.get("deleted_count"),
        "task_id_present": bool(surface.get("task_id_present")),
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
        "required": bool(confirmation.get("required")),
        "method": confirmation.get("method"),
        "token_id": confirmation.get("token_id"),
    }


def _faq_kb_target(backend: WeKnoraApiBackend, settings: Settings) -> tuple[str | None, str]:
    if settings.weknora_default_kb_id:
        try:
            kb = backend.get_knowledge_base(settings.weknora_default_kb_id)
            if kb.get("type") == "faq":
                return str(kb.get("id") or settings.weknora_default_kb_id), "default_faq_kb"
        except KnowledgeBackendUnavailableError:
            pass
    try:
        for kb in backend.list_knowledge_bases():
            if kb.get("type") == "faq" and kb.get("id"):
                return str(kb.get("id")), "first_faq_kb"
    except KnowledgeBackendUnavailableError:
        return None, "unavailable"
    return None, "missing"


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
