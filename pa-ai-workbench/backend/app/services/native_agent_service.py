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
from app.services.native_audit_service import NativeConfirmationError
from app.services.native_audit_service import record_native_mutation_audit
from app.services.native_audit_service import require_native_confirmation
from app.services.native_audit_service import update_native_mutation_audit
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.log_context import weknora_log_context
from knowledge_engine.schemas import Evidence


class NativeAgentError(Exception):
    """Raised when the native AgentQA workflow cannot complete."""


CONFIRM_AGENT_MUTATION_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"
CONFIRM_AGENT_MUTATION_TOKEN_ID = "native_custom_agent_mutation"


def native_agent_catalog(session: Session) -> dict[str, Any]:
    if get_settings().knowledge_backend != "weknora_api":
        raise NativeAgentError("Native AgentQA requires the WeKnora backend.")
    backend = _weknora_backend()
    try:
        agents = backend.list_agents()
        presets = backend.list_agent_type_presets()
        placeholders = backend.list_agent_placeholders()
    except KnowledgeBackendUnavailableError as exc:
        raise NativeAgentError(str(exc)) from exc

    active_kb_id = active_knowledge_base_id(session)
    safe_agents = [_safe_agent_item(agent) for agent in agents]
    selected_agent_id = _select_agent_id(safe_agents, None)
    suggested_questions: list[dict[str, Any]] = []
    suggested_status = "backlog"
    if selected_agent_id:
        try:
            suggested_questions = [
                _safe_suggested_question(item)
                for item in backend.get_agent_suggested_questions(
                    agent_id=selected_agent_id,
                    knowledge_base_ids=[active_kb_id] if active_kb_id else [],
                    limit=6,
                )
            ]
            suggested_status = "live"
        except KnowledgeBackendUnavailableError:
            suggested_status = "blocked"

    return {
        "schema_version": "wnx-p1-05",
        "source": "weknora_api",
        "status": "live" if safe_agents else "partial",
        "agents": safe_agents,
        "presets": [_safe_agent_preset(item) for item in presets],
        "placeholder_groups": _placeholder_counts(placeholders),
        "suggested_questions": suggested_questions,
        "selected_agent_id": selected_agent_id,
        "active_knowledge_base_id": active_kb_id,
        "surfaces": {
            "list": "live",
            "type_presets": "live" if presets else "partial",
            "placeholders": "live" if placeholders else "partial",
            "suggested_questions": suggested_status,
            "copy": "live",
            "mutations": "live",
            "ownership": "native_owned_agent_or_admin",
        },
        "warnings": [
            "Agent copy/update/delete require confirm_token and NativeMutationAudit."
        ],
    }


def create_native_agent(
    *,
    session: Session,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_agent(
        session=session,
        action="create",
        confirm_token=confirm_token,
        target_type="custom_agent",
        target_id=None,
        request_summary=_agent_request_summary("create", payload=payload),
        mutate=lambda backend: {"agent": backend.create_agent(_agent_payload(payload))},
    )


def update_native_agent(
    *,
    session: Session,
    agent_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_agent(
        session=session,
        action="update",
        confirm_token=confirm_token,
        target_type="custom_agent",
        target_id=_safe_public_id(agent_id),
        request_summary=_agent_request_summary("update", payload=payload, agent_id=agent_id),
        mutate=lambda backend: {"agent": backend.update_agent(agent_id, _agent_payload(payload))},
    )


def copy_native_agent(
    *,
    session: Session,
    agent_id: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_agent(
        session=session,
        action="copy",
        confirm_token=confirm_token,
        target_type="custom_agent",
        target_id=_safe_public_id(agent_id),
        request_summary={"action": "copy", "agent_id_present": bool(str(agent_id or "").strip())},
        mutate=lambda backend: {"agent": backend.copy_agent(agent_id)},
    )


def delete_native_agent(
    *,
    session: Session,
    agent_id: str,
    confirm_token: str | None,
) -> dict[str, Any]:
    return _mutate_agent(
        session=session,
        action="delete",
        confirm_token=confirm_token,
        target_type="custom_agent",
        target_id=_safe_public_id(agent_id),
        request_summary={"action": "delete", "agent_id_present": bool(str(agent_id or "").strip())},
        mutate=lambda backend: {"deleted": bool(backend.delete_agent(agent_id).get("success"))},
    )


def run_native_agent_qa(
    *,
    session: Session,
    query: str,
    agent_id: str | None = None,
    conversation_id: str | None = None,
    title: str | None = None,
    knowledge_base_ids: list[str] | None = None,
    knowledge_ids: list[str] | None = None,
    web_search_enabled: bool = False,
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
        raise NativeAgentError("Query is required.")
    if get_settings().knowledge_backend != "weknora_api":
        raise NativeAgentError("Native AgentQA requires the WeKnora backend.")

    backend = _weknora_backend()
    try:
        safe_agents = [_safe_agent_item(agent) for agent in backend.list_agents()]
    except KnowledgeBackendUnavailableError as exc:
        raise NativeAgentError(str(exc)) from exc
    resolved_agent_id = _select_agent_id(safe_agents, agent_id)
    if not resolved_agent_id:
        raise NativeAgentError("No runnable native agent is available.")
    if not any(agent["id"] == resolved_agent_id for agent in safe_agents):
        raise NativeAgentError("Selected native agent is unavailable.")
    selected_agent = next(agent for agent in safe_agents if agent["id"] == resolved_agent_id)

    kb_ids = _normalize_str_list(knowledge_base_ids or [])
    native_knowledge_ids = _normalize_str_list(knowledge_ids or [])
    if not kb_ids and not native_knowledge_ids:
        active_kb_id = active_knowledge_base_id(session)
        if active_kb_id:
            kb_ids = [active_kb_id]

    conversation, user_message = _ensure_conversation(
        session=session,
        conversation_id=conversation_id,
        title=title,
        query=normalized_query,
        agent_id=resolved_agent_id,
        kb_ids=kb_ids,
        knowledge_ids=native_knowledge_ids,
        web_search_enabled=web_search_enabled,
    )
    task = create_task(
        session=session,
        task_type="native_agentqa",
        title=title or normalized_query,
        conversation_id=conversation.id,
        input_json=_json_dumps(
            {
                "query": normalized_query,
                "agent_id": resolved_agent_id,
                "knowledge_base_ids": kb_ids,
                "knowledge_ids": native_knowledge_ids,
                "web_search_enabled": web_search_enabled,
            }
        ),
        status="running",
        current_step="weknora_agentqa",
        progress=20,
    )

    try:
        with weknora_log_context(
            correlation_id=uuid4().hex,
            task_id=task.id,
            conversation_id=conversation.id,
        ):
            native_session_id = backend.create_agent_session(title or normalized_query)
            result = backend.run_agent_qa(
                session_id=native_session_id,
                query=normalized_query,
                agent_id=resolved_agent_id,
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
        raise NativeAgentError(str(exc)) from exc

    answer = str(result.get("answer") or "").strip()
    evidence_items = [
        item for item in result.get("evidence_items", []) if isinstance(item, Evidence)
    ]
    warnings = _result_warnings(result, evidence_items)
    status = "completed" if answer else "failed"
    if not answer:
        warnings.append("Native AgentQA returned no answer content.")

    assistant = add_message(
        session=session,
        conversation=conversation,
        role="assistant",
        content=answer or "Native AgentQA returned no answer.",
        metadata_json=_json_dumps(
            {
                "task_id": task.id,
                "task_type": "native_agentqa",
                "source": "weknora_api",
                "native_session_id": result.get("session_id"),
                "agent_id": resolved_agent_id,
                "event_counts": result.get("event_counts") or {},
                "reference_count": result.get("reference_count") or 0,
                "tool_names": result.get("tool_names") or [],
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
                    "task_type": "native_agentqa",
                    "source": "weknora_api",
                    "agent_id": resolved_agent_id,
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
                "agent_id": resolved_agent_id,
                "agent": selected_agent,
                "event_counts": result.get("event_counts") or {},
                "tool_names": result.get("tool_names") or [],
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
        "agent_id": resolved_agent_id,
        "agent_name": selected_agent.get("name"),
        "event_counts": result.get("event_counts") or {},
        "tool_names": result.get("tool_names") or [],
        "reference_count": result.get("reference_count") or 0,
        "saved_citation_count": len(citations),
        "citation_blocked": len(citations) == 0,
        "warnings": warnings,
        "assistant_message_id": assistant.id,
        "user_message_id": user_message.id if user_message is not None else None,
    }
    return conversation, messages, task, output, citations, runtime


def _mutate_agent(
    *,
    session: Session,
    action: str,
    confirm_token: str | None,
    target_type: str,
    target_id: str | None,
    request_summary: dict[str, Any],
    mutate: Any,
) -> dict[str, Any]:
    settings = get_settings()
    response = {
        "schema_version": f"wnfc-p5-03-agent-{action}",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"][action] = {"status": "backlog", "reason": "weknora_api backend is required"}
        return response
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_AGENT_MUTATION_TOKEN,
            token_id=CONFIRM_AGENT_MUTATION_TOKEN_ID,
            action=f"native custom agent {action}",
        )
    except NativeConfirmationError:
        response["surfaces"][action] = _agent_confirmation_blocked(action)
        response["warnings"].append(f"blocked: native custom agent {action} requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="custom_agent",
        operation=f"weknora_agent_{action}",
        target_type=target_type,
        target_id=target_id,
        status="started",
        confirmation=confirmation,
        request_summary=request_summary,
    )
    session.commit()

    try:
        result = mutate(_weknora_backend())
    except (KnowledgeBackendUnavailableError, ValueError) as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": action, "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"][action] = {"status": "partial", "reason": _error_code_from_exception(exc)}
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: agent_{action}: {_error_code_from_exception(exc)}")
        return response

    surface = {"status": "live", **_agent_result_surface(result)}
    if action == "create":
        created_id = _safe_public_id((surface.get("agent") or {}).get("id") if isinstance(surface.get("agent"), dict) else None)
        if created_id:
            audit.target_id = created_id
    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={"action": action, "success": True, **_agent_surface_summary(surface)},
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"][action] = surface
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


def _agent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("agent name is required")
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    safe_config = dict(config)
    safe_config.setdefault("agent_mode", "quick-answer")
    safe_config.setdefault("kb_selection_mode", "none")
    safe_config.setdefault("knowledge_bases", [])
    safe_config["web_search_enabled"] = False
    return {
        "name": name[:255],
        "description": str(payload.get("description") or "").strip()[:1000],
        "avatar": str(payload.get("avatar") or "").strip()[:64],
        "config": safe_config,
    }


def _agent_request_summary(action: str, *, payload: dict[str, Any], agent_id: str | None = None) -> dict[str, Any]:
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    return {
        "action": action,
        "agent_id_present": bool(str(agent_id or "").strip()),
        "name_present": bool(str(payload.get("name") or "").strip()),
        "description_present": bool(str(payload.get("description") or "").strip()),
        "agent_mode": str(config.get("agent_mode") or "quick-answer")[:40],
        "kb_selection_mode": str(config.get("kb_selection_mode") or "none")[:40],
        "web_search_enabled": bool(config.get("web_search_enabled")),
    }


def _agent_result_surface(result: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    agent = result.get("agent") if isinstance(result.get("agent"), dict) else None
    if agent:
        safe["agent"] = _public_agent(agent)
    if "deleted" in result:
        safe["deleted"] = bool(result.get("deleted"))
    return safe


def _agent_surface_summary(surface: dict[str, Any]) -> dict[str, Any]:
    agent = surface.get("agent") if isinstance(surface.get("agent"), dict) else {}
    return {
        "status": surface.get("status"),
        "deleted": surface.get("deleted"),
        "agent_id_present": bool(agent.get("id")),
        "is_builtin": bool(agent.get("is_builtin")),
        "agent_mode": agent.get("agent_mode"),
    }


def _public_agent(agent: dict[str, Any]) -> dict[str, Any]:
    safe = _safe_agent_item(agent)
    safe["created_by_present"] = bool(agent.get("created_by"))
    return safe


def _agent_confirmation_blocked(action: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": f"confirm_token={CONFIRM_AGENT_MUTATION_TOKEN} is required",
        "action": action,
        "confirm_token_id": CONFIRM_AGENT_MUTATION_TOKEN_ID,
    }


def _audit_surface(audit: Any) -> dict[str, Any]:
    return {
        "id": audit.id,
        "capability": audit.capability,
        "operation": audit.operation,
        "target_type": audit.target_type,
        "target_id": audit.target_id,
        "source": audit.source,
        "status": audit.status,
        "confirmation_required": audit.confirmation_required,
        "confirmation_method": audit.confirmation_method,
        "confirm_token_id": audit.confirm_token_id,
        "created_at": audit.created_at.isoformat(),
    }


def _confirmation_read(confirmation: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": bool(confirmation.get("required")),
        "method": confirmation.get("method"),
        "token_id": confirmation.get("token_id"),
    }


def _safe_public_id(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= 12:
        return text
    return f"{text[:6]}...{text[-4:]}"


def _error_code_from_exception(exc: Exception) -> str:
    return str(getattr(exc, "error_code", None) or exc.__class__.__name__)


def _ensure_conversation(
    *,
    session: Session,
    conversation_id: str | None,
    title: str | None,
    query: str,
    agent_id: str,
    kb_ids: list[str],
    knowledge_ids: list[str],
    web_search_enabled: bool,
) -> tuple[Conversation, ConversationMessage | None]:
    metadata = _json_dumps(
        {
            "task_type": "native_agentqa",
            "source": "weknora_api",
            "agent_id": agent_id,
            "knowledge_base_ids": kb_ids,
            "knowledge_ids": knowledge_ids,
            "web_search_enabled": web_search_enabled,
        }
    )
    if conversation_id:
        conversation = get_conversation(session, conversation_id)
        if conversation is None:
            raise NativeAgentError("Conversation not found.")
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
        default_task_type="native_agentqa",
        initial_message=query,
    )
    user_message = messages[0] if messages else None
    if user_message is not None:
        user_message.metadata_json = metadata
        session.add(user_message)
        session.commit()
        session.refresh(user_message)
    return conversation, user_message


def _safe_agent_item(agent: dict[str, Any]) -> dict[str, Any]:
    config = agent.get("config") if isinstance(agent.get("config"), dict) else {}
    allowed_tools = config.get("allowed_tools") if isinstance(config.get("allowed_tools"), list) else []
    knowledge_bases = config.get("knowledge_bases") if isinstance(config.get("knowledge_bases"), list) else []
    suggested_prompts = config.get("suggested_prompts") if isinstance(config.get("suggested_prompts"), list) else []
    return {
        "id": _optional_str(agent.get("id")),
        "name": _optional_str(agent.get("name")) or "Unnamed agent",
        "description": _optional_str(agent.get("description")),
        "avatar": _optional_str(agent.get("avatar")),
        "is_builtin": bool(agent.get("is_builtin")),
        "creator_name": _optional_str(agent.get("creator_name")),
        "runnable_by_viewer": bool(agent.get("runnable_by_viewer", True)),
        "agent_mode": _optional_str(config.get("agent_mode")) or "quick-answer",
        "agent_type": _optional_str(config.get("agent_type")),
        "allowed_tools": [str(item) for item in allowed_tools if item],
        "knowledge_base_count": len([item for item in knowledge_bases if item]),
        "model_configured": bool(config.get("model_id")),
        "rerank_configured": bool(config.get("rerank_model_id")),
        "web_search_enabled": bool(config.get("web_search_enabled")),
        "suggested_prompt_count": len([item for item in suggested_prompts if item]),
    }


def _safe_agent_preset(preset: dict[str, Any]) -> dict[str, Any]:
    allowed_tools = preset.get("allowed_tools") if isinstance(preset.get("allowed_tools"), list) else []
    return {
        "agent_type": _optional_str(preset.get("agent_type") or preset.get("type") or preset.get("id")),
        "name": _optional_str(preset.get("name") or preset.get("label")),
        "description": _optional_str(preset.get("description")),
        "allowed_tools": [str(item) for item in allowed_tools if item],
    }


def _safe_suggested_question(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": _optional_str(item.get("question")),
        "source": _optional_str(item.get("source")),
        "knowledge_base_id": _optional_str(item.get("knowledge_base_id")),
    }


def _placeholder_counts(placeholders: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in placeholders.items():
        if isinstance(value, list):
            counts[str(key)] = len(value)
    return counts


def _select_agent_id(agents: list[dict[str, Any]], requested_agent_id: str | None) -> str | None:
    requested = _optional_str(requested_agent_id)
    if requested and any(agent.get("id") == requested for agent in agents):
        return requested
    preferred = [
        "builtin-wiki-researcher",
        "builtin-smart-reasoning",
        "builtin-document-assistant",
        "builtin-quick-answer",
    ]
    for agent_id in preferred:
        if any(agent.get("id") == agent_id for agent in agents):
            return agent_id
    for agent in agents:
        agent_id = _optional_str(agent.get("id"))
        if agent_id:
            return agent_id
    return None


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


def _result_warnings(result: dict[str, Any], evidence_items: list[Evidence]) -> list[str]:
    warnings = [str(item) for item in result.get("errors", []) if str(item)]
    if not evidence_items:
        warnings.append(
            "CITATION_BLOCKED: native AgentQA returned a live answer but did not emit traceable references."
        )
    return warnings


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


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_string(*values: Any) -> str | None:
    for value in values:
        text = _optional_str(value)
        if text:
            return text
    return None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
