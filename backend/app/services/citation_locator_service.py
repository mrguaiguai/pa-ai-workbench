import json
from typing import Any
from urllib.parse import quote
from urllib.parse import urlencode

from sqlmodel import Session
from sqlmodel import select

from app.models import Citation
from app.models import Document
from app.models import DocumentChunk
from app.models import WikiCitation
from app.models import WikiPage
from app.schemas import CitationLocateRequest
from app.schemas import CitationLocateResponse


def locate_citation(
    session: Session,
    request: CitationLocateRequest,
) -> CitationLocateResponse:
    payload = _payload_from_request(session=session, request=request)
    source_type = _source_type(payload)
    if source_type == "wiki_page":
        return _locate_wiki_page(session=session, payload=payload)
    if source_type == "document_chunk":
        return _locate_document_chunk(session=session, payload=payload)
    return _unavailable(
        "Citation is missing source_type; cannot determine a document or Wiki target."
    )


def _payload_from_request(
    session: Session,
    request: CitationLocateRequest,
) -> dict[str, Any]:
    metadata = _metadata_from_request(request)
    payload: dict[str, Any] = {
        "id": request.id,
        "document_id": request.document_id,
        "external_doc_id": request.external_doc_id,
        "chunk_id": request.chunk_id,
        "evidence_id": request.evidence_id,
        "source_type": request.source_type,
        "wiki_page_id": request.wiki_page_id,
        "source": request.source,
        "metadata": metadata,
    }
    if request.id:
        citation = session.get(Citation, request.id)
        if citation is not None:
            payload.update(
                {
                    "id": citation.id,
                    "document_id": citation.document_id,
                    "external_doc_id": citation.external_doc_id,
                    "chunk_id": citation.chunk_id,
                    "source": citation.source,
                    "metadata": _json_object(citation.metadata_json),
                }
            )
        wiki_citation = session.get(WikiCitation, request.id)
        if wiki_citation is not None:
            payload.update(
                {
                    "id": wiki_citation.id,
                    "document_id": wiki_citation.document_id,
                    "external_doc_id": wiki_citation.external_doc_id,
                    "chunk_id": wiki_citation.chunk_id,
                    "evidence_id": wiki_citation.evidence_id,
                    "source_type": wiki_citation.source_type,
                    "wiki_page_id": wiki_citation.wiki_page_id,
                    "metadata": _json_object(wiki_citation.metadata_json),
                }
            )
    return _hydrate_payload(payload)


def _hydrate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    binding = metadata.get("citation_binding")
    binding = binding if isinstance(binding, dict) else {}
    payload["wiki_slug"] = _first_string(
        metadata.get("slug"),
        metadata.get("weknora_slug"),
        metadata.get("weknora_wiki_page_slug"),
        metadata.get("wiki_page_slug"),
        metadata.get("page_slug"),
    )
    for key in (
        "evidence_id",
        "source_type",
        "wiki_page_id",
        "document_id",
        "external_doc_id",
        "chunk_id",
    ):
        payload[key] = _first_string(payload.get(key), binding.get(key), metadata.get(key))
    payload["source_type"] = _source_type(payload)
    return payload


def _locate_document_chunk(
    session: Session,
    payload: dict[str, Any],
) -> CitationLocateResponse:
    document = _find_document(session=session, payload=payload)
    if document is None:
        return _unavailable(
            "Citation cannot be located because the source document is not in PA."
        )
    chunk = _find_chunk(session=session, document=document, payload=payload)
    chunk_id = _first_string(payload.get("chunk_id"), chunk.id if chunk else None)
    if not chunk_id:
        return _unavailable("Citation cannot be located because chunk_id is missing.")
    if chunk is None and document.knowledge_backend != "weknora_api":
        return _unavailable("Citation cannot be located because the chunk is missing.")
    params = {"document": document.id}
    params["chunk"] = chunk_id
    return CitationLocateResponse(
        located=True,
        target_type="document_chunk",
        route="/library",
        ui_hash=f"#/library?{urlencode(params)}",
        message="Open document preview and focus the cited chunk.",
        document_id=document.id,
        external_doc_id=document.external_doc_id or payload.get("external_doc_id"),
        chunk_id=chunk_id,
        chunk_index=chunk.chunk_index if chunk else None,
    )


def _locate_wiki_page(
    session: Session,
    payload: dict[str, Any],
) -> CitationLocateResponse:
    page = _find_wiki_page(session=session, payload=payload)
    slug = _first_string(page.slug if page else None, payload.get("wiki_slug"))
    if not slug:
        return _unavailable("Citation cannot be located because the Wiki slug is missing.")
    return CitationLocateResponse(
        located=True,
        target_type="wiki_page",
        route="/wiki",
        ui_hash=f"#/wiki?slug={quote(slug, safe='')}",
        message="Open the cited Wiki page.",
        wiki_page_id=page.id if page else payload.get("wiki_page_id"),
        wiki_slug=slug,
    )


def _find_document(session: Session, payload: dict[str, Any]) -> Document | None:
    document_id = _first_string(payload.get("document_id"))
    if document_id:
        document = session.get(Document, document_id)
        if document is not None:
            return document
    external_doc_id = _first_string(payload.get("external_doc_id"))
    if external_doc_id:
        statement = select(Document).where(Document.external_doc_id == external_doc_id)
        return session.exec(statement).first()
    return None


def _find_chunk(
    session: Session,
    document: Document,
    payload: dict[str, Any],
) -> DocumentChunk | None:
    chunk_id = _first_string(payload.get("chunk_id"))
    if not chunk_id:
        return None
    statement = select(DocumentChunk).where(
        DocumentChunk.document_id == document.id,
        DocumentChunk.id == chunk_id,
    )
    chunk = session.exec(statement).first()
    if chunk is not None:
        return chunk
    statement = select(DocumentChunk).where(
        DocumentChunk.document_id == document.id,
        DocumentChunk.vector_id == chunk_id,
    )
    return session.exec(statement).first()


def _find_wiki_page(session: Session, payload: dict[str, Any]) -> WikiPage | None:
    page_id = _first_string(payload.get("wiki_page_id"))
    if page_id:
        page = session.get(WikiPage, page_id)
        if page is not None:
            return page
    slug = _first_string(payload.get("wiki_slug"))
    if slug:
        statement = select(WikiPage).where(WikiPage.slug == slug)
        return session.exec(statement).first()
    return None


def _metadata_from_request(request: CitationLocateRequest) -> dict[str, Any]:
    metadata = dict(request.metadata or {})
    if request.metadata_json:
        metadata.update(_json_object(request.metadata_json))
    return metadata


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _source_type(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    raw = (
        payload.get("source_type")
        or metadata.get("citation_source_type")
        or metadata.get("source_type")
        or ("wiki_page" if payload.get("wiki_page_id") or payload.get("wiki_slug") else None)
        or ("document_chunk" if payload.get("chunk_id") else None)
    )
    normalized = str(raw or "").strip().lower()
    if normalized in {"document", "document_chunk", "chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki_page", "wiki-page"}:
        return "wiki_page"
    return normalized


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _unavailable(message: str) -> CitationLocateResponse:
    return CitationLocateResponse(
        located=False,
        target_type=None,
        route=None,
        ui_hash=None,
        message=message,
    )
