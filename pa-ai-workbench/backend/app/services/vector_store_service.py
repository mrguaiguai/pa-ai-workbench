from __future__ import annotations

from collections import Counter
from typing import Any

from app.config import Settings
from app.config import get_settings
from app.models import NativeMutationAudit
from app.services.model_status_service import get_model_status
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.errors import WeKnoraUnavailableError
from sqlmodel import Session


CONFIRM_VECTOR_STORE_TEST_TOKEN = "TEST_NATIVE_VECTOR_STORE"
CONFIRM_VECTOR_STORE_TEST_TOKEN_ID = "native_vector_store_test"
CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN = "TEST_NATIVE_VECTOR_STORE_RAW"
CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN_ID = "native_vector_store_raw_test"
CONFIRM_VECTOR_STORE_MANAGE_TOKEN = "MANAGE_NATIVE_VECTOR_STORE"
CONFIRM_VECTOR_STORE_MANAGE_TOKEN_ID = "native_vector_store_management"


def native_vector_store_overview(limit: int = 5) -> dict[str, Any]:
    settings = get_settings()
    item_limit = max(min(limit, 10), 1)
    overview: dict[str, Any] = {
        "schema_version": "wnx-p2-04",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "management_mode": "safe_read_confirmed_test_confirmed_crud",
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
        overview["surfaces"]["store_read"] = {
            "status": "backlog",
            "reason": "native vector store read requires weknora_api backend",
        }
        overview["surfaces"]["store_test"] = {
            "status": "backlog",
            "reason": "native vector store test requires weknora_api backend",
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
        stores = backend.list_vector_stores(include_internal_refs=True)
    except KnowledgeBackendUnavailableError as exc:
        blocker = f"stores: {exc.error_code}"
        overview["surfaces"]["store_types"] = _store_type_surface(store_types, item_limit)
        overview["surfaces"]["stores"] = {"status": "blocked", "reason": blocker}
        overview["warnings"].append(f"blocked: {blocker}")
        return overview

    overview["surfaces"]["store_types"] = _store_type_surface(store_types, item_limit)
    overview["surfaces"]["stores"] = _stores_surface(stores, item_limit)
    overview["surfaces"]["kb_binding"] = _kb_binding_surface(settings, backend)
    overview["surfaces"]["store_read"] = _store_read_surface(stores)
    overview["surfaces"]["store_test"] = _store_test_surface(stores)
    overview["surfaces"]["embedding_compatibility"] = _embedding_compatibility_surface(
        settings=settings,
        kb_binding=overview["surfaces"]["kb_binding"],
        stores=stores,
    )
    overview["surfaces"]["mutations"] = _vector_store_management_boundaries(stores)
    overview["status"] = "live"
    return overview


def native_vector_store_detail_by_index(store_index: int) -> dict[str, Any]:
    settings = get_settings()
    response: dict[str, Any] = {
        "schema_version": "wnx-p2-04-store",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["store_read"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store detail",
        }
        response["surfaces"]["store_test"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store test",
        }
        return response

    response["source"] = "weknora_api"
    backend = _weknora_backend(settings)
    try:
        store_ref = _store_ref_by_index(backend, store_index)
        store = backend.get_vector_store(store_ref)
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["store_read"] = {
            "status": "blocked",
            "reason": f"store_read: {exc.error_code}",
        }
        response["surfaces"]["store_test"] = _store_test_blocked_surface()
        response["warnings"].append(f"blocked: store_read: {exc.error_code}")
        return response

    response["status"] = "partial"
    response["surfaces"]["store_read"] = {
        "status": "live",
        "store": _public_store_item(store),
    }
    response["surfaces"]["store_test"] = _store_test_blocked_surface()
    response["surfaces"]["mutations"] = _vector_store_management_boundaries([store])
    return response


def test_native_vector_store_by_index(
    store_index: int,
    session: Session,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response: dict[str, Any] = {
        "schema_version": "wnfc-p3-04-store-test",
        "source": settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["store_test"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store test",
        }
        return response

    response["source"] = "weknora_api"
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_VECTOR_STORE_TEST_TOKEN,
            token_id=CONFIRM_VECTOR_STORE_TEST_TOKEN_ID,
            action="native vector store connectivity test",
        )
    except NativeConfirmationError:
        response["surfaces"]["store_test"] = _store_test_blocked_surface()
        response["warnings"].append("blocked: vector store test requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    try:
        store_ref = _store_ref_by_index(backend, store_index)
        stores = backend.list_vector_stores(include_internal_refs=True)
        store = stores[store_index] if 0 <= store_index < len(stores) else {}
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["store_test"] = {
            "status": "partial",
            "success": False,
            "version_detected": False,
            "reason": f"test_failed: {exc.error_code}",
        }
        response["status"] = "partial"
        response["warnings"].append(f"partial: test_failed: {exc.error_code}")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="vector_store",
        operation="weknora_vector_store_test",
        target_type="vector_store",
        target_id=_safe_store_target_id(store_index),
        status="started",
        confirmation=confirmation,
        request_summary={
            "safe_index": store_index,
            "action": "test",
            "store": _public_store_item(store) if isinstance(store, dict) else {},
        },
    )
    session.commit()
    try:
        result = backend.test_vector_store(store_ref)
    except KnowledgeBackendUnavailableError as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": "test", "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["surfaces"]["store_test"] = {
            "status": "partial",
            "success": False,
            "version_detected": False,
            "reason": f"test_failed: {exc.error_code}",
        }
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["status"] = "partial"
        response["warnings"].append(f"partial: test_failed: {exc.error_code}")
        return response

    success = bool(result.get("success"))
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if success else "failed",
        response_summary={
            "action": "test",
            "success": success,
            "version_detected": bool(result.get("version_detected")),
            "store": _public_store_item(store) if isinstance(store, dict) else {},
        },
    )
    session.commit()
    response["status"] = "live" if success else "partial"
    response["surfaces"]["store_test"] = {
        "status": "live" if success else "partial",
        "success": success,
        "version_detected": bool(result.get("version_detected")),
        "native_call": "confirmed",
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def test_native_vector_store_raw(
    *,
    engine_type: str,
    connection_config: dict[str, Any],
    session: Session,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _mutation_response("wnfc-p3-04-raw-test", settings)
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["raw_test"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store raw test",
        }
        return response

    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN,
            token_id=CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN_ID,
            action="native vector store raw connection test",
        )
    except NativeConfirmationError:
        response["surfaces"]["raw_test"] = _raw_test_blocked_surface()
        response["warnings"].append("blocked: raw vector store test requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="vector_store",
        operation="weknora_vector_store_raw_test",
        target_type="vector_store",
        target_id="raw_config",
        status="started",
        confirmation=confirmation,
        request_summary=_config_request_summary(
            action="raw_test",
            engine_type=engine_type,
            connection_config=connection_config,
            index_config={},
        ),
    )
    session.commit()
    backend = _weknora_backend(settings)
    try:
        result = backend.test_vector_store_raw(
            engine_type=engine_type,
            connection_config=connection_config,
        )
    except KnowledgeBackendUnavailableError as exc:
        return _mutation_failed(
            response=response,
            session=session,
            audit=audit,
            surface_name="raw_test",
            reason=f"raw_test_failed: {exc.error_code}",
            error=exc,
            confirmation=confirmation,
        )

    success = bool(result.get("success"))
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if success else "failed",
        response_summary={
            "action": "raw_test",
            "success": success,
            "version_detected": bool(result.get("version_detected")),
            "engine_type": engine_type,
        },
    )
    session.commit()
    response["status"] = "live" if success else "partial"
    response["surfaces"]["raw_test"] = {
        "status": "live" if success else "partial",
        "success": success,
        "version_detected": bool(result.get("version_detected")),
        "native_call": "confirmed",
        "engine_type": engine_type,
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def create_native_vector_store(
    *,
    name: str,
    engine_type: str,
    connection_config: dict[str, Any],
    index_config: dict[str, Any] | None,
    session: Session,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _mutation_response("wnfc-p3-04-store-create", settings)
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["store_create"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store create",
        }
        return response

    try:
        confirmation = _require_management_confirmation(
            confirm_token=confirm_token,
            action="native vector store create",
        )
    except NativeConfirmationError:
        response["surfaces"]["store_create"] = _management_blocked_surface("create")
        response["warnings"].append("blocked: vector store create requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="vector_store",
        operation="weknora_vector_store_create",
        target_type="vector_store",
        target_id="pending_create",
        status="started",
        confirmation=confirmation,
        request_summary=_config_request_summary(
            action="create",
            engine_type=engine_type,
            connection_config=connection_config,
            index_config=index_config or {},
        ),
    )
    session.commit()
    backend = _weknora_backend(settings)
    try:
        created = backend.create_vector_store(
            name=name,
            engine_type=engine_type,
            connection_config=connection_config,
            index_config=index_config or {},
            include_internal_refs=True,
        )
        store_ref = str(created.get("_native_store_id") or "").strip()
        if not store_ref:
            raise WeKnoraUnavailableError(
                "Native vector store create did not return a store reference",
                error_code="vector_store_ref_unavailable",
                operation="vector_store_create",
            )
        safe_index = _store_index_by_ref(backend, store_ref)
    except KnowledgeBackendUnavailableError as exc:
        return _mutation_failed(
            response=response,
            session=session,
            audit=audit,
            surface_name="store_create",
            reason=f"create_failed: {exc.error_code}",
            error=exc,
            confirmation=confirmation,
        )

    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={
            "action": "create",
            "success": True,
            "safe_index": safe_index,
            "engine_type": engine_type,
            "store": _public_store_item(created),
        },
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"]["store_create"] = {
        "status": "live",
        "success": True,
        "safe_index": safe_index,
        "store": _public_store_item(created),
        "native_call": "confirmed",
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def update_native_vector_store_by_index(
    *,
    store_index: int,
    name: str,
    session: Session,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _mutation_response("wnfc-p3-04-store-update", settings)
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["store_update"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store update",
        }
        return response

    try:
        confirmation = _require_management_confirmation(
            confirm_token=confirm_token,
            action="native vector store update",
        )
    except NativeConfirmationError:
        response["surfaces"]["store_update"] = _management_blocked_surface("update")
        response["warnings"].append("blocked: vector store update requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    try:
        store_ref, store = _store_ref_and_item_by_index(backend, store_index)
        if store.get("source") != "user" or store.get("readonly"):
            response["surfaces"]["store_update"] = {
                "status": "blocked",
                "reason": "only user-owned non-readonly vector stores can be updated",
            }
            response["warnings"].append("blocked: update target is not a user-owned store")
            return response
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["store_update"] = {
            "status": "blocked",
            "reason": f"store_read: {exc.error_code}",
        }
        response["warnings"].append(f"blocked: store_read: {exc.error_code}")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="vector_store",
        operation="weknora_vector_store_update",
        target_type="vector_store",
        target_id=_safe_store_target_id(store_index),
        status="started",
        confirmation=confirmation,
        request_summary={
            "safe_index": store_index,
            "action": "update_name",
            "store": _public_store_item(store),
        },
    )
    session.commit()
    try:
        updated = backend.update_vector_store(store_id=store_ref, name=name)
    except KnowledgeBackendUnavailableError as exc:
        return _mutation_failed(
            response=response,
            session=session,
            audit=audit,
            surface_name="store_update",
            reason=f"update_failed: {exc.error_code}",
            error=exc,
            confirmation=confirmation,
        )

    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={
            "action": "update_name",
            "success": True,
            "safe_index": store_index,
            "store": _public_store_item(updated),
        },
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"]["store_update"] = {
        "status": "live",
        "success": True,
        "safe_index": store_index,
        "store": _public_store_item(updated),
        "native_call": "confirmed",
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def delete_native_vector_store_by_index(
    *,
    store_index: int,
    session: Session,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    response = _mutation_response("wnfc-p3-04-store-delete", settings)
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["store_delete"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required for native vector store delete",
        }
        return response

    try:
        confirmation = _require_management_confirmation(
            confirm_token=confirm_token,
            action="native vector store delete",
        )
    except NativeConfirmationError:
        response["surfaces"]["store_delete"] = _management_blocked_surface("delete")
        response["warnings"].append("blocked: vector store delete requires explicit confirmation")
        return response

    backend = _weknora_backend(settings)
    try:
        store_ref, store = _store_ref_and_item_by_index(backend, store_index)
        if store.get("source") != "user" or store.get("readonly"):
            response["surfaces"]["store_delete"] = {
                "status": "blocked",
                "reason": "only user-owned non-readonly vector stores can be deleted",
            }
            response["warnings"].append("blocked: delete target is not a user-owned store")
            return response
    except KnowledgeBackendUnavailableError as exc:
        response["surfaces"]["store_delete"] = {
            "status": "blocked",
            "reason": f"store_read: {exc.error_code}",
        }
        response["warnings"].append(f"blocked: store_read: {exc.error_code}")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="vector_store",
        operation="weknora_vector_store_delete",
        target_type="vector_store",
        target_id=_safe_store_target_id(store_index),
        status="started",
        confirmation=confirmation,
        request_summary={
            "safe_index": store_index,
            "action": "delete",
            "store": _public_store_item(store),
        },
    )
    session.commit()
    try:
        result = backend.delete_vector_store(store_ref)
    except KnowledgeBackendUnavailableError as exc:
        return _mutation_failed(
            response=response,
            session=session,
            audit=audit,
            surface_name="store_delete",
            reason=f"delete_failed: {exc.error_code}",
            error=exc,
            confirmation=confirmation,
        )

    success = bool(result.get("success"))
    update_native_mutation_audit(
        audit=audit,
        status="succeeded" if success else "failed",
        response_summary={
            "action": "delete",
            "success": success,
            "safe_index": store_index,
            "store": _public_store_item(store),
        },
    )
    session.commit()
    response["status"] = "live" if success else "partial"
    response["surfaces"]["store_delete"] = {
        "status": "live" if success else "partial",
        "success": success,
        "safe_index": store_index,
        "native_call": "confirmed",
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


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
        "items": _public_store_items(stores, item_limit),
    }


def _store_read_surface(stores: list[dict]) -> dict[str, Any]:
    if not stores:
        return {
            "status": "backlog",
            "reason": "no native vector stores are configured",
        }
    return {
        "status": "live",
        "count": len(stores),
        "detail_endpoint": "/api/vector-stores/native/stores/by-index/{store_index}",
    }


def _store_test_surface(stores: list[dict]) -> dict[str, Any]:
    if not stores:
        return {
            "status": "backlog",
            "reason": "no native vector stores are configured",
        }
    return _store_test_blocked_surface()


def _store_test_blocked_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "explicit confirmation is required before probing external vector store connectivity",
        "confirm_token_required": CONFIRM_VECTOR_STORE_TEST_TOKEN,
        "confirm_token_id": CONFIRM_VECTOR_STORE_TEST_TOKEN_ID,
        "test_endpoint": "/api/vector-stores/native/stores/by-index/{store_index}/test",
    }


def _raw_test_blocked_surface() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "explicit confirmation is required before probing raw vector store connectivity",
        "confirm_token_required": CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN,
        "confirm_token_id": CONFIRM_VECTOR_STORE_RAW_TEST_TOKEN_ID,
        "test_endpoint": "/api/vector-stores/native/raw-test",
    }


def _management_blocked_surface(action: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": f"explicit confirmation is required before native vector store {action}",
        "confirm_token_required": CONFIRM_VECTOR_STORE_MANAGE_TOKEN,
        "confirm_token_id": CONFIRM_VECTOR_STORE_MANAGE_TOKEN_ID,
    }


def _store_ref_by_index(backend: WeKnoraApiBackend, store_index: int) -> str:
    store_ref, _store = _store_ref_and_item_by_index(backend, store_index)
    return store_ref


def _store_ref_and_item_by_index(
    backend: WeKnoraApiBackend,
    store_index: int,
) -> tuple[str, dict[str, Any]]:
    stores = backend.list_vector_stores(include_internal_refs=True)
    if store_index < 0 or store_index >= len(stores):
        raise WeKnoraUnavailableError(
            "Requested vector store index is not available",
            error_code="vector_store_index_out_of_range",
            operation="vector_store_ref",
        )
    store_ref = str(stores[store_index].get("_native_store_id") or "").strip()
    if not store_ref:
        raise WeKnoraUnavailableError(
            "Native vector store reference is not available",
            error_code="vector_store_ref_unavailable",
            operation="vector_store_ref",
        )
    return store_ref, stores[store_index]


def _store_index_by_ref(backend: WeKnoraApiBackend, store_ref: str) -> int:
    stores = backend.list_vector_stores(include_internal_refs=True)
    for index, store in enumerate(stores):
        if str(store.get("_native_store_id") or "").strip() == store_ref:
            return index
    raise WeKnoraUnavailableError(
        "Created vector store is not visible in the native list response",
        error_code="vector_store_ref_not_listed",
        operation="vector_store_create",
    )


def _public_store_items(stores: list[dict], item_limit: int) -> list[dict[str, Any]]:
    return [
        {
            **_public_store_item(store),
            "safe_index": index,
            "detail_endpoint": f"/api/vector-stores/native/stores/by-index/{index}",
        }
        for index, store in enumerate(stores[:item_limit])
    ]


def _public_store_item(store: dict) -> dict[str, Any]:
    return {
        "engine_type": store.get("engine_type"),
        "source": store.get("source"),
        "readonly": bool(store.get("readonly")),
        "status": store.get("status"),
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


def _embedding_compatibility_surface(
    *,
    settings: Settings,
    kb_binding: dict[str, Any],
    stores: list[dict],
) -> dict[str, Any]:
    embedding = _embedding_surface(settings)
    store_count = len(stores)
    compatible = (
        embedding.get("status") == "live"
        and store_count > 0
        and kb_binding.get("status") == "live"
    )
    return {
        "status": "live" if compatible else "blocked",
        "embedding_status": embedding.get("status"),
        "embedding_dimension": embedding.get("dimension"),
        "kb_binding_status": kb_binding.get("binding_status") or kb_binding.get("status"),
        "kb_binding_source": kb_binding.get("binding_source"),
        "store_count": store_count,
        "reason": None
        if compatible
        else "embedding, active KB binding, and at least one native vector store must all be live",
    }


def _vector_store_management_boundaries(stores: list[dict] | None = None) -> dict[str, Any]:
    stores = stores or []
    env_count = sum(1 for store in stores if store.get("source") == "env")
    user_count = sum(1 for store in stores if store.get("source") == "user")
    return {
        "status": "live",
        "native_api_present": True,
        "env_store_count": env_count,
        "user_store_count": user_count,
        "items": [
            {
                "name": "saved/env vector store test",
                "status": "live",
                "reason": "PA exposes confirmed test for existing native store references with NativeMutationAudit",
            },
            {
                "name": "raw connection test/create",
                "status": "live",
                "reason": "PA exposes confirmed raw test and create paths that pass through native WeKnora without echoing raw config",
            },
            {
                "name": "user-store update/delete",
                "status": "live" if user_count > 0 else "ready",
                "reason": "confirmed update/delete are available after a user-owned store is created"
                if user_count == 0
                else "native API supports name-only update and guarded delete for user-owned stores",
            },
            {
                "name": "KB vector-store rebind",
                "status": "native_immutable",
                "reason": "native knowledge_base.vector_store_id is immutable after creation; PA surfaces this instead of faking rebind",
            },
        ],
        "reason": (
            "P3-04 exposes native read, confirmed saved/env test, raw test, create, "
            "name update, guarded delete, embedding compatibility, and audit. "
            "KB rebind remains native-immutable and is surfaced as such."
        ),
    }


def _mutation_response(schema_version: str, settings: Settings) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source": settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }


def _require_management_confirmation(*, confirm_token: str | None, action: str) -> dict[str, Any]:
    return require_native_confirmation(
        confirm=None,
        confirm_token=confirm_token,
        expected_token=CONFIRM_VECTOR_STORE_MANAGE_TOKEN,
        token_id=CONFIRM_VECTOR_STORE_MANAGE_TOKEN_ID,
        action=action,
    )


def _config_request_summary(
    *,
    action: str,
    engine_type: str,
    connection_config: dict[str, Any],
    index_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action": action,
        "engine_type": engine_type,
        "connection_field_count": len(connection_config),
        "index_field_count": len(index_config),
        "connection_has_sensitive_fields": any(
            str(key).lower() in {"api_key", "password", "secret", "authorization"}
            for key in connection_config
        ),
    }


def _mutation_failed(
    *,
    response: dict[str, Any],
    session: Session,
    audit: NativeMutationAudit,
    surface_name: str,
    reason: str,
    error: KnowledgeBackendUnavailableError,
    confirmation: dict[str, Any],
) -> dict[str, Any]:
    update_native_mutation_audit(
        audit=audit,
        status="failed",
        response_summary={"success": False},
        error_message=str(error),
    )
    session.commit()
    response["surfaces"][surface_name] = {
        "status": "partial",
        "success": False,
        "reason": reason,
    }
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    response["status"] = "partial"
    response["warnings"].append(f"partial: {reason}")
    return response


def _safe_store_target_id(store_index: int) -> str:
    return f"safe_index:{store_index}"


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
