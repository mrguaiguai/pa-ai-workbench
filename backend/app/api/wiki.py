from typing import Annotated

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
from app.services.wiki_service import search_wiki_pages
from app.services.wiki_service import update_wiki_page_record
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
        wiki_citations=[_citation_record_to_read(citation) for citation in citations],
        source="wiki",
        metadata=page_metadata(page),
        created_by=page.created_by,
        published_at=page.published_at,
        embedding_status=page.embedding_status,
        vector_id=page.vector_id,
        indexed_at=page.indexed_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


def _wiki_page_to_read(page: WikiPage) -> WikiPageRead:
    metadata = page.metadata or {}
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
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
    )


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
        created_at=citation.get("created_at"),
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
