from typing import Any
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from sqlmodel import Session

from app.database import get_session
from app.services.web_search_service import clear_native_web_search_credential
from app.services.web_search_service import create_native_web_search_provider
from app.services.web_search_service import delete_native_web_search_provider
from app.services.web_search_service import native_web_search_overview
from app.services.web_search_service import native_web_search_provider_detail
from app.services.web_search_service import test_native_web_search_provider_raw
from app.services.web_search_service import test_native_web_search_provider
from app.services.web_search_service import update_native_web_search_credentials
from app.services.web_search_service import update_native_web_search_provider

router = APIRouter(prefix="/api/web-search", tags=["web-search"])


class NativeWebSearchTestRequest(BaseModel):
    confirm_token: str | None = None


class NativeWebSearchRawTestRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeWebSearchProviderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=1000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeWebSearchProviderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    parameters: dict[str, Any] | None = None
    is_default: bool | None = None
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeWebSearchCredentialsRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=4000)
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeWebSearchCredentialClearRequest(BaseModel):
    confirm_token: str | None = Field(default=None, max_length=120)


@router.get("/native/overview")
def native_web_search_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_web_search_overview(limit=limit)


@router.get("/native/providers/{provider_id}")
def native_web_search_provider_detail_api(provider_id: str) -> dict[str, Any]:
    return native_web_search_provider_detail(provider_id=provider_id)


@router.post("/native/providers/test")
def test_native_web_search_provider_raw_api(
    request: NativeWebSearchRawTestRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return test_native_web_search_provider_raw(
        session=session,
        provider=request.provider,
        parameters=request.parameters,
        confirm_token=request.confirm_token,
    )


@router.post("/native/providers")
def create_native_web_search_provider_api(
    request: NativeWebSearchProviderCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return create_native_web_search_provider(
        session=session,
        name=request.name,
        provider=request.provider,
        description=request.description or "",
        parameters=request.parameters,
        is_default=request.is_default,
        confirm_token=request.confirm_token,
    )


@router.put("/native/providers/{provider_id}")
def update_native_web_search_provider_api(
    provider_id: str,
    request: NativeWebSearchProviderUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return update_native_web_search_provider(
        session=session,
        provider_id=provider_id,
        name=request.name,
        description=request.description,
        parameters=request.parameters,
        is_default=request.is_default,
        confirm_token=request.confirm_token,
    )


@router.put("/native/providers/{provider_id}/credentials")
def update_native_web_search_credentials_api(
    provider_id: str,
    request: NativeWebSearchCredentialsRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return update_native_web_search_credentials(
        session=session,
        provider_id=provider_id,
        api_key=request.api_key,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/providers/{provider_id}/credentials/{field}")
def clear_native_web_search_credential_api(
    provider_id: str,
    field: str,
    request: NativeWebSearchCredentialClearRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return clear_native_web_search_credential(
        session=session,
        provider_id=provider_id,
        field=field,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/providers/{provider_id}")
def delete_native_web_search_provider_api(
    provider_id: str,
    request: NativeWebSearchCredentialClearRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return delete_native_web_search_provider(
        session=session,
        provider_id=provider_id,
        confirm_token=request.confirm_token,
    )


@router.post("/native/providers/{provider_id}/test")
def test_native_web_search_provider_api(
    provider_id: str,
    request: NativeWebSearchTestRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return test_native_web_search_provider(
        session=session,
        provider_id=provider_id,
        confirm_token=request.confirm_token,
    )
