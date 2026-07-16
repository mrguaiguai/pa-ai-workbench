from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(frozen=True)
class CitationBinding:
    evidence_id: str
    source_type: str
    title: str
    text: str
    document_id: str | None = None
    external_doc_id: str | None = None
    chunk_id: str | None = None
    wiki_page_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
