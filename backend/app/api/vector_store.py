from typing import Any

from fastapi import APIRouter
from fastapi import Query

from app.services.vector_store_service import native_vector_store_overview

router = APIRouter(prefix="/api/vector-stores", tags=["vector-stores"])


@router.get("/native/overview")
def native_vector_store_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_vector_store_overview(limit=limit)
