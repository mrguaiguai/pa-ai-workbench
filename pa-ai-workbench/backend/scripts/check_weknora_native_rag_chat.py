"""Live WNX-P1-04 native RAG + knowledge-chat smoke.

The script starts temporary PA backend/frontend services, uploads a sanitized
document through PA into WeKnora, verifies native RAG debug current-run search,
runs native knowledge-chat through PA, and checks PA history/citation persistence
plus the RAG browser workflow. It prints only statuses/counts and never raw
answers, raw chunks, service tokens, provider payloads, or private endpoints.
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
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_document_lifecycle import _active_or_first_kb_id
from check_weknora_native_document_lifecycle import _multipart_request
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_kb_management import CHROME_BIN
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
    marker = f"WNX-P1-04 marker {run_id}"
    query = f"What validates {marker}?"
    with tempfile.TemporaryDirectory(prefix="pa-wnx-rag-chat-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'rag-chat.db'}"
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

            document = _upload_rag_document(backend_port, selected_kb_id, run_id, marker)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            indexed = _wait_until_indexed(backend_port, document_id)
            external_doc_id = str(indexed.get("external_doc_id") or "")
            _assert(bool(external_doc_id), "native document id saved")

            debug = _request_json(
                backend_port,
                "POST",
                "/api/rag/debug",
                {
                    "query": query,
                    "top_k": 5,
                    "filters": {
                        "source_type": "document_chunk",
                        "knowledge_ids": [external_doc_id],
                        "current_run": {"expected_external_doc_ids": [external_doc_id]},
                    },
                },
            )
            _assert(debug.get("status") == "ok", "RAG debug returned ok")
            _assert(int(debug.get("total") or 0) > 0, "RAG debug returned current-run evidence")
            _assert(_contains_external_doc(debug.get("items"), external_doc_id), "RAG evidence matches current run")

            chat = _request_json_timeout(
                backend_port,
                "POST",
                "/api/rag/knowledge-chat",
                {
                    "query": query,
                    "title": f"WNX-P1-04 native chat {run_id}",
                    "knowledge_ids": [external_doc_id],
                    "current_run": {"expected_external_doc_ids": [external_doc_id]},
                },
                timeout=180,
            )
            runtime = chat.get("runtime") if isinstance(chat.get("runtime"), dict) else {}
            output = chat.get("output") if isinstance(chat.get("output"), dict) else {}
            citations = chat.get("citations") if isinstance(chat.get("citations"), list) else []
            guard = runtime.get("current_run_guard") if isinstance(runtime.get("current_run_guard"), dict) else {}
            _assert(output.get("status") == "completed", "native knowledge-chat output completed")
            _assert(int(runtime.get("reference_count") or 0) > 0, "native knowledge-chat references returned")
            _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved native citations")
            _assert(bool(guard.get("passed")), "current-run guard passed")
            _assert(_citations_match_external_doc(citations, external_doc_id), "saved citations match current run")

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_knowledge_chat")
            _assert(int(history.get("total") or 0) > 0, "history lists native knowledge-chat output")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_rag_dom(frontend_port, temp_path / "chrome-profile")
                for marker_text in ("RAG 调试", "原生知识问答", "运行问答"):
                    _assert(marker_text in dom, f"browser DOM contains {marker_text}")

            print("WeKnora native RAG + knowledge-chat")
            print("- decision: PASS")
            print("- evidence_type: live_api")
            print(f"- rag_debug: total={int(debug.get('total') or 0)} current_run=passed")
            print(
                "- knowledge_chat: references={refs} saved_citations={citations} guard=passed".format(
                    refs=int(runtime.get("reference_count") or 0),
                    citations=int(runtime.get("saved_citation_count") or 0),
                )
            )
            print("- history: native_knowledge_chat output listed")
            if browser_mode:
                print("- browser: RAG page rendered native knowledge-chat workflow")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _upload_rag_document(port: int, kb_id: str, run_id: str, marker: str) -> dict[str, Any]:
    body = (
        f"# WNX-P1-04 native RAG chat {run_id}\n\n"
        f"{marker} validates native WeKnora RAG search and native knowledge-chat.\n\n"
        "The workflow must persist PA history and traceable citations without using mock evidence.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnx-p1-04-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNX-P1-04 native chat {run_id}",
            "document_type": "wnx_rag_chat",
            "source": "wnx_p1_04_file",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _request_json_timeout(
    port: int,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    timeout: float,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {path} failed status={exc.code} body={body_text[:500]}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{method} {path} returned non-object JSON")
    return data


def _contains_external_doc(items: Any, external_doc_id: str) -> bool:
    if not isinstance(items, list):
        return False
    for item in items:
        if isinstance(item, dict) and item.get("external_doc_id") == external_doc_id:
            return True
    return False


def _citations_match_external_doc(citations: list[Any], external_doc_id: str) -> bool:
    for citation in citations:
        if isinstance(citation, dict) and citation.get("external_doc_id") == external_doc_id:
            return True
    return False


def _dump_rag_dom(port: int, user_data_dir: Path) -> str:
    if not CHROME_BIN.exists():
        raise RuntimeError("Google Chrome executable not found")
    debug_port = _free_port()
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/rag-debug', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if "原生知识问答" in dom and "运行问答" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
