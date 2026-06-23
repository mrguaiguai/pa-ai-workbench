from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.services.knowledge_base_service import native_knowledge_base_overview
from app.services.knowledge_base_service import select_active_knowledge_base
from knowledge_engine.errors import KnowledgeBackendUnavailableError

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


class ActiveKnowledgeBaseSelectionRequest(BaseModel):
    kb_id: str


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
