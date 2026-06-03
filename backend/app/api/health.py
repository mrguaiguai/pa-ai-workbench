from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "pa-ai-workbench-backend",
        "version": "0.1.0",
    }


@router.get("/api/status")
def api_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "pa-ai-workbench-backend",
        "version": "0.1.0",
        "knowledge_backend": "mock",
        "mock_mode": True,
    }

