from typing import Any

from agent.schemas import Citation
from agent.tools.capability_guard import AgentCapabilityGuard
from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.current_run import apply_current_run_isolation
from knowledge_engine.current_run import attach_current_run_warnings
from knowledge_engine.current_run import current_run_fetch_top_k
from knowledge_engine.current_run import prepare_current_run_filters
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
        self.capabilities = AgentCapabilityGuard(self.knowledge_engine)
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
        self.capabilities.require("rag_retrieve")
        resolved_filters = self._build_filters(filters=filters, source_type=source_type)
        resolved_top_k = max(self.default_top_k if top_k is None else top_k, 0)
        prepared = prepare_current_run_filters(resolved_filters)
        raw_items = self.knowledge_engine.retrieve(
            query=query,
            filters=prepared.filters,
            top_k=current_run_fetch_top_k(resolved_top_k, prepared.scope),
        )
        isolated = apply_current_run_isolation(raw_items, prepared.scope)
        warnings = [*prepared.warnings, *isolated.warnings]
        evidence_items = normalize_evidence_results(
            attach_current_run_warnings(isolated.items, warnings),
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
