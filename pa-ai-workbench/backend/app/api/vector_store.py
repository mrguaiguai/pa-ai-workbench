from typing import Any

from fastapi import APIRouter
from fastapi import Query
from pydantic import BaseModel

from app.services.vector_store_service import native_vector_store_detail_by_index
from app.services.vector_store_service import native_vector_store_overview
from app.services.vector_store_service import test_native_vector_store_by_index

router = APIRouter(prefix="/api/vector-stores", tags=["vector-stores"])


class NativeVectorStoreTestRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_vector_store_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_vector_store_overview(limit=limit)


@router.get("/native/stores/by-index/{store_index}")
def native_vector_store_detail_api(store_index: int) -> dict[str, Any]:
    return native_vector_store_detail_by_index(store_index=store_index)


@router.post("/native/stores/by-index/{store_index}/test")
def test_native_vector_store_api(
    store_index: int,
    request: NativeVectorStoreTestRequest,
) -> dict[str, Any]:
    return test_native_vector_store_by_index(
        store_index=store_index,
        confirm_token=request.confirm_token,
    )
