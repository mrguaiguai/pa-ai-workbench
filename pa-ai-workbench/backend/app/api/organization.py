from typing import Any

from fastapi import APIRouter
from fastapi import Query

from app.services.organization_service import native_workbench_organization_overview

router = APIRouter(prefix="/api/organization", tags=["organization"])


@router.get("/native/overview")
def native_workbench_organization_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_workbench_organization_overview(limit=limit)
