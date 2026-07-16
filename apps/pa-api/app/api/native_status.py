from typing import Any

from fastapi import APIRouter
from fastapi import Query

from app.services.native_status_service import native_status_center

router = APIRouter(prefix="/api/native", tags=["native-status"])


@router.get("/status")
def native_status_api(
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    return native_status_center(limit=limit)
