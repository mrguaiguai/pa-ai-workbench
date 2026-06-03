from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from app.schemas import EvidenceRead
from app.schemas import WikiPageRead
from app.schemas import WikiPageSummaryRead
from app.schemas import WikiSearchResponse
from app.services.wiki_service import read_wiki_page
from app.services.wiki_service import search_wiki_pages

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


@router.get("/search", response_model=WikiSearchResponse)
def search_wiki(
    query: str = Query(default=""),
    kb_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> WikiSearchResponse:
    pages = search_wiki_pages(query=query, kb_id=kb_id, limit=limit)
    return WikiSearchResponse(
        items=[
            WikiPageSummaryRead(
                slug=page.slug,
                title=page.title,
                page_type=page.page_type,
                summary=page.summary,
                source=page.source,
                metadata=page.metadata,
            )
            for page in pages
        ],
        total=len(pages),
    )


@router.get("/pages/{slug}", response_model=WikiPageRead)
def read_wiki(slug: str, kb_id: str | None = None) -> WikiPageRead:
    page = read_wiki_page(slug=slug, kb_id=kb_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return WikiPageRead(
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        content=page.content,
        citations=[
            EvidenceRead(
                document_id=citation.document_id,
                external_doc_id=citation.external_doc_id,
                chunk_id=citation.chunk_id,
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

