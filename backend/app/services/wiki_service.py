import json
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app import pathing as _pathing  # noqa: F401
from app.models import utc_now
from app.models import WikiCitation
from app.models import WikiPage as WikiPageModel
from app.schemas import WikiCitationPayload
from app.schemas import WikiPageCreateRequest
from app.schemas import WikiPageUpdateRequest
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary
from knowledge_engine.wiki import WikiPageStatus


class WikiPageConflictError(Exception):
    pass


class WikiPageNotFoundError(Exception):
    pass


def search_wiki_page_records(
    session: Session,
    query: str = "",
    limit: int = 10,
) -> list[WikiPageModel]:
    statement = select(WikiPageModel).order_by(WikiPageModel.updated_at.desc())
    pages = list(session.exec(statement).all())
    normalized_query = query.strip().lower()
    if normalized_query:
        pages = [
            page
            for page in pages
            if normalized_query in page.slug.lower()
            or normalized_query in page.title.lower()
            or normalized_query in (page.summary or "").lower()
            or normalized_query in page.content_markdown.lower()
        ]
    return pages[:limit]


def get_wiki_page_record(session: Session, slug: str) -> WikiPageModel | None:
    statement = select(WikiPageModel).where(WikiPageModel.slug == slug)
    return session.exec(statement).first()


def list_wiki_citation_records(
    session: Session,
    wiki_page_id: str,
) -> list[WikiCitation]:
    statement = (
        select(WikiCitation)
        .where(WikiCitation.wiki_page_id == wiki_page_id)
        .order_by(WikiCitation.created_at)
    )
    return list(session.exec(statement).all())


def create_wiki_page_record(
    session: Session,
    payload: WikiPageCreateRequest,
) -> WikiPageModel:
    slug = _normalize_slug(payload.slug)
    if get_wiki_page_record(session, slug) is not None:
        raise WikiPageConflictError(f"Wiki page already exists: {slug}")

    page = WikiPageModel(
        slug=slug,
        title=_normalize_title(payload.title),
        summary=payload.summary,
        content_markdown=payload.content_markdown,
        tags_json=_to_json(payload.tags),
        business_area=payload.business_area,
        page_type=payload.page_type,
        source_output_id=payload.source_output_id,
        source_document_ids_json=_to_json(payload.source_document_ids),
        source_citation_ids_json=_to_json(payload.source_citation_ids),
        created_by=payload.created_by,
        metadata_json=_to_json(payload.metadata),
    )
    session.add(page)
    session.flush()
    _replace_wiki_citations(session, page.id, payload.citations)
    session.commit()
    session.refresh(page)
    return page


def update_wiki_page_record(
    session: Session,
    slug: str,
    payload: WikiPageUpdateRequest,
) -> WikiPageModel:
    page = get_wiki_page_record(session, slug)
    if page is None:
        raise WikiPageNotFoundError(f"Wiki page not found: {slug}")

    updates = payload.model_dump(exclude_unset=True)
    for field_name in (
        "title",
        "summary",
        "content_markdown",
        "business_area",
        "page_type",
        "source_output_id",
        "created_by",
    ):
        if field_name in updates:
            value = updates[field_name]
            if field_name == "title" and isinstance(value, str):
                value = _normalize_title(value)
            setattr(page, field_name, value)

    if "tags" in updates:
        page.tags_json = _to_json(updates["tags"] or [])
    if "source_document_ids" in updates:
        page.source_document_ids_json = _to_json(updates["source_document_ids"] or [])
    if "source_citation_ids" in updates:
        page.source_citation_ids_json = _to_json(updates["source_citation_ids"] or [])
    if "metadata" in updates:
        page.metadata_json = _to_json(updates["metadata"] or {})
    if "citations" in updates:
        _replace_wiki_citations(session, page.id, payload.citations or [])

    page.updated_at = utc_now()
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def publish_wiki_page_record(session: Session, slug: str) -> WikiPageModel:
    page = get_wiki_page_record(session, slug)
    if page is None:
        raise WikiPageNotFoundError(f"Wiki page not found: {slug}")

    if page.status == WikiPageStatus.PUBLISHED:
        return page

    now = utc_now()
    page.status = WikiPageStatus.PUBLISHED
    page.published_at = page.published_at or now
    page.updated_at = now
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def search_wiki_pages(
    query: str,
    kb_id: str | None = None,
    limit: int = 10,
) -> list[WikiPageSummary]:
    engine = create_knowledge_engine()
    return engine.search_wiki(query=query, kb_id=kb_id, limit=limit)


def read_wiki_page(slug: str, kb_id: str | None = None) -> WikiPage | None:
    engine = create_knowledge_engine()
    return engine.read_wiki_page(slug=slug, kb_id=kb_id)


def page_tags(page: WikiPageModel) -> list[str]:
    value = _from_json(page.tags_json, default=[])
    return value if isinstance(value, list) else []


def page_source_document_ids(page: WikiPageModel) -> list[str]:
    value = _from_json(page.source_document_ids_json, default=[])
    return value if isinstance(value, list) else []


def page_source_citation_ids(page: WikiPageModel) -> list[str]:
    value = _from_json(page.source_citation_ids_json, default=[])
    return value if isinstance(value, list) else []


def page_metadata(page: WikiPageModel) -> dict[str, Any]:
    value = _from_json(page.metadata_json, default={})
    return value if isinstance(value, dict) else {}


def citation_metadata(citation: WikiCitation) -> dict[str, Any]:
    value = _from_json(citation.metadata_json, default={})
    return value if isinstance(value, dict) else {}


def _replace_wiki_citations(
    session: Session,
    wiki_page_id: str,
    citations: list[WikiCitationPayload],
) -> None:
    for existing in list_wiki_citation_records(session, wiki_page_id):
        session.delete(existing)
    session.flush()
    for payload in citations:
        session.add(_citation_payload_to_model(wiki_page_id, payload))


def _citation_payload_to_model(
    wiki_page_id: str,
    payload: WikiCitationPayload,
) -> WikiCitation:
    return WikiCitation(
        wiki_page_id=wiki_page_id,
        document_id=payload.document_id,
        external_doc_id=payload.external_doc_id,
        chunk_id=payload.chunk_id,
        output_id=payload.output_id,
        citation_id=payload.citation_id,
        evidence_id=payload.evidence_id,
        source_type=payload.source_type,
        excerpt=payload.excerpt,
        score=payload.score,
        metadata_json=_to_json(payload.metadata),
    )


def _normalize_slug(slug: str) -> str:
    normalized = slug.strip()
    if not normalized:
        raise ValueError("Wiki page slug must not be empty.")
    return normalized


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise ValueError("Wiki page title must not be empty.")
    return normalized


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _from_json(value: str | None, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
