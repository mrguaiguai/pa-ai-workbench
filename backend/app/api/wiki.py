from datetime import UTC
from datetime import datetime
from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlmodel import Session

from app.database import get_session
from app.models import WikiCitation
from app.models import WikiPage as WikiPageModel
from app.schemas import EvidenceRead
from app.schemas import WikiCitationRead
from app.schemas import WikiDraftFromOutputRequest
from app.schemas import WikiPageCreateRequest
from app.schemas import WikiPageRead
from app.schemas import WikiPageSummaryRead
from app.schemas import WikiPageUpdateRequest
from app.schemas import WikiSearchResponse
from app.services.wiki_service import citation_metadata
from app.services.wiki_service import create_wiki_draft_from_output
from app.services.wiki_service import create_wiki_page_record
from app.services.wiki_service import index_wiki_page_record
from app.services.wiki_service import list_wiki_citation_records
from app.services.wiki_service import page_metadata
from app.services.wiki_service import page_source_citation_ids
from app.services.wiki_service import page_source_document_ids
from app.services.wiki_service import page_tags
from app.services.wiki_service import publish_wiki_page_record
from app.services.wiki_service import read_wiki_page
from app.services.wiki_service import recover_wiki_page_status
from app.services.wiki_service import refresh_wiki_page_status
from app.services.wiki_service import search_wiki_pages
from app.services.wiki_service import update_wiki_page_record
from app.services.wiki_service import wiki_status_summary
from app.services.wiki_service import WikiDraftSourceNotFoundError
from app.services.wiki_service import WikiPageIndexError
from app.services.wiki_service import WikiPageConflictError
from app.services.wiki_service import WikiPageNotFoundError
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/search", response_model=WikiSearchResponse)
def search_wiki(
    session: Annotated[Session, Depends(get_session)],
    query: str = Query(default=""),
    kb_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> WikiSearchResponse:
    pages = search_wiki_pages(
        session=session,
        query=query,
        kb_id=kb_id,
        limit=limit,
    )
    if not pages:
        pages = search_wiki_pages(query=query, kb_id=kb_id, limit=limit)
    return WikiSearchResponse(
        items=[_wiki_summary_to_read(page) for page in pages],
        total=len(pages),
    )


@router.post(
    "/pages",
    response_model=WikiPageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_wiki(
    payload: WikiPageCreateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page = create_wiki_page_record(session=session, payload=payload)
    except WikiPageConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.post(
    "/drafts/from-output/{output_id}",
    response_model=WikiPageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_wiki_draft_from_output_api(
    output_id: str,
    session: Annotated[Session, Depends(get_session)],
    payload: WikiDraftFromOutputRequest | None = None,
) -> WikiPageRead:
    try:
        page = create_wiki_draft_from_output(
            session=session,
            output_id=output_id,
            payload=payload,
        )
    except WikiDraftSourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.get("/pages/{slug}", response_model=WikiPageRead)
def read_wiki(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
    kb_id: str | None = None,
) -> WikiPageRead:
    page = read_wiki_page(slug=slug, kb_id=kb_id, session=session)
    if page is None:
        page = read_wiki_page(slug=slug, kb_id=kb_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return _wiki_page_to_read(page)


@router.put("/pages/{slug}", response_model=WikiPageRead)
def update_wiki(
    slug: str,
    payload: WikiPageUpdateRequest,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page = update_wiki_page_record(session=session, slug=slug, payload=payload)
    except WikiPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.post("/pages/{slug}/publish", response_model=WikiPageRead)
def publish_wiki(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page = publish_wiki_page_record(session=session, slug=slug)
    except WikiPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.post("/pages/{slug}/refresh-status", response_model=WikiPageRead)
def refresh_wiki_status(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page = refresh_wiki_page_status(session=session, slug=slug)
    except WikiPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.post("/pages/{slug}/recover-status", response_model=WikiPageRead)
def recover_wiki_status(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page, _message = recover_wiki_page_status(session=session, slug=slug)
    except WikiPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


@router.post("/pages/{slug}/reindex", response_model=WikiPageRead)
def reindex_wiki(
    slug: str,
    session: Annotated[Session, Depends(get_session)],
) -> WikiPageRead:
    try:
        page = index_wiki_page_record(session=session, slug=slug)
    except WikiPageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WikiPageIndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _page_record_to_read(session=session, page=page)


def _wiki_summary_to_read(page: WikiPageSummary) -> WikiPageSummaryRead:
    metadata = page.metadata or {}
    tags = metadata.get("tags")
    return WikiPageSummaryRead(
        id=metadata.get("id"),
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        status=metadata.get("status"),
        tags=tags if isinstance(tags, list) else [],
        source=page.source,
        metadata=metadata,
    )


def _page_record_to_read(session: Session, page: WikiPageModel) -> WikiPageRead:
    citations = list_wiki_citation_records(session=session, wiki_page_id=page.id)
    wiki_citations = [_citation_record_to_read(citation) for citation in citations]
    metadata = {
        **page_metadata(page),
        "source_output_id": page.source_output_id,
        "source_document_ids": page_source_document_ids(page),
        "source_citation_ids": page_source_citation_ids(page),
        "wiki_citations": [
            _citation_record_to_metadata(citation) for citation in citations
        ],
    }
    status_summary = wiki_status_summary(page)
    return WikiPageRead(
        id=page.id,
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        content=page.content_markdown,
        content_markdown=page.content_markdown,
        status=page.status,
        tags=page_tags(page),
        business_area=page.business_area,
        source_output_id=page.source_output_id,
        source_document_ids=page_source_document_ids(page),
        source_citation_ids=page_source_citation_ids(page),
        citations=[_citation_record_to_evidence(page, citation) for citation in citations],
        wiki_citations=wiki_citations,
        source="wiki",
        metadata=metadata,
        created_by=page.created_by,
        published_at=page.published_at,
        embedding_status=page.embedding_status,
        vector_id=page.vector_id,
        indexed_at=page.indexed_at,
        **status_summary,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


def _wiki_page_to_read(page: WikiPage) -> WikiPageRead:
    metadata = _normalized_wiki_page_metadata(page)
    wiki_retrievable = bool(metadata.get("weknora_retrievable") or page.source == "weknora_api")
    wiki_state = str(
        metadata.get("wiki_state")
        or ("retrievable" if wiki_retrievable else "unknown")
    )
    wiki_message = str(
        metadata.get("wiki_message")
        or (
            "Wiki page was returned by WeKnora."
            if wiki_retrievable
            else "Wiki page status is unknown."
        )
    )
    return WikiPageRead(
        id=metadata.get("id"),
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        content=page.content,
        content_markdown=page.content,
        status=metadata.get("status"),
        tags=_metadata_list(metadata, "tags"),
        business_area=metadata.get("business_area"),
        source_output_id=metadata.get("source_output_id"),
        source_document_ids=_metadata_list(metadata, "source_document_ids"),
        source_citation_ids=_metadata_list(metadata, "source_citation_ids"),
        citations=[
            EvidenceRead(
                evidence_id=citation.evidence_id,
                source_type=citation.source_type,
                document_id=citation.document_id,
                external_doc_id=citation.external_doc_id,
                chunk_id=citation.chunk_id,
                wiki_page_id=citation.wiki_page_id,
                title=citation.title,
                text=citation.text,
                score=citation.score,
                source=citation.source,
                metadata=citation.metadata,
            )
            for citation in page.citations
        ],
        wiki_citations=[
            _wiki_citation_metadata_to_read(citation)
            for citation in _metadata_list(metadata, "wiki_citations")
            if isinstance(citation, dict)
        ],
        source=page.source,
        metadata=metadata,
        created_by=metadata.get("created_by"),
        published_at=metadata.get("published_at"),
        embedding_status=metadata.get("embedding_status"),
        vector_id=metadata.get("vector_id"),
        indexed_at=metadata.get("indexed_at"),
        wiki_state=wiki_state,
        wiki_message=wiki_message,
        wiki_next_action=metadata.get("wiki_next_action") or ("ask" if wiki_retrievable else "refresh"),
        wiki_retryable=bool(metadata.get("wiki_retryable")),
        wiki_retrievable=wiki_retrievable,
        wiki_index_timed_out=bool(metadata.get("wiki_index_timed_out")),
        wiki_processing_seconds=0,
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
    )


def _citation_record_to_metadata(citation: WikiCitation) -> dict:
    return {
        "id": citation.id,
        "wiki_page_id": citation.wiki_page_id,
        "document_id": citation.document_id,
        "external_doc_id": citation.external_doc_id,
        "chunk_id": citation.chunk_id,
        "output_id": citation.output_id,
        "citation_id": citation.citation_id,
        "evidence_id": citation.evidence_id,
        "source_type": citation.source_type,
        "excerpt": citation.excerpt,
        "score": citation.score,
        "metadata": citation_metadata(citation),
        "created_at": citation.created_at,
    }


def _normalized_wiki_page_metadata(page: WikiPage) -> dict:
    metadata = dict(page.metadata or {})
    source_output_id = _first_string(
        metadata.get("source_output_id"),
        metadata.get("pa_source_output_id"),
    )
    source_refs = _unique_strings(
        metadata.get("source_refs"),
        metadata.get("weknora_source_refs"),
    )
    chunk_refs = _unique_strings(
        metadata.get("chunk_refs"),
        metadata.get("weknora_chunk_refs"),
    )
    source_document_ids = _unique_strings(
        metadata.get("source_document_ids"),
        metadata.get("pa_source_document_ids"),
        _source_ids_from_refs(source_refs),
    )
    source_citation_ids = _unique_strings(
        metadata.get("source_citation_ids"),
        metadata.get("pa_source_citation_ids"),
    )
    wiki_citations = [
        citation
        for citation in _metadata_list(metadata, "wiki_citations")
        if isinstance(citation, dict)
    ]
    if not wiki_citations:
        wiki_citations = _wiki_reference_citations(
            page=page,
            metadata=metadata,
            source_output_id=source_output_id,
            source_refs=source_refs,
            chunk_refs=chunk_refs,
            source_citation_ids=source_citation_ids,
        )

    if source_output_id:
        metadata["source_output_id"] = source_output_id
    metadata["source_document_ids"] = source_document_ids
    metadata["source_citation_ids"] = source_citation_ids
    if source_refs:
        metadata["source_refs"] = source_refs
    if chunk_refs:
        metadata["chunk_refs"] = chunk_refs
    metadata["wiki_citations"] = wiki_citations
    return metadata


def _wiki_reference_citations(
    page: WikiPage,
    metadata: dict,
    source_output_id: str | None,
    source_refs: list[str],
    chunk_refs: list[str],
    source_citation_ids: list[str],
) -> list[dict]:
    ref_count = max(len(source_refs), len(chunk_refs), len(source_citation_ids))
    if ref_count == 0:
        return []

    wiki_page_id = _first_string(
        metadata.get("id"),
        metadata.get("pa_wiki_page_id"),
        metadata.get("wiki_page_id"),
        page.slug,
    )
    created_at = _first_datetime(
        metadata.get("created_at"),
        metadata.get("updated_at"),
        metadata.get("published_at"),
    )
    citations: list[dict] = []
    for index in range(ref_count):
        source_ref = source_refs[index] if index < len(source_refs) else None
        external_doc_id, source_title = _split_source_ref(source_ref)
        chunk_id = chunk_refs[index] if index < len(chunk_refs) else None
        citation_id = (
            source_citation_ids[index] if index < len(source_citation_ids) else None
        )
        evidence_id = f"document_chunk:{chunk_id}" if chunk_id else None
        citations.append(
            {
                "id": citation_id or evidence_id or f"wiki_ref:{wiki_page_id}:{index + 1}",
                "wiki_page_id": wiki_page_id,
                "external_doc_id": external_doc_id,
                "chunk_id": chunk_id,
                "output_id": source_output_id,
                "citation_id": citation_id,
                "evidence_id": evidence_id,
                "source_type": "document_chunk" if chunk_id or external_doc_id else "wiki_page",
                "excerpt": _reference_excerpt(
                    source_title=source_title,
                    external_doc_id=external_doc_id,
                    chunk_id=chunk_id,
                    citation_id=citation_id,
                ),
                "metadata": {
                    "reference_only": True,
                    "source_ref": source_ref,
                    "source_title": source_title,
                    "weknora_ref_index": index,
                },
                "created_at": created_at,
            }
        )
    return citations


def _metadata_list(metadata: dict, key: str) -> list:
    value = metadata.get(key)
    return value if isinstance(value, list) else []


def _wiki_citation_metadata_to_read(citation: dict) -> WikiCitationRead:
    return WikiCitationRead(
        id=str(citation.get("id") or ""),
        wiki_page_id=str(citation.get("wiki_page_id") or ""),
        document_id=citation.get("document_id"),
        external_doc_id=citation.get("external_doc_id"),
        chunk_id=citation.get("chunk_id"),
        output_id=citation.get("output_id"),
        citation_id=citation.get("citation_id"),
        evidence_id=citation.get("evidence_id"),
        source_type=str(citation.get("source_type") or "document_chunk"),
        excerpt=str(citation.get("excerpt") or ""),
        score=citation.get("score"),
        metadata=citation.get("metadata") if isinstance(citation.get("metadata"), dict) else {},
        created_at=_first_datetime(citation.get("created_at")),
    )


def _citation_record_to_read(citation: WikiCitation) -> WikiCitationRead:
    return WikiCitationRead(
        id=citation.id,
        wiki_page_id=citation.wiki_page_id,
        document_id=citation.document_id,
        external_doc_id=citation.external_doc_id,
        chunk_id=citation.chunk_id,
        output_id=citation.output_id,
        citation_id=citation.citation_id,
        evidence_id=citation.evidence_id,
        source_type=citation.source_type,
        excerpt=citation.excerpt,
        score=citation.score,
        metadata=citation_metadata(citation),
        created_at=citation.created_at,
    )


def _citation_record_to_evidence(
    page: WikiPageModel,
    citation: WikiCitation,
) -> EvidenceRead:
    return EvidenceRead(
        evidence_id=citation.evidence_id,
        source_type=citation.source_type,
        document_id=citation.document_id,
        external_doc_id=citation.external_doc_id,
        chunk_id=citation.chunk_id,
        wiki_page_id=page.id,
        title=page.title,
        text=citation.excerpt,
        score=citation.score,
        source="wiki",
        metadata=citation_metadata(citation),
    )


def _first_string(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _unique_strings(*values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
            return
        text = str(value).strip()
        if not text or text in seen:
            return
        seen.add(text)
        result.append(text)

    for value in values:
        add(value)
    return result


def _source_ids_from_refs(source_refs: list[str]) -> list[str]:
    ids: list[str] = []
    for ref in source_refs:
        source_id, _ = _split_source_ref(ref)
        if source_id:
            ids.append(source_id)
    return ids


def _split_source_ref(source_ref: str | None) -> tuple[str | None, str | None]:
    if not source_ref:
        return None, None
    source_id, _, title = source_ref.partition("|")
    return _first_string(source_id), _first_string(title)


def _reference_excerpt(
    source_title: str | None,
    external_doc_id: str | None,
    chunk_id: str | None,
    citation_id: str | None,
) -> str:
    if source_title:
        return source_title
    if chunk_id:
        return f"WeKnora chunk reference: {chunk_id}"
    if external_doc_id:
        return f"WeKnora source reference: {external_doc_id}"
    if citation_id:
        return f"PA citation reference: {citation_id}"
    return "Wiki source reference"


def _first_datetime(*values: Any) -> datetime:
    for value in values:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return datetime.now(UTC)
