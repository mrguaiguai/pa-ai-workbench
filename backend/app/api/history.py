from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import CitationRead
from app.schemas import GeneratedOutputRead
from app.schemas import HistoryListResponse
from app.schemas import OutputDetailResponse
from app.services.history_service import get_output
from app.services.history_service import list_history
from app.services.history_service import list_output_citations

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
def list_generated_history(
    session: Annotated[Session, Depends(get_session)],
) -> HistoryListResponse:
    outputs = list_history(session)
    return HistoryListResponse(
        items=[GeneratedOutputRead.model_validate(output) for output in outputs],
        total=len(outputs),
    )


@router.get("/{output_id}", response_model=OutputDetailResponse)
def read_history_output(
    output_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> OutputDetailResponse:
    output = get_output(session, output_id)
    if output is None:
        raise HTTPException(status_code=404, detail="Output not found")
    citations = list_output_citations(session, output_id)
    return OutputDetailResponse(
        output=GeneratedOutputRead.model_validate(output),
        citations=[CitationRead.model_validate(citation) for citation in citations],
    )

