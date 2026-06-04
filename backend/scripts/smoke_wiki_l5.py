"""L5 Wiki smoke test for draft, publish, and retrieve.

The test is intentionally self-contained:
- uses in-memory SQLite;
- uses a temporary sanitized markdown file;
- uses mock chat, mock embedding, and mock vector store;
- creates a generated output with real document-chunk citations;
- creates a Wiki draft from that output, publishes and indexes it;
- retrieves the published Wiki page as wiki_page evidence;
- does not read or write backend/data, uploads, .env secrets, or real documents.
"""

from pathlib import Path
import json
import os
import sys
from tempfile import TemporaryDirectory

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "extracted"
    os.environ["MOCK_MODE"] = "false"
    os.environ["CHAT_MODEL_PROVIDER"] = "mock"
    os.environ["CHAT_MODEL_NAME"] = "mock-chat"
    os.environ["CHAT_MODEL_API_KEY"] = ""
    os.environ["MOCK_MODEL_MODE"] = "true"
    os.environ["EMBEDDING_PROVIDER"] = "mock"
    os.environ["EMBEDDING_MODEL_NAME"] = "mock-embedding"
    os.environ["EMBEDDING_DIMENSION"] = "64"
    os.environ["EMBEDDING_API_KEY"] = ""
    os.environ["VECTOR_STORE_PROVIDER"] = "mock"
    os.environ["VECTOR_COLLECTION_NAME"] = "l5_wiki_smoke"


_set_smoke_env()

from app import models as _models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.models import Document  # noqa: E402
from app.schemas import WikiDraftFromOutputRequest  # noqa: E402
from app.services.document_service import index_document_chunks  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402
from app.services.rag_service import retrieve_evidence  # noqa: E402
from app.services import rag_service as rag_service_module  # noqa: E402
from app.services.wiki_service import create_wiki_draft_from_output  # noqa: E402
from app.services.wiki_service import index_wiki_page_record  # noqa: E402
from app.services.wiki_service import list_wiki_citation_records  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from app.services.wiki_service import page_source_citation_ids  # noqa: E402
from app.services.wiki_service import page_source_document_ids  # noqa: E402
from app.services.wiki_service import page_tags  # noqa: E402
from app.services.wiki_service import publish_wiki_page_record  # noqa: E402
from app.services.wiki_service import read_wiki_page  # noqa: E402
from app.services.wiki_service import search_wiki_pages  # noqa: E402
from app.services.wiki_service import WikiPageIndexError  # noqa: E402
from knowledge_engine.backends.extracted_backend import (  # noqa: E402
    ExtractedBackendComponents,
)
from knowledge_engine.backends.extracted_backend import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402
from knowledge_engine.wiki import WikiPageStatus  # noqa: E402


SANITIZED_SOURCE_TEXT = """# L5 Sanitized Wiki Source

The public affairs team keeps a synthetic briefing checklist for partner updates.
The checklist requires an evidence note, an owner, and a follow-up review date.
This document is fabricated for local smoke testing and contains no real material.
"""


def main() -> None:
    get_settings.cache_clear()
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
    vector_store = MockVectorStore(name="l5-wiki-smoke")
    knowledge_engine = ExtractedKnowledgeBackend(
        components=ExtractedBackendComponents(vector_store=vector_store),
        embedding_provider=embedding_provider,
    )
    rag_service_module.create_knowledge_engine = lambda backend_name=None: knowledge_engine

    with TemporaryDirectory(prefix="pa-l5-wiki-smoke-") as temp_dir:
        sample_path = Path(temp_dir) / "l5_sanitized_wiki_source.md"
        sample_path.write_text(SANITIZED_SOURCE_TEXT, encoding="utf-8")

        with Session(engine) as session:
            document = _index_source_document(
                session=session,
                sample_path=sample_path,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
            output_id = _create_source_output(
                session=session,
                document=document,
                knowledge_engine=knowledge_engine,
            )
            draft = _assert_draft_from_output(session=session, output_id=output_id)
            published = _assert_publish_and_index(
                session=session,
                draft_slug=draft.slug,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
            _assert_wiki_retrieve(
                session=session,
                page_id=published.id,
                slug=published.slug,
            )

    print("L5 wiki smoke passed: draft, publish, index, and retrieve wiki evidence")


def _index_source_document(
    session: Session,
    sample_path: Path,
    embedding_provider: MockEmbeddingProvider,
    vector_store: MockVectorStore,
) -> Document:
    document = Document(
        title="L5 Sanitized Wiki Source",
        business_area="public_affairs",
        document_type="wiki_smoke_source",
        source="l5_wiki_smoke",
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

    indexed_document, chunk_count = index_document_chunks(
        session=session,
        document=document,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    assert indexed_document.status == "indexed"
    assert chunk_count > 0
    return indexed_document


def _create_source_output(
    session: Session,
    document: Document,
    knowledge_engine: ExtractedKnowledgeBackend,
) -> str:
    evidence_items = knowledge_engine.retrieve(
        query="synthetic briefing checklist evidence owner review date",
        filters={
            "source_type": "document_chunk",
            "document_id": document.id,
        },
        top_k=2,
    )
    assert evidence_items, "source document retrieve returned no evidence"

    task = create_task(
        session=session,
        task_type="policy_analysis",
        title="L5 Sanitized Wiki Output",
        input_json=_to_json(
            {
                "query_or_topic": "Create a synthetic Wiki checklist draft.",
                "document_ids": [document.id],
            }
        ),
        status="completed",
        current_step="completed",
        progress=100,
    )
    output, citations = create_output_with_citations(
        session=session,
        task=task,
        title="L5 Sanitized Wiki Output",
        content_markdown=(
            "## Synthetic Partner Briefing Checklist\n\n"
            "- Keep an evidence note with every partner update.\n"
            "- Assign a single owner before external sharing.\n"
            "- Add a follow-up review date after publication.\n"
        ),
        status="completed",
        citations=[
            {
                "document_id": evidence.document_id,
                "external_doc_id": evidence.external_doc_id,
                "chunk_id": evidence.chunk_id,
                "title": evidence.title,
                "text": evidence.text,
                "score": evidence.score,
                "source": evidence.source,
                "metadata_json": _to_json(evidence.metadata),
            }
            for evidence in evidence_items
        ],
    )
    assert output.status == "completed"
    assert citations
    return output.id


def _assert_draft_from_output(session: Session, output_id: str):
    draft = create_wiki_draft_from_output(
        session=session,
        output_id=output_id,
        payload=WikiDraftFromOutputRequest(
            slug="l5-sanitized-wiki-smoke",
            title="L5 Sanitized Wiki Smoke",
            summary="Synthetic Wiki smoke draft for partner briefing checklist.",
            tags=["l5-smoke", "wiki"],
            business_area="public_affairs",
            page_type="policy_analysis",
            created_by="l5_smoke",
            metadata={"kb_id": "l5-smoke-kb"},
        ),
    )

    citations = list_wiki_citation_records(session=session, wiki_page_id=draft.id)
    assert draft.status == WikiPageStatus.DRAFT
    assert draft.published_at is None
    assert draft.embedding_status == "pending"
    assert draft.source_output_id == output_id
    assert "evidence note" in draft.content_markdown.lower()
    assert "l5-smoke" in page_tags(draft)
    assert page_metadata(draft)["source"] == "generated_output"
    assert page_metadata(draft)["kb_id"] == "l5-smoke-kb"
    assert page_source_document_ids(draft)
    assert page_source_citation_ids(draft)
    assert citations
    assert all(citation.source_type == "document_chunk" for citation in citations)

    try:
        index_wiki_page_record(session=session, slug=draft.slug)
    except WikiPageIndexError:
        pass
    else:
        raise AssertionError("draft Wiki page should not be indexable before publish")

    return draft


def _assert_publish_and_index(
    session: Session,
    draft_slug: str,
    embedding_provider: MockEmbeddingProvider,
    vector_store: MockVectorStore,
):
    published = publish_wiki_page_record(session=session, slug=draft_slug)
    assert published.status == WikiPageStatus.PUBLISHED
    assert published.published_at is not None

    republished = publish_wiki_page_record(session=session, slug=draft_slug)
    assert republished.status == WikiPageStatus.PUBLISHED
    assert republished.published_at == published.published_at

    indexed = index_wiki_page_record(
        session=session,
        slug=draft_slug,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    assert indexed.embedding_status == "indexed"
    assert indexed.vector_id == f"wiki_page:{indexed.id}"
    assert indexed.indexed_at is not None
    assert vector_store.health()["record_count"] >= 2
    return indexed


def _assert_wiki_retrieve(session: Session, page_id: str, slug: str) -> None:
    search_results = search_wiki_pages(
        session=session,
        query="partner briefing checklist",
        kb_id="l5-smoke-kb",
        limit=5,
    )
    assert any(page.slug == slug for page in search_results)

    read_page = read_wiki_page(session=session, slug=slug, kb_id="l5-smoke-kb")
    assert read_page is not None
    assert read_page.metadata["status"] == WikiPageStatus.PUBLISHED
    assert read_page.citations

    evidence_items = retrieve_evidence(
        query="partner briefing checklist evidence owner review date",
        filters={"source_type": "wiki_page", "wiki_page_id": page_id},
        top_k=3,
    )
    assert evidence_items, "wiki retrieve returned no evidence"
    wiki_evidence = evidence_items[0]
    assert wiki_evidence.source == "extracted"
    assert wiki_evidence.source_type == "wiki_page"
    assert wiki_evidence.wiki_page_id == page_id
    assert wiki_evidence.evidence_id == f"wiki_page:{page_id}"
    assert wiki_evidence.metadata["slug"] == slug
    assert wiki_evidence.metadata["citation_source_type"] == "wiki_page"
    assert "partner briefing checklist" in wiki_evidence.text.lower()

    document_only = retrieve_evidence(
        query="partner briefing checklist evidence owner review date",
        filters={"source_type": "document_chunk", "wiki_page_id": page_id},
        top_k=3,
    )
    assert not document_only


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


if __name__ == "__main__":
    main()
