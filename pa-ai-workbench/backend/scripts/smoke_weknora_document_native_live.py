"""Live smoke for PA document service -> WeKnora native ingestion.

This script uploads a sanitized in-memory Markdown file through PA's document
service, waits for native WeKnora indexing, and checks native chunk preview.
It uses a temporary database and upload directory, and it does not print
service tokens or document body text.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

from fastapi import UploadFile
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
from app.config import Settings  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import DocumentProcessingEvent  # noqa: E402
from app.services.document_service import create_document  # noqa: E402
from app.services.document_service import list_document_chunks  # noqa: E402
from app.services.document_service import sync_document_status  # noqa: E402


TERMINAL_INDEXED_STATUSES = {"indexed"}
TERMINAL_FAILED_STATUSES = {"failed"}
PROGRESS_STATUSES = {"uploaded", "parsing", "chunking", "embedding", "indexing", "unknown"}


class SmokeError(RuntimeError):
    """Raised when live native document validation fails."""


def main() -> int:
    try:
        with TemporaryDirectory(prefix="pa-wf-p0-02-live-doc-") as temp_dir:
            result = asyncio.run(_run_live_smoke(Path(temp_dir)))
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native document live smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora native document live smoke passed")
    print(f"- base URL: {result['base_url']}")
    print(f"- external doc id: {result['external_doc_id']}")
    print(f"- indexed status: {result['status']}")
    print(f"- native chunk count: {result['chunk_count']}")
    print(f"- upload/status events: {result['event_count']}")
    return 0


async def _run_live_smoke(temp_dir: Path) -> dict[str, Any]:
    original_upload_dir = os.environ.get("UPLOAD_DIR")
    os.environ["UPLOAD_DIR"] = str(temp_dir / "uploads")
    get_settings.cache_clear()
    try:
        settings = Settings()
        _validate_settings(settings)
        engine = create_engine(f"sqlite:///{temp_dir / 'smoke.db'}")
        SQLModel.metadata.create_all(engine)
        run_id = uuid4().hex[:12]
        upload = UploadFile(
            filename=f"wf-p0-02-native-{run_id}.md",
            file=BytesIO(_fixture_body(run_id)),
        )
        with Session(engine) as session:
            document = await create_document(
                session=session,
                upload=upload,
                title=f"WF-P0-02 Native Smoke {run_id}",
                business_area="public_affairs",
                document_type="smoke",
                source="wf_p0_02_native_smoke",
            )
            if document.knowledge_backend != "weknora_api":
                raise SmokeError(f"unexpected knowledge_backend: {document.knowledge_backend}")
            if not document.external_doc_id:
                detail = document.error_message or document.failed_step or document.status
                raise SmokeError(
                    "PA document service did not save native external_doc_id "
                    f"(status={document.status}, detail={detail})"
                )

            status = _wait_until_indexed(session, document, _wait_seconds(), _poll_seconds())
            chunks = list_document_chunks(session, document.id)
            if not chunks:
                raise SmokeError("native chunk preview returned no chunks")
            events = list(
                session.exec(
                    select(DocumentProcessingEvent).where(
                        DocumentProcessingEvent.document_id == document.id
                    )
                ).all()
            )
            if not any(event.step == "weknora_upload" for event in events):
                raise SmokeError("missing weknora_upload event")
            if not any(event.step == "weknora_status" for event in events):
                raise SmokeError("missing weknora_status event")
            return {
                "base_url": settings.weknora_base_url.rstrip("/"),
                "external_doc_id": document.external_doc_id,
                "status": status,
                "chunk_count": len(chunks),
                "event_count": len(events),
            }
    finally:
        if original_upload_dir is None:
            os.environ.pop("UPLOAD_DIR", None)
        else:
            os.environ["UPLOAD_DIR"] = original_upload_dir
        get_settings.cache_clear()


def _validate_settings(settings: Settings) -> None:
    missing = []
    if settings.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if settings.mock_mode:
        missing.append("MOCK_MODE=false")
    if not settings.weknora_base_url.strip():
        missing.append("WEKNORA_BASE_URL")
    if not settings.weknora_service_token.strip():
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not settings.weknora_default_kb_id.strip():
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _wait_until_indexed(
    session: Session,
    document,
    wait_seconds: int,
    poll_seconds: int,
) -> str:
    deadline = time.monotonic() + wait_seconds
    last_status = document.status
    while time.monotonic() <= deadline:
        sync_document_status(session, document)
        session.refresh(document)
        last_status = document.status
        if last_status in TERMINAL_INDEXED_STATUSES:
            return last_status
        if last_status in TERMINAL_FAILED_STATUSES:
            detail = document.error_message or document.failed_step or "unknown"
            raise SmokeError(f"WeKnora indexing failed: {detail}")
        if last_status not in PROGRESS_STATUSES:
            raise SmokeError(f"unexpected WeKnora document status: {last_status}")
        time.sleep(poll_seconds)
    raise SmokeError(
        f"WeKnora document did not reach indexed within {wait_seconds}s "
        f"(last status: {last_status or 'unknown'})"
    )


def _fixture_body(run_id: str) -> bytes:
    return (
        "# WF-P0-02 Native Document Smoke\n\n"
        "This is a synthetic fixture with no private data.\n"
        f"The smoke run id is {run_id}.\n"
        "The document is uploaded through PA document service into WeKnora.\n"
    ).encode("utf-8")


def _wait_seconds() -> int:
    return _int_env("WEKNORA_DOCUMENT_SMOKE_WAIT_SECONDS", 180)


def _poll_seconds() -> int:
    return _int_env("WEKNORA_DOCUMENT_SMOKE_POLL_SECONDS", 5)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(int(raw), 1)
    except ValueError:
        return default


if __name__ == "__main__":
    raise SystemExit(main())
