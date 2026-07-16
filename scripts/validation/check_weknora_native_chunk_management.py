"""Live WNX-P1-03 chunk management smoke.

The script starts temporary PA backend/frontend services, uploads a sanitized
document through PA into WeKnora, verifies native chunk list/by-id, exercises
safe toggle/delete controls with PA confirmation/audit events, and checks the
Library browser chunk workflow. It prints only statuses and counts, never raw
chunk body text, service tokens, provider payloads, or private endpoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4

from check_weknora_native_document_lifecycle import _active_or_first_kb_id
from check_weknora_native_document_lifecycle import _multipart_request
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_kb_management import CHROME_BIN
from check_weknora_native_kb_management import BACKEND_ROOT
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _read_dom_text_via_cdp
from check_weknora_native_kb_management import _request_chrome_json
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_chrome
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="pa-wnx-chunk-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'chunk-management.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(
                backend_port,
                "GET",
                "/api/knowledge-bases/native/overview?limit=10",
            )
            selected_kb_id = _active_or_first_kb_id(overview)
            _assert(bool(selected_kb_id), "active KB id is available internally")

            document = _upload_chunk_document(backend_port, selected_kb_id, run_id)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            _assert(document.get("knowledge_backend") == "weknora_api", "document uses WeKnora")
            _assert(bool(document.get("external_doc_id")), "native document id saved")

            indexed = _wait_until_indexed(backend_port, document_id)
            _assert(indexed.get("status") == "indexed", "document reached indexed status")

            chunks_before = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
            before_total = int(chunks_before.get("total") or 0)
            _assert(before_total > 0, "native chunk list is non-empty")
            items = chunks_before.get("items")
            _assert(isinstance(items, list) and bool(items), "chunk list contains items")
            first_chunk = items[0]
            _assert(isinstance(first_chunk, dict), "first chunk is object")
            chunk_id = str(first_chunk.get("id") or "")
            _assert(bool(chunk_id), "native chunk id is present")

            detail = _request_json(
                backend_port,
                "GET",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}",
            )
            _assert(detail.get("id") == chunk_id, "chunk by-id returns selected chunk")
            _assert(detail.get("external_doc_id") == indexed.get("external_doc_id"), "chunk belongs to document")

            disabled = _request_json(
                backend_port,
                "PATCH",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/enabled",
                {
                    "confirm": True,
                    "is_enabled": False,
                    "reason": "wnx_p1_03_smoke_toggle_off",
                },
            )
            _assert(disabled.get("action") == "toggle", "chunk disable action returned")
            disabled_chunk = disabled.get("chunk") if isinstance(disabled.get("chunk"), dict) else {}
            _assert(disabled_chunk.get("embedding_status") == "disabled", "chunk disabled state is visible")

            enabled = _request_json(
                backend_port,
                "PATCH",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/enabled",
                {
                    "confirm": True,
                    "is_enabled": True,
                    "reason": "wnx_p1_03_smoke_toggle_on",
                },
            )
            _assert(enabled.get("action") == "toggle", "chunk enable action returned")
            enabled_chunk = enabled.get("chunk") if isinstance(enabled.get("chunk"), dict) else {}
            _assert(enabled_chunk.get("embedding_status") == "indexed", "chunk enabled state is visible")

            generated_question_status = _generated_question_status(enabled_chunk)

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_library_chunk_dom(
                    frontend_port,
                    document_id=document_id,
                    chunk_id=str(enabled_chunk.get("id") or ""),
                    user_data_dir=temp_path / "chrome-profile",
                )
                for marker in ("资料库", "分块", "生成问题", "已启用", "定位"):
                    _assert(marker in dom, f"browser DOM contains {marker}; dom={_dom_excerpt(dom)}")

            delete = _request_json(
                backend_port,
                "DELETE",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}",
                {
                    "confirm": True,
                    "reason": "wnx_p1_03_smoke_delete_test_chunk",
                },
            )
            _assert(delete.get("action") == "delete_chunk", "chunk delete action returned")
            chunks_after = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
            after_total = int(chunks_after.get("total") or 0)
            _assert(after_total == max(before_total - 1, 0), "chunk delete changed live chunk count")

            events = _request_json(backend_port, "GET", f"/api/documents/{document_id}/events")
            event_steps = [
                str(item.get("step") or "")
                for item in events.get("items", [])
                if isinstance(item, dict)
            ]
            _assert("weknora_chunk_toggle" in event_steps, "toggle audit event recorded")
            _assert("weknora_chunk_delete" in event_steps, "delete audit event recorded")

            print("WeKnora native chunk management")
            print("- decision: PASS")
            print("- evidence_type: live_api")
            print(f"- chunks: before={before_total} after_delete={after_total}")
            print("- by_id: live")
            print("- toggle: disabled=live enabled=live audit=recorded")
            print("- delete: live-with-confirmation audit=recorded")
            print(f"- generated_questions: {generated_question_status}")
            print("- content_update: backlog_pending_reembed_safety")
            print("- search_by_chunk: backlog_native_route_not_found")

            if browser_mode:
                print("- browser: Library DOM rendered chunk detail workflow")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _upload_chunk_document(port: int, kb_id: str, run_id: str) -> dict[str, Any]:
    body = (
        f"# WNX-P1-03 chunk management {run_id}\n\n"
        "This sanitized document validates native WeKnora chunk list and detail controls.\n\n"
        "Section alpha covers chunk toggle state and product audit events.\n\n"
        "Section beta covers delete confirmation against a temporary smoke document.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnx-p1-03-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNX-P1-03 chunk {run_id}",
            "document_type": "wnx_chunk_management",
            "source": "wnx_p1_03_file",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _start_backend_with_cors(
    port: int,
    database_url: str,
    frontend_port: int | None,
) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    origins = {"http://127.0.0.1:5173", "http://localhost:5173"}
    if frontend_port is not None:
        origins.add(f"http://127.0.0.1:{frontend_port}")
        origins.add(f"http://localhost:{frontend_port}")
    env["CORS_ORIGINS"] = ",".join(sorted(origins))
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _generated_question_status(chunk: dict[str, Any]) -> str:
    metadata = _json_object(chunk.get("metadata_json"))
    questions = metadata.get("generated_questions")
    if isinstance(questions, list) and questions:
        return f"read_only_visible count={len(questions)} delete_requires_explicit_test_data"
    return "backlog_no_generated_question_data_in_smoke"


def _json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dom_excerpt(dom: str) -> str:
    return " ".join(dom.split())[:500]


def _dump_library_chunk_dom(
    port: int,
    *,
    document_id: str,
    chunk_id: str,
    user_data_dir: Path,
) -> str:
    if not CHROME_BIN.exists():
        raise RuntimeError("Google Chrome executable not found")
    debug_port = _free_port()
    url = f"http://127.0.0.1:{port}/#/library?document={quote(document_id)}&chunk={quote(chunk_id)}"
    chrome = subprocess.Popen(
        [
            str(CHROME_BIN),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            f"--user-data-dir={user_data_dir}",
            f"--remote-debugging-port={debug_port}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_for_chrome(debug_port)
        target = _request_chrome_json(
            debug_port,
            "PUT",
            f"/json/new?{quote(url, safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if "分块" in dom and "生成问题" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
