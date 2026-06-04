from typing import Any

from agent.schemas import Citation
from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence


class RetrieverTool:
    def __init__(self, knowledge_engine: KnowledgeEngine | None = None) -> None:
        self.knowledge_engine = knowledge_engine or create_knowledge_engine()

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 8,
    ) -> list[Citation]:
        evidence_items = self.knowledge_engine.retrieve(
            query=query,
            filters=filters,
            top_k=top_k,
        )
        return [self._to_citation(evidence) for evidence in evidence_items]

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
