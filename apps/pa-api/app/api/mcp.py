from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from sqlmodel import Session

from app.database import get_session
from app.services.mcp_service import clear_native_mcp_credential
from app.services.mcp_service import create_native_mcp_service
from app.services.mcp_service import delete_native_mcp_service
from app.services.mcp_service import execute_native_mcp_tool
from app.services.mcp_service import native_mcp_overview
from app.services.mcp_service import native_mcp_service_detail
from app.services.mcp_service import read_native_mcp_prompt
from app.services.mcp_service import set_native_mcp_tool_approval
from app.services.mcp_service import test_native_mcp_service
from app.services.mcp_service import update_native_mcp_credentials
from app.services.mcp_service import update_native_mcp_service

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class NativeMCPTestRequest(BaseModel):
    confirm_token: str | None = None


class NativeMCPServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    transport_type: str = Field(min_length=1, max_length=64)
    url: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default="", max_length=1000)
    enabled: bool = False
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPServiceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    transport_type: str | None = Field(default=None, min_length=1, max_length=64)
    url: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=1000)
    enabled: bool | None = None
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPCredentialsRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=4000)
    token: str | None = Field(default=None, max_length=4000)
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPCredentialClearRequest(BaseModel):
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPToolApprovalRequest(BaseModel):
    require_approval: bool = True
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPToolExecutionRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval_decision: str | None = Field(default=None, max_length=16)
    conversation_id: str | None = Field(default=None, max_length=80)
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeMCPPromptReadRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    confirm_token: str | None = Field(default=None, max_length=120)


@router.get("/native/overview")
def native_mcp_overview_api(
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, Any]:
    return native_mcp_overview(limit=limit)


@router.get("/native/services/{service_id}")
def native_mcp_service_detail_api(service_id: str) -> dict[str, Any]:
    return native_mcp_service_detail(service_id=service_id)


@router.post("/native/services")
def create_native_mcp_service_api(
    request: NativeMCPServiceCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return create_native_mcp_service(
        session=session,
        name=request.name,
        transport_type=request.transport_type,
        url=request.url,
        description=request.description or "",
        enabled=request.enabled,
        confirm_token=request.confirm_token,
    )


@router.put("/native/services/{service_id}")
def update_native_mcp_service_api(
    service_id: str,
    request: NativeMCPServiceUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return update_native_mcp_service(
        session=session,
        service_id=service_id,
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        transport_type=request.transport_type,
        url=request.url,
        confirm_token=request.confirm_token,
    )


@router.put("/native/services/{service_id}/credentials")
def update_native_mcp_credentials_api(
    service_id: str,
    request: NativeMCPCredentialsRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return update_native_mcp_credentials(
        session=session,
        service_id=service_id,
        api_key=request.api_key,
        token=request.token,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/services/{service_id}/credentials/{field}")
def clear_native_mcp_credential_api(
    service_id: str,
    field: str,
    request: NativeMCPCredentialClearRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return clear_native_mcp_credential(
        session=session,
        service_id=service_id,
        field=field,
        confirm_token=request.confirm_token,
    )


@router.delete("/native/services/{service_id}")
def delete_native_mcp_service_api(
    service_id: str,
    request: NativeMCPTestRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return delete_native_mcp_service(
        session=session,
        service_id=service_id,
        confirm_token=request.confirm_token,
    )


@router.post("/native/services/{service_id}/test")
def test_native_mcp_service_api(
    service_id: str,
    request: NativeMCPTestRequest,
) -> dict[str, Any]:
    return test_native_mcp_service(
        service_id=service_id,
        confirm_token=request.confirm_token,
    )


@router.post("/native/services/{service_id}/prompts/{prompt_name}/read")
def read_native_mcp_prompt_api(
    service_id: str,
    prompt_name: str,
    request: NativeMCPPromptReadRequest,
) -> dict[str, Any]:
    return read_native_mcp_prompt(
        service_id=service_id,
        prompt_name=prompt_name,
        arguments=request.arguments,
        confirm_token=request.confirm_token,
    )


@router.put("/native/services/{service_id}/tool-approvals/{tool_name}")
def set_native_mcp_tool_approval_api(
    service_id: str,
    tool_name: str,
    request: NativeMCPToolApprovalRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return set_native_mcp_tool_approval(
        session=session,
        service_id=service_id,
        tool_name=tool_name,
        require_approval=request.require_approval,
        confirm_token=request.confirm_token,
    )


@router.post("/native/services/{service_id}/tools/{tool_name}/execute")
def execute_native_mcp_tool_api(
    service_id: str,
    tool_name: str,
    request: NativeMCPToolExecutionRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return execute_native_mcp_tool(
        session=session,
        service_id=service_id,
        tool_name=tool_name,
        arguments=request.arguments,
        approval_decision=request.approval_decision,
        conversation_id=request.conversation_id,
        confirm_token=request.confirm_token,
    )
