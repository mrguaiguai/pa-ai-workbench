"""Smoke-check WeKnora-first document actions stay on the native path.

This smoke uses an in-memory database and a fake WeKnora backend. It verifies
that PA parse/index/reindex actions for `weknora_api` documents do not call the
local parser, chunker, embedding provider, or vector store pipeline.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Iterator

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine
from sqlmodel import select


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.models import Document  # noqa: E402
from app.models import DocumentProcessingEvent  # noqa: E402
from app.services import document_service  # noqa: E402
from app.services.document_service import index_document_chunks  # noqa: E402
from app.services.document_service import parse_document_file  # noqa: E402
from app.services.document_service import reindex_document_chunks  # noqa: E402
from app.services.document_service import retry_index_document  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the smoke contract fails."""


class FixtureWeKnoraBackend:
    def __init__(self) -> None:
        self.upload_calls = 0
        self.status_calls = 0
        self.chunk_calls = 0
        self.status_by_id: dict[str, dict[str, object]] = {
            "wk-doc-native": _status("wk-doc-native", "indexed"),
        }

    def get_document_status(self, external_doc_id: str) -> dict[str, object]:
        self.status_calls += 1
        return self.status_by_id.get(
            external_doc_id,
            _status(external_doc_id, "indexed"),
        )

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        self.upload_calls += 1
        path = Path(file_path)
        if not path.is_file():
            raise SmokeError("native retry did not use the stored PA document file")
        return KnowledgeDocument(
            document_id=str(metadata.get("document_id") or ""),
            external_doc_id=f"wk-retry-native-{self.upload_calls}",
            title=str(metadata.get("title") or path.name),
            status="uploaded",
            source="weknora_api",
            metadata={"fixture": "true", "retry_call": self.upload_calls},
        )

    def list_document_chunks(self, external_doc_id: str) -> list[dict[str, object]]:
        self.chunk_calls += 1
        return [
            {
                "id": f"{external_doc_id}-chunk-1",
                "knowledge_id": external_doc_id,
                "chunk_index": 1,
                "content": "sanitized native chunk",
                "is_enabled": True,
                "metadata": {"fixture": "true"},
            }
        ]


@contextmanager
def patched_native_path(backend: FixtureWeKnoraBackend) -> Iterator[None]:
    original_backend = document_service._weknora_backend
    original_parse = document_service._parse_document
    original_embedding = document_service.get_embedding_provider
    original_vector_store = document_service.get_vector_store

    def fail_local_pipeline(*_args, **_kwargs):
        raise SmokeError("local PA document pipeline was called for weknora_api document")

    document_service._weknora_backend = lambda: backend  # type: ignore[assignment]
    document_service._parse_document = fail_local_pipeline  # type: ignore[assignment]
    document_service.get_embedding_provider = fail_local_pipeline  # type: ignore[assignment]
    document_service.get_vector_store = fail_local_pipeline  # type: ignore[assignment]
    try:
        yield
    finally:
        document_service._weknora_backend = original_backend  # type: ignore[assignment]
        document_service._parse_document = original_parse  # type: ignore[assignment]
        document_service.get_embedding_provider = original_embedding  # type: ignore[assignment]
        document_service.get_vector_store = original_vector_store  # type: ignore[assignment]


def main() -> int:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with TemporaryDirectory(prefix="pa-wf-p0-02-doc-") as temp_dir:
        fixture_path = Path(temp_dir) / "fixture.md"
        fixture_path.write_text("# Fixture\n\nsanitized fixture body\n", encoding="utf-8")
        backend = FixtureWeKnoraBackend()
        with patched_native_path(backend), Session(engine) as session:
            document = _create_weknora_document(session, fixture_path)

            parsed, parse_metadata = parse_document_file(session, document)
            _assert(parsed.status == "indexed", "parse action did not refresh native status")
            _assert(parse_metadata["source"] == "weknora_api", "parse metadata source missing")

            indexed, chunk_count = index_document_chunks(session, parsed)
            _assert(indexed.status == "indexed", "index action changed native indexed status")
            _assert(chunk_count == 1, "index action did not read native chunk count")
            _assert(backend.upload_calls == 0, "index action unexpectedly retried upload")

            indexed.status = "failed"
            indexed.failed_step = "embedding"
            indexed.external_doc_id = "wk-doc-failed"
            backend.status_by_id["wk-doc-failed"] = _status(
                "wk-doc-failed",
                "failed",
                failed_step="embedding",
                error_message="fixture embedding failed",
            )
            retried, retry_chunk_count = reindex_document_chunks(session, indexed)
            _assert(
                retried.external_doc_id == "wk-retry-native-1",
                "reindex did not use native retry upload",
            )
            _assert(retry_chunk_count == 1, "reindex did not read native retry chunk count")

            retry_index_document(session, retried)
            _assert(backend.upload_calls == 1, "retry-index retried an active native upload")

            events = list(session.exec(select(DocumentProcessingEvent)).all())
            _assert(
                any(event.step == "weknora_status" for event in events),
                "native status event missing",
            )
            _assert(
                any(event.step == "weknora_retry" for event in events),
                "native retry event missing",
            )

    print(
        "WeKnora document native path smoke passed "
        "(fixture: parse/index avoid local pipeline, reindex uses native retry)"
    )
    return 0


def _create_weknora_document(session: Session, fixture_path: Path) -> Document:
    document = Document(
        title="WF-P0-02 fixture",
        business_area="fixture",
        document_type="markdown",
        source="fixture",
        file_name=fixture_path.name,
        file_path=str(fixture_path),
        file_size=fixture_path.stat().st_size,
        mime_type="text/markdown",
        knowledge_backend="weknora_api",
        external_doc_id="wk-doc-native",
        status="indexing",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _status(
    external_doc_id: str,
    status: str,
    failed_step: str | None = None,
    error_message: str | None = None,
) -> dict[str, object]:
    return {
        "external_doc_id": external_doc_id,
        "status": status,
        "source": "weknora_api",
        "message": f"fixture native status: {status}",
        "failed_step": failed_step,
        "error_message": error_message,
        "metadata": {"fixture": "true"},
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
