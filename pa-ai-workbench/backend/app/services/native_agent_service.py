import json
from typing import Any
from urllib.parse import quote
from urllib.parse import urlencode
from uuid import uuid4

from sqlmodel import Session
from sqlmodel import select

from app.models import Citation
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
CONFIRM_WIKI_AGENT_RUN_TOKEN = "CONFIRM_NATIVE_WIKI_AGENT_RUN"
CONFIRM_WIKI_AGENT_RUN_TOKEN_ID = "native_wiki_agent_run"

WIKI_MUTATION_TOOLS = {
    "wiki_write_page",
    "wiki_replace_text",
    "wiki_rename_page",
    "wiki_delete_page",
    "wiki_flag_issue",
    "wiki_update_issue",
}

STRATEGY_STRING_FIELDS = {
    "system_prompt",
    "context_template",
    "web_search_provider_id",
}
STRATEGY_BOOL_FIELDS = {
    "web_search_enabled",
    "web_fetch_enabled",
    "multi_turn_enabled",
}
STRATEGY_INT_FIELDS = {
    "web_fetch_top_n": (0, 20),
    "history_turns": (0, 50),
    "embedding_top_k": (0, 200),
    "rerank_top_k": (0, 200),
}
STRATEGY_FLOAT_FIELDS = {
    "keyword_threshold": (0.0, 1.0),
    "vector_threshold": (0.0, 1.0),
    "rerank_threshold": (-10.0, 10.0),
}
STRATEGY_LIST_FIELDS = {
    "allowed_tools",
    "mcp_services",
    "suggested_prompts",
}
STRATEGY_MODE_FIELDS = {
    "mcp_selection_mode": {"all", "selected", "none"},
}


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


def native_agent_suggested_questions(
    *,
    session: Session,
    agent_id: str,
    knowledge_base_ids: list[str] | None = None,
    knowledge_ids: list[str] | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    if get_settings().knowledge_backend != "weknora_api":
        raise NativeAgentError("Native AgentQA requires the WeKnora backend.")
    normalized_agent_id = str(agent_id or "").strip()
    if not normalized_agent_id:
        raise NativeAgentError("Native Agent id is required.")
    kb_ids = _normalize_str_list(knowledge_base_ids or [])
    native_knowledge_ids = _normalize_str_list(knowledge_ids or [])
    if not kb_ids and not native_knowledge_ids:
        active_kb_id = active_knowledge_base_id(session)
        if active_kb_id:
            kb_ids = [active_kb_id]

    backend = _weknora_backend()
    try:
        questions = [
            _safe_suggested_question(item)
            for item in backend.get_agent_suggested_questions(
                agent_id=normalized_agent_id,
                knowledge_base_ids=kb_ids,
                knowledge_ids=native_knowledge_ids,
                limit=limit,
            )
        ]
    except KnowledgeBackendUnavailableError as exc:
        raise NativeAgentError(str(exc)) from exc
    safe_questions = [item for item in questions if item.get("question")]
    return {
        "schema_version": "wnid-p6-01-suggested-questions",
        "source": "weknora_api",
        "status": "live" if safe_questions else "empty",
        "agent_id": normalized_agent_id,
        "knowledge_base_ids": kb_ids,
        "knowledge_ids": native_knowledge_ids,
        "questions": safe_questions,
        "source_counts": _suggested_question_source_counts(safe_questions),
        "surfaces": {
            "native_endpoint": "live",
            "scope_override": "live",
            "click_to_run": "pa_dialogue_shell",
        },
        "warnings": [] if safe_questions else ["native suggested questions returned an empty list for this scope"],
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


def update_native_agent_strategy(
    *,
    session: Session,
    agent_id: str,
    payload: dict[str, Any],
    confirm_token: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    response = {
        "schema_version": "wnid-p2-01-agent-strategy",
        "source": "weknora_api" if settings.knowledge_backend == "weknora_api" else settings.knowledge_backend,
        "status": "blocked",
        "masked": True,
        "surfaces": {},
        "warnings": [],
    }
    if settings.knowledge_backend != "weknora_api":
        response["status"] = "backlog"
        response["surfaces"]["strategy_update"] = {
            "status": "backlog",
            "reason": "weknora_api backend is required",
        }
        return response
    normalized_agent_id = str(agent_id or "").strip()
    if not normalized_agent_id:
        raise ValueError("agent id is required")
    strategy_patch = _strategy_patch(payload)
    if not strategy_patch:
        raise ValueError("at least one strategy field is required")
    try:
        confirmation = require_native_confirmation(
            confirm=None,
            confirm_token=confirm_token,
            expected_token=CONFIRM_AGENT_MUTATION_TOKEN,
            token_id=CONFIRM_AGENT_MUTATION_TOKEN_ID,
            action="native custom agent strategy update",
        )
    except NativeConfirmationError:
        response["surfaces"]["strategy_update"] = {
            "status": "blocked",
            "reason": f"confirm_token={CONFIRM_AGENT_MUTATION_TOKEN} is required",
            "action": "strategy_update",
            "confirm_token_id": CONFIRM_AGENT_MUTATION_TOKEN_ID,
        }
        response["warnings"].append("blocked: native custom agent strategy update requires explicit confirmation")
        return response

    audit = record_native_mutation_audit(
        session=session,
        capability="custom_agent",
        operation="weknora_agent_strategy_update",
        target_type="custom_agent",
        target_id=_safe_public_id(normalized_agent_id),
        status="started",
        confirmation=confirmation,
        request_summary=_strategy_request_summary(strategy_patch, agent_id=normalized_agent_id),
    )
    session.commit()

    try:
        backend = _weknora_backend()
        existing = backend.get_agent(normalized_agent_id)
        if not existing:
            raise ValueError("agent not found")
        existing_config = existing.get("config") if isinstance(existing.get("config"), dict) else {}
        next_config = dict(existing_config)
        next_config.update(strategy_patch)
        result_agent = backend.update_agent_strategy(
            normalized_agent_id,
            {
                "name": existing.get("name"),
                "description": existing.get("description"),
                "avatar": existing.get("avatar"),
                "config": next_config,
            },
        )
    except (KnowledgeBackendUnavailableError, ValueError) as exc:
        update_native_mutation_audit(
            audit=audit,
            status="failed",
            response_summary={"action": "strategy_update", "success": False},
            error_message=str(exc),
        )
        session.commit()
        response["status"] = "partial"
        response["surfaces"]["strategy_update"] = {"status": "partial", "reason": _error_code_from_exception(exc)}
        response["audit"] = _audit_surface(audit)
        response["confirmation"] = _confirmation_read(confirmation)
        response["warnings"].append(f"partial: agent_strategy_update: {_error_code_from_exception(exc)}")
        return response

    surface = {
        "status": "live",
        "agent": _public_agent(result_agent),
        "updated_fields": sorted(strategy_patch),
        "strategy": _safe_agent_strategy(result_agent.get("config") if isinstance(result_agent.get("config"), dict) else {}),
    }
    update_native_mutation_audit(
        audit=audit,
        status="succeeded",
        response_summary={
            "action": "strategy_update",
            "success": True,
            "updated_fields": sorted(strategy_patch),
            "field_count": len(strategy_patch),
        },
    )
    session.commit()
    response["status"] = "live"
    response["surfaces"]["strategy_update"] = surface
    response["audit"] = _audit_surface(audit)
    response["confirmation"] = _confirmation_read(confirmation)
    return response


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
    answer_mode: str = "qa",
    confirm_token: str | None = None,
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
    normalized_answer_mode = _normalize_answer_mode(answer_mode)
    effective_query = _answer_mode_query(normalized_query, normalized_answer_mode)
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
    selected_agent_contract = _selected_agent_contract(selected_agent)
    wiki_mutation_tools = _wiki_mutation_tools(selected_agent_contract)
    wiki_mode_audit = None
    if wiki_mutation_tools:
        try:
            confirmation = require_native_confirmation(
                confirm=False,
                confirm_token=confirm_token,
                expected_token=CONFIRM_WIKI_AGENT_RUN_TOKEN,
                token_id=CONFIRM_WIKI_AGENT_RUN_TOKEN_ID,
                action="native Wiki AgentQA mutation run",
            )
        except NativeConfirmationError as exc:
            raise NativeAgentError(str(exc)) from exc
        wiki_mode_audit = record_native_mutation_audit(
            session=session,
            capability="wiki",
            operation="weknora_agentqa_wiki_mode_run",
            target_type="custom_agent",
            target_id=_safe_public_id(resolved_agent_id),
            status="started",
            confirmation=confirmation,
            request_summary={
                "action": "agentqa_wiki_mode_run",
                "agent_id": resolved_agent_id,
                "tool_count": len(wiki_mutation_tools),
                "wiki_mutation_tools": wiki_mutation_tools,
                "web_search_enabled": web_search_enabled,
            },
        )
        session.commit()

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
        answer_mode=normalized_answer_mode,
    )
    native_session_id = _conversation_native_agent_session_id(
        list_messages(session, conversation.id),
        agent_id=resolved_agent_id,
    )
    native_session_reused = bool(native_session_id)
    native_session_source = "conversation_history" if native_session_id else "created"
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
                "answer_mode": normalized_answer_mode,
                "native_session_reused": native_session_reused,
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
            if not native_session_id:
                native_session_id = backend.create_agent_session(title or normalized_query)
            result = backend.run_agent_qa(
                session_id=native_session_id,
                query=effective_query,
                agent_id=resolved_agent_id,
                knowledge_base_ids=kb_ids,
                knowledge_ids=native_knowledge_ids,
                web_search_enabled=web_search_enabled,
                disable_title=True,
            )
    except KnowledgeBackendUnavailableError as exc:
        if wiki_mode_audit is not None:
            update_native_mutation_audit(
                audit=wiki_mode_audit,
                status="failed",
                response_summary={"action": "agentqa_wiki_mode_run", "success": False},
                error_message=str(exc),
            )
            session.commit()
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
    if native_session_reused and not evidence_items:
        evidence_items = _conversation_history_evidence(
            session=session,
            conversation_id=conversation.id,
            agent_id=resolved_agent_id,
        )
        if evidence_items:
            result["reference_count"] = len(evidence_items)
            result["reference_event_source"] = "conversation_history"
    run_contract = _agent_run_contract(result)
    web_reference_count = _web_reference_count(evidence_items)
    web_providers = _web_providers(evidence_items)
    wiki_reference_count = _wiki_reference_count(evidence_items)
    wiki_slugs = _wiki_slugs(evidence_items)
    web_reference_summary = {
        "reference_count": web_reference_count,
        "providers": web_providers,
        "url_count": _web_url_count(evidence_items),
    }
    warnings = _result_warnings(
        result,
        evidence_items,
        web_search_enabled=web_search_enabled,
        web_reference_count=web_reference_count,
        wiki_mutation_required=bool(wiki_mutation_tools),
        wiki_reference_count=wiki_reference_count,
    )
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
                "answer_mode": normalized_answer_mode,
                "native_session_reused": native_session_reused,
                "native_session_source": native_session_source,
                "agent_id": resolved_agent_id,
                "event_counts": result.get("event_counts") or {},
                "event_sequence": result.get("event_sequence") or [],
                "run_contract": run_contract,
                "selected_agent": selected_agent_contract,
                "reference_count": result.get("reference_count") or 0,
                "reference_event_source": result.get("reference_event_source") or "references",
                "web_reference_count": web_reference_count,
                "web_providers": web_providers,
                "web_search_evidence": web_reference_summary,
                "wiki_reference_count": wiki_reference_count,
                "wiki_slugs": wiki_slugs,
                "wiki_mode_mutation_required": bool(wiki_mutation_tools),
                "wiki_mode_audit": _audit_surface(wiki_mode_audit) if wiki_mode_audit is not None else None,
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
                    "answer_mode": normalized_answer_mode,
                }
            ),
        )

    messages_after_run = list_messages(session, conversation.id)
    conversation_continuity = _conversation_continuity(
        conversation=conversation,
        messages=messages_after_run,
        user_message=user_message,
        assistant_message=assistant,
        requested_conversation_id=conversation_id,
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
                "answer_mode": normalized_answer_mode,
                "native_session_reused": native_session_reused,
                "native_session_source": native_session_source,
                "agent_id": resolved_agent_id,
                "agent": selected_agent,
                "event_counts": result.get("event_counts") or {},
                "event_sequence": result.get("event_sequence") or [],
                "run_contract": run_contract,
                "selected_agent": selected_agent_contract,
                "conversation_continuity": conversation_continuity,
                "tool_names": result.get("tool_names") or [],
                "reference_count": result.get("reference_count") or 0,
                "reference_event_source": result.get("reference_event_source") or "references",
                "web_reference_count": web_reference_count,
                "web_providers": web_providers,
                "web_search_evidence": web_reference_summary,
                "wiki_reference_count": wiki_reference_count,
                "wiki_slugs": wiki_slugs,
                "wiki_mode_mutation_required": bool(wiki_mutation_tools),
                "wiki_mode_audit": _audit_surface(wiki_mode_audit) if wiki_mode_audit is not None else None,
            }
        ),
        content_markdown=answer,
        warnings_json=_json_dumps(warnings),
        status=status,
        citations=[_citation_payload(item) for item in evidence_items],
    )
    if wiki_mode_audit is not None:
        update_native_mutation_audit(
            audit=wiki_mode_audit,
            status="succeeded" if status == "completed" else "failed",
            response_summary={
                "action": "agentqa_wiki_mode_run",
                "success": status == "completed",
                "tool_names": result.get("tool_names") or [],
                "wiki_reference_count": wiki_reference_count,
                "saved_citation_count": len(citations),
            },
            error_message=None if status == "completed" else "; ".join(warnings),
        )
        session.commit()
    update_task_status(
        session=session,
        task=task,
        status=status,
        current_step="completed" if status == "completed" else "failed",
        progress=100,
        error_message=None if status == "completed" else "; ".join(warnings),
    )
    runtime = {
        "native_session_id": result.get("session_id"),
        "answer_mode": normalized_answer_mode,
        "native_session_reused": native_session_reused,
        "native_session_source": native_session_source,
        "agent_id": resolved_agent_id,
        "agent_name": selected_agent.get("name"),
        "event_counts": result.get("event_counts") or {},
        "event_sequence": result.get("event_sequence") or [],
        "run_contract": run_contract,
        "selected_agent": selected_agent_contract,
        "conversation_continuity": conversation_continuity,
        "tool_names": result.get("tool_names") or [],
        "reference_count": result.get("reference_count") or 0,
        "reference_event_source": result.get("reference_event_source") or "references",
        "web_reference_count": web_reference_count,
        "web_providers": web_providers,
        "wiki_reference_count": wiki_reference_count,
        "wiki_slugs": wiki_slugs,
        "wiki_mode_mutation_required": bool(wiki_mutation_tools),
        "wiki_mode_audit": _audit_surface(wiki_mode_audit) if wiki_mode_audit is not None else None,
        "saved_citation_count": len(citations),
        "citation_blocked": len(citations) == 0,
        "warnings": warnings,
        "assistant_message_id": assistant.id,
        "user_message_id": user_message.id if user_message is not None else None,
    }
    return conversation, messages_after_run, task, output, citations, runtime


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


def _strategy_patch(payload: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    for key in STRATEGY_STRING_FIELDS:
        if key in payload and payload.get(key) is not None:
            patch[key] = str(payload.get(key) or "").strip()
    for key in STRATEGY_BOOL_FIELDS:
        if key in payload and payload.get(key) is not None:
            patch[key] = bool(payload.get(key))
    for key, (minimum, maximum) in STRATEGY_INT_FIELDS.items():
        if key in payload and payload.get(key) is not None:
            value = int(payload.get(key) or 0)
            patch[key] = max(min(value, maximum), minimum)
    for key, (minimum, maximum) in STRATEGY_FLOAT_FIELDS.items():
        if key in payload and payload.get(key) is not None:
            value = float(payload.get(key) or 0)
            patch[key] = max(min(value, maximum), minimum)
    for key in STRATEGY_LIST_FIELDS:
        if key in payload and payload.get(key) is not None:
            values = payload.get(key)
            if key == "suggested_prompts":
                patch[key] = [item[:300] for item in _normalize_str_list(values)[:12]]
            else:
                patch[key] = _normalize_str_list(values)[:50]
    for key, allowed in STRATEGY_MODE_FIELDS.items():
        if key in payload and payload.get(key) is not None:
            value = str(payload.get(key) or "").strip().lower()
            if value not in allowed:
                raise ValueError(f"{key} must be one of: {', '.join(sorted(allowed))}")
            patch[key] = value
    return patch


def _strategy_request_summary(strategy_patch: dict[str, Any], *, agent_id: str) -> dict[str, Any]:
    return {
        "action": "strategy_update",
        "agent_id_present": bool(str(agent_id or "").strip()),
        "updated_fields": sorted(strategy_patch),
        "field_count": len(strategy_patch),
        "prompt_fields_present": [
            key for key in ("system_prompt", "context_template") if key in strategy_patch
        ],
        "allowed_tools_count": len(strategy_patch.get("allowed_tools") or []),
        "mcp_services_count": len(strategy_patch.get("mcp_services") or []),
        "suggested_prompts_count": len(strategy_patch.get("suggested_prompts") or []),
        "mcp_selection_mode": strategy_patch.get("mcp_selection_mode"),
        "web_search_enabled": strategy_patch.get("web_search_enabled"),
        "multi_turn_enabled": strategy_patch.get("multi_turn_enabled"),
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
    answer_mode: str,
) -> tuple[Conversation, ConversationMessage | None]:
    metadata = _json_dumps(
        {
            "task_type": "native_agentqa",
            "source": "weknora_api",
            "agent_id": agent_id,
            "knowledge_base_ids": kb_ids,
            "knowledge_ids": knowledge_ids,
            "web_search_enabled": web_search_enabled,
            "answer_mode": answer_mode,
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
        "strategy": _safe_agent_strategy(config),
    }


def _safe_agent_strategy(config: dict[str, Any]) -> dict[str, Any]:
    strategy = {
        "system_prompt": _optional_str(config.get("system_prompt")) or "",
        "context_template": _optional_str(config.get("context_template")) or "",
        "allowed_tools": _normalize_str_list(config.get("allowed_tools") or []),
        "mcp_selection_mode": _optional_str(config.get("mcp_selection_mode")) or "none",
        "mcp_services": _normalize_str_list(config.get("mcp_services") or []),
        "web_search_enabled": bool(config.get("web_search_enabled")),
        "web_search_provider_id": _optional_str(config.get("web_search_provider_id")) or "",
        "web_fetch_enabled": bool(config.get("web_fetch_enabled")),
        "web_fetch_top_n": _safe_int(config.get("web_fetch_top_n")),
        "multi_turn_enabled": bool(config.get("multi_turn_enabled")),
        "history_turns": _safe_int(config.get("history_turns")),
        "embedding_top_k": _safe_int(config.get("embedding_top_k")),
        "keyword_threshold": _safe_float(config.get("keyword_threshold")),
        "vector_threshold": _safe_float(config.get("vector_threshold")),
        "rerank_top_k": _safe_int(config.get("rerank_top_k")),
        "rerank_threshold": _safe_float(config.get("rerank_threshold")),
        "suggested_prompts": _normalize_str_list(config.get("suggested_prompts") or []),
    }
    return strategy


def _selected_agent_contract(agent: dict[str, Any]) -> dict[str, Any]:
    strategy = agent.get("strategy") if isinstance(agent.get("strategy"), dict) else {}
    return {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "agent_mode": agent.get("agent_mode"),
        "agent_type": agent.get("agent_type"),
        "is_builtin": bool(agent.get("is_builtin")),
        "runnable_by_viewer": bool(agent.get("runnable_by_viewer")),
        "allowed_tools": _normalize_str_list(agent.get("allowed_tools") or []),
        "strategy": {
            "allowed_tools": _normalize_str_list(strategy.get("allowed_tools") or []),
            "mcp_selection_mode": _optional_str(strategy.get("mcp_selection_mode")) or "none",
            "mcp_service_count": len(_normalize_str_list(strategy.get("mcp_services") or [])),
            "web_search_enabled": bool(strategy.get("web_search_enabled")),
            "web_fetch_enabled": bool(strategy.get("web_fetch_enabled")),
            "web_fetch_top_n": _safe_int(strategy.get("web_fetch_top_n")),
            "multi_turn_enabled": bool(strategy.get("multi_turn_enabled")),
            "history_turns": _safe_int(strategy.get("history_turns")),
            "embedding_top_k": _safe_int(strategy.get("embedding_top_k")),
            "keyword_threshold": _safe_float(strategy.get("keyword_threshold")),
            "vector_threshold": _safe_float(strategy.get("vector_threshold")),
            "rerank_top_k": _safe_int(strategy.get("rerank_top_k")),
            "rerank_threshold": _safe_float(strategy.get("rerank_threshold")),
            "suggested_prompt_count": len(_normalize_str_list(strategy.get("suggested_prompts") or [])),
            "system_prompt_present": bool(_optional_str(strategy.get("system_prompt"))),
            "context_template_present": bool(_optional_str(strategy.get("context_template"))),
        },
    }


def _wiki_mutation_tools(selected_agent_contract: dict[str, Any]) -> list[str]:
    strategy = selected_agent_contract.get("strategy")
    strategy_tools: list[str] = []
    if isinstance(strategy, dict):
        strategy_tools = _normalize_str_list(strategy.get("allowed_tools") or [])
    tools = _normalize_str_list(selected_agent_contract.get("allowed_tools") or []) + strategy_tools
    matched: list[str] = []
    for tool in tools:
        if tool in WIKI_MUTATION_TOOLS and tool not in matched:
            matched.append(tool)
    return matched


def _agent_run_contract(result: dict[str, Any]) -> dict[str, Any]:
    contract = result.get("event_contract") if isinstance(result.get("event_contract"), dict) else {}
    event_counts = result.get("event_counts") if isinstance(result.get("event_counts"), dict) else {}
    event_sequence = result.get("event_sequence") if isinstance(result.get("event_sequence"), list) else []
    safe_sequence = [str(item) for item in event_sequence[:80] if item]
    thinking_count = _contract_count(contract, event_counts, "thinking")
    tool_call_count = _contract_count(contract, event_counts, "tool_call")
    tool_result_count = _contract_count(contract, event_counts, "tool_result")
    reflection_count = _contract_count(contract, event_counts, "reflection")
    return {
        "schema_version": _optional_str(contract.get("schema_version")) or "wnid-p2-02-react-run-contract",
        "source": _optional_str(contract.get("source")) or "weknora_agent_stream",
        "event_counts": dict(event_counts),
        "event_sequence": safe_sequence,
        "first_event": _optional_str(contract.get("first_event")) or (safe_sequence[0] if safe_sequence else None),
        "last_event": _optional_str(contract.get("last_event")) or (safe_sequence[-1] if safe_sequence else None),
        "thinking_count": thinking_count,
        "tool_call_count": tool_call_count,
        "tool_result_count": tool_result_count,
        "reflection_count": reflection_count,
        "references_count": _contract_count(contract, event_counts, "references"),
        "answer_count": _contract_count(contract, event_counts, "answer"),
        "complete_count": _contract_count(contract, event_counts, "complete"),
        "error_count": _contract_count(contract, event_counts, "error"),
        "tool_approval_required_count": _safe_int(contract.get("tool_approval_required_count")),
        "tool_approval_resolved_count": _safe_int(contract.get("tool_approval_resolved_count")),
        "answer_seen": bool(contract.get("answer_seen")) or _contract_count(contract, event_counts, "answer") > 0,
        "complete_seen": bool(contract.get("complete_seen")) or _contract_count(contract, event_counts, "complete") > 0,
        "react_trace_seen": bool(contract.get("react_trace_seen"))
        or any(count > 0 for count in (thinking_count, tool_call_count, tool_result_count, reflection_count)),
        "tool_call_result_balanced": bool(contract.get("tool_call_result_balanced"))
        or tool_call_count == 0
        or tool_result_count >= tool_call_count,
        "completion": contract.get("completion") if isinstance(contract.get("completion"), dict) else {},
    }


def _contract_count(contract: dict[str, Any], event_counts: dict[str, Any], event_type: str) -> int:
    explicit = contract.get(f"{event_type}_count")
    if explicit is not None:
        return _safe_int(explicit)
    return _safe_int(event_counts.get(event_type))


def _conversation_continuity(
    *,
    conversation: Conversation,
    messages: list[ConversationMessage],
    user_message: ConversationMessage | None,
    assistant_message: ConversationMessage,
    requested_conversation_id: str | None,
) -> dict[str, Any]:
    roles = [message.role for message in messages]
    return {
        "conversation_id": conversation.id,
        "requested_conversation_id": _optional_str(requested_conversation_id),
        "continued_existing_conversation": bool(_optional_str(requested_conversation_id)),
        "message_count": len(messages),
        "user_message_id": user_message.id if user_message is not None else None,
        "assistant_message_id": assistant_message.id,
        "user_message_persisted": user_message is not None and any(message.id == user_message.id for message in messages),
        "assistant_message_persisted": any(message.id == assistant_message.id for message in messages),
        "roles": roles[-8:],
    }


def _conversation_native_agent_session_id(
    messages: list[ConversationMessage],
    *,
    agent_id: str,
) -> str | None:
    for message in reversed(messages):
        metadata = _json_loads(message.metadata_json)
        if metadata.get("task_type") != "native_agentqa":
            continue
        if _optional_str(metadata.get("agent_id")) != agent_id:
            continue
        native_session_id = _optional_str(metadata.get("native_session_id"))
        if native_session_id:
            return native_session_id
    return None


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


def _suggested_question_source_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        source = _optional_str(item.get("source")) or "native"
        counts[source] = counts.get(source, 0) + 1
    return counts


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
    if evidence.source_type == "web_search":
        return _first_string(
            evidence.metadata.get("url"),
            evidence.metadata.get("weknora_url"),
            evidence.metadata.get("source_url"),
            evidence.external_doc_id,
        )
    if evidence.chunk_id:
        return f"#/library?{urlencode({'document': evidence.external_doc_id or '', 'chunk': evidence.chunk_id})}"
    return None


def _result_warnings(
    result: dict[str, Any],
    evidence_items: list[Evidence],
    *,
    web_search_enabled: bool = False,
    web_reference_count: int = 0,
    wiki_mutation_required: bool = False,
    wiki_reference_count: int = 0,
) -> list[str]:
    warnings = [str(item) for item in result.get("errors", []) if str(item)]
    if not evidence_items:
        warnings.append(
            "CITATION_BLOCKED: native AgentQA returned a live answer but did not emit traceable references."
        )
    if web_search_enabled and web_reference_count <= 0:
        warnings.append(
            "WEB_SEARCH_REFERENCE_BLOCKED: native AgentQA did not emit traceable Web Search references."
        )
    if wiki_mutation_required and wiki_reference_count <= 0:
        warnings.append(
            "WIKI_REFERENCE_BLOCKED: native Wiki AgentQA mutation did not emit traceable Wiki page references."
        )
    return warnings


def _conversation_history_evidence(
    *,
    session: Session,
    conversation_id: str,
    agent_id: str,
    limit: int = 8,
) -> list[Evidence]:
    outputs = session.exec(
        select(GeneratedOutput)
        .where(GeneratedOutput.conversation_id == conversation_id)
        .where(GeneratedOutput.task_type == "native_agentqa")
        .order_by(GeneratedOutput.created_at.desc())
        .limit(5)
    ).all()
    evidence_items: list[Evidence] = []
    seen: set[str] = set()
    for output in outputs:
        content = _json_loads(output.content_json)
        if content.get("agent_id") and content.get("agent_id") != agent_id:
            continue
        citations = session.exec(
            select(Citation)
            .where(Citation.output_id == output.id)
            .order_by(Citation.created_at)
        ).all()
        for citation in citations:
            evidence = _citation_to_evidence(citation, inherited_from_output_id=output.id)
            key = (
                evidence.evidence_id
                or evidence.chunk_id
                or evidence.wiki_page_id
                or f"{evidence.external_doc_id}:{evidence.title}:{evidence.text[:80]}"
            )
            if key in seen:
                continue
            seen.add(key)
            evidence_items.append(evidence)
            if len(evidence_items) >= limit:
                return evidence_items
    return evidence_items


def _citation_to_evidence(citation: Citation, *, inherited_from_output_id: str) -> Evidence:
    metadata = _json_loads(citation.metadata_json)
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    source_type = _first_string(
        metadata.get("citation_source_type"),
        binding.get("source_type"),
        metadata.get("source_type"),
    ) or "document_chunk"
    wiki_page_id = _first_string(
        metadata.get("wiki_page_id"),
        metadata.get("weknora_wiki_page_id"),
        binding.get("wiki_page_id"),
    )
    evidence_id = _first_string(
        metadata.get("evidence_id"),
        binding.get("evidence_id"),
        citation.chunk_id,
        wiki_page_id,
    )
    if evidence_id and ":" not in evidence_id:
        evidence_id = f"{source_type}:{evidence_id}"
    metadata["weknora_agentqa_event_source"] = "conversation_history"
    metadata["weknora_agentqa_inherited_from_output_id"] = inherited_from_output_id
    metadata.setdefault("citation_source_type", source_type)
    metadata.setdefault("evidence_id", evidence_id)
    return Evidence(
        document_id=citation.document_id,
        external_doc_id=citation.external_doc_id,
        chunk_id=citation.chunk_id,
        title=citation.title,
        text=citation.text,
        score=citation.score,
        source=citation.source,
        metadata=metadata,
        evidence_id=evidence_id,
        source_type=source_type,
        wiki_page_id=wiki_page_id,
    )


def _web_reference_count(evidence_items: list[Evidence]) -> int:
    return sum(1 for item in evidence_items if item.source_type == "web_search")


def _wiki_reference_count(evidence_items: list[Evidence]) -> int:
    return sum(1 for item in evidence_items if item.source_type == "wiki_page")


def _wiki_slugs(evidence_items: list[Evidence]) -> list[str]:
    slugs: list[str] = []
    for item in evidence_items:
        if item.source_type != "wiki_page":
            continue
        slug = _first_string(
            item.metadata.get("weknora_wiki_page_slug"),
            item.metadata.get("wiki_page_slug"),
            item.metadata.get("slug"),
            item.wiki_page_id,
        )
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def _web_url_count(evidence_items: list[Evidence]) -> int:
    urls = {
        url
        for item in evidence_items
        if item.source_type == "web_search"
        for url in (
            _first_string(
                item.metadata.get("url"),
                item.metadata.get("weknora_url"),
                item.external_doc_id,
            ),
        )
        if url
    }
    return len(urls)


def _web_providers(evidence_items: list[Evidence]) -> list[str]:
    providers: list[str] = []
    for item in evidence_items:
        if item.source_type != "web_search":
            continue
        provider = _first_string(
            item.metadata.get("source"),
            item.metadata.get("weknora_source"),
            item.metadata.get("provider"),
        )
        if provider and provider not in providers:
            providers.append(provider)
    return providers


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


def _normalize_answer_mode(value: str | None) -> str:
    normalized = str(value or "qa").strip()
    return normalized if normalized in {"qa", "policy_analysis", "case_review"} else "qa"


def _answer_mode_query(query: str, answer_mode: str) -> str:
    if answer_mode == "policy_analysis":
        return (
            "请基于可检索到的资料库证据进行政策分析，按“政策要点、影响对象、风险提示、可执行建议”组织回答；"
            "如果证据不足，请明确说明不足之处。\n\n用户问题："
            f"{query}"
        )
    if answer_mode == "case_review":
        return (
            "请基于可检索到的资料库证据进行案例复盘，按“事实经过、关键问题、风险点、后续建议”组织回答；"
            "如果证据不足，请明确说明不足之处。\n\n用户问题："
            f"{query}"
        )
    return query


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _first_string(*values: Any) -> str | None:
    for value in values:
        text = _optional_str(value)
        if text:
            return text
    return None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
