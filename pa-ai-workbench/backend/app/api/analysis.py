from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from sqlmodel import Session

from app.database import get_session
from app.schemas import AnalysisRunRequest
from app.schemas import AnalysisRunResponse
from app.schemas import CitationRead
from app.schemas import ConversationMessageRead
from app.schemas import ConversationRead
from app.schemas import GeneratedOutputRead
from app.schemas import NativeAgentCatalogResponse
from app.schemas import NativeAgentQaRequest
from app.schemas import NativeAgentQaResponse
from app.schemas import NativeAgentQaRuntime
from app.schemas import OutputDetailResponse
from app.schemas import TaskRead
from app.services.analysis_service import AnalysisRunError
from app.services.analysis_service import run_analysis
from app.services.generation_service import get_output
from app.services.generation_service import get_task
from app.services.generation_service import list_output_citations
from app.services.native_agent_service import copy_native_agent
from app.services.native_agent_service import create_native_agent
from app.services.native_agent_service import delete_native_agent
from app.services.native_agent_service import NativeAgentError
from app.services.native_agent_service import native_agent_catalog
from app.services.native_agent_service import run_native_agent_qa
from app.services.native_agent_service import update_native_agent

router = APIRouter(prefix="/api", tags=["analysis"])


class NativeAgentMutationRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    avatar: str | None = Field(default=None, max_length=64)
    config: dict = Field(default_factory=dict)
    confirm_token: str | None = Field(default=None, max_length=120)


class NativeAgentConfirmRequest(BaseModel):
    confirm_token: str | None = Field(default=None, max_length=120)


@router.get("/analysis/native-agents", response_model=NativeAgentCatalogResponse)
def list_native_agents(
    session: Annotated[Session, Depends(get_session)],
) -> NativeAgentCatalogResponse:
    try:
        return NativeAgentCatalogResponse.model_validate(native_agent_catalog(session))
    except NativeAgentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/analysis/native-agents")
def create_native_agent_api(
    payload: NativeAgentMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    try:
        return create_native_agent(
            session=session,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/analysis/native-agents/{agent_id}")
def update_native_agent_api(
    agent_id: str,
    payload: NativeAgentMutationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    try:
        return update_native_agent(
            session=session,
            agent_id=agent_id,
            payload=payload.model_dump(exclude={"confirm_token"}),
            confirm_token=payload.confirm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analysis/native-agents/{agent_id}/copy")
def copy_native_agent_api(
    agent_id: str,
    payload: NativeAgentConfirmRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    return copy_native_agent(
        session=session,
        agent_id=agent_id,
        confirm_token=payload.confirm_token,
    )


@router.delete("/analysis/native-agents/{agent_id}")
def delete_native_agent_api(
    agent_id: str,
    payload: NativeAgentConfirmRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    return delete_native_agent(
        session=session,
        agent_id=agent_id,
        confirm_token=payload.confirm_token,
    )


@router.post("/analysis/native-agentqa", response_model=NativeAgentQaResponse)
def run_native_agentqa_task(
    payload: NativeAgentQaRequest,
    session: Annotated[Session, Depends(get_session)],
) -> NativeAgentQaResponse:
    try:
        conversation, messages, task, output, citations, runtime = run_native_agent_qa(
            session=session,
            query=payload.query,
            agent_id=payload.agent_id,
            conversation_id=payload.conversation_id,
            title=payload.title,
            knowledge_base_ids=payload.knowledge_base_ids,
            knowledge_ids=payload.knowledge_ids,
            web_search_enabled=payload.web_search_enabled,
        )
    except NativeAgentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return NativeAgentQaResponse(
        conversation=ConversationRead.model_validate(conversation),
        messages=[ConversationMessageRead.model_validate(message) for message in messages],
        task=TaskRead.model_validate(task),
        output=GeneratedOutputRead.model_validate(output),
        citations=[CitationRead.model_validate(citation) for citation in citations],
        runtime=NativeAgentQaRuntime.model_validate(runtime),
    )


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
            retrieval_scope=payload.retrieval_scope,
            current_run=payload.current_run,
            expected_source_types=payload.expected_source_types,
            should_answer_insufficient=payload.should_answer_insufficient,
            forbidden_anchors=payload.forbidden_anchors,
            question_type=payload.question_type,
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
