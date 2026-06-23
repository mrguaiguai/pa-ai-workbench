"""Smoke-check PA -> WeKnora document upload/status mapping.

This script uses a local sanitized fixture server by default. It validates:
- PA saves the uploaded file and creates a Document row.
- WeKnoraApiBackend calls WeKnora's real M1 upload/status API shapes.
- PA stores external_doc_id and maps WeKnora parse_status to PA status.

It does not upload real pilot documents and does not print service tokens.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any

from fastapi import UploadFile
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine
from sqlmodel import select


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.models import DocumentProcessingEvent  # noqa: E402
from app.services.document_service import create_document  # noqa: E402
from app.services.document_service import sync_document_status  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when a smoke step fails."""


class FixtureWeKnoraHandler(BaseHTTPRequestHandler):
    server_version = "FixtureWeKnora/1.0"
    uploaded = False

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/v1/knowledge/wk-doc-fixture":
            self._require_auth()
            self._json(
                {
                    "success": True,
                    "data": {
                        "id": "wk-doc-fixture",
                        "knowledge_base_id": "kb-fixture",
                        "title": "Fixture Upload",
                        "file_name": "fixture.md",
                        "parse_status": "completed",
                        "pending_subtasks_count": 0,
                        "summary_status": "completed",
                        "enable_status": "enabled",
                        "metadata": {"fixture": "true"},
                    },
                }
            )
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/v1/knowledge-bases/kb-fixture/knowledge/file":
            self.send_error(404)
            return
        self._require_auth()
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise SmokeError("fixture upload did not use multipart/form-data")
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        required_markers = [
            b'name="file"',
            b'name="metadata"',
            b'name="fileName"',
            b"fixture.md",
            b"sanitized fixture content",
        ]
        missing = [marker.decode("utf-8", errors="replace") for marker in required_markers if marker not in body]
        if missing:
            raise SmokeError("fixture upload body missing markers: " + ", ".join(missing))
        FixtureWeKnoraHandler.uploaded = True
        self._json(
            {
                "success": True,
                "data": {
                    "id": "wk-doc-fixture",
                    "knowledge_base_id": "kb-fixture",
                    "title": "Fixture Upload",
                    "file_name": "fixture.md",
                    "file_type": "md",
                    "parse_status": "processing",
                    "pending_subtasks_count": 1,
                    "summary_status": "pending",
                    "enable_status": "enabled",
                    "metadata": {"fixture": "true"},
                },
            }
        )

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _require_auth(self) -> None:
        api_key = self.headers.get("X-API-Key")
        bearer = self.headers.get("Authorization")
        if api_key != "fixture-token" or bearer != "Bearer fixture-token":
            raise SmokeError("fixture request did not include expected auth headers")

    def _json(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    try:
        with TemporaryDirectory(prefix="pa-weknora-doc-smoke-") as temp_dir:
            result = asyncio.run(_run_fixture_smoke(Path(temp_dir)))
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora document smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora document smoke passed (fixture)")
    print(f"- document id: {result['document_id']}")
    print(f"- external doc id: {result['external_doc_id']}")
    print(f"- upload status: {result['upload_status']}")
    print(f"- refreshed status: {result['refreshed_status']}")
    print(f"- events: {result['event_count']}")
    return 0


async def _run_fixture_smoke(temp_dir: Path) -> dict[str, Any]:
    server = HTTPServer(("127.0.0.1", 0), FixtureWeKnoraHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        os.environ.update(
            {
                "KNOWLEDGE_BACKEND": "weknora_api",
                "MOCK_MODE": "false",
                "WEKNORA_BASE_URL": base_url,
                "WEKNORA_SERVICE_TOKEN": "fixture-token",
                "WEKNORA_DEFAULT_KB_ID": "kb-fixture",
                "WEKNORA_WORKSPACE_ID": "10000",
                "WEKNORA_TIMEOUT_SECONDS": "5",
                "UPLOAD_DIR": str(temp_dir / "uploads"),
            }
        )
        get_settings.cache_clear()
        engine = create_engine(f"sqlite:///{temp_dir / 'smoke.db'}")
        SQLModel.metadata.create_all(engine)
        upload = UploadFile(
            filename="fixture.md",
            file=BytesIO(b"# Fixture\n\nsanitized fixture content\n"),
        )
        with Session(engine) as session:
            document = await create_document(
                session=session,
                upload=upload,
                title="Fixture Upload",
                business_area="public_affairs",
                document_type="policy",
                source="smoke",
            )
            if not FixtureWeKnoraHandler.uploaded:
                raise SmokeError("fixture server did not receive upload")
            if document.external_doc_id != "wk-doc-fixture":
                raise SmokeError(f"external_doc_id not saved: {document.external_doc_id}")
            if document.knowledge_backend != "weknora_api":
                raise SmokeError(f"unexpected knowledge_backend: {document.knowledge_backend}")
            if document.status != "parsing":
                raise SmokeError(f"unexpected upload status: {document.status}")

            upload_status = document.status
            sync_document_status(session, document)
            if document.status != "indexed":
                raise SmokeError(f"unexpected refreshed status: {document.status}")
            events = list(
                session.exec(
                    select(DocumentProcessingEvent).where(
                        DocumentProcessingEvent.document_id == document.id
                    )
                ).all()
            )
            if not any(event.step == "weknora_upload" for event in events):
                raise SmokeError("missing weknora_upload processing event")
            if not any(event.step == "weknora_status" for event in events):
                raise SmokeError("missing weknora_status processing event")
            return {
                "document_id": document.id,
                "external_doc_id": document.external_doc_id,
                "upload_status": upload_status,
                "refreshed_status": document.status,
                "event_count": len(events),
            }
    finally:
        server.shutdown()
        with suppress(Exception):
            server.server_close()
        thread.join(timeout=2)
        get_settings.cache_clear()


if __name__ == "__main__":
    raise SystemExit(main())
