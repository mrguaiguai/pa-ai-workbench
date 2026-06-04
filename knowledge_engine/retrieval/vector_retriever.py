from typing import Any

from knowledge_engine.citations import CitationBuilder
from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.retrieval.schemas import RetrieveRequest
from knowledge_engine.schemas import Evidence
from knowledge_engine.vectorstores import VectorSearchRequest
from knowledge_engine.vectorstores import VectorSearchResult
from knowledge_engine.vectorstores import VectorStore


class VectorRetriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        citation_builder: CitationBuilder | None = None,
        source: str = "extracted",
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.citation_builder = citation_builder or CitationBuilder()
        self.source = source

    def retrieve(self, request: RetrieveRequest) -> list[Evidence]:
        query = request.normalized_query
        if not query or request.top_k <= 0:
            return []

        query_embedding = self.embedding_provider.embed_text(query)
        results = self.vector_store.search(
            VectorSearchRequest(
                query_vector=query_embedding.vector,
                top_k=request.top_k,
                filters=self._document_filters(request.filters),
                score_threshold=request.score_threshold,
            )
        )
        return self.citation_builder.build_many(
            [self._to_evidence(result) for result in results]
        )

    @staticmethod
    def _document_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
        normalized = {
            key: value
            for key, value in (filters or {}).items()
            if value is not None and key != "source_type"
        }
        return {**normalized, "source_type": "document"}

    def _to_evidence(self, result: VectorSearchResult) -> Evidence:
        metadata = result.record.metadata
        return Evidence(
            document_id=self._optional_str(metadata.get("document_id")),
            external_doc_id=self._optional_str(metadata.get("external_doc_id")),
            chunk_id=self._optional_str(metadata.get("chunk_id")),
            title=str(
                metadata.get("title")
                or metadata.get("document_title")
                or "Untitled evidence"
            ),
            text=result.record.text,
            score=result.score,
            source=self.source,
            metadata=self._evidence_metadata(metadata),
            source_type=self._evidence_source_type(metadata),
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value)
        return text or None

    @staticmethod
    def _evidence_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return dict(metadata)

    @staticmethod
    def _evidence_source_type(metadata: dict[str, Any]) -> str:
        raw = str(metadata.get("source_type") or "").strip().lower()
        if raw in {"document", "document_chunk", "chunk"}:
            return "document_chunk"
        if raw in {"wiki", "wiki_page", "wiki-page"}:
            return "wiki_page"
        return raw or "document_chunk"
