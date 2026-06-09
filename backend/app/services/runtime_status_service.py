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
        )

    backend = WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=min(settings.weknora_timeout_seconds, 3),
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
    )
    health = backend.health()
    health_status = str(health.get("status") or "unknown").strip().lower()
    connected = health_status in CONNECTED_HEALTH_STATUSES
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
    )
