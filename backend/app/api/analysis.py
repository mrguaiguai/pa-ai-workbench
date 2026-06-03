from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import CitationRead
from app.schemas import GeneratedOutputRead
from app.schemas import OutputDetailResponse
from app.schemas import TaskRead
from app.services.generation_service import get_output
from app.services.generation_service import get_task
from app.services.generation_service import list_output_citations

router = APIRouter(prefix="/api", tags=["analysis"])


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

