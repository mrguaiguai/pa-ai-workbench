from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.config import get_settings
from app.schemas import StatusResponse
from app.services.backend_capability_service import get_backend_capabilities
from app.services.runtime_status_service import get_weknora_status
from app.services.status_service import get_status_counts

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "pa-ai-workbench-backend",
        "version": settings.app_version,
    }


@router.get("/api/status", response_model=StatusResponse)
def api_status(session: Annotated[Session, Depends(get_session)]) -> StatusResponse:
    settings = get_settings()
    return StatusResponse(
        status="ok",
        service="pa-ai-workbench-backend",
        version=settings.app_version,
        environment=settings.app_env,
        knowledge_backend=settings.knowledge_backend,
        mock_mode=settings.mock_mode,
        weknora=get_weknora_status(settings),
        backend_capabilities=get_backend_capabilities(settings),
        memory_recent_limit=settings.memory_recent_limit,
        database="ok",
        counts=get_status_counts(session),
    )
