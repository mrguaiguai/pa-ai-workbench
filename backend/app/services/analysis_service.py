import json
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app import pathing as _pathing  # noqa: F401
from app.config import get_settings
from app.models import Conversation
from app.models import ConversationMessage
from app.models import GeneratedOutput
from app.models import GenerationTask
from app.services.conversation_service import add_message
from app.services.conversation_service import create_conversation
from app.services.conversation_service import get_conversation
from app.services.conversation_service import list_messages
from app.services.generation_service import create_output_with_citations
from app.services.generation_service import create_task
from app.services.generation_service import update_task_status
from agent.orchestrator import AgentOrchestrator
from agent.schemas import AgentRequest
from agent.schemas import AgentResult
from agent.schemas import AgentStatus
from knowledge_engine.source_scope import normalize_source_scope
from knowledge_engine.log_context import weknora_log_context


class AnalysisRunError(Exception):
    pass


def run_analysis(
    session: Session,
    task_type: str,
    query_or_topic: str,
    title: str | None = None,
    conversation_id: str | None = None,
    business_area: str | None = None,
    document_type: str | None = None,
    document_ids: list[str] | None = None,
    extra_requirements: str | None = None,
    retrieval_scope: str = "all",
) -> tuple[Conversation, list[ConversationMessage], GenerationTask, GeneratedOutput, list]:
    normalized_retrieval_scope = normalize_source_scope(retrieval_scope)
    conversation, user_message = _ensure_conversation(
        session=session,
        conversation_id=conversation_id,
        task_type=task_type,
        title=title,
        query_or_topic=query_or_topic,
    )

    if user_message is None:
        user_message = add_message(
            session=session,
            conversation=conversation,
            role="user",
            content=query_or_topic,
            metadata_json=_json_dumps(
                {
                    "task_type": task_type,
                    "retrieval_scope": normalized_retrieval_scope,
                }
            ),
        )
    elif user_message.metadata_json is None:
        user_message.metadata_json = _json_dumps(
            {
                "task_type": task_type,
                "retrieval_scope": normalized_retrieval_scope,
            }
        )
        session.add(user_message)

    task = create_task(
        session=session,
        task_type=task_type,
        title=title or query_or_topic,
        conversation_id=conversation.id,
        input_json=_json_dumps(
            {
                "query_or_topic": query_or_topic,
                "business_area": business_area,
                "document_type": document_type,
                "document_ids": document_ids or [],
                "extra_requirements": extra_requirements,
                "retrieval_scope": normalized_retrieval_scope,
            }
        ),
        status="running",
        current_step="agent",
        progress=10,
    )

    recent_messages = _recent_message_dicts(session, conversation.id)
    request = AgentRequest(
        task_id=task.id,
        conversation_id=conversation.id,
        task_type=task_type,
        title=title,
        query_or_topic=query_or_topic,
        business_area=business_area,
        document_type=document_type,
        document_ids=document_ids or [],
        extra_requirements=extra_requirements,
        retrieval_scope=normalized_retrieval_scope,
        metadata={"retrieval_scope": normalized_retrieval_scope},
    )
    with weknora_log_context(
        correlation_id=uuid4().hex,
        task_id=task.id,
        conversation_id=conversation.id,
    ):
        result = AgentOrchestrator().run(
            request=request,
            recent_messages=recent_messages,
        )
    _write_result_messages(session, conversation, result)
    output, citations = _persist_result(session, task, result)
    final_status = "completed" if result.status == AgentStatus.SUCCEEDED else "failed"
    update_task_status(
        session=session,
        task=task,
        status=final_status,
        current_step="completed" if final_status == "completed" else "failed",
        progress=100,
        error_message=None if final_status == "completed" else "; ".join(result.warnings),
    )
    messages = list_messages(session, conversation.id)
    return conversation, messages, task, output, citations


def _ensure_conversation(
    session: Session,
    conversation_id: str | None,
    task_type: str,
    title: str | None,
    query_or_topic: str,
) -> tuple[Conversation, ConversationMessage | None]:
    if conversation_id:
        conversation = get_conversation(session, conversation_id)
        if conversation is None:
            raise AnalysisRunError("Conversation not found")
        return conversation, None

    conversation, messages = create_conversation(
        session=session,
        title=title or query_or_topic,
        default_task_type=task_type,
        initial_message=query_or_topic,
    )
    return conversation, messages[0] if messages else None


def _recent_message_dicts(session: Session, conversation_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    messages = list_messages(session, conversation_id)[-settings.memory_recent_limit :]
    return [
        {
            "role": message.role,
            "content": message.content,
            "metadata_json": message.metadata_json,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]


def _write_result_messages(
    session: Session,
    conversation: Conversation,
    result: AgentResult,
) -> None:
    for update in result.memory_updates:
        role = update.get("role")
        content = update.get("content")
        if role == "assistant" and isinstance(content, str) and content:
            add_message(
                session=session,
                conversation=conversation,
                role="assistant",
                content=content,
                metadata_json=_json_dumps(update.get("metadata") or {}),
            )

    if result.warnings:
        add_message(
            session=session,
            conversation=conversation,
            role="system_status",
            content="; ".join(result.warnings),
            metadata_json=_json_dumps(
                {
                    "task_id": result.task_id,
                    "task_type": result.task_type,
                    "status": result.status,
                }
            ),
        )


def _persist_result(
    session: Session,
    task: GenerationTask,
    result: AgentResult,
) -> tuple[GeneratedOutput, list]:
    return create_output_with_citations(
        session=session,
        task=task,
        title=result.title,
        content_json=_json_dumps(result.content),
        content_markdown=result.markdown,
        warnings_json=_json_dumps(result.warnings),
        status="completed" if result.status == AgentStatus.SUCCEEDED else "failed",
        citations=[
            {
                "document_id": citation.document_id,
                "external_doc_id": citation.external_doc_id,
                "chunk_id": citation.chunk_id,
                "title": citation.title,
                "text": citation.text,
                "score": citation.score,
                "source": citation.source,
                "metadata_json": _json_dumps(_citation_metadata(citation)),
            }
            for citation in result.citations
        ],
    )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _citation_metadata(citation) -> dict:
    metadata = dict(citation.metadata)
    if citation.evidence_id:
        metadata.setdefault("evidence_id", citation.evidence_id)
    if citation.source_type:
        metadata.setdefault("citation_source_type", citation.source_type)
    if citation.wiki_page_id:
        metadata.setdefault("wiki_page_id", citation.wiki_page_id)
    return metadata
