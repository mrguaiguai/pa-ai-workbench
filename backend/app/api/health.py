from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "pa-ai-workbench-backend",
        "version": settings.app_version,
    }


@router.get("/api/status")
def api_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "pa-ai-workbench-backend",
        "version": settings.app_version,
        "environment": settings.app_env,
        "knowledge_backend": settings.knowledge_backend,
        "mock_mode": settings.mock_mode,
        "memory_recent_limit": settings.memory_recent_limit,
    }
