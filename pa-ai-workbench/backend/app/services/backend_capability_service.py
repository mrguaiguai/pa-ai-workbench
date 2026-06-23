from __future__ import annotations

from app.config import Settings
from knowledge_engine.kb_mapping import KbMappingResolver
from knowledge_engine.capabilities import backend_capability_snapshot


def get_backend_capabilities(settings: Settings) -> dict:
    weknora_configured = (
        bool(settings.weknora_base_url.strip())
        and bool(settings.weknora_service_token.strip())
        and bool(settings.weknora_workspace_id.strip())
        and bool(settings.weknora_default_kb_id.strip())
    )
    snapshot = backend_capability_snapshot(
        backend_name=settings.knowledge_backend,
        app_env=settings.app_env,
        mock_mode=settings.mock_mode,
        weknora_configured=weknora_configured,
    )
    snapshot["kb_mapping"] = KbMappingResolver(
        default_workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        mapping_config=settings.weknora_kb_mappings,
        allow_default=settings.weknora_kb_allow_default,
    ).public_summary()
    return snapshot


__all__ = ["get_backend_capabilities"]
