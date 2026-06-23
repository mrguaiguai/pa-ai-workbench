"""Fixture smoke for P3-M2-A2 document processing recovery.

The smoke uses an in-memory database and a fake WeKnora backend. It does not
read .env, upload real files, call live WeKnora, or print document bodies.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import os
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
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.models import Document  # noqa: E402
from app.models import DocumentProcessingEvent  # noqa: E402
from app.models import utc_now  # noqa: E402
from app.services import document_service  # noqa: E402
from app.services.document_service import document_processing_summary  # noqa: E402
from app.services.document_service import recover_document_processing  # noqa: E402
from app.services.document_service import sync_document_status  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the recovery smoke contract fails."""


class FixtureWeKnoraBackend:
    def __init__(self) -> None:
        self.statuses: dict[str, list[dict[str, object]]] = {}
        self.upload_calls = 0

    def get_document_status(self, external_doc_id: str) -> dict[str, object]:
        sequence = self.statuses.get(external_doc_id)
        if not sequence:
            return {
                "external_doc_id": external_doc_id,
                "status": "indexed",
                "source": "weknora_api",
                "message": "fixture indexed",
                "failed_step": None,
                "error_message": None,
                "metadata": {"fixture": "true"},
            }
        if len(sequence) > 1:
            return sequence.pop(0)
        return sequence[0]

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        self.upload_calls += 1
        path = Path(file_path)
        if not path.is_file():
            raise SmokeError("retry upload did not use stored file")
        return KnowledgeDocument(
            document_id=str(metadata.get("document_id") or ""),
            external_doc_id=f"wk-retry-{self.upload_calls}",
            title=str(metadata.get("title") or path.name),
            status="uploaded",
            source="weknora_api",
            metadata={"fixture": "true", "retry_call": self.upload_calls},
        )

    def list_document_chunks(self, external_doc_id: str) -> list[dict[str, object]]:
        return []


@contextmanager
def patched_backend(backend: FixtureWeKnoraBackend) -> Iterator[None]:
    original_backend = document_service._weknora_backend
    document_service._weknora_backend = lambda: backend  # type: ignore[assignment]
    try:
        yield
    finally:
        document_service._weknora_backend = original_backend  # type: ignore[assignment]


@contextmanager
def processing_timeout(value: str) -> Iterator[None]:
    original = os.environ.get("DOCUMENT_PROCESSING_TIMEOUT_SECONDS")
    os.environ["DOCUMENT_PROCESSING_TIMEOUT_SECONDS"] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DOCUMENT_PROCESSING_TIMEOUT_SECONDS", None)
        else:
            os.environ["DOCUMENT_PROCESSING_TIMEOUT_SECONDS"] = original


def main() -> int:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with TemporaryDirectory(prefix="pa-m2-doc-recovery-") as temp_dir:
        fixture_path = Path(temp_dir) / "fixture.md"
        fixture_path.write_text("# Fixture\n\nsanitized document body\n", encoding="utf-8")
        backend = FixtureWeKnoraBackend()
        with patched_backend(backend), processing_timeout("1"), Session(engine) as session:
            _assert_adapter_failed_step_mapping()
            active = _create_document(session, fixture_path, "wk-active", "parsing")
            backend.statuses["wk-active"] = [_status("wk-active", "parsing")]
            recovered_active, active_message = recover_document_processing(session, active)
            _assert("no duplicate retry" in active_message, "active retry should skip")
            _assert(recovered_active.external_doc_id == "wk-active", "active doc id changed")
            _assert(backend.upload_calls == 0, "active processing retried unexpectedly")

            stale = _create_document(session, fixture_path, "wk-stale", "indexing", stale=True)
            backend.statuses["wk-stale"] = [_status("wk-stale", "indexing")]
            summary = document_processing_summary(stale)
            _assert(summary["processing_state"] == "stalled", "stale doc not stalled")
            _assert(summary["retryable"] is True, "stale doc not retryable")
            recovered_stale, _ = recover_document_processing(session, stale)
            _assert(recovered_stale.external_doc_id == "wk-retry-1", "stale retry not uploaded")
            _assert(backend.upload_calls == 1, "stale retry call count mismatch")

            failed = _create_document(session, fixture_path, "wk-failed", "indexing")
            backend.statuses["wk-failed"] = [
                _status(
                    "wk-failed",
                    "failed",
                    failed_step="embedding",
                    error_message="fixture embedding failed",
                )
            ]
            synced_failed = sync_document_status(session, failed)
            _assert(synced_failed.status == "failed", "failed status not synced")
            _assert(synced_failed.failed_step == "embedding", "failed step not preserved")
            recovered_failed, _ = recover_document_processing(session, synced_failed)
            _assert(
                recovered_failed.external_doc_id == "wk-retry-2",
                "failed retry not uploaded",
            )

            doc_count = len(session.exec(select(Document)).all())
            _assert(doc_count == 3, "retry created duplicate PA document rows")
            events = list(session.exec(select(DocumentProcessingEvent)).all())
            _assert(
                any(event.step == "weknora_retry" and event.status == "skipped" for event in events),
                "active skip event missing",
            )
            _assert(
                any(event.step == "weknora_retry" and event.status == "completed" for event in events),
                "retry completion event missing",
            )

    print(
        "Document processing recovery M2 smoke passed "
        "(fixture: active skip, stalled retry, failed retry, no duplicate PA rows)"
    )
    return 0


def _assert_adapter_failed_step_mapping() -> None:
    backend = WeKnoraApiBackend(base_url="http://fixture", service_token="fixture-token")
    original_request_json = WeKnoraApiBackend._request_json

    def fixture_request_json(self: WeKnoraApiBackend, method: str, path: str, payload=None):
        return {
            "success": True,
            "data": {
                "id": "wk-adapter",
                "parse_status": "embedding_failed",
                "error_message": "fixture embedding failed",
            },
        }

    WeKnoraApiBackend._request_json = fixture_request_json  # type: ignore[assignment]
    try:
        status = backend.get_document_status("wk-adapter")
    finally:
        WeKnoraApiBackend._request_json = original_request_json  # type: ignore[assignment]
    _assert(status["status"] == "failed", "adapter did not map embedding_failed to failed")
    _assert(status["failed_step"] == "embedding", "adapter did not map embedding failed step")


def _create_document(
    session: Session,
    fixture_path: Path,
    external_doc_id: str,
    status: str,
    stale: bool = False,
) -> Document:
    document = Document(
        title=f"Fixture {external_doc_id}",
        file_name=fixture_path.name,
        file_path=str(fixture_path),
        file_size=fixture_path.stat().st_size,
        mime_type="text/markdown",
        knowledge_backend="weknora_api",
        external_doc_id=external_doc_id,
        status=status,
    )
    if stale:
        document.updated_at = utc_now() - timedelta(seconds=5)
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
        "message": f"fixture status {status}",
        "failed_step": failed_step,
        "error_message": error_message,
        "metadata": {"fixture": "true"},
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
