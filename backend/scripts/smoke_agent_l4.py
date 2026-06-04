"""L4 agent smoke test for QA/policy/case workflows with evidence.

The test is intentionally self-contained:
- uses in-memory SQLite;
- uses temporary sanitized markdown files;
- uses mock chat, mock embedding, and mock vector store;
- runs backend analysis_service.run_analysis for the three Agent workflows;
- does not read or write backend/data, uploads, .env secrets, or real documents.
"""

from pathlib import Path
import json
import os
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine
from sqlmodel import select

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
    os.environ["VECTOR_COLLECTION_NAME"] = "l4_agent_smoke"


_set_smoke_env()

from agent.schemas import AgentTaskType  # noqa: E402
from agent.tools import real_retriever as real_retriever_module  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.models import Citation  # noqa: E402
from app.models import Document  # noqa: E402
from app.models import GeneratedOutput  # noqa: E402
from app.models import GenerationTask  # noqa: E402
from app.services.analysis_service import run_analysis  # noqa: E402
from app.services.document_service import index_document_chunks  # noqa: E402
from app.services.document_service import list_document_chunks  # noqa: E402
from knowledge_engine.backends.extracted_backend import (  # noqa: E402
    ExtractedBackendComponents,
)
from knowledge_engine.backends.extracted_backend import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402


SMOKE_DOCUMENTS = [
    {
        "task_type": AgentTaskType.KNOWLEDGE_QA,
        "title": "L4 Sanitized QA Evidence",
        "file_name": "l4_qa_evidence.md",
        "document_type": "qa_smoke",
        "query": "What does the public affairs evidence say about response windows?",
        "content": (
            "# L4 Sanitized QA Evidence\n\n"
            "The public affairs desk records a synthetic response window of two "
            "business days for low-risk stakeholder questions. The note is "
            "sanitized and contains no real department material.\n"
        ),
    },
    {
        "task_type": AgentTaskType.POLICY_ANALYSIS,
        "title": "L4 Sanitized Policy Evidence",
        "file_name": "l4_policy_evidence.md",
        "document_type": "policy_smoke",
        "query": "Analyze the synthetic policy change for partner briefings.",
        "content": (
            "# L4 Sanitized Policy Evidence\n\n"
            "A synthetic policy update requires partner briefing drafts to include "
            "an evidence checklist, an owner, and a review date before external "
            "sharing. The text is fabricated for smoke testing.\n"
        ),
    },
    {
        "task_type": AgentTaskType.CASE_REVIEW,
        "title": "L4 Sanitized Case Evidence",
        "file_name": "l4_case_evidence.md",
        "document_type": "case_smoke",
        "query": "Review the synthetic escalation case and evidence gaps.",
        "content": (
            "# L4 Sanitized Case Evidence\n\n"
            "A synthetic escalation case notes that the first reply was delayed, "
            "the owner handoff was unclear, and the follow-up log should capture "
            "the final stakeholder acknowledgement. This is test-only content.\n"
        ),
    },
]


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
    vector_store = MockVectorStore(name="l4-agent-smoke")
    knowledge_engine = ExtractedKnowledgeBackend(
        components=ExtractedBackendComponents(vector_store=vector_store),
        embedding_provider=embedding_provider,
    )
    real_retriever_module.create_knowledge_engine = lambda backend_name=None: knowledge_engine

    with TemporaryDirectory(prefix="pa-l4-agent-smoke-") as temp_dir:
        temp_path = Path(temp_dir)
        with Session(engine) as session:
            indexed_documents = _index_smoke_documents(
                session=session,
                temp_path=temp_path,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
            )
            _assert_agent_workflows(
                session=session,
                indexed_documents=indexed_documents,
            )

    print("L4 agent smoke passed: QA, policy, and case workflows cited real evidence")


def _index_smoke_documents(
    session: Session,
    temp_path: Path,
    embedding_provider: MockEmbeddingProvider,
    vector_store: MockVectorStore,
) -> dict[str, Document]:
    indexed_documents: dict[str, Document] = {}
    for document_spec in SMOKE_DOCUMENTS:
        sample_path = temp_path / str(document_spec["file_name"])
        sample_path.write_text(str(document_spec["content"]), encoding="utf-8")

        document = Document(
            title=str(document_spec["title"]),
            business_area="public_affairs",
            document_type=str(document_spec["document_type"]),
            source="l4_agent_smoke",
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
        chunks = list_document_chunks(session=session, document_id=indexed_document.id)
        assert chunks
        assert all(chunk.embedding_status == "indexed" for chunk in chunks)
        indexed_documents[str(document_spec["task_type"])] = indexed_document

    assert vector_store.health()["record_count"] >= len(SMOKE_DOCUMENTS)
    return indexed_documents


def _assert_agent_workflows(
    session: Session,
    indexed_documents: dict[str, Document],
) -> None:
    for document_spec in SMOKE_DOCUMENTS:
        task_type = str(document_spec["task_type"])
        document = indexed_documents[task_type]
        conversation, messages, task, output, citations = run_analysis(
            session=session,
            task_type=task_type,
            query_or_topic=str(document_spec["query"]),
            title=f"L4 Smoke {task_type}",
            business_area="public_affairs",
            document_type=str(document_spec["document_type"]),
            document_ids=[document.id],
            extra_requirements="Use only the retrieved smoke evidence.",
        )

        _assert_analysis_result(
            session=session,
            expected_task_type=task_type,
            expected_document=document,
            conversation_id=conversation.id,
            message_count=len(messages),
            task=task,
            output=output,
            citations=citations,
        )


def _assert_analysis_result(
    session: Session,
    expected_task_type: str,
    expected_document: Document,
    conversation_id: str,
    message_count: int,
    task: GenerationTask,
    output: GeneratedOutput,
    citations: list[Citation],
) -> None:
    assert task.status == "completed"
    assert task.task_type == expected_task_type
    assert task.conversation_id == conversation_id
    assert output.status == "completed"
    assert output.task_type == expected_task_type
    assert output.content_markdown
    assert message_count >= 2

    content = _json_object(output.content_json)
    assert content["citation_count"] >= 1
    assert content["model"]["provider"] == "mock"
    assert citations, f"{expected_task_type} returned no citations"

    saved_citations = list(
        session.exec(select(Citation).where(Citation.output_id == output.id)).all()
    )
    assert len(saved_citations) == len(citations)

    for citation in saved_citations:
        metadata = _json_object(citation.metadata_json)
        evidence_id = metadata.get("evidence_id")
        binding = metadata.get("citation_binding")
        assert citation.source == "extracted"
        assert citation.document_id == expected_document.id
        assert citation.chunk_id
        assert citation.text.strip()
        assert citation.title.strip()
        assert metadata.get("citation_source_type") == "document_chunk"
        assert evidence_id or (isinstance(binding, dict) and binding.get("evidence_id"))
        warnings_text = json.dumps(_json_value(output.warnings_json), ensure_ascii=False)
        assert "No evidence" not in warnings_text


def _json_object(value: str | None) -> dict[str, Any]:
    parsed = _json_value(value)
    return parsed if isinstance(parsed, dict) else {}


def _json_value(value: str | None) -> Any:
    if not value:
        return {}
    return json.loads(value)


if __name__ == "__main__":
    main()
