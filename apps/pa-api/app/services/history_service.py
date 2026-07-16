import json
from typing import Any
from typing import TypedDict

from sqlmodel import Session
from sqlmodel import select

from app.models import Citation
from app.models import GeneratedOutput
from app.services.generation_service import get_output
from app.services.generation_service import list_output_citations


class HistoryOutputSummary(TypedDict):
    citation_count: int
    weknora_citation_count: int
    mock_citation_count: int
    document_citation_count: int
    wiki_citation_count: int
    web_search_citation_count: int
    traceable_citation_count: int
    warning_count: int
    evidence_state: str
    wnid_capability: str | None
    wnid_capabilities: list[str]
    wnid_evidence_state: str
    evidence_source_types: list[str]
    citation_blocked: bool
    citation_blocker: str | None


def list_history(
    session: Session,
    query: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    citation_source: str | None = None,
    source_type: str | None = None,
    evidence_state: str | None = None,
    wnid_capability: str | None = None,
    wnid_evidence_state: str | None = None,
    has_warnings: bool | None = None,
) -> list[GeneratedOutput]:
    statement = select(GeneratedOutput).order_by(GeneratedOutput.created_at.desc())
    outputs = list(session.exec(statement).all())
    return [
        output
        for output in outputs
        if _matches_history_filters(
            session=session,
            output=output,
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
    ]


def history_output_summary(session: Session, output: GeneratedOutput) -> HistoryOutputSummary:
    citations = list_output_citations(session, output.id)
    warnings = _warning_messages(output.warnings_json)
    citation_blocker = _citation_blocker(warnings)
    weknora_count = sum(1 for citation in citations if _is_weknora_citation(citation))
    mock_count = sum(1 for citation in citations if _citation_source(citation) == "mock")
    document_count = sum(1 for citation in citations if _citation_source_type(citation) == "document_chunk")
    wiki_count = sum(1 for citation in citations if _citation_source_type(citation) == "wiki_page")
    web_search_count = sum(1 for citation in citations if _citation_source_type(citation) == "web_search")
    traceable_count = sum(1 for citation in citations if _citation_traceable(citation))
    citation_blocked = citation_blocker is not None
    source_types = _citation_source_types(citations)
    wnid_capability = _wnid_capability(output, source_types=source_types, warnings=warnings)
    return {
        "citation_count": len(citations),
        "weknora_citation_count": weknora_count,
        "mock_citation_count": mock_count,
        "document_citation_count": document_count,
        "wiki_citation_count": wiki_count,
        "web_search_citation_count": web_search_count,
        "traceable_citation_count": traceable_count,
        "warning_count": len(warnings),
        "evidence_state": _evidence_state(
            citations=citations,
            weknora_count=weknora_count,
            mock_count=mock_count,
            citation_blocked=citation_blocked,
        ),
        "wnid_capability": wnid_capability,
        "wnid_capabilities": _wnid_capabilities(output, primary=wnid_capability),
        "wnid_evidence_state": _wnid_evidence_state(
            output=output,
            citations=citations,
            traceable_count=traceable_count,
            citation_blocked=citation_blocked,
            source_types=source_types,
            warnings=warnings,
        ),
        "evidence_source_types": source_types,
        "citation_blocked": citation_blocked,
        "citation_blocker": citation_blocker,
    }


def _matches_history_filters(
    session: Session,
    output: GeneratedOutput,
    query: str | None,
    task_type: str | None,
    status: str | None,
    citation_source: str | None,
    source_type: str | None,
    evidence_state: str | None,
    wnid_capability: str | None,
    wnid_evidence_state: str | None,
    has_warnings: bool | None,
) -> bool:
    if query and not _matches_query(output, query):
        return False
    if task_type and task_type != "all" and output.task_type != task_type:
        return False
    if status and status != "all" and output.status != status:
        return False

    citations = list_output_citations(session, output.id)
    summary = history_output_summary(session, output)

    if citation_source and citation_source != "all":
        if citation_source == "none":
            if citations:
                return False
        elif not any(_citation_source(citation) == citation_source for citation in citations):
            return False
    if source_type and source_type != "all":
        normalized_source_type = _normalize_source_type(source_type)
        if normalized_source_type == "unknown":
            if any(_citation_source_type(citation) != "unknown" for citation in citations):
                return False
        elif not any(_citation_source_type(citation) == normalized_source_type for citation in citations):
            return False
    if evidence_state and evidence_state != "all" and summary["evidence_state"] != evidence_state:
        return False
    if (
        wnid_capability
        and wnid_capability != "all"
        and wnid_capability not in summary["wnid_capabilities"]
    ):
        return False
    if (
        wnid_evidence_state
        and wnid_evidence_state != "all"
        and summary["wnid_evidence_state"] != wnid_evidence_state
    ):
        return False
    if has_warnings is not None and (summary["warning_count"] > 0) != has_warnings:
        return False
    return True


def _matches_query(output: GeneratedOutput, query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return True
    haystack = " ".join(
        value
        for value in [
            output.title,
            output.task_type,
            output.status,
            output.content_markdown or "",
            _short_json_text(output.content_json),
        ]
        if value
    ).lower()
    return normalized in haystack


def _short_json_text(value: str | None) -> str:
    if not value:
        return ""
    return value[:1000]


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _warning_messages(warnings_json: str | None) -> list[str]:
    if not warnings_json:
        return []
    try:
        parsed = json.loads(warnings_json)
    except json.JSONDecodeError:
        return [warnings_json] if warnings_json.strip() else []
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        if not parsed:
            return []
        return [f"{key}: {value}" for key, value in parsed.items()]
    normalized = str(parsed).strip()
    return [normalized] if normalized else []


def _citation_blocker(warnings: list[str]) -> str | None:
    for warning in warnings:
        normalized = warning.strip()
        lower = normalized.lower()
        if "citation_blocked" in lower or "no traceable references" in lower:
            return normalized
    return None


def _evidence_state(
    citations: list[Citation],
    weknora_count: int,
    mock_count: int,
    citation_blocked: bool,
) -> str:
    if citation_blocked:
        return "citation_blocked"
    if not citations:
        return "no_evidence"
    if weknora_count and mock_count:
        return "mixed"
    if weknora_count:
        return "weknora"
    if mock_count == len(citations):
        return "mock_only"
    return "other"


def _citation_metadata(citation: Citation) -> dict[str, Any]:
    if not citation.metadata_json:
        return {}
    try:
        metadata = json.loads(citation.metadata_json)
    except json.JSONDecodeError:
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _citation_binding(citation: Citation) -> dict[str, Any]:
    binding = _citation_metadata(citation).get("citation_binding")
    return binding if isinstance(binding, dict) else {}


def _citation_source(citation: Citation) -> str:
    metadata = _citation_metadata(citation)
    binding = _citation_binding(citation)
    value = binding.get("source") or metadata.get("source") or citation.source
    normalized = str(value or "").strip().lower()
    return normalized or "unknown"


def _is_weknora_citation(citation: Citation) -> bool:
    source = _citation_source(citation)
    if source in {"weknora", "weknora_api"}:
        return True
    if source == "mock":
        return False
    return _citation_traceable(citation)


def _citation_source_type(citation: Citation) -> str:
    metadata = _citation_metadata(citation)
    binding = _citation_binding(citation)
    value = (
        binding.get("source_type")
        or metadata.get("citation_source_type")
        or metadata.get("source_type")
        or ("document_chunk" if citation.chunk_id else None)
        or ("wiki_page" if binding.get("wiki_page_id") or metadata.get("wiki_page_id") else None)
    )
    return _normalize_source_type(value)


def _citation_traceable(citation: Citation) -> bool:
    metadata = _citation_metadata(citation)
    binding = _citation_binding(citation)
    evidence_id = _first_string(binding.get("evidence_id"), metadata.get("evidence_id"))
    source_type = _citation_source_type(citation)
    if source_type == "wiki_page":
        return bool(
            evidence_id
            and _first_string(
                binding.get("wiki_page_id"),
                metadata.get("wiki_page_id"),
                metadata.get("weknora_wiki_page_id"),
                metadata.get("weknora_wiki_page_slug"),
                metadata.get("wiki_page_slug"),
            )
        )
    if source_type == "document_chunk":
        return bool(
            evidence_id
            and citation.chunk_id
            and (citation.document_id or citation.external_doc_id)
        )
    if source_type == "web_search":
        return bool(
            evidence_id
            and _first_string(
                binding.get("locator"),
                binding.get("url"),
                metadata.get("url"),
                metadata.get("weknora_url"),
                metadata.get("source_url"),
                citation.external_doc_id,
            )
        )
    return False


def _normalize_source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    if normalized in {"web", "web_search", "web-search", "search_result"}:
        return "web_search"
    return normalized or "unknown"


def _citation_source_types(citations: list[Citation]) -> list[str]:
    return sorted({_citation_source_type(citation) for citation in citations})


def _wnid_capability(
    output: GeneratedOutput,
    *,
    source_types: list[str],
    warnings: list[str],
) -> str | None:
    if output.task_type == "native_knowledge_chat":
        return "quick_qa"
    if output.task_type == "native_mcp_tool_execution":
        return "mcp_tools"
    if output.task_type != "native_agentqa":
        return None

    content = _json_object(output.content_json)
    warning_text = " ".join(warnings).lower()
    if (
        "web_search" in source_types
        or int(content.get("web_reference_count") or 0) > 0
        or "web_search_reference_blocked" in warning_text
    ):
        return "web_search"
    if (
        "wiki_page" in source_types
        or int(content.get("wiki_reference_count") or 0) > 0
        or "wiki_reference_blocked" in warning_text
    ):
        return "wiki_mode"
    return "react_agentqa"


def _wnid_capabilities(output: GeneratedOutput, *, primary: str | None) -> list[str]:
    capabilities: list[str] = []
    if output.task_type == "native_agentqa":
        capabilities.append("react_agentqa")
    if primary and primary not in capabilities:
        capabilities.append(primary)
    return capabilities


def _wnid_evidence_state(
    *,
    output: GeneratedOutput,
    citations: list[Citation],
    traceable_count: int,
    citation_blocked: bool,
    source_types: list[str],
    warnings: list[str],
) -> str:
    if output.task_type == "native_mcp_tool_execution":
        return "mcp_audited" if output.status == "completed" else "mcp_blocked"
    warning_text = " ".join(warnings).lower()
    if "web_search_reference_blocked" in warning_text:
        return "web_search_blocked"
    if "wiki_reference_blocked" in warning_text:
        return "wiki_blocked"
    if citation_blocked:
        return "citation_blocked"
    if "web_search" in source_types and traceable_count > 0:
        return "web_search_traceable"
    if "wiki_page" in source_types and traceable_count > 0:
        return "wiki_traceable"
    if "document_chunk" in source_types and traceable_count > 0:
        return "document_traceable"
    if citations and traceable_count > 0:
        return "traceable"
    return "no_evidence"


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


__all__ = ["get_output", "history_output_summary", "list_history", "list_output_citations"]
