from __future__ import annotations

from collections import Counter
from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.config import get_settings
from app.models import NativeMutationAudit
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.errors import WeKnoraUnavailableError


CONFIRM_DATA_SOURCE_SYNC_TOKEN = "SYNC_NATIVE_DATA_SOURCE"
CONFIRM_DATA_SOURCE_PAUSE_TOKEN = "PAUSE_NATIVE_DATA_SOURCE"
CONFIRM_DATA_SOURCE_RESUME_TOKEN = "RESUME_NATIVE_DATA_SOURCE"
CONFIRM_DATA_SOURCE_DELETE_TOKEN = "DELETE_NATIVE_DATA_SOURCE"

DATA_SOURCE_CONFIRM_TOKEN_IDS = {
    "sync": "native_data_source_sync",
    "pause": "native_data_source_pause",
    "resume": "native_data_source_resume",
    "delete": "native_data_source_delete",
}


def native_data_source_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = _base_response(settings, "wnx-p2-05")
    overview["management_mode"] = "safe_read_confirmed_sync"
    if settings.knowledge_backend != "weknora_api":
        overview["status"] = "backlog"
        overview["surfaces"]["connector_types"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native data source connector management",
        }
        overview["warnings"].append("backlog: KNOWLEDGE_BACKEND is not weknora_api")
        return overview

    backend = _weknora_backend(settings)
    try:
        connector_types = backend.list_data_source_connector_types()
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"connector_types: {_error_code(exc)}"
        overview["surfaces"]["connector_types"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    try:
        data_sources = backend.list_data_sources(include_internal_refs=True)
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"data_sources: {_error_code(exc)}"
        overview["surfaces"]["connector_types"] = _connector_type_surface(connector_types, item_limit)
        overview["surfaces"]["data_sources"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    overview["surfaces"]["connector_types"] = _connector_type_surface(connector_types, item_limit)
    overview["surfaces"]["data_sources"] = _data_sources_surface(data_sources, item_limit)
    overview["surfaces"]["connector_read"] = _connector_read_surface(data_sources)
    overview["surfaces"]["sync_logs"] = _sync_logs_surface(data_sources)
    overview["surfaces"]["resources"] = _external_probe_surface(
        data_sources,
        name="resources",
        reason="listing connector resources can call external data source APIs and may reveal private resource names",
    )
    overview["surfaces"]["validation"] = _external_probe_surface(
        data_sources,
        name="validation",
        reason="validating connector credentials calls external systems and needs operator confirmation plus secret handling",
    )
    overview["surfaces"]["sync_control"] = _sync_control_surface(data_sources)
    overview["surfaces"]["delete_control"] = _delete_control_surface(data_sources)
    overview["surfaces"]["mutations"] = _data_source_mutation_surface(data_sources)
    overview["status"] = "partial" if data_sources else "live"
    if not data_sources:
        overview["warnings"].append("read-only: no native data sources are configured for the active KB")
    return overview


def native_data_source_detail_by_index(data_source_index: int) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings, "wnx-p2-05-data-source")
    response["management_mode"] = "safe_read_confirmed_sync"
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["connector_read"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native data source detail",
        }
        return response

    backend = _weknora_backend(settings)
    try:
        data_source_ref = _data_source_ref_by_index(backend, data_source_index)
        data_source = backend.get_data_source(data_source_ref)
        logs = backend.list_data_source_sync_logs(data_source_ref, limit=5)
        resources_surface = _data_source_resources_surface(backend, data_source_ref, data_source)
        validation_surface = _data_source_validation_surface(backend, data_source_ref, data_source)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["connector_read"] = {
            "status": "blocked",
            "reason": f"connector_read: {_error_code(exc)}",
        }
        response["surfaces"]["sync_control"] = _sync_control_blocked_surface()
        response["warnings"].append(f"blocked: connector_read: {_error_code(exc)}")
        return response

    response["status"] = "partial"
    response["surfaces"]["connector_read"] = {
        "status": "live",
        "data_source": _public_data_source_item(data_source),
    }
    response["surfaces"]["sync_logs"] = _logs_surface(logs)
    response["surfaces"]["resources"] = resources_surface
    response["surfaces"]["validation"] = validation_surface
    response["surfaces"]["sync_control"] = _sync_control_blocked_surface()
    response["surfaces"]["delete_control"] = _delete_control_blocked_surface()
    response["surfaces"]["mutations"] = _data_source_mutation_surface([data_source])
    return response


def trigger_native_data_source_sync_by_index(
    session: Session,
    data_source_index: int,
    *,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _confirmed_data_source_action(
        session=session,
        data_source_index=data_source_index,
        confirm_token=confirm_token,
        expected_token=CONFIRM_DATA_SOURCE_SYNC_TOKEN,
        action="sync",
    )


def pause_native_data_source_by_index(
    session: Session,
    data_source_index: int,
    *,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _confirmed_data_source_action(
        session=session,
        data_source_index=data_source_index,
        confirm_token=confirm_token,
        expected_token=CONFIRM_DATA_SOURCE_PAUSE_TOKEN,
        action="pause",
    )


def resume_native_data_source_by_index(
    session: Session,
    data_source_index: int,
    *,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _confirmed_data_source_action(
        session=session,
        data_source_index=data_source_index,
        confirm_token=confirm_token,
        expected_token=CONFIRM_DATA_SOURCE_RESUME_TOKEN,
        action="resume",
    )


def delete_native_data_source_by_index(
    session: Session,
    data_source_index: int,
    *,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _confirmed_data_source_action(
        session=session,
        data_source_index=data_source_index,
        confirm_token=confirm_token,
        expected_token=CONFIRM_DATA_SOURCE_DELETE_TOKEN,
        action="delete",
    )


def _confirmed_data_source_action(
    *,
    session: Session,
    data_source_index: int,
    confirm_token: str | None,
    expected_token: str,
    action: str,
) -> dict[str, Any]:
    settings = get_settings()
    response = _base_response(settings, f"wnfc-p1-02-{action}")
    response["management_mode"] = "safe_read_confirmed_sync"
    surface_name = "delete_control" if action == "delete" else "sync_control"
    blocked_surface = _delete_control_blocked_surface if action == "delete" else _sync_control_blocked_surface
    response["surfaces"]["mutations"] = _data_source_mutation_surface([{}])
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"][surface_name] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native data source mutation control",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=False,
            confirm_token=confirm_token,
            expected_token=expected_token,
            token_id=DATA_SOURCE_CONFIRM_TOKEN_IDS[action],
            action=f"weknora_data_source_{action}",
        )
    except NativeConfirmationError:
        response["surfaces"][surface_name] = blocked_surface()
        response["warnings"].append(f"blocked: data source {action} requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    try:
        data_source_ref = _data_source_ref_by_index(backend, data_source_index)
        data_source = backend.get_data_source(data_source_ref)
    except KnowledgeBackendUnavailableError as exc:
        response["status"] = "partial"
        response["surfaces"][surface_name] = {
            "status": "partial",
            "action": action,
            "success": False,
            "reason": f"native_{action}: {_error_code(exc)}",
        }
        response["warnings"].append(f"partial: native_{action}: {_error_code(exc)}")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="data_source",
        operation=f"weknora_data_source_{action}",
        target_type="data_source",
        target_id=_safe_data_source_target_id(data_source_index),
        status="started",
        confirmation=confirmation,
        request_summary={
            "safe_index": data_source_index,
            "action": action,
            "data_source": _public_data_source_item(data_source),
        },
    )
    session.commit()
    try:
        if action == "sync":
            result = backend.manual_sync_data_source(data_source_ref)
        elif action == "pause":
            result = backend.pause_data_source(data_source_ref)
        elif action == "resume":
            result = backend.resume_data_source(data_source_ref)
        elif action == "delete":
            result = backend.delete_data_source(data_source_ref)
        else:
            raise WeKnoraUnavailableError(
                "unsupported data source action",
                error_code="data_source_action_unsupported",
                operation="data_source_action",
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
        response["surfaces"][surface_name] = {
            "status": "partial",
            "action": action,
            "success": False,
            "reason": f"native_{action}: {_error_code(exc)}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: native_{action}: {_error_code(exc)}")
        return response

    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={
            "action": action,
            "success": True,
            "data_source": _public_data_source_item(data_source),
            "outcome": _data_source_action_outcome(result),
        },
    )
    session.commit()
    response["status"] = "partial"
    response["surfaces"][surface_name] = {
        "status": "live",
        "action": action,
        "success": True,
        "outcome": _data_source_action_outcome(result),
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _base_response(settings: Settings, schema_version: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _connector_type_surface(connector_types: list[dict], item_limit: int) -> dict[str, Any]:
    auth_counts = Counter(str(item.get("auth_type") or "unknown") for item in connector_types)
    return {
        "status": "live",
        "count": len(connector_types),
        "auth_type_summary": [
            {"auth_type": auth_type, "count": count}
            for auth_type, count in sorted(auth_counts.items())
        ],
        "credential_required_count": sum(
            1 for item in connector_types if str(item.get("auth_type") or "none") != "none"
        ),
        "items": connector_types[:item_limit],
    }


def _data_sources_surface(data_sources: list[dict], item_limit: int) -> dict[str, Any]:
    status_counts = Counter(str(item.get("status") or "unknown") for item in data_sources)
    type_counts = Counter(str(item.get("type") or "unknown") for item in data_sources)
    return {
        "status": "live",
        "count": len(data_sources),
        "status_counts": dict(sorted(status_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "credential_configured_count": sum(1 for item in data_sources if item.get("credential_configured")),
        "scheduled_count": sum(1 for item in data_sources if item.get("sync_schedule_configured")),
        "items": _public_data_source_items(data_sources, item_limit),
    }


def _connector_read_surface(data_sources: list[dict]) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "reason": "no native data sources are configured for the active KB",
            "count": 0,
        }
    return {
        "status": "live",
        "count": len(data_sources),
        "endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}",
    }


def _sync_logs_surface(data_sources: list[dict]) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "reason": "no native data sources are configured for sync-log reads",
            "count": 0,
        }
    return {
        "status": "live",
        "count": len(data_sources),
        "endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}",
    }


def _logs_surface(logs: list[dict]) -> dict[str, Any]:
    status_counts = Counter(str(log.get("status") or "unknown") for log in logs)
    return {
        "status": "live",
        "count": len(logs),
        "status_counts": dict(sorted(status_counts.items())),
        "items": logs[:5],
    }


def _data_source_resources_surface(
    backend: WeKnoraApiBackend,
    data_source_ref: str,
    data_source: dict[str, Any],
) -> dict[str, Any]:
    if data_source.get("type") != "rss":
        return _external_probe_blocked_surface(
            "listing connector resources requires a separate credential/resource privacy review"
        )
    try:
        summary = backend.list_data_source_resources(data_source_ref)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "partial",
            "reason": f"resources: {_error_code(exc)}",
            "count": 0,
        }
    return {
        "status": "live",
        "count": int(summary.get("count") or 0),
        "type_counts": summary.get("type_counts") if isinstance(summary.get("type_counts"), dict) else {},
    }


def _data_source_validation_surface(
    backend: WeKnoraApiBackend,
    data_source_ref: str,
    data_source: dict[str, Any],
) -> dict[str, Any]:
    if data_source.get("type") != "rss":
        return _external_probe_blocked_surface(
            "connector validation calls external systems and is not run by default"
        )
    try:
        result = backend.validate_data_source(data_source_ref)
    except KnowledgeBackendUnavailableError as exc:
        return {
            "status": "partial",
            "connected": False,
            "reason": f"validation: {_error_code(exc)}",
        }
    return {
        "status": "live",
        "connected": bool(result.get("connected")),
    }


def _external_probe_surface(data_sources: list[dict], *, name: str, reason: str) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "reason": f"no native data sources are configured for {name}",
            "count": 0,
        }
    return _external_probe_blocked_surface(reason)


def _external_probe_blocked_surface(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
    }


def _sync_control_surface(data_sources: list[dict]) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "reason": "no native data sources are configured for sync/pause/resume",
            "count": 0,
        }
    return _sync_control_blocked_surface()


def _sync_control_blocked_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "explicit confirmation is required before native sync, pause, or resume",
        "sync_confirm_phrase": CONFIRM_DATA_SOURCE_SYNC_TOKEN,
        "pause_confirm_phrase": CONFIRM_DATA_SOURCE_PAUSE_TOKEN,
        "resume_confirm_phrase": CONFIRM_DATA_SOURCE_RESUME_TOKEN,
        "sync_endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}/sync",
        "pause_endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}/pause",
        "resume_endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}/resume",
    }


def _delete_control_surface(data_sources: list[dict]) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "reason": "no native data sources are configured for delete control",
            "count": 0,
        }
    return _delete_control_blocked_surface()


def _delete_control_blocked_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "explicit confirmation is required before native data source deletion",
        "delete_confirm_phrase": CONFIRM_DATA_SOURCE_DELETE_TOKEN,
        "delete_endpoint": "/api/data-sources/native/sources/by-index/{data_source_index}",
    }


def _data_source_mutation_surface(data_sources: list[dict]) -> dict[str, Any]:
    if not data_sources:
        return {
            "status": "backlog",
            "items": [
                "sync/pause/resume/delete controls need at least one native data source",
                "connector create/update and credential forms remain blocked by credential setup",
            ],
            "reason": "no native data sources are configured for mutation controls",
        }
    return {
        "status": "partial",
        "items": [
            "sync/pause/resume are live with explicit confirmation and NativeMutationAudit",
            "delete is live with explicit confirmation and NativeMutationAudit",
            "connector create/update and credential forms remain blocked by missing third-party credential setup",
            "raw credential material and raw resource names are intentionally not exposed",
        ],
        "reason": (
            "WNFC-P1-02 exposes confirmation-gated native data source operations while "
            "keeping credential-heavy setup and raw connector payloads out of PA responses."
        ),
    }


def _data_source_ref_by_index(backend: WeKnoraApiBackend, data_source_index: int) -> str:
    data_sources = backend.list_data_sources(include_internal_refs=True)
    if data_source_index < 0 or data_source_index >= len(data_sources):
        raise WeKnoraUnavailableError(
            "Requested data source index is not available",
            error_code="data_source_index_out_of_range",
            operation="data_source_ref",
        )
    data_source_ref = str(data_sources[data_source_index].get("_native_data_source_id") or "").strip()
    if not data_source_ref:
        raise WeKnoraUnavailableError(
            "Native data source reference is not available",
            error_code="data_source_ref_unavailable",
            operation="data_source_ref",
        )
    return data_source_ref


def _public_data_source_items(data_sources: list[dict], item_limit: int) -> list[dict[str, Any]]:
    return [
        {
            **_public_data_source_item(data_source),
            "safe_index": index,
            "detail_endpoint": f"/api/data-sources/native/sources/by-index/{index}",
        }
        for index, data_source in enumerate(data_sources[:item_limit])
    ]


def _public_data_source_item(data_source: dict) -> dict[str, Any]:
    return {
        "name": data_source.get("name"),
        "type": data_source.get("type"),
        "status": data_source.get("status"),
        "sync_mode": data_source.get("sync_mode"),
        "sync_schedule_configured": bool(data_source.get("sync_schedule_configured")),
        "sync_deletions": bool(data_source.get("sync_deletions")),
        "credential_configured": bool(data_source.get("credential_configured")),
        "resource_count": data_source.get("resource_count"),
        "settings_count": data_source.get("settings_count"),
        "last_sync_at_configured": bool(data_source.get("last_sync_at_configured")),
        "total_items_synced": data_source.get("total_items_synced"),
    }


def _safe_data_source_target_id(data_source_index: int) -> str:
    return f"data_source_index:{max(int(data_source_index), 0)}"


def _data_source_action_outcome(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"source": "weknora_api"}
    safe: dict[str, Any] = {
        "source": result.get("source") or "weknora_api",
        "status": result.get("status"),
    }
    for key in (
        "deleted",
        "started_at_configured",
        "finished_at_configured",
        "items_total",
        "items_created",
        "items_updated",
        "items_deleted",
        "items_skipped",
        "items_failed",
        "has_error",
        "result_configured",
    ):
        if key in result:
            safe[key] = result.get(key)
    return safe


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
        "required": bool(confirmation.get("required", True)),
        "method": confirmation.get("method"),
        "token_id": confirmation.get("token_id"),
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
