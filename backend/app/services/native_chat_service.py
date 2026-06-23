import json
from typing import Any
from urllib.parse import quote
from urllib.parse import urlencode
from uuid import uuid4

from sqlmodel import Session

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
from app.services.knowledge_base_service import active_knowledge_base_id
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.log_context import weknora_log_context
from knowledge_engine.schemas import Evidence


class NativeKnowledgeChatError(Exception):
    """Raised when the native knowledge-chat workflow cannot complete."""


def run_native_knowledge_chat(
    *,
    session: Session,
    query: str,
    conversation_id: str | None = None,
    title: str | None = None,
    knowledge_base_ids: list[str] | None = None,
    knowledge_ids: list[str] | None = None,
    web_search_enabled: bool = False,
    current_run: dict[str, Any] | None = None,
) -> tuple[
    Conversation,
    list[ConversationMessage],
    GenerationTask,
    GeneratedOutput,
    list,
    dict[str, Any],
]:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise NativeKnowledgeChatError("Query is required.")
    if get_settings().knowledge_backend != "weknora_api":
        raise NativeKnowledgeChatError("Native knowledge-chat requires the WeKnora backend.")

    kb_ids = _normalize_str_list(knowledge_base_ids or [])
    native_knowledge_ids = _normalize_str_list(knowledge_ids or [])
    if not kb_ids and not native_knowledge_ids:
        active_kb_id = active_knowledge_base_id(session)
        if active_kb_id:
            kb_ids = [active_kb_id]
    if not kb_ids and not native_knowledge_ids:
        raise NativeKnowledgeChatError("A knowledge base or knowledge id is required.")

    conversation, user_message = _ensure_conversation(
        session=session,
        conversation_id=conversation_id,
        title=title,
        query=normalized_query,
        kb_ids=kb_ids,
        knowledge_ids=native_knowledge_ids,
        current_run=current_run or {},
    )
    task = create_task(
        session=session,
        task_type="native_knowledge_chat",
        title=title or normalized_query,
        conversation_id=conversation.id,
        input_json=_json_dumps(
            {
                "query": normalized_query,
                "knowledge_base_ids": kb_ids,
                "knowledge_ids": native_knowledge_ids,
                "web_search_enabled": web_search_enabled,
                "current_run": current_run or {},
            }
        ),
        status="running",
        current_step="weknora_knowledge_chat",
        progress=20,
    )

    backend = _weknora_backend()
    try:
        with weknora_log_context(
            correlation_id=uuid4().hex,
            task_id=task.id,
            conversation_id=conversation.id,
        ):
            native_session_id = backend.create_agent_session(title or normalized_query)
            result = backend.run_knowledge_chat(
                session_id=native_session_id,
                query=normalized_query,
                knowledge_base_ids=kb_ids,
                knowledge_ids=native_knowledge_ids,
                web_search_enabled=web_search_enabled,
                disable_title=True,
            )
    except KnowledgeBackendUnavailableError as exc:
        update_task_status(
            session=session,
            task=task,
            status="failed",
            current_step="failed",
            progress=100,
            error_message=str(exc)[:500],
        )
        raise NativeKnowledgeChatError(str(exc)) from exc

    answer = str(result.get("answer") or "").strip()
    evidence_items = [
        item for item in result.get("evidence_items", []) if isinstance(item, Evidence)
    ]
    warnings = _result_warnings(result, evidence_items, current_run or {})
    status = "completed" if answer else "failed"
    if not answer:
        warnings.append("Native knowledge-chat returned no answer content.")
    assistant = add_message(
        session=session,
        conversation=conversation,
        role="assistant",
        content=answer or "Native knowledge-chat returned no answer.",
        metadata_json=_json_dumps(
            {
                "task_id": task.id,
                "task_type": "native_knowledge_chat",
                "source": "weknora_api",
                "native_session_id": result.get("session_id"),
                "event_counts": result.get("event_counts") or {},
                "reference_count": result.get("reference_count") or 0,
                "current_run": current_run or {},
            }
        ),
    )
    if warnings:
        add_message(
            session=session,
            conversation=conversation,
            role="system_status",
            content="; ".join(warnings),
            metadata_json=_json_dumps(
                {
                    "task_id": task.id,
                    "task_type": "native_knowledge_chat",
                    "source": "weknora_api",
                }
            ),
        )

    output, citations = create_output_with_citations(
        session=session,
        task=task,
        title=title or normalized_query,
        content_json=_json_dumps(
            {
                "answer": answer,
                "source": "weknora_api",
                "native_session_id": result.get("session_id"),
                "event_counts": result.get("event_counts") or {},
                "reference_count": result.get("reference_count") or 0,
            }
        ),
        content_markdown=answer,
        warnings_json=_json_dumps(warnings),
        status=status,
        citations=[_citation_payload(item) for item in evidence_items],
    )
    update_task_status(
        session=session,
        task=task,
        status=status,
        current_step="completed" if status == "completed" else "failed",
        progress=100,
        error_message=None if status == "completed" else "; ".join(warnings),
    )
    messages = list_messages(session, conversation.id)
    runtime = {
        "native_session_id": result.get("session_id"),
        "event_counts": result.get("event_counts") or {},
        "reference_count": result.get("reference_count") or 0,
        "saved_citation_count": len(citations),
        "warnings": warnings,
        "assistant_message_id": assistant.id,
        "user_message_id": user_message.id if user_message is not None else None,
        "current_run_guard": _current_run_guard(evidence_items, current_run or {}),
    }
    return conversation, messages, task, output, citations, runtime


def _ensure_conversation(
    *,
    session: Session,
    conversation_id: str | None,
    title: str | None,
    query: str,
    kb_ids: list[str],
    knowledge_ids: list[str],
    current_run: dict[str, Any],
) -> tuple[Conversation, ConversationMessage | None]:
    metadata = _json_dumps(
        {
            "task_type": "native_knowledge_chat",
            "source": "weknora_api",
            "knowledge_base_ids": kb_ids,
            "knowledge_ids": knowledge_ids,
            "current_run": current_run,
        }
    )
    if conversation_id:
        conversation = get_conversation(session, conversation_id)
        if conversation is None:
            raise NativeKnowledgeChatError("Conversation not found.")
        user_message = add_message(
            session=session,
            conversation=conversation,
            role="user",
            content=query,
            metadata_json=metadata,
        )
        return conversation, user_message
    conversation, messages = create_conversation(
        session=session,
        title=title or query,
        default_task_type="native_knowledge_chat",
        initial_message=query,
    )
    user_message = messages[0] if messages else None
    if user_message is not None:
        user_message.metadata_json = metadata
        session.add(user_message)
        session.commit()
        session.refresh(user_message)
    return conversation, user_message


def _citation_payload(evidence: Evidence) -> dict[str, Any]:
    metadata = dict(evidence.metadata)
    metadata.setdefault("evidence_id", evidence.evidence_id)
    metadata.setdefault("citation_source_type", evidence.source_type)
    metadata.setdefault(
        "citation_binding",
        {
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "external_doc_id": evidence.external_doc_id,
            "chunk_id": evidence.chunk_id,
            "wiki_page_id": evidence.wiki_page_id,
            "locator": _locator(evidence),
        },
    )
    if evidence.wiki_page_id:
        metadata.setdefault("wiki_page_id", evidence.wiki_page_id)
    return {
        "document_id": evidence.document_id,
        "external_doc_id": evidence.external_doc_id,
        "chunk_id": evidence.chunk_id,
        "title": evidence.title,
        "text": evidence.text,
        "score": evidence.score,
        "source": evidence.source,
        "metadata_json": _json_dumps(metadata),
    }


def _locator(evidence: Evidence) -> str | None:
    if evidence.source_type == "wiki_page" and evidence.wiki_page_id:
        slug = _first_string(
            evidence.metadata.get("weknora_wiki_page_slug"),
            evidence.metadata.get("wiki_page_slug"),
            evidence.metadata.get("slug"),
            evidence.wiki_page_id,
        )
        return f"#/wiki?slug={quote(slug, safe='')}" if slug else None
    if evidence.chunk_id:
        return f"#/library?{urlencode({'document': evidence.external_doc_id or '', 'chunk': evidence.chunk_id})}"
    return None


def _result_warnings(
    result: dict[str, Any],
    evidence_items: list[Evidence],
    current_run: dict[str, Any],
) -> list[str]:
    warnings = [str(item) for item in result.get("errors", []) if str(item)]
    if not evidence_items:
        warnings.append("Native knowledge-chat returned no traceable references.")
    guard = _current_run_guard(evidence_items, current_run)
    if guard["required"] and not guard["passed"]:
        warnings.append("Current-run guard did not find required native evidence.")
    return warnings


def _current_run_guard(evidence_items: list[Evidence], current_run: dict[str, Any]) -> dict[str, Any]:
    expected_external_doc_ids = set(
        _normalize_str_list(
            current_run.get("external_doc_ids")
            or current_run.get("expected_external_doc_ids")
            or []
        )
    )
    expected_chunk_ids = set(
        _normalize_str_list(current_run.get("chunk_ids") or current_run.get("expected_chunk_ids") or [])
    )
    found_external_doc_ids = {
        str(item.external_doc_id)
        for item in evidence_items
        if item.external_doc_id
    }
    found_chunk_ids = {str(item.chunk_id) for item in evidence_items if item.chunk_id}
    required = bool(expected_external_doc_ids or expected_chunk_ids)
    missing_external_doc_ids = sorted(expected_external_doc_ids - found_external_doc_ids)
    missing_chunk_ids = sorted(expected_chunk_ids - found_chunk_ids)
    return {
        "required": required,
        "passed": not missing_external_doc_ids and not missing_chunk_ids,
        "expected_external_doc_ids": sorted(expected_external_doc_ids),
        "found_external_doc_ids": sorted(found_external_doc_ids),
        "missing_external_doc_ids": missing_external_doc_ids,
        "expected_chunk_ids": sorted(expected_chunk_ids),
        "found_chunk_ids": sorted(found_chunk_ids),
        "missing_chunk_ids": missing_chunk_ids,
    }


def _weknora_backend() -> WeKnoraApiBackend:
    settings = get_settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
    )


def _normalize_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
