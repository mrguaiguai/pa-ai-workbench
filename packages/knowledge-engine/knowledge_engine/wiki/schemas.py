from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import StrEnum
from typing import Any


class WikiPageStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WikiCitationSourceType(StrEnum):
    DOCUMENT_CHUNK = "document_chunk"
    WIKI_PAGE = "wiki_page"


@dataclass(frozen=True)
class WikiPageRecord:
    id: str
    slug: str
    title: str
    content_markdown: str
    status: str = WikiPageStatus.DRAFT
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    business_area: str | None = None
    page_type: str | None = None
    source_output_id: str | None = None
    source_document_ids: list[str] = field(default_factory=list)
    source_citation_ids: list[str] = field(default_factory=list)
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
    embedding_status: str = "pending"
    vector_id: str | None = None
    indexed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WikiCitationRecord:
    id: str
    wiki_page_id: str
    source_type: str
    excerpt: str
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    output_id: str | None = None
    citation_id: str | None = None
    evidence_id: str | None = None
    score: float | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
