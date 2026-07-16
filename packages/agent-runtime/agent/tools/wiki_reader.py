from dataclasses import dataclass
from dataclasses import field
from typing import Any

from agent.schemas import Citation
from agent.tools.capability_guard import AgentCapabilityGuard
from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import WikiPage


@dataclass(frozen=True)
class WikiReadResult:
    slug: str
    title: str
    page_type: str
    summary: str
    content: str
    citations: list[Citation] = field(default_factory=list)
    source: str = "wiki"
    metadata: dict[str, Any] = field(default_factory=dict)


class WikiReadTool:
    def __init__(self, knowledge_engine: KnowledgeEngine | None = None) -> None:
        self.knowledge_engine = knowledge_engine or create_knowledge_engine()
        self.capabilities = AgentCapabilityGuard(self.knowledge_engine)

    def read(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiReadResult | None:
        normalized_slug = slug.strip()
        if not normalized_slug:
            return None
        self.capabilities.require("wiki_read")
        page = self.knowledge_engine.read_wiki_page(
            slug=normalized_slug,
            kb_id=kb_id,
        )
        if page is None:
            return None
        return self._to_result(page)

    @classmethod
    def _to_result(cls, page: WikiPage) -> WikiReadResult:
        return WikiReadResult(
            slug=page.slug,
            title=page.title,
            page_type=page.page_type,
            summary=page.summary,
            content=page.content,
            citations=[cls._to_citation(evidence) for evidence in page.citations],
            source=page.source,
            metadata=page.metadata,
        )

    @staticmethod
    def _to_citation(evidence: Evidence) -> Citation:
        return Citation(
            document_id=evidence.document_id,
            external_doc_id=evidence.external_doc_id,
            chunk_id=evidence.chunk_id,
            title=evidence.title,
            text=evidence.text,
            score=evidence.score,
            source=evidence.source,
            metadata=evidence.metadata,
            evidence_id=evidence.evidence_id,
            source_type=evidence.source_type,
            wiki_page_id=evidence.wiki_page_id,
        )
