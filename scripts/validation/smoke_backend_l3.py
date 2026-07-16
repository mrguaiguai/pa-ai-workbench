"""L3 backend smoke test for model/status/document index/retrieve.

The test is intentionally self-contained:
- uses in-memory SQLite;
- uses a temporary sanitized text file;
- uses mock embedding and mock vector store;
- does not read or write backend/data, uploads, .env secrets, or real documents.
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.models import Document  # noqa: E402
from app.schemas import StatusResponse  # noqa: E402
from app.services.document_service import index_document_chunks  # noqa: E402
from app.services.document_service import list_document_chunks  # noqa: E402
from app.services.document_service import list_document_events  # noqa: E402
from app.services.model_status_service import get_model_status  # noqa: E402
from app.services.status_service import get_status_counts  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.retrieval import RetrieveRequest  # noqa: E402
from knowledge_engine.retrieval import VectorRetriever  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402


SANITIZED_TEXT = """# Sanitized Public Affairs Backend Smoke

The public affairs team keeps evidence-linked notes for policy tracking.
The team indexes sanitized documents so analysis can cite document chunks.
This file is synthetic and contains no real department material.
"""


def main() -> None:
    settings = Settings(
        knowledge_backend="extracted",
        mock_mode=False,
        chat_model_provider="mock",
        chat_model_name="mock-chat",
        mock_model_mode=True,
        embedding_provider="mock",
        embedding_model_name="mock-embedding",
        embedding_dimension=64,
    )

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    embedding_provider = MockEmbeddingProvider(
        EmbeddingProviderConfig(
            provider="mock",
            model_name="mock-embedding",
            dimension=64,
        )
    )
    vector_store = MockVectorStore(name="l3-smoke")

    with TemporaryDirectory(prefix="pa-l3-smoke-") as temp_dir:
        sample_path = Path(temp_dir) / "sanitized_policy_note.md"
        sample_path.write_text(SANITIZED_TEXT, encoding="utf-8")

        with Session(engine) as session:
            _assert_status_models(session=session, settings=settings)
            document = _create_document(session=session, sample_path=sample_path)
            indexed_document, chunk_count = index_document_chunks(
                session=session,
                document=document,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
            _assert_document_indexed(
                session=session,
                document=indexed_document,
                chunk_count=chunk_count,
                vector_store=vector_store,
            )
            _assert_retrieve(
                embedding_provider=embedding_provider,
                vector_store=vector_store,
                document_id=indexed_document.id,
            )

    print(
        "L3 backend smoke passed: model/status, document index, chunks/events, retrieve evidence"
    )


def _assert_status_models(session: Session, settings: Settings) -> None:
    status = StatusResponse(
        status="ok",
        service="pa-ai-workbench-backend",
        version=settings.app_version,
        environment=settings.app_env,
        knowledge_backend=settings.knowledge_backend,
        mock_mode=settings.mock_mode,
        memory_recent_limit=settings.memory_recent_limit,
        database="ok",
        counts=get_status_counts(session),
    )
    model_status = get_model_status(settings)

    assert status.status == "ok"
    assert status.knowledge_backend == "extracted"
    assert "documents" in status.counts
    assert "document_chunks" in status.counts
    assert model_status.chat_provider == "mock"
    assert model_status.embedding_provider == "mock"
    assert model_status.configured is True
    assert model_status.chat.configured is True
    assert model_status.embedding.configured is True
    assert model_status.embedding.dimension == 64


def _create_document(session: Session, sample_path: Path) -> Document:
    document = Document(
        title="L3 Sanitized Policy Note",
        business_area="public_affairs",
        document_type="policy_note",
        source="l3_smoke",
        file_name=sample_path.name,
        file_path=str(sample_path),
        file_size=sample_path.stat().st_size,
        mime_type="text/markdown",
        knowledge_backend="extracted",
        status="uploaded",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _assert_document_indexed(
    session: Session,
    document: Document,
    chunk_count: int,
    vector_store: MockVectorStore,
) -> None:
    chunks = list_document_chunks(session=session, document_id=document.id)
    events = list_document_events(session=session, document_id=document.id)
    health = vector_store.health()

    assert document.status == "indexed"
    assert chunk_count > 0
    assert len(chunks) == chunk_count
    assert all(chunk.embedding_status == "indexed" for chunk in chunks)
    assert all(chunk.vector_id for chunk in chunks)
    assert health["record_count"] == chunk_count
    assert health["dimension"] == 64
    assert any(event.step == "parse" and event.status == "completed" for event in events)
    assert any(event.step == "chunk" and event.status == "completed" for event in events)
    assert any(event.step == "index" and event.status == "completed" for event in events)


def _assert_retrieve(
    embedding_provider: MockEmbeddingProvider,
    vector_store: MockVectorStore,
    document_id: str,
) -> None:
    retriever = VectorRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        source="extracted",
    )
    evidence = retriever.retrieve(
        RetrieveRequest(
            query="policy tracking evidence linked notes",
            filters={"source_type": "document_chunk", "document_id": document_id},
            top_k=3,
        )
    )

    assert evidence, "retrieve returned no evidence"
    first = evidence[0]
    assert first.source == "extracted"
    assert first.source_type == "document_chunk"
    assert first.document_id == document_id
    assert first.chunk_id
    assert "public affairs" in first.text.lower() or "policy" in first.text.lower()
    assert first.score is not None


if __name__ == "__main__":
    main()
