import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import CitationRead
from app.schemas import ConversationMessageRead
from app.schemas import ConversationRead
from app.schemas import EvidenceRead
from app.schemas import GeneratedOutputRead
from app.schemas import NativeKnowledgeChatRequest
from app.schemas import NativeKnowledgeChatResponse
from app.schemas import NativeKnowledgeChatRuntime
from app.schemas import RagDebugError
from app.schemas import RagDebugEvidenceRead
from app.schemas import RagDebugRequest
from app.schemas import RagDebugResponse
from app.schemas import RagRetrieveRequest
from app.schemas import RagRetrieveResponse
from app.schemas import TaskRead
from app.services.native_chat_service import NativeKnowledgeChatError
from app.services.native_chat_service import run_native_knowledge_chat
from app.services.rag_service import retrieve_evidence_with_context
from knowledge_engine.errors import KnowledgeBackendUnavailableError
from knowledge_engine.errors import WeKnoraUnavailableError
from knowledge_engine.log_context import weknora_log_context
from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY
from knowledge_engine.retrieval import normalize_retrieval_options
from knowledge_engine.retrieval import retrieval_debug_trace
from knowledge_engine.schemas import Evidence

router = APIRouter(prefix="/api/rag", tags=["rag"])

DEBUG_SUMMARY_LIMIT = 180
DEBUG_VALUE_LIMIT = 120
DEBUG_QUERY_LIMIT = 500
DEBUG_LIST_LIMIT = 8
SENSITIVE_KEY_MARKERS = (
    "token",
    "api_key",
    "apikey",
    "secret",
    "authorization",
    "password",
    "credential",
)
DEBUG_METADATA_ALLOWLIST = {
    "business_area",
    "document_type",
    "source",
    "evidence_id",
    "score_semantics",
    "citation_source_type",
    "weknora_knowledge_base_id",
    "weknora_knowledge_id",
    "weknora_chunk_index",
    "weknora_start_at",
    "weknora_end_at",
    "weknora_seq",
    "weknora_match_type",
    "weknora_chunk_type",
    "weknora_sub_chunk_id",
    "weknora_parent_chunk_id",
    "weknora_wiki_page_id",
    "weknora_wiki_page_slug",
    "weknora_search_endpoint",
    "weknora_search_native",
    "weknora_native_rank",
    "slug",
    "page_type",
    "retrieval_debug_trace",
    "retrieval_options",
    "retrieval_rank",
    "raw_retrieval_rank",
    "score_display",
    "score_display_mode",
    "weknora_retrieval_options_forwarded",
    "current_run_corpus_id",
    "current_run_id",
    "current_run_isolated",
    "current_run_isolation_warnings",
    "current_run_namespace",
    "current_run_scope",
    "source_scope",
    "source_scope_warnings",
    "answer_bearing_matched_metadata",
    "answer_bearing_matched_terms",
    "answer_bearing_rank",
    "answer_bearing_rank_delta",
    "answer_bearing_raw_rank",
    "answer_bearing_score",
    "answer_bearing_strategy",
    "distractor_guard_decision",
    "distractor_guard_warnings",
}


@router.post("/retrieve", response_model=RagRetrieveResponse)
def retrieve_rag_evidence(request: RagRetrieveRequest) -> RagRetrieveResponse:
    with weknora_log_context(correlation_id=uuid4().hex):
        result = retrieve_evidence_with_context(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )
    return RagRetrieveResponse(
        items=[_to_read_model(evidence) for evidence in result.items],
        total=len(result.items),
        query=request.query,
        filters=result.filters,
        top_k=request.top_k,
        warnings=result.warnings,
    )


@router.post("/debug", response_model=RagDebugResponse)
def retrieve_rag_debug(request: RagDebugRequest) -> RagDebugResponse:
    trace_id = uuid4().hex
    query = _short_text(request.query, DEBUG_QUERY_LIMIT)
    filters = _sanitize_mapping(request.filters)
    retrieval_options = normalize_retrieval_options(
        request.filters.get(RETRIEVAL_OPTIONS_KEY)
    )
    debug_trace = retrieval_debug_trace(retrieval_options)
    requested_source_type = _optional_str(
        request.filters.get("source_type")
        or request.filters.get("source_scope")
        or request.filters.get("source")
        or request.filters.get("sourceType")
    )
    try:
        with weknora_log_context(correlation_id=trace_id):
            result = retrieve_evidence_with_context(
                query=request.query,
                filters=request.filters,
                top_k=request.top_k,
            )
            evidence_items = result.items
            filters = _sanitize_mapping(result.filters)
    except WeKnoraUnavailableError as exc:
        return RagDebugResponse(
            trace_id=trace_id,
            status="error",
            query=query,
            filters=filters,
            top_k=request.top_k,
            requested_source_type=requested_source_type,
            retrieval_options=retrieval_options,
            debug_trace=debug_trace,
            items=[],
            total=0,
            warnings=[],
            error=_to_debug_error(exc),
        )
    except KnowledgeBackendUnavailableError:
        return RagDebugResponse(
            trace_id=trace_id,
            status="error",
            query=query,
            filters=filters,
            top_k=request.top_k,
            requested_source_type=requested_source_type,
            retrieval_options=retrieval_options,
            debug_trace=debug_trace,
            items=[],
            total=0,
            warnings=[],
            error=RagDebugError(
                error_code="knowledge_backend_unavailable",
                message="Knowledge backend is unavailable.",
                retryable=True,
            ),
        )

    warnings: list[str] = list(result.warnings)
    sources = {item.source for item in evidence_items}
    if sources and sources != {"weknora_api"}:
        warnings.append(
            "Retrieve returned non-WeKnora evidence; check KNOWLEDGE_BACKEND and WeKnora configuration."
        )

    items = [
        _to_debug_item(rank=index + 1, evidence=evidence)
        for index, evidence in enumerate(evidence_items)
    ]
    return RagDebugResponse(
        trace_id=trace_id,
        status="ok",
        query=query,
        filters=filters,
        top_k=request.top_k,
        requested_source_type=requested_source_type,
        retrieval_options=retrieval_options,
        debug_trace=debug_trace,
        items=items,
        total=len(items),
        warnings=warnings,
    )


@router.post("/knowledge-chat", response_model=NativeKnowledgeChatResponse)
def run_knowledge_chat(
    request: NativeKnowledgeChatRequest,
    session: Session = Depends(get_session),
) -> NativeKnowledgeChatResponse:
    try:
        conversation, messages, task, output, citations, runtime = run_native_knowledge_chat(
            session=session,
            query=request.query,
            conversation_id=request.conversation_id,
            title=request.title,
            knowledge_base_ids=request.knowledge_base_ids,
            knowledge_ids=request.knowledge_ids,
            web_search_enabled=request.web_search_enabled,
            answer_mode=request.answer_mode,
            current_run=request.current_run,
        )
    except NativeKnowledgeChatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return NativeKnowledgeChatResponse(
        conversation=ConversationRead.model_validate(conversation),
        messages=[ConversationMessageRead.model_validate(message) for message in messages],
        task=TaskRead.model_validate(task),
        output=GeneratedOutputRead.model_validate(output),
        citations=[CitationRead.model_validate(citation) for citation in citations],
        runtime=NativeKnowledgeChatRuntime(**runtime),
    )


def _to_read_model(evidence: Evidence) -> EvidenceRead:
    return EvidenceRead(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        wiki_page_id=evidence.wiki_page_id,
        title=evidence.title,
        text=evidence.text,
        score=evidence.score,
        source=evidence.source,
        metadata=evidence.metadata,
    )


def _to_debug_item(rank: int, evidence: Evidence) -> RagDebugEvidenceRead:
    return RagDebugEvidenceRead(
        rank=rank,
        source_type=evidence.source_type,
        source=evidence.source,
        score=evidence.score,
        evidence_id=evidence.evidence_id,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        wiki_page_id=evidence.wiki_page_id,
        title=_short_text(evidence.title, DEBUG_VALUE_LIMIT),
        summary=_short_text(evidence.text, DEBUG_SUMMARY_LIMIT),
        metadata=_safe_debug_metadata(evidence.metadata),
    )


def _to_debug_error(exc: WeKnoraUnavailableError) -> RagDebugError:
    public = exc.to_public_dict()
    return RagDebugError(
        error_code=str(public.get("error_code") or "weknora_unavailable"),
        message=_short_text(str(public.get("message") or "WeKnora is unavailable."), 240),
        operation=_optional_str(public.get("operation")),
        retryable=bool(public.get("retryable")),
    )


def _safe_debug_metadata(metadata: dict) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key)
        if normalized_key not in DEBUG_METADATA_ALLOWLIST:
            continue
        safe[normalized_key] = _sanitize_debug_value(normalized_key, value)
    return safe


def _sanitize_mapping(value: dict) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in value.items():
        safe[str(key)] = _sanitize_debug_value(str(key), item)
    return safe


def _sanitize_debug_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _short_text(value, DEBUG_VALUE_LIMIT)
    if isinstance(value, (list, tuple, set)):
        return [
            _sanitize_debug_value(key, item)
            for item in list(value)[:DEBUG_LIST_LIMIT]
        ]
    if isinstance(value, dict):
        return {
            str(child_key): _sanitize_debug_value(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    return _short_text(str(value), DEBUG_VALUE_LIMIT)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower()
    return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)


def _short_text(value: str, limit: int) -> str:
    collapsed = " ".join(_redact_sensitive_text(str(value or "")).split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: max(limit - 3, 0)].rstrip()}..."


def _redact_sensitive_text(value: str) -> str:
    redacted = re.sub(
        r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [redacted]",
        value,
    )
    redacted = re.sub(
        r"(?i)(authorization|x-api-key|api[_-]?key|token|secret|password)(\s*[:=]\s*)\S+",
        r"\1\2[redacted]",
        redacted,
    )
    return re.sub(r"sk-[A-Za-z0-9_-]{12,}", "sk-[redacted]", redacted)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
