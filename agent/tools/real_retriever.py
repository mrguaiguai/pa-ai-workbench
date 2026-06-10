from typing import Any

from agent.schemas import Citation
from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.evidence import normalize_evidence_results
from knowledge_engine.factory import create_knowledge_engine
from knowledge_engine.schemas import Evidence


class RealRetrieverTool:
    def __init__(
        self,
        knowledge_engine: KnowledgeEngine | None = None,
        default_top_k: int = 8,
    ) -> None:
        self.knowledge_engine = knowledge_engine or create_knowledge_engine()
        self.default_top_k = default_top_k

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
        source_type: str | None = None,
    ) -> list[Citation]:
        if not query.strip():
            return []
        resolved_filters = self._build_filters(filters=filters, source_type=source_type)
        resolved_top_k = max(self.default_top_k if top_k is None else top_k, 0)
        evidence_items = normalize_evidence_results(
            self.knowledge_engine.retrieve(
                query=query,
                filters=resolved_filters,
                top_k=max(resolved_top_k * 2, resolved_top_k),
            ),
            top_k=resolved_top_k,
        )
        return [self._to_citation(evidence) for evidence in evidence_items]

    @staticmethod
    def _build_filters(
        filters: dict[str, Any] | None,
        source_type: str | None,
    ) -> dict[str, Any]:
        resolved = {
            key: value
            for key, value in (filters or {}).items()
            if value is not None
        }
        if source_type and "source_type" not in resolved:
            resolved["source_type"] = source_type
        return resolved

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
