from typing import Any

from fastapi import APIRouter
from fastapi import Query
from pydantic import BaseModel

from app.services.web_search_service import native_web_search_overview
from app.services.web_search_service import native_web_search_provider_detail
from app.services.web_search_service import test_native_web_search_provider

router = APIRouter(prefix="/api/web-search", tags=["web-search"])


class NativeWebSearchTestRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_web_search_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_web_search_overview(limit=limit)


@router.get("/native/providers/{provider_id}")
def native_web_search_provider_detail_api(provider_id: str) -> dict[str, Any]:
    return native_web_search_provider_detail(provider_id=provider_id)


@router.post("/native/providers/{provider_id}/test")
def test_native_web_search_provider_api(
    provider_id: str,
    request: NativeWebSearchTestRequest,
) -> dict[str, Any]:
    return test_native_web_search_provider(
        provider_id=provider_id,
        confirm_token=request.confirm_token,
    )
