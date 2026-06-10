from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas import CitationLocateRequest
from app.schemas import CitationLocateResponse
from app.services.citation_locator_service import locate_citation

router = APIRouter(prefix="/api/citations", tags=["citations"])


@router.post("/locate", response_model=CitationLocateResponse)
def locate_citation_target(
    payload: CitationLocateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CitationLocateResponse:
    return locate_citation(session=session, request=payload)
