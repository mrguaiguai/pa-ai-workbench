"""Live WNX-P1-02 document lifecycle smoke.

The script starts temporary PA backend/frontend services, uploads a sanitized
document through the PA BFF into WeKnora, checks native status/chunks/spans and
preview/download proxying, exercises safe lifecycle controls, and verifies the
Library browser workflow. It prints statuses and counts only, never raw file
body text, service tokens, provider payloads, or private endpoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4

from check_weknora_native_kb_management import _dump_library_dom
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_backend
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="pa-wnx-doc-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'document-lifecycle.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend(backend_port, database_url)
        frontend = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            kb_overview = _request_json(
                backend_port,
                "GET",
                "/api/knowledge-bases/native/overview?limit=10",
            )
            selected_kb_id = _active_or_first_kb_id(kb_overview)
            _assert(bool(selected_kb_id), "active KB id is available internally")

            title = f"WNX-P1-02 lifecycle {run_id}"
            file_doc = _upload_file_document(backend_port, title, selected_kb_id, run_id)
            document_id = str(file_doc.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            _assert(file_doc.get("knowledge_backend") == "weknora_api", "document uses WeKnora backend")
            _assert(bool(file_doc.get("external_doc_id")), "native document id saved")

            indexed = _wait_until_indexed(backend_port, document_id)
            chunks = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
            _assert(int(chunks.get("total") or 0) > 0, "native chunk preview is non-empty")

            spans = _request_json(backend_port, "GET", f"/api/documents/{document_id}/spans")
            _assert(spans.get("source") == "weknora_api", "native spans source is WeKnora")
            preview_bytes = _request_bytes(backend_port, f"/api/documents/{document_id}/preview")
            download_bytes = _request_bytes(backend_port, f"/api/documents/{document_id}/download")
            _assert(preview_bytes > 0, "preview proxy returned bytes")
            _assert(download_bytes > 0, "download proxy returned bytes")

            manual_doc = _create_manual_document(backend_port, selected_kb_id, run_id)
            _assert(manual_doc.get("knowledge_backend") == "weknora_api", "manual document uses WeKnora")
            _assert(bool(manual_doc.get("external_doc_id")), "manual native document id saved")

            url_status = _try_url_document(backend_port, selected_kb_id, run_id)

            reparse = _request_json(
                backend_port,
                "POST",
                f"/api/documents/{document_id}/native-reparse",
            )
            _assert(reparse.get("evidence_type") == "live_api", "native reparse response is live API")

            cancel = _request_json(
                backend_port,
                "POST",
                f"/api/documents/{document_id}/cancel-processing",
            )
            _assert(cancel.get("action") == "cancel", "cancel control is exposed safely")

            delete = _request_json(backend_port, "DELETE", f"/api/documents/{document_id}")
            _assert(delete.get("action") == "delete", "native delete action submitted")

            print("WeKnora native document lifecycle")
            print("- decision: PASS")
            print("- evidence_type: live_api")
            print(
                "- file: uploaded indexed chunks={chunks} preview=live download=live".format(
                    chunks=int(chunks.get("total") or 0)
                )
            )
            print("- manual: ingestion=live")
            print(f"- url: ingestion={url_status}")
            print("- lifecycle: reparse=live cancel=safe-control delete=live-submitted")
            print(
                "- spans: source={source} parse_status={parse_status} current_stage={stage}".format(
                    source=spans.get("source"),
                    parse_status=spans.get("parse_status"),
                    stage=spans.get("current_stage") or "not_running",
                )
            )
            print(f"- status: final_file_status={indexed.get('status')}")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_library_dom(frontend_port, temp_path / "chrome-profile")
                for marker in ("资料库", "总资料", "文件", "URL", "手工", "提交"):
                    _assert(marker in dom, f"browser DOM contains {marker}")
                print("- browser: Library DOM rendered lifecycle workflow")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _active_or_first_kb_id(overview: dict[str, Any]) -> str:
    active = overview.get("active_selection")
    if isinstance(active, dict) and active.get("kb_id"):
        return str(active["kb_id"])
    items = overview.get("items")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        return str(items[0].get("id") or "")
    return ""


def _upload_file_document(port: int, title: str, kb_id: str, run_id: str) -> dict[str, Any]:
    body = (
        f"# WNX-P1-02 lifecycle {run_id}\n\n"
        "This sanitized document validates native WeKnora lifecycle controls.\n"
        "It contains no secrets, credentials, provider payloads, or private data.\n"
    ).encode("utf-8")
    fields = {
        "title": title,
        "document_type": "wnx_lifecycle",
        "source": "wnx_p1_02_file",
        "knowledge_base_id": kb_id,
    }
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnx-p1-02-{run_id}.md",
        file_content=body,
        fields=fields,
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _create_manual_document(port: int, kb_id: str, run_id: str) -> dict[str, Any]:
    response = _request_json(
        port,
        "POST",
        "/api/documents/manual",
        {
            "title": f"WNX-P1-02 manual {run_id}",
            "content": "Manual lifecycle smoke content. No secrets or raw provider payloads.",
            "document_type": "manual",
            "source": "wnx_p1_02_manual",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _try_url_document(port: int, kb_id: str, run_id: str) -> str:
    url = os.environ.get("WNX_DOCUMENT_URL_SMOKE_URL") or f"https://example.com/?wnx={run_id}"
    try:
        response = _request_json(
            port,
            "POST",
            "/api/documents/url",
            {
                "url": url,
                "title": f"WNX-P1-02 url {run_id}",
                "document_type": "url",
                "source": "wnx_p1_02_url",
                "knowledge_base_id": kb_id,
            },
        )
    except Exception:
        return "blocked_or_backlog"
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return "live" if document.get("external_doc_id") else "blocked_or_backlog"


def _wait_until_indexed(port: int, document_id: str, timeout_seconds: float = 180.0) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_document: dict[str, Any] = {}
    while time.time() < deadline:
        document = _request_json(port, "GET", f"/api/documents/{document_id}")
        last_document = document
        status = str(document.get("status") or "")
        if status == "indexed":
            return document
        if status == "failed":
            raise AssertionError("document reached failed status")
        time.sleep(2)
    raise AssertionError(f"document did not reach indexed, last_status={last_document.get('status')}")


def _multipart_request(
    *,
    port: int,
    path: str,
    file_name: str,
    file_content: bytes,
    fields: dict[str, str],
) -> dict[str, Any]:
    boundary = f"----pa-wnx-doc-{uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("ascii"),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{file_name}"\r\n'
                "Content-Type: text/markdown\r\n\r\n"
            ).encode("utf-8"),
            file_content,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=b"".join(chunks),
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("multipart response was not a JSON object")
    return payload


def _request_bytes(port: int, path: str) -> int:
    request = Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            return len(response.read())
    except HTTPError as exc:
        raise AssertionError(f"binary endpoint failed with HTTP {exc.code}") from exc


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
