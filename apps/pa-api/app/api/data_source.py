from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services.data_source_service import delete_native_data_source_by_index
from app.services.data_source_service import native_data_source_detail_by_index
from app.services.data_source_service import native_data_source_overview
from app.services.data_source_service import pause_native_data_source_by_index
from app.services.data_source_service import resume_native_data_source_by_index
from app.services.data_source_service import trigger_native_data_source_sync_by_index

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


class NativeDataSourceControlRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_data_source_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_data_source_overview(limit=limit)


@router.get("/native/sources/by-index/{data_source_index}")
def native_data_source_detail_api(data_source_index: int) -> dict[str, Any]:
    return native_data_source_detail_by_index(data_source_index=data_source_index)


@router.post("/native/sources/by-index/{data_source_index}/sync")
def trigger_native_data_source_sync_api(
    data_source_index: int,
    request: NativeDataSourceControlRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return trigger_native_data_source_sync_by_index(
        session=session,
        data_source_index=data_source_index,
        confirm_token=request.confirm_token,
    )


@router.post("/native/sources/by-index/{data_source_index}/pause")
def pause_native_data_source_api(
    data_source_index: int,
    request: NativeDataSourceControlRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return pause_native_data_source_by_index(
        session=session,
        data_source_index=data_source_index,
        confirm_token=request.confirm_token,
    )


@router.post("/native/sources/by-index/{data_source_index}/resume")
def resume_native_data_source_api(
    data_source_index: int,
    request: NativeDataSourceControlRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return resume_native_data_source_by_index(
        session=session,
        data_source_index=data_source_index,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/sources/by-index/{data_source_index}")
def delete_native_data_source_api(
    data_source_index: int,
    request: NativeDataSourceControlRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return delete_native_data_source_by_index(
        session=session,
        data_source_index=data_source_index,
        confirm_token=request.confirm_token,
    )
