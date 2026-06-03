from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import NoReturn
from uuid import uuid4

from knowledge_engine.base import KnowledgeEngine
from knowledge_engine.chunking import Chunker
from knowledge_engine.chunking import ParagraphChunker
from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.embeddings.factory import get_embedding_provider
from knowledge_engine.errors import KnowledgeDocumentNotFoundError
from knowledge_engine.parsers import DocumentParser
from knowledge_engine.parsers import DocumentParseError
from knowledge_engine.parsers import FileDocumentParser
from knowledge_engine.parsers import ParsedDocument
from knowledge_engine.schemas import Evidence
from knowledge_engine.schemas import KnowledgeDocument
from knowledge_engine.schemas import WikiPage
from knowledge_engine.schemas import WikiPageSummary
from knowledge_engine.vectorstores import VectorStore
from knowledge_engine.vectorstores import get_vector_store


@dataclass(frozen=True)
class ExtractedBackendComponents:
    document_parser: DocumentParser | None = None
    chunker: Chunker | None = None
    vector_store: VectorStore | None = None
    retriever: object | None = None
    citation_builder: object | None = None
    wiki_store: object | None = None


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
        self._documents: dict[str, KnowledgeDocument] = {}

    def health(self) -> dict:
        embedding_config = getattr(self.embedding_provider, "config", None)
        return {
            "status": "ok",
            "backend": self.config.backend_name,
            "source": self.config.source,
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
        self._documents[external_doc_id] = document
        return document

    def get_document_status(self, external_doc_id: str) -> dict:
        document = self._documents.get(external_doc_id)
        if document is None:
            return {
                "external_doc_id": external_doc_id,
                "status": "not_found",
                "source": self.config.source,
            }
        return {
            "external_doc_id": external_doc_id,
            "status": document.status,
            "source": self.config.source,
            "metadata": document.metadata,
        }

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        return []

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        return []

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        return None

    def parse_document(self, external_doc_id: str) -> dict:
        return self._parse_registered_document(external_doc_id).to_dict()

    def chunk_document(self, external_doc_id: str) -> dict:
        parsed = self._parse_registered_document(external_doc_id)
        chunks = self.chunker.chunk(parsed)
        return {
            "external_doc_id": external_doc_id,
            "status": "chunked",
            "source": self.config.source,
            "chunk_count": len(chunks),
            "chunks": [chunk.to_dict() for chunk in chunks],
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
        self._raise_pending("index_document", "H5")

    def reindex_document(self, external_doc_id: str) -> dict:
        self._raise_pending("reindex_document", "H8")

    def list_document_chunks(self, external_doc_id: str) -> list[dict]:
        self._raise_pending("list_document_chunks", "H4")

    def create_wiki_draft(self, output_id: str, metadata: dict | None = None) -> WikiPage:
        self._raise_pending("create_wiki_draft", "I4")

    def create_wiki_page(self, payload: dict) -> WikiPage:
        self._raise_pending("create_wiki_page", "I2")

    def update_wiki_page(self, slug: str, payload: dict) -> WikiPage:
        self._raise_pending("update_wiki_page", "I2")

    def publish_wiki_page(self, slug: str) -> WikiPage:
        self._raise_pending("publish_wiki_page", "I3")

    def index_wiki_page(self, slug: str) -> dict:
        self._raise_pending("index_wiki_page", "I5")

    def _pipeline_status(self) -> dict[str, str]:
        return {
            "document_parser": self._component_status(self.document_parser),
            "chunker": self._component_status(self.chunker),
            "embedding_provider": "ready",
            "vector_store": self._component_status(self.vector_store),
            "retriever": self._component_status(self.components.retriever),
            "citation_builder": self._component_status(self.components.citation_builder),
            "wiki_store": self._component_status(self.components.wiki_store),
        }

    @staticmethod
    def _component_status(component: object | None) -> str:
        return "pending" if component is None else "ready"

    @staticmethod
    def _raise_pending(method_name: str, task_id: str) -> NoReturn:
        raise NotImplementedError(
            f"{method_name} is planned for PHASE2 task {task_id} and is not implemented yet."
        )
