from typing import Any

from fastapi import APIRouter
from fastapi import Query

from app.services.web_search_service import native_web_search_overview

router = APIRouter(prefix="/api/web-search", tags=["web-search"])


@router.get("/native/overview")
def native_web_search_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_web_search_overview(limit=limit)
