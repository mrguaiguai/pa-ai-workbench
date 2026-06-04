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
from app.services.wiki_service import get_wiki_page_record
from app.services.wiki_service import list_wiki_citation_records
from app.services.wiki_service import page_metadata
from app.services.wiki_service import page_source_citation_ids
from app.services.wiki_service import page_source_document_ids
from app.services.wiki_service import page_tags
from app.services.wiki_service import publish_wiki_page_record
from app.services.wiki_service import read_wiki_page
from app.services.wiki_service import search_wiki_page_records
from app.services.wiki_service import search_wiki_pages
from app.services.wiki_service import update_wiki_page_record
from app.services.wiki_service import WikiDraftSourceNotFoundError
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
    page_records = search_wiki_page_records(session=session, query=query, limit=limit)
    if page_records:
        return WikiSearchResponse(
            items=[_page_record_to_summary(page) for page in page_records],
            total=len(page_records),
        )

    pages = search_wiki_pages(query=query, kb_id=kb_id, limit=limit)
    return WikiSearchResponse(
        items=[_mock_page_to_summary(page) for page in pages],
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
    page_record = get_wiki_page_record(session=session, slug=slug)
    if page_record is not None:
        return _page_record_to_read(session=session, page=page_record)

    page = read_wiki_page(slug=slug, kb_id=kb_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return _mock_page_to_read(page)


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


def _page_record_to_summary(page: WikiPageModel) -> WikiPageSummaryRead:
    return WikiPageSummaryRead(
        id=page.id,
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        status=page.status,
        tags=page_tags(page),
        source="wiki",
        metadata=page_metadata(page),
    )


def _mock_page_to_summary(page: WikiPageSummary) -> WikiPageSummaryRead:
    return WikiPageSummaryRead(
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        source=page.source,
        metadata=page.metadata,
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


def _mock_page_to_read(page: WikiPage) -> WikiPageRead:
    return WikiPageRead(
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        content=page.content,
        content_markdown=page.content,
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
        source=page.source,
        metadata=page.metadata,
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
