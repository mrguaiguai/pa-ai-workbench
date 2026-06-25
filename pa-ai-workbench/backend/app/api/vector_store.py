from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from sqlmodel import Session

from app.database import get_session
from app.services.vector_store_service import create_native_vector_store
from app.services.vector_store_service import delete_native_vector_store_by_index
from app.services.vector_store_service import native_vector_store_detail_by_index
from app.services.vector_store_service import native_vector_store_overview
from app.services.vector_store_service import test_native_vector_store_raw
from app.services.vector_store_service import test_native_vector_store_by_index
from app.services.vector_store_service import update_native_vector_store_by_index

router = APIRouter(prefix="/api/vector-stores", tags=["vector-stores"])


class NativeVectorStoreTestRequest(BaseModel):
    confirm_token: str | None = None


class NativeVectorStoreRawTestRequest(BaseModel):
    engine_type: str
    connection_config: dict[str, Any]
    confirm_token: str | None = None


class NativeVectorStoreCreateRequest(BaseModel):
    name: str
    engine_type: str
    connection_config: dict[str, Any]
    index_config: dict[str, Any] = Field(default_factory=dict)
    confirm_token: str | None = None


class NativeVectorStoreUpdateRequest(BaseModel):
    name: str
    confirm_token: str | None = None


@router.get("/native/overview")
def native_vector_store_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_vector_store_overview(limit=limit)


@router.get("/native/stores/by-index/{store_index}")
def native_vector_store_detail_api(store_index: int) -> dict[str, Any]:
    return native_vector_store_detail_by_index(store_index=store_index)


@router.post("/native/raw-test")
def test_native_vector_store_raw_api(
    request: NativeVectorStoreRawTestRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return test_native_vector_store_raw(
        engine_type=request.engine_type,
        connection_config=request.connection_config,
        session=session,
        confirm_token=request.confirm_token,
    )


@router.post("/native/stores")
def create_native_vector_store_api(
    request: NativeVectorStoreCreateRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return create_native_vector_store(
        name=request.name,
        engine_type=request.engine_type,
        connection_config=request.connection_config,
        index_config=request.index_config,
        session=session,
        confirm_token=request.confirm_token,
    )


@router.put("/native/stores/by-index/{store_index}")
def update_native_vector_store_api(
    store_index: int,
    request: NativeVectorStoreUpdateRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return update_native_vector_store_by_index(
        store_index=store_index,
        name=request.name,
        session=session,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/stores/by-index/{store_index}")
def delete_native_vector_store_api(
    store_index: int,
    request: NativeVectorStoreTestRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return delete_native_vector_store_by_index(
        store_index=store_index,
        session=session,
        confirm_token=request.confirm_token,
    )


@router.post("/native/stores/by-index/{store_index}/test")
def test_native_vector_store_api(
    store_index: int,
    request: NativeVectorStoreTestRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return test_native_vector_store_by_index(
        store_index=store_index,
        session=session,
        confirm_token=request.confirm_token,
    )
