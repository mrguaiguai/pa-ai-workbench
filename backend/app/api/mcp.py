from typing import Any

from fastapi import APIRouter
from fastapi import Query

from app.services.mcp_service import native_mcp_overview

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/native/overview")
def native_mcp_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_mcp_overview(limit=limit)
