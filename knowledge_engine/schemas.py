from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str | None
    external_doc_id: str | None
    title: str
    status: str
    source: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    document_id: str | None
    external_doc_id: str | None
    chunk_id: str | None
    title: str
    text: str
    score: float | None
    source: str
    metadata: dict = field(default_factory=dict)
    evidence_id: str | None = None
    source_type: str = "document_chunk"
    wiki_page_id: str | None = None


@dataclass(frozen=True)
class WikiPageSummary:
    slug: str
    title: str
    page_type: str
    summary: str
    source: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class WikiPage:
    slug: str
    title: str
    page_type: str
    summary: str
    content: str
    citations: list[Evidence] = field(default_factory=list)
    source: str = "mock"
    metadata: dict = field(default_factory=dict)
