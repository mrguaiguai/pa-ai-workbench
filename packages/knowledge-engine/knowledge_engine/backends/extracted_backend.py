from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import NoReturn
from uuid import uuid4

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.chunking import Chunker
from knowledge_engine.chunking import DocumentChunkCandidate
from knowledge_engine.chunking import ParagraphChunker
from knowledge_engine.citations import CitationBuilder
from knowledge_engine.backends.extracted_schema import EXTRACTED_SOURCE
from knowledge_engine.backends.extracted_schema import extracted_wiki_fallback_metadata
from knowledge_engine.backends.extracted_schema import normalize_extracted_chunk_preview
from knowledge_engine.backends.extracted_schema import normalize_extracted_document
from knowledge_engine.backends.extracted_schema import normalize_extracted_evidence
from knowledge_engine.backends.extracted_schema import normalize_extracted_status
from knowledge_engine.backends.extracted_schema import normalize_extracted_wiki_page
from knowledge_engine.backends.extracted_schema import normalize_extracted_wiki_summary
from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.embeddings.factory import get_embedding_provider
from knowledge_engine.embeddings.schemas import EmbeddingVector
from knowledge_engine.errors import KnowledgeDocumentNotFoundError
from knowledge_engine.parsers import DocumentParser
from knowledge_engine.parsers import DocumentParseError
from knowledge_engine.parsers import FileDocumentParser
from knowledge_engine.parsers import ParsedDocument
from knowledge_engine.retrieval import RetrieveRequest
from knowledge_engine.retrieval import VectorRetriever
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary
from knowledge_engine.vectorstores import VectorStore
from knowledge_engine.vectorstores import VectorRecord
from knowledge_engine.vectorstores import get_vector_store
from knowledge_engine.wiki import InMemoryWikiStore
from knowledge_engine.wiki import WikiStore


@dataclass(frozen=True)
class ExtractedBackendComponents:
    document_parser: DocumentParser | None = None
    chunker: Chunker | None = None
    vector_store: VectorStore | None = None
    retriever: VectorRetriever | None = None
    citation_builder: CitationBuilder | None = None
    wiki_store: WikiStore | None = None


@dataclass(frozen=True)
class ExtractedBackendConfig:
    source: str = "extracted"
    backend_name: str = "extracted"
    metadata: dict = field(default_factory=dict)


class ExtractedKnowledgeBackend(KnowledgeEngine):
    """Scaffold for the Phase 2 Python-native Knowledge Engine backend."""

    def __init__(
        self,
        config: ExtractedBackendConfig | None = None,
        components: ExtractedBackendComponents | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.config = config or ExtractedBackendConfig()
        self.components = components or ExtractedBackendComponents()
        self.document_parser = self.components.document_parser or FileDocumentParser()
        self.chunker = self.components.chunker or ParagraphChunker()
        self.vector_store = self.components.vector_store or get_vector_store()
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.citation_builder = self.components.citation_builder or CitationBuilder()
        self.wiki_store = self.components.wiki_store or InMemoryWikiStore()
        self.retriever = self.components.retriever or VectorRetriever(
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store,
            citation_builder=self.citation_builder,
            source=self.config.source,
        )
        self._documents: dict[str, KnowledgeDocument] = {}

    def health(self) -> dict:
        embedding_config = getattr(self.embedding_provider, "config", None)
        return {
            "status": "ok",
            "backend": self.config.backend_name,
            "source": EXTRACTED_SOURCE,
            "fallback_backend": EXTRACTED_SOURCE,
            "fallback_explicit": True,
            "storage": "in_memory_scaffold",
            "documents": len(self._documents),
            "pipeline": self._pipeline_status(),
            "embedding": {
                "provider": getattr(embedding_config, "provider", "unknown"),
                "model": getattr(embedding_config, "model_name", "unknown"),
            },
        }

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        path = Path(file_path)
        external_doc_id = f"extracted_doc_{uuid4().hex[:12]}"
        document = KnowledgeDocument(
            document_id=metadata.get("document_id"),
            external_doc_id=external_doc_id,
            title=metadata.get("title") or path.name,
            status="uploaded",
            source=self.config.source,
            metadata={
                **metadata,
                "file_path": str(path),
                "pipeline_stage": "uploaded",
                "storage": "in_memory_scaffold",
            },
        )
        document = normalize_extracted_document(document)
        self._documents[external_doc_id] = document
        return document

    def get_document_status(self, external_doc_id: str) -> dict:
        document = self._documents.get(external_doc_id)
        if document is None:
            return normalize_extracted_status(
                {
                    "external_doc_id": external_doc_id,
                    "status": "not_found",
                    "source": self.config.source,
                    "message": "Extracted document status: not_found",
                }
            )
        return normalize_extracted_status(
            {
                "external_doc_id": external_doc_id,
                "status": document.status,
                "source": self.config.source,
                "message": f"Extracted document status: {document.status}",
                "failed_step": document.metadata.get("failed_step"),
                "error_message": document.metadata.get("error_message"),
                "metadata": document.metadata,
            }
        )

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        evidence_items = self.retriever.retrieve(
            RetrieveRequest(
                query=query,
                filters=filters or {},
                top_k=top_k,
            )
        )
        return [normalize_extracted_evidence(evidence) for evidence in evidence_items]

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        if self.wiki_store is None:
            return []
        return [
            normalize_extracted_wiki_summary(summary)
            for summary in self.wiki_store.search(query=query, kb_id=kb_id, limit=limit)
        ]

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        if self.wiki_store is None:
            return None
        page = self.wiki_store.read(slug=slug, kb_id=kb_id)
        if page is None:
            return None
        return normalize_extracted_wiki_page(page)

    def parse_document(self, external_doc_id: str) -> dict:
        return self._parse_registered_document(external_doc_id).to_dict()

    def chunk_document(self, external_doc_id: str) -> dict:
        parsed = self._parse_registered_document(external_doc_id)
        chunks = self.chunker.chunk(parsed)
        return {
            "external_doc_id": external_doc_id,
            "status": "chunked",
            "source": EXTRACTED_SOURCE,
            "chunk_count": len(chunks),
            "metadata": normalize_extracted_status({"status": "chunked"}).get("metadata"),
            "chunks": [
                normalize_extracted_chunk_preview(
                    {
                        **chunk.to_dict(),
                        "id": f"{external_doc_id}:chunk:{chunk.chunk_index}",
                        "external_doc_id": external_doc_id,
                        "source": EXTRACTED_SOURCE,
                    }
                )
                for chunk in chunks
            ],
        }

    def _parse_registered_document(self, external_doc_id: str) -> ParsedDocument:
        document = self._documents.get(external_doc_id)
        if document is None:
            raise KnowledgeDocumentNotFoundError(
                f"Document is not registered in extracted backend: {external_doc_id}"
            )
        file_path = document.metadata.get("file_path")
        if not file_path:
            raise DocumentParseError(
                f"Document has no file_path metadata: {external_doc_id}"
            )
        parsed = self.document_parser.parse(str(file_path), metadata=document.metadata)
        return parsed

    def index_document(self, external_doc_id: str) -> dict:
        parsed = self._parse_registered_document(external_doc_id)
        chunks = self.chunker.chunk(parsed)
        document = self._documents[external_doc_id]
        old_vector_ids = [
            str(vector_id)
            for vector_id in document.metadata.get("vector_ids", [])
            if vector_id
        ]

        records = self._build_vector_records(
            external_doc_id=external_doc_id,
            document=document,
            chunks=chunks,
        )
        self.vector_store.upsert(records)
        self._delete_old_vectors_after_reindex(
            old_vector_ids=old_vector_ids,
            current_vector_ids=[record.id for record in records],
        )

        updated_metadata = {
            **document.metadata,
            "pipeline_stage": "indexed",
            "chunk_count": len(chunks),
            "vector_count": len(records),
            "vector_ids": [record.id for record in records],
        }
        self._documents[external_doc_id] = normalize_extracted_document(
            KnowledgeDocument(
                document_id=document.document_id,
                external_doc_id=document.external_doc_id,
                title=document.title,
                status="indexed",
                source=document.source,
                metadata=updated_metadata,
            )
        )
        return normalize_extracted_status(
            {
                "external_doc_id": external_doc_id,
                "status": "indexed",
                "source": EXTRACTED_SOURCE,
                "chunk_count": len(chunks),
                "vector_count": len(records),
                "vector_ids": [record.id for record in records],
            }
        )

    def reindex_document(self, external_doc_id: str) -> dict:
        return self.index_document(external_doc_id)

    def list_document_chunks(self, external_doc_id: str) -> list[dict]:
        parsed = self._parse_registered_document(external_doc_id)
        chunks = self.chunker.chunk(parsed)
        return [
            normalize_extracted_chunk_preview(
                {
                    **chunk.to_dict(),
                    "id": f"{external_doc_id}:chunk:{chunk.chunk_index}",
                    "external_doc_id": external_doc_id,
                    "source": EXTRACTED_SOURCE,
                    "metadata": {
                        **chunk.metadata,
                        "source": EXTRACTED_SOURCE,
                        "external_doc_id": external_doc_id,
                    },
                }
            )
            for chunk in chunks
        ]

    def create_wiki_draft(self, output_id: str, metadata: dict | None = None) -> WikiPage:
        self._raise_pending("create_wiki_draft", "I4")

    def create_wiki_page(
        self,
        payload: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        slug = self._wiki_slug(payload)
        page = WikiPage(
            slug=slug,
            title=str(payload.get("title") or "Untitled"),
            page_type=str(payload.get("page_type") or payload.get("type") or "wiki"),
            summary=str(payload.get("summary") or ""),
            content=str(payload.get("content") or payload.get("content_markdown") or ""),
            citations=self._wiki_payload_citations(payload),
            source=EXTRACTED_SOURCE,
            metadata=extracted_wiki_fallback_metadata(
                self._wiki_payload_metadata(payload, kb_id=kb_id),
                slug=slug,
                page_id=self._wiki_page_id(payload, slug),
                status=str(payload.get("status") or "draft"),
                operation="create",
            ),
        )
        return self._upsert_wiki_page(page)

    def update_wiki_page(
        self,
        slug: str,
        payload: dict,
        kb_id: str | None = None,
    ) -> WikiPage:
        current = self.read_wiki_page(slug, kb_id=kb_id)
        current_metadata = current.metadata if current is not None else {}
        current_status = str(current_metadata.get("status") or "draft")
        page = WikiPage(
            slug=slug.strip(),
            title=str(payload.get("title") or (current.title if current else "Untitled")),
            page_type=str(
                payload.get("page_type")
                or payload.get("type")
                or (current.page_type if current else "wiki")
            ),
            summary=str(payload.get("summary") or (current.summary if current else "")),
            content=str(
                payload.get("content")
                or payload.get("content_markdown")
                or (current.content if current else "")
            ),
            citations=(
                self._wiki_payload_citations(payload)
                if "citations" in payload
                else (current.citations if current else [])
            ),
            source=EXTRACTED_SOURCE,
            metadata=extracted_wiki_fallback_metadata(
                {
                    **current_metadata,
                    **self._wiki_payload_metadata(payload, kb_id=kb_id),
                },
                slug=slug.strip(),
                page_id=self._wiki_page_id(payload, slug.strip(), current_metadata),
                status=str(payload.get("status") or current_status),
                operation="update",
            ),
        )
        return self._upsert_wiki_page(page)

    def publish_wiki_page(self, slug: str) -> WikiPage:
        current = self.read_wiki_page(slug)
        if current is None:
            raise KnowledgeDocumentNotFoundError(f"Wiki page is not registered: {slug}")
        published = WikiPage(
            slug=current.slug,
            title=current.title,
            page_type=current.page_type,
            summary=current.summary,
            content=current.content,
            citations=current.citations,
            source=EXTRACTED_SOURCE,
            metadata=extracted_wiki_fallback_metadata(
                current.metadata,
                slug=current.slug,
                page_id=self._wiki_page_id({}, current.slug, current.metadata),
                status="published",
                operation="publish",
            ),
        )
        return self._upsert_wiki_page(published)

    def index_wiki_page(self, slug: str) -> dict:
        current = self.read_wiki_page(slug)
        if current is None:
            raise KnowledgeDocumentNotFoundError(f"Wiki page is not registered: {slug}")
        metadata = extracted_wiki_fallback_metadata(
            current.metadata,
            slug=current.slug,
            page_id=self._wiki_page_id({}, current.slug, current.metadata),
            status=str(current.metadata.get("status") or "draft"),
            operation="index",
        )
        self._upsert_wiki_page(
            WikiPage(
                slug=current.slug,
                title=current.title,
                page_type=current.page_type,
                summary=current.summary,
                content=current.content,
                citations=current.citations,
                source=EXTRACTED_SOURCE,
                metadata=metadata,
            )
        )
        return {
            "slug": current.slug,
            "status": metadata["wiki_state"],
            "source": EXTRACTED_SOURCE,
            "wiki_retrievable": False,
            "weknora_retrievable": False,
            "metadata": metadata,
        }

    def _upsert_wiki_page(self, page: WikiPage) -> WikiPage:
        normalized = normalize_extracted_wiki_page(page)
        upsert = getattr(self.wiki_store, "upsert", None)
        if callable(upsert):
            upsert(normalized)
        return normalized

    @staticmethod
    def _wiki_slug(payload: dict) -> str:
        slug = str(payload.get("slug") or "").strip()
        if slug:
            return slug
        title = str(payload.get("title") or "untitled").strip().lower()
        normalized = "-".join(part for part in title.replace("_", "-").split() if part)
        return normalized or f"local-wiki-{uuid4().hex[:12]}"

    @staticmethod
    def _wiki_page_id(
        payload: dict,
        slug: str,
        metadata: dict | None = None,
    ) -> str:
        candidates = [
            payload.get("id"),
            payload.get("wiki_page_id"),
            (metadata or {}).get("id"),
            (metadata or {}).get("wiki_page_id"),
        ]
        for candidate in candidates:
            if candidate not in (None, ""):
                return str(candidate)
        return f"extracted:{slug}"

    @staticmethod
    def _wiki_payload_metadata(payload: dict, kb_id: str | None = None) -> dict:
        page_metadata = payload.get("page_metadata")
        metadata = dict(page_metadata) if isinstance(page_metadata, dict) else {}
        raw_metadata = payload.get("metadata")
        if isinstance(raw_metadata, dict):
            metadata.update(raw_metadata)
        if kb_id:
            metadata.setdefault("kb_id", kb_id)
        for key in (
            "tags",
            "business_area",
            "source_output_id",
            "source_document_ids",
            "source_citation_ids",
            "created_by",
        ):
            if key in payload:
                metadata[key] = payload.get(key)
        return metadata

    def _wiki_payload_citations(self, payload: dict) -> list[Evidence]:
        raw_citations = payload.get("citations")
        if not isinstance(raw_citations, list):
            return []
        citations: list[Evidence] = []
        for index, item in enumerate(raw_citations, start=1):
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type") or "document_chunk")
            chunk_id = item.get("chunk_id")
            wiki_page_id = item.get("wiki_page_id")
            evidence_id = (
                item.get("evidence_id")
                or (f"document_chunk:{chunk_id}" if chunk_id else None)
                or (f"wiki_page:{wiki_page_id}" if wiki_page_id else None)
                or f"wiki_citation:{index}"
            )
            citations.append(
                normalize_extracted_evidence(
                    Evidence(
                        document_id=item.get("document_id"),
                        external_doc_id=item.get("external_doc_id"),
                        chunk_id=chunk_id,
                        title=str(item.get("title") or payload.get("title") or "Wiki citation"),
                        text=str(item.get("text") or item.get("excerpt") or ""),
                        score=item.get("score"),
                        source=EXTRACTED_SOURCE,
                        metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                        evidence_id=str(evidence_id),
                        source_type=source_type,
                        wiki_page_id=wiki_page_id,
                    )
                )
            )
        return citations

    def _pipeline_status(self) -> dict[str, str]:
        return {
            "document_parser": self._component_status(self.document_parser),
            "chunker": self._component_status(self.chunker),
            "embedding_provider": "ready",
            "vector_store": self._component_status(self.vector_store),
            "retriever": self._component_status(self.retriever),
            "citation_builder": self._component_status(self.citation_builder),
            "wiki_store": self._component_status(self.wiki_store),
        }

    @staticmethod
    def _component_status(component: object | None) -> str:
        return "pending" if component is None else "ready"

    def _delete_old_vectors_after_reindex(
        self,
        old_vector_ids: list[str],
        current_vector_ids: list[str],
    ) -> None:
        current_ids = set(current_vector_ids)
        old_ids_to_delete = [
            vector_id for vector_id in old_vector_ids if vector_id not in current_ids
        ]
        if old_ids_to_delete:
            self.vector_store.delete(old_ids_to_delete)

    def _build_vector_records(
        self,
        external_doc_id: str,
        document: KnowledgeDocument,
        chunks: list[DocumentChunkCandidate],
    ) -> list[VectorRecord]:
        if not chunks:
            return []
        embeddings = self.embedding_provider.embed_batch(
            [chunk.content for chunk in chunks]
        )
        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "EmbeddingProvider returned a vector count that did not match chunks."
            )
        return [
            VectorRecord(
                id=self._chunk_vector_id(external_doc_id, chunk),
                vector=embedding.vector,
                text=chunk.content,
                metadata=self._chunk_vector_metadata(
                    document=document,
                    external_doc_id=external_doc_id,
                    chunk=chunk,
                    embedding=embedding,
                ),
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

    @staticmethod
    def _chunk_vector_id(
        external_doc_id: str,
        chunk: DocumentChunkCandidate,
    ) -> str:
        return f"document_chunk:{external_doc_id}:{chunk.chunk_index}"

    @staticmethod
    def _chunk_vector_metadata(
        document: KnowledgeDocument,
        external_doc_id: str,
        chunk: DocumentChunkCandidate,
        embedding: EmbeddingVector,
    ) -> dict[str, Any]:
        return {
            "source_type": "document",
            "source": document.source,
            "document_id": document.document_id,
            "external_doc_id": external_doc_id,
            "chunk_id": f"{external_doc_id}:{chunk.chunk_index}",
            "chunk_index": chunk.chunk_index,
            "title": chunk.title or document.title,
            "document_title": document.title,
            "business_area": document.metadata.get("business_area"),
            "document_type": document.metadata.get("document_type"),
            "content_hash": chunk.content_hash,
            "token_count": chunk.token_count,
            "char_count": chunk.char_count,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "page_number": chunk.page_number,
            "section_path": chunk.section_path,
            "paragraph_start_index": chunk.paragraph_start_index,
            "paragraph_end_index": chunk.paragraph_end_index,
            "embedding_provider": embedding.provider,
            "embedding_model": embedding.model,
            "embedding_dimension": embedding.dimension,
            "embedding_text_hash": embedding.text_hash,
            "chunk_metadata": chunk.metadata,
        }

    @staticmethod
    def _raise_pending(method_name: str, task_id: str) -> NoReturn:
        raise NotImplementedError(
            f"{method_name} is planned for PHASE2 task {task_id} and is not implemented yet."
        )
