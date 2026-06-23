from dataclasses import replace
from typing import Any

from knowledge_engine.citations import CitationBuilder
from knowledge_engine.citations.builder import CitationBindingError
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary


EXTRACTED_SOURCE = "extracted"
SCHEMA_ADAPTER = "extracted_schema_parity_m3_b1"
SCHEMA_PARITY_TARGET = "weknora_api_pa_schema"


def normalize_extracted_document(document: KnowledgeDocument) -> KnowledgeDocument:
    return replace(
        document,
        source=EXTRACTED_SOURCE,
        metadata=_metadata(document.metadata),
    )


def normalize_extracted_status(status: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(status)
    raw_status = str(normalized.get("status") or "unknown")
    normalized["source"] = EXTRACTED_SOURCE
    normalized.setdefault("message", f"Extracted document status: {raw_status}")
    normalized.setdefault("failed_step", None)
    normalized.setdefault("error_message", None)
    normalized["metadata"] = _metadata(normalized.get("metadata"))
    return normalized


def normalize_extracted_chunk_preview(chunk: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(chunk)
    normalized["source"] = EXTRACTED_SOURCE
    metadata = _metadata(normalized.get("metadata"), source_type="document_chunk")
    if normalized.get("id") not in (None, ""):
        metadata.setdefault("extracted_chunk_id", normalized.get("id"))
    if normalized.get("external_doc_id") not in (None, ""):
        metadata.setdefault("extracted_external_doc_id", normalized.get("external_doc_id"))
    normalized["metadata"] = metadata
    return normalized


def normalize_extracted_evidence(evidence: Evidence) -> Evidence:
    source_type = _source_type(evidence.source_type or evidence.metadata.get("source_type"))
    chunk_id = _optional_str(evidence.chunk_id)
    wiki_page_id = _optional_str(evidence.wiki_page_id) or _optional_str(
        evidence.metadata.get("wiki_page_id") or evidence.metadata.get("slug")
    )
    evidence_id = (
        _optional_str(evidence.evidence_id)
        or _optional_str(evidence.metadata.get("evidence_id"))
        or _evidence_id(source_type, chunk_id, wiki_page_id)
    )
    metadata = _metadata(evidence.metadata, source_type=source_type)
    metadata["citation_source_type"] = source_type
    metadata["source_type"] = source_type
    metadata["score_semantics"] = (
        "local_vector_cosine" if evidence.score is not None else "unavailable"
    )
    if evidence_id:
        metadata["evidence_id"] = evidence_id
    if chunk_id:
        metadata.setdefault("extracted_chunk_id", chunk_id)
    if evidence.external_doc_id:
        metadata.setdefault("extracted_external_doc_id", evidence.external_doc_id)
    if wiki_page_id:
        metadata.setdefault("wiki_page_id", wiki_page_id)
        metadata.setdefault("extracted_wiki_page_id", wiki_page_id)

    normalized = replace(
        evidence,
        source=EXTRACTED_SOURCE,
        metadata=metadata,
        evidence_id=evidence_id,
        source_type=source_type,
        wiki_page_id=wiki_page_id,
    )
    return _ensure_citation_binding(normalized)


def normalize_extracted_wiki_summary(summary: WikiPageSummary) -> WikiPageSummary:
    return replace(
        summary,
        source=EXTRACTED_SOURCE,
        metadata=_wiki_metadata(summary.metadata, summary.slug),
    )


def normalize_extracted_wiki_page(page: WikiPage) -> WikiPage:
    page_id = _wiki_page_id(page)
    metadata = _wiki_metadata(page.metadata, page.slug, page_id=page_id)
    return replace(
        page,
        source=EXTRACTED_SOURCE,
        citations=[normalize_extracted_evidence(citation) for citation in page.citations],
        metadata=metadata,
    )


def extracted_wiki_fallback_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    slug: str,
    page_id: str | None = None,
    status: str = "draft",
    operation: str = "create",
) -> dict[str, Any]:
    normalized = _wiki_metadata(metadata or {}, slug, page_id=page_id)
    published = status == "published"
    sync_pending = published or operation in {"update", "publish", "index"}
    normalized["status"] = status
    normalized["wiki_state"] = "sync_pending" if sync_pending else "draft"
    normalized["wiki_message"] = (
        "Local extracted Wiki page is published locally and waiting for WeKnora sync."
        if sync_pending
        else "Local extracted Wiki draft is not searchable by WeKnora."
    )
    normalized["wiki_next_action"] = "sync_weknora" if sync_pending else "publish"
    normalized["wiki_retryable"] = False
    normalized["wiki_retrievable"] = False
    normalized["weknora_retrievable"] = False
    normalized["weknora_sync_status"] = "pending" if sync_pending else "not_synced"
    normalized["weknora_sync_operation"] = operation
    normalized["weknora_index_status"] = "not_synced"
    normalized["sync_conflict_status"] = normalized.get("sync_conflict_status") or "none"
    normalized["local_publish_state"] = status
    return normalized


def wiki_page_to_extracted_evidence(page: WikiPage) -> Evidence:
    normalized_page = normalize_extracted_wiki_page(page)
    page_id = _wiki_page_id(normalized_page)
    metadata = _wiki_metadata(normalized_page.metadata, normalized_page.slug, page_id=page_id)
    metadata["citation_source_type"] = "wiki_page"
    metadata["source_type"] = "wiki_page"
    evidence_id = f"wiki_page:{page_id}"
    metadata["evidence_id"] = evidence_id
    return normalize_extracted_evidence(
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            title=normalized_page.title or normalized_page.slug or "Untitled wiki page",
            text=normalized_page.content or normalized_page.summary,
            score=None,
            source=EXTRACTED_SOURCE,
            metadata=metadata,
            evidence_id=evidence_id,
            source_type="wiki_page",
            wiki_page_id=page_id,
        )
    )


def _ensure_citation_binding(evidence: Evidence) -> Evidence:
    binding = evidence.metadata.get("citation_binding")
    binding_metadata = binding.get("metadata") if isinstance(binding, dict) else None
    if (
        isinstance(binding, dict)
        and isinstance(binding_metadata, dict)
        and binding_metadata.get("source") == EXTRACTED_SOURCE
    ):
        return evidence
    try:
        return CitationBuilder().build(evidence)
    except CitationBindingError:
        return evidence


def _metadata(
    value: object,
    *,
    source_type: str | None = None,
) -> dict[str, Any]:
    metadata = dict(value) if isinstance(value, dict) else {}
    metadata["source"] = EXTRACTED_SOURCE
    metadata["backend"] = EXTRACTED_SOURCE
    metadata["fallback_backend"] = EXTRACTED_SOURCE
    metadata["fallback_explicit"] = True
    metadata["data_fact_source"] = "local_extracted"
    metadata["schema_adapter"] = SCHEMA_ADAPTER
    metadata["schema_parity"] = SCHEMA_PARITY_TARGET
    if source_type:
        metadata["source_type"] = source_type
        metadata["citation_source_type"] = source_type
    return metadata


def _wiki_metadata(
    value: object,
    slug: str,
    *,
    page_id: str | None = None,
) -> dict[str, Any]:
    metadata = _metadata(value, source_type="wiki_page")
    resolved_page_id = page_id or _optional_str(metadata.get("wiki_page_id")) or slug
    metadata.setdefault("wiki_page_id", resolved_page_id)
    metadata.setdefault("extracted_wiki_page_id", resolved_page_id)
    metadata.setdefault("slug", slug)
    return metadata


def _wiki_page_id(page: WikiPage) -> str:
    return (
        _optional_str(page.metadata.get("wiki_page_id"))
        or _optional_str(page.metadata.get("id"))
        or _optional_str(page.metadata.get("slug"))
        or page.slug
    )


def _source_type(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized or "document_chunk"


def _evidence_id(
    source_type: str,
    chunk_id: str | None,
    wiki_page_id: str | None,
) -> str | None:
    if source_type == "document_chunk" and chunk_id:
        return f"document_chunk:{chunk_id}"
    if source_type == "wiki_page" and wiki_page_id:
        return f"wiki_page:{wiki_page_id}"
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
