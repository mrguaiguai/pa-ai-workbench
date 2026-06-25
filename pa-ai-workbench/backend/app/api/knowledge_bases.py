from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services.knowledge_base_service import create_native_knowledge_base
from app.services.knowledge_base_service import delete_native_knowledge_base
from app.services.knowledge_base_service import native_knowledge_base_overview
from app.services.knowledge_base_service import select_active_knowledge_base
from app.services.knowledge_base_service import toggle_native_knowledge_base_pin
from app.services.knowledge_base_service import update_native_knowledge_base
from knowledge_engine.errors import KnowledgeBackendUnavailableError

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


class ActiveKnowledgeBaseSelectionRequest(BaseModel):
    kb_id: str


class NativeKnowledgeBaseMutationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str = "document"
    is_temporary: bool = False
    confirm_token: str | None = None


class NativeKnowledgeBaseConfirmRequest(BaseModel):
    confirm_token: str | None = None


@router.get("/native/overview")
def native_knowledge_base_overview_api(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    return native_knowledge_base_overview(session=session, limit=limit)


@router.post("/native/active")
def select_active_knowledge_base_api(
    payload: ActiveKnowledgeBaseSelectionRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    try:
        return select_active_knowledge_base(session=session, kb_id=payload.kb_id)
    except KnowledgeBackendUnavailableError as exc:
        raise HTTPException(status_code=503, detail=exc.to_public_dict()) from exc


@router.post("/native")
def create_native_knowledge_base_api(
    payload: NativeKnowledgeBaseMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    try:
        return create_native_knowledge_base(
            session=session,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/native/{kb_id}")
def update_native_knowledge_base_api(
    kb_id: str,
    payload: NativeKnowledgeBaseMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    try:
        return update_native_knowledge_base(
            session=session,
            kb_id=kb_id,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/native/{kb_id}")
def delete_native_knowledge_base_api(
    kb_id: str,
    payload: NativeKnowledgeBaseConfirmRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return delete_native_knowledge_base(
        session=session,
        kb_id=kb_id,
        confirm_token=payload.confirm_token,
    )


@router.post("/native/{kb_id}/delete")
def delete_native_knowledge_base_post_api(
    kb_id: str,
    payload: NativeKnowledgeBaseConfirmRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return delete_native_knowledge_base(
        session=session,
        kb_id=kb_id,
        confirm_token=payload.confirm_token,
    )


@router.post("/native/{kb_id}/pin-toggle")
def toggle_native_knowledge_base_pin_api(
    kb_id: str,
    payload: NativeKnowledgeBaseConfirmRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    return toggle_native_knowledge_base_pin(
        session=session,
        kb_id=kb_id,
        confirm_token=payload.confirm_token,
    )
