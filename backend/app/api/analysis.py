from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import AnalysisRunRequest
from app.schemas import AnalysisRunResponse
from app.schemas import CitationRead
from app.schemas import ConversationMessageRead
from app.schemas import ConversationRead
from app.schemas import GeneratedOutputRead
from app.schemas import OutputDetailResponse
from app.schemas import TaskRead
from app.services.analysis_service import AnalysisRunError
from app.services.analysis_service import run_analysis
from app.services.generation_service import get_output
from app.services.generation_service import get_task
from app.services.generation_service import list_output_citations

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analysis/run", response_model=AnalysisRunResponse)
def run_analysis_task(
    payload: AnalysisRunRequest,
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisRunResponse:
    try:
        conversation, messages, task, output, citations = run_analysis(
            session=session,
            conversation_id=payload.conversation_id,
            task_type=payload.task_type,
            title=payload.title,
            query_or_topic=payload.query_or_topic,
            business_area=payload.business_area,
            document_type=payload.document_type,
            document_ids=payload.document_ids,
            extra_requirements=payload.extra_requirements,
        )
    except AnalysisRunError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AnalysisRunResponse(
        conversation=ConversationRead.model_validate(conversation),
        messages=[ConversationMessageRead.model_validate(message) for message in messages],
        task=TaskRead.model_validate(task),
        output=GeneratedOutputRead.model_validate(output),
        citations=[CitationRead.model_validate(citation) for citation in citations],
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
def read_task(
    task_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> TaskRead:
    task = get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRead.model_validate(task)


@router.get("/outputs/{output_id}", response_model=OutputDetailResponse)
def read_output(
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
