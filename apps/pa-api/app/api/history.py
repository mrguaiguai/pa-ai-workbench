from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlmodel import Session

from app.database import get_session
from app.schemas import CitationRead
from app.schemas import GeneratedOutputRead
from app.schemas import HistoryListResponse
from app.schemas import OutputDetailResponse
from app.services.history_service import get_output
from app.services.history_service import history_output_summary
from app.services.history_service import list_history
from app.services.history_service import list_output_citations

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
def list_generated_history(
    session: Annotated[Session, Depends(get_session)],
    query: Annotated[str | None, Query(max_length=200)] = None,
    task_type: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    citation_source: Annotated[str | None, Query()] = None,
    source_type: Annotated[str | None, Query()] = None,
    evidence_state: Annotated[str | None, Query()] = None,
    wnid_capability: Annotated[str | None, Query()] = None,
    wnid_evidence_state: Annotated[str | None, Query()] = None,
    has_warnings: Annotated[bool | None, Query()] = None,
) -> HistoryListResponse:
    outputs = list_history(
        session=session,
        query=query,
        task_type=task_type,
        status=status,
        citation_source=citation_source,
        source_type=source_type,
        evidence_state=evidence_state,
        wnid_capability=wnid_capability,
        wnid_evidence_state=wnid_evidence_state,
        has_warnings=has_warnings,
    )
    return HistoryListResponse(
        items=[_output_read(session, output) for output in outputs],
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
        output=_output_read(session, output),
        citations=[CitationRead.model_validate(citation) for citation in citations],
    )


def _output_read(session: Session, output) -> GeneratedOutputRead:
    return GeneratedOutputRead.model_validate(output).model_copy(
        update=history_output_summary(session, output)
    )
