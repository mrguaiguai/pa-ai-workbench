"""Fixture smoke for P3-M2-C1 document list filters and batch refresh."""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.models import Document  # noqa: E402
from app.models import DocumentProcessingEvent  # noqa: E402
from app.services.document_service import list_documents  # noqa: E402
from app.services.document_service import refresh_document_statuses  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when document filter expectations fail."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Document filter refresh smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Document filter refresh smoke passed (fixture)")
    print(f"- processing: {result['processing']}")
    print(f"- indexed: {result['indexed']}")
    print(f"- failed/error: {result['failed_error']}")
    print(f"- unavailable: {result['unavailable']}")
    print(f"- deleted: {result['deleted']}")
    print(f"- refreshed: {result['refreshed']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-document-filter-smoke-") as temp_dir:
        engine = create_engine(f"sqlite:///{Path(temp_dir) / 'smoke.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            docs = _seed_documents(session)

            processing = list_documents(session=session, status="processing")
            indexed = list_documents(session=session, status="indexed")
            failed_error = list_documents(session=session, status="failed", has_error=True)
            unavailable = list_documents(session=session, status="unavailable")
            weknora = list_documents(session=session, knowledge_backend="weknora_api")
            deleted = list_documents(session=session, status="deleted")
            default_records = list_documents(session=session)
            refreshed = refresh_document_statuses(
                session=session,
                status="processing",
                knowledge_backend="weknora_api",
                limit=5,
            )

            _assert(
                {doc.id for doc in processing} == {docs["uploaded"].id, docs["unavailable"].id},
                "processing filter failed",
            )
            _assert(
                {doc.id for doc in indexed} == {docs["indexed"].id, docs["mock"].id},
                "indexed filter failed",
            )
            _assert([doc.id for doc in failed_error] == [docs["failed"].id], "failed/error filter failed")
            _assert([doc.id for doc in unavailable] == [docs["unavailable"].id], "unavailable filter failed")
            _assert(
                {doc.id for doc in weknora}
                == {docs["uploaded"].id, docs["indexed"].id, docs["failed"].id, docs["unavailable"].id},
                "backend filter failed",
            )
            _assert(
                {doc.id for doc in deleted} == {docs["deleted"].id, docs["delete_submitted"].id},
                "deleted filter failed",
            )
            _assert(
                docs["deleted"].id not in {doc.id for doc in default_records}
                and docs["delete_submitted"].id not in {doc.id for doc in default_records},
                "default list leaked deleted documents",
            )
            _assert(
                {doc.id for doc in refreshed} == {docs["uploaded"].id, docs["unavailable"].id},
                "refresh filter failed",
            )

            return {
                "processing": len(processing),
                "indexed": len(indexed),
                "failed_error": len(failed_error),
                "unavailable": len(unavailable),
                "deleted": len(deleted),
                "refreshed": len(refreshed),
            }


def _seed_documents(session: Session) -> dict[str, Document]:
    docs = {
        "uploaded": Document(
            title="Uploaded Fixture",
            knowledge_backend="weknora_api",
            external_doc_id=None,
            status="uploaded",
            source="fixture",
        ),
        "indexed": Document(
            title="Indexed Fixture",
            knowledge_backend="weknora_api",
            external_doc_id=None,
            status="indexed",
            source="fixture",
        ),
        "failed": Document(
            title="Failed Fixture",
            knowledge_backend="weknora_api",
            external_doc_id=None,
            status="failed",
            failed_step="weknora_status",
            error_message="synthetic unavailable",
            source="fixture",
        ),
        "unavailable": Document(
            title="Unavailable Fixture",
            knowledge_backend="weknora_api",
            external_doc_id=None,
            status="parsing",
            source="fixture",
        ),
        "mock": Document(
            title="Mock Fixture",
            knowledge_backend="mock",
            external_doc_id=None,
            status="indexed",
            source="fixture",
        ),
        "deleted": Document(
            title="Deleted Fixture",
            knowledge_backend="weknora_api",
            external_doc_id="deleted-fixture",
            status="deleted",
            source="fixture",
        ),
        "delete_submitted": Document(
            title="Delete Submitted Fixture",
            knowledge_backend="weknora_api",
            external_doc_id="delete-submitted-fixture",
            status="deleting",
            source="fixture",
        ),
    }
    for document in docs.values():
        session.add(document)
    session.commit()
    for document in docs.values():
        session.refresh(document)
    session.add(
        DocumentProcessingEvent(
            document_id=docs["unavailable"].id,
            external_doc_id=None,
            step="weknora_status",
            status="failed",
            message="synthetic status refresh failure",
            error_message="WeKnora unavailable",
        )
    )
    session.add(
        DocumentProcessingEvent(
            document_id=docs["delete_submitted"].id,
            external_doc_id=docs["delete_submitted"].external_doc_id,
            step="weknora_delete",
            status="completed",
            message="synthetic delete completed",
        )
    )
    session.commit()
    return docs


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
