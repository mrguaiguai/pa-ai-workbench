from app.config import Settings
from app.schemas import WeKnoraStatus
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONNECTED_HEALTH_STATUSES = {"ok", "healthy", "ready", "connected"}


def get_weknora_status(settings: Settings) -> WeKnoraStatus:
    mode = (settings.knowledge_backend or "mock").strip().lower()
    base_url_configured = bool(settings.weknora_base_url.strip())
    service_token_configured = bool(settings.weknora_service_token.strip())
    workspace_configured = bool(settings.weknora_workspace_id.strip())
    kb_configured = bool(settings.weknora_default_kb_id.strip())
    kb_mapping = _kb_mapping_status(settings)
    configured = (
        base_url_configured
        and service_token_configured
        and workspace_configured
        and kb_configured
    )

    if mode != "weknora_api":
        return WeKnoraStatus(
            mode=mode,
            status="mock" if settings.mock_mode or mode == "mock" else "disabled",
            connected=False,
            configured=False,
            base_url_configured=base_url_configured,
            service_token_configured=service_token_configured,
            workspace_configured=workspace_configured,
            kb_configured=kb_configured,
            health_status=None,
            message="WeKnora is not the active knowledge backend.",
            kb_mapping=kb_mapping,
        )

    if not configured:
        return WeKnoraStatus(
            mode=mode,
            status="missing_config",
            connected=False,
            configured=False,
            base_url_configured=base_url_configured,
            service_token_configured=service_token_configured,
            workspace_configured=workspace_configured,
            kb_configured=kb_configured,
            health_status=None,
            message="WeKnora backend is selected but required config is incomplete.",
            kb_mapping=kb_mapping,
        )

    backend = WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=min(settings.weknora_timeout_seconds, 3),
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )
    health = backend.health()
    health_status = str(health.get("status") or "unknown").strip().lower()
    connected = health_status in CONNECTED_HEALTH_STATUSES
    kb_mapping = _kb_mapping_status(settings, backend=backend, health_connected=connected)
    return WeKnoraStatus(
        mode=mode,
        status="connected" if connected else "unavailable",
        connected=connected,
        configured=True,
        base_url_configured=base_url_configured,
        service_token_configured=service_token_configured,
        workspace_configured=workspace_configured,
        kb_configured=kb_configured,
        health_status=health_status,
        message=(
            "WeKnora health check passed."
            if connected
            else "WeKnora health check failed or returned unavailable."
        ),
        kb_mapping=kb_mapping,
    )


def _kb_mapping_status(
    settings: Settings,
    *,
    backend: WeKnoraApiBackend | None = None,
    health_connected: bool = False,
) -> dict:
    summary = {
        "schema_version": "wf-p1-03",
        "status": "blocked",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "configured": False,
        "validated": False,
        "workspace_id": settings.weknora_workspace_id or None,
        "kb_id": settings.weknora_default_kb_id or None,
        "selection_source": None,
        "mapping_name": None,
        "default_used": None,
        "default_fallback_allowed": settings.weknora_kb_allow_default,
        "mapping_configured": bool(settings.weknora_kb_mappings.strip()),
        "blocked_reason": None,
        "workspace": None,
        "knowledge_base": None,
        "backlog": ["multi-KB management UI", "KB CRUD", "credential management UI"],
    }
    if settings.knowledge_backend != "weknora_api":
        summary["status"] = "backlog"
        summary["blocked_reason"] = "WeKnora is not the active knowledge backend."
        return summary
    if not (settings.weknora_workspace_id and settings.weknora_default_kb_id):
        summary["blocked_reason"] = "Active workspace or default knowledge base is not configured."
        return summary

    summary["configured"] = True
    if backend is None:
        backend = WeKnoraApiBackend(
            base_url=settings.weknora_base_url,
            service_token=settings.weknora_service_token,
            timeout=min(settings.weknora_timeout_seconds, 3),
            workspace_id=settings.weknora_workspace_id,
            default_kb_id=settings.weknora_default_kb_id,
            kb_mapping_config=settings.weknora_kb_mappings,
            kb_allow_default=settings.weknora_kb_allow_default,
            retry_attempts=0,
        )
    try:
        target = backend.active_kb_target()
    except Exception as exc:  # noqa: BLE001
        summary["blocked_reason"] = _public_error(exc)
        return summary

    summary.update(
        {
            "workspace_id": target.get("workspace_id") or settings.weknora_workspace_id,
            "kb_id": target.get("kb_id") or settings.weknora_default_kb_id,
            "selection_source": target.get("selection_source"),
            "mapping_name": target.get("mapping_name"),
            "default_used": bool(target.get("default_used")),
        }
    )
    if not health_connected:
        summary["status"] = "configured"
        summary["blocked_reason"] = "WeKnora health is not connected; mapping was not validated live."
        return summary

    try:
        workspace = backend.get_workspace(str(summary["workspace_id"] or ""))
        kb = backend.get_knowledge_base(str(summary["kb_id"] or ""))
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "blocked"
        summary["blocked_reason"] = _public_error(exc)
        return summary

    summary["workspace"] = workspace
    summary["knowledge_base"] = kb
    summary["validated"] = True
    summary["status"] = "validated"
    summary["blocked_reason"] = None
    return summary


def _public_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password"):
        text = text.replace(marker, "[redacted]")
    if len(text) <= 180:
        return text
    return text[:177].rstrip() + "..."
