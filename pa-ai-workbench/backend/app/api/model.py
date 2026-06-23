from fastapi import APIRouter
from fastapi import Query

from app.config import get_settings
from app.schemas import ModelStatusResponse
from app.services.model_config_service import native_model_config_overview
from app.services.model_status_service import get_model_status

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/status", response_model=ModelStatusResponse)
def model_status() -> ModelStatusResponse:
    return get_model_status(get_settings())


@router.get("/native/overview")
def native_model_overview(
    limit: int = Query(default=10, ge=1, le=20),
) -> dict:
    return native_model_config_overview(limit=limit)
