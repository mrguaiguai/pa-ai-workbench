from typing import Any

from fastapi import APIRouter
from fastapi import Query
from pydantic import BaseModel

from app.services.mcp_service import native_mcp_overview
from app.services.mcp_service import native_mcp_service_detail
from app.services.mcp_service import test_native_mcp_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class NativeMCPTestRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_mcp_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_mcp_overview(limit=limit)


@router.get("/native/services/{service_id}")
def native_mcp_service_detail_api(service_id: str) -> dict[str, Any]:
    return native_mcp_service_detail(service_id=service_id)


@router.post("/native/services/{service_id}/test")
def test_native_mcp_service_api(
    service_id: str,
    request: NativeMCPTestRequest,
) -> dict[str, Any]:
    return test_native_mcp_service(
        service_id=service_id,
        confirm_token=request.confirm_token,
    )
