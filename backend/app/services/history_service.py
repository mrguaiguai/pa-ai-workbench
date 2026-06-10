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
    warning_count: int
    evidence_state: str


def list_history(
    session: Session,
    query: str | None = None,
    task_type: str | None = None,
    status: str | None = None,
    citation_source: str | None = None,
    source_type: str | None = None,
    evidence_state: str | None = None,
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
            has_warnings=has_warnings,
        )
    ]


def history_output_summary(session: Session, output: GeneratedOutput) -> HistoryOutputSummary:
    citations = list_output_citations(session, output.id)
    warning_count = _warning_count(output.warnings_json)
    weknora_count = sum(1 for citation in citations if _citation_source(citation) == "weknora_api")
    mock_count = sum(1 for citation in citations if _citation_source(citation) == "mock")
    document_count = sum(1 for citation in citations if _citation_source_type(citation) == "document_chunk")
    wiki_count = sum(1 for citation in citations if _citation_source_type(citation) == "wiki_page")
    return {
        "citation_count": len(citations),
        "weknora_citation_count": weknora_count,
        "mock_citation_count": mock_count,
        "document_citation_count": document_count,
        "wiki_citation_count": wiki_count,
        "warning_count": warning_count,
        "evidence_state": _evidence_state(citations, weknora_count, mock_count),
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


def _warning_count(warnings_json: str | None) -> int:
    if not warnings_json:
        return 0
    try:
        parsed = json.loads(warnings_json)
    except json.JSONDecodeError:
        return 1
    if isinstance(parsed, list):
        return len(parsed)
    if isinstance(parsed, dict):
        return len(parsed) or 1
    return 1 if str(parsed).strip() else 0


def _evidence_state(citations: list[Citation], weknora_count: int, mock_count: int) -> str:
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


def _normalize_source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or "unknown"


__all__ = ["get_output", "history_output_summary", "list_history", "list_output_citations"]
