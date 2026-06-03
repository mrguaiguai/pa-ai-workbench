from fastapi import APIRouter

from app.config import get_settings
from app.schemas import ModelStatusResponse
from app.services.model_status_service import get_model_status

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/status", response_model=ModelStatusResponse)
def model_status() -> ModelStatusResponse:
    return get_model_status(get_settings())
