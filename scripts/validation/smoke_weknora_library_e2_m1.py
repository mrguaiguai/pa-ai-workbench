"""Smoke-check M1 LibraryPage status/chunk/event contract for WeKnora.

This fixture smoke covers P3-M1-E2:
- /api/documents exposes WeKnora indexed and failed documents with PA status fields;
- parse/chunk/index failures are normalized enough for LibraryPage display;
- chunk preview and processing events are available without leaking service config.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

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
from app.api.documents import list_document_records  # noqa: E402
from app.api.documents import read_document_chunks  # noqa: E402
from app.api.documents import read_document_events  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import Document  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the WeKnora library contract fails."""


def main() -> int:
    original_request_json = WeKnoraApiBackend._request_json
    original_env = dict(os.environ)
    WeKnoraApiBackend._request_json = fixture_request_json  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora library E2 smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        get_settings.cache_clear()
        WeKnoraApiBackend._request_json = original_request_json  # type: ignore[assignment]

    print("WeKnora library E2 smoke passed (fixture)")
    print(f"- indexed status: {result['indexed_status']}")
    print(f"- chunk count: {result['chunk_count']}")
    print(f"- failed step: {result['failed_step']}")
    print(f"- failed events: {result['failed_event_count']}")
    print(f"- leaked secrets: {result['leaked_secrets']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    _set_weknora_env()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        indexed_doc = _add_document(session, "Indexed Handbook", "weknora-indexed")
        failed_doc = _add_document(session, "Broken Policy", "weknora-failed")

        document_list = list_document_records(session)
        by_id = {document.id: document for document in document_list.items}
        indexed_read = by_id[indexed_doc.id]
        failed_read = by_id[failed_doc.id]

        if indexed_read.status != "indexed":
            raise SmokeError(f"indexed document status mismatch: {indexed_read.status}")
        if indexed_read.knowledge_backend != "weknora_api":
            raise SmokeError("indexed document lost WeKnora backend marker")
        if indexed_read.chunk_count != 2 or indexed_read.indexed_chunk_count != 2:
            raise SmokeError(f"indexed chunk counts mismatch: {indexed_read}")
        if indexed_read.embedding_status != "indexed":
            raise SmokeError(f"embedding status mismatch: {indexed_read.embedding_status}")

        if failed_read.status != "failed":
            raise SmokeError(f"failed document status mismatch: {failed_read.status}")
        if failed_read.failed_step != "parse":
            raise SmokeError(f"failed step was not normalized: {failed_read.failed_step}")
        if not failed_read.error_message:
            raise SmokeError("failed document did not expose a safe error summary")

        chunks = read_document_chunks(indexed_doc.id, session)
        if chunks.total != 2:
            raise SmokeError(f"chunk preview total mismatch: {chunks.total}")
        if {chunk.source for chunk in chunks.items} != {"weknora_api"}:
            raise SmokeError("chunk preview did not preserve WeKnora source")
        if not all(chunk.embedding_status == "indexed" for chunk in chunks.items):
            raise SmokeError("chunk preview did not expose indexed embedding status")

        failed_events = read_document_events(failed_doc.id, session)
        if not any(event.step == "weknora_status" for event in failed_events.items):
            raise SmokeError("failed document did not record WeKnora status event")

        response_text = (
            document_list.model_dump_json()
            + chunks.model_dump_json()
            + failed_events.model_dump_json()
        )
        leaked = [
            value
            for value in (
                "http://weknora.fixture/private",
                "fixture-secret-token",
                "workspace-fixture",
                "kb-fixture",
            )
            if value in response_text
        ]
        if leaked:
            raise SmokeError("library response leaked sensitive config: " + ", ".join(leaked))

    return {
        "indexed_status": indexed_read.status,
        "chunk_count": chunks.total,
        "failed_step": failed_read.failed_step,
        "failed_event_count": len(failed_events.items),
        "leaked_secrets": len(leaked),
    }


def _set_weknora_env() -> None:
    os.environ.update(
        {
            "KNOWLEDGE_BACKEND": "weknora_api",
            "MOCK_MODE": "false",
            "WEKNORA_BASE_URL": "http://weknora.fixture/private",
            "WEKNORA_SERVICE_TOKEN": "fixture-secret-token",
            "WEKNORA_WORKSPACE_ID": "workspace-fixture",
            "WEKNORA_DEFAULT_KB_ID": "kb-fixture",
        }
    )
    get_settings.cache_clear()


def _add_document(session: Session, title: str, external_doc_id: str) -> Document:
    document = Document(
        title=title,
        business_area="compliance",
        document_type="policy",
        source="fixture",
        file_name=f"{external_doc_id}.md",
        file_size=2048,
        mime_type="text/markdown",
        knowledge_backend="weknora_api",
        external_doc_id=external_doc_id,
        status="uploaded",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def fixture_request_json(
    self: WeKnoraApiBackend,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    del self, payload
    if method == "GET" and path.startswith("/api/v1/knowledge/"):
        external_doc_id = path.rsplit("/", 1)[-1]
        if external_doc_id == "weknora-indexed":
            return {
                "success": True,
                "data": {
                    "id": external_doc_id,
                    "title": "Indexed Handbook",
                    "parse_status": "completed",
                    "pending_subtasks_count": 0,
                },
            }
        if external_doc_id == "weknora-failed":
            return {
                "success": True,
                "data": {
                    "id": external_doc_id,
                    "title": "Broken Policy",
                    "parse_status": "parse_failed",
                    "error_message": "Parser rejected fixture document.",
                },
            }
        return {"success": True, "data": {"id": external_doc_id, "parse_status": "pending"}}

    if method == "GET" and path.startswith("/api/v1/chunks/"):
        external_doc_id = path.split("?", 1)[0].rsplit("/", 1)[-1]
        if external_doc_id != "weknora-indexed":
            return {"success": True, "data": {"items": []}}
        return {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": "chunk-fixture-1",
                        "knowledge_id": external_doc_id,
                        "chunk_index": 0,
                        "content": "Indexed handbook chunk one.",
                        "token_count": 12,
                        "start_at": 0,
                        "end_at": 28,
                        "is_enabled": True,
                    },
                    {
                        "id": "chunk-fixture-2",
                        "knowledge_id": external_doc_id,
                        "chunk_index": 1,
                        "content": "Indexed handbook chunk two.",
                        "token_count": 12,
                        "start_at": 29,
                        "end_at": 57,
                        "is_enabled": True,
                    },
                ]
            },
        }

    raise SmokeError(f"unexpected WeKnora fixture request: {method} {path}")


if __name__ == "__main__":
    raise SystemExit(main())
