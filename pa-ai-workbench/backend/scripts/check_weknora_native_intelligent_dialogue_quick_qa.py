"""Live WNID-P1-02 dialogue Quick Q&A check.

The script starts temporary PA backend/frontend services, uploads a sanitized
document through PA into WeKnora, runs native knowledge-chat from the PA BFF,
checks PA history/citation persistence, and opens `#/dialogue` in Chrome to
prove the Quick Q&A mode is visible in the first-class dialogue shell.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.parse import urlparse
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
from check_weknora_native_kb_management import _request_chrome_json
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_chrome
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from check_weknora_native_kb_management import _websocket_handshake
from check_weknora_native_kb_management import _websocket_recv_json
from check_weknora_native_kb_management import _websocket_send_json


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    marker = f"WNID-P1-02 marker {run_id}"
    query = f"What validates {marker}?"
    with tempfile.TemporaryDirectory(prefix="pa-wnid-quick-qa-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'quick-qa.db'}"
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
            _assert(bool(selected_kb_id), "native KB id is available")

            document = _upload_quick_qa_document(backend_port, selected_kb_id, run_id, marker)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            indexed = _wait_until_indexed(backend_port, document_id)
            external_doc_id = str(indexed.get("external_doc_id") or "")
            _assert(bool(external_doc_id), "native document id saved")

            chat = _request_json_timeout(
                backend_port,
                "POST",
                "/api/rag/knowledge-chat",
                {
                    "query": query,
                    "title": f"WNID-P1-02 quick Q&A {run_id}",
                    "knowledge_ids": [external_doc_id],
                    "current_run": {
                        "task_id": "WNID-P1-02",
                        "source": "dialogue_shell_checker",
                        "expected_external_doc_ids": [external_doc_id],
                    },
                },
                timeout=180,
            )
            runtime = chat.get("runtime") if isinstance(chat.get("runtime"), dict) else {}
            output = chat.get("output") if isinstance(chat.get("output"), dict) else {}
            citations = chat.get("citations") if isinstance(chat.get("citations"), list) else []
            guard = runtime.get("current_run_guard") if isinstance(runtime.get("current_run_guard"), dict) else {}
            _assert(output.get("status") == "completed", "native knowledge-chat output completed")
            _assert(int(runtime.get("reference_count") or 0) > 0, "native references returned")
            _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved traceable citations")
            _assert(bool(guard.get("passed")), "current-run guard passed")
            _assert(_citations_match_external_doc(citations, external_doc_id), "citations match current native doc")

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_knowledge_chat")
            _assert(int(history.get("total") or 0) > 0, "history lists native knowledge-chat output")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "智能对话",
                "Native Intelligent Dialogue",
                "Quick Q&A",
                "运行 Quick Q&A",
                "RAG Trace",
                "Citations",
                "Messages",
            )
            dom = _dialogue_dom_after_quick_qa_click(frontend_port, temp_path / "chrome-profile", markers)
            _assert("高级工具" not in dom, "Quick Q&A is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue shell does not render secret-shaped text")

            print("WeKnora native intelligent dialogue quick Q&A")
            print("- decision: PASS")
            print("- task: WNID-P1-02")
            print("- evidence_type: live_api + live_browser")
            print(
                "- api: "
                f"knowledge_chat=live references={int(runtime.get('reference_count') or 0)} "
                f"saved_citations={int(runtime.get('saved_citation_count') or 0)} "
                "history=saved current_run=passed"
            )
            print("- browser: route=dialogue mode=quick_q_and_a markers=7 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _upload_quick_qa_document(port: int, kb_id: str, run_id: str, marker: str) -> dict[str, Any]:
    body = (
        f"# WNID-P1-02 native Quick Q&A {run_id}\n\n"
        f"{marker} validates the dialogue shell Quick Q&A path.\n\n"
        "The required evidence is a native knowledge-chat answer with saved PA citations.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnid-p1-02-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNID-P1-02 quick Q&A {run_id}",
            "document_type": "wnid_quick_qa",
            "source": "wnid_p1_02_file",
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


def _citations_match_external_doc(citations: list[Any], external_doc_id: str) -> bool:
    for citation in citations:
        if isinstance(citation, dict) and citation.get("external_doc_id") == external_doc_id:
            return True
    return False


def _dialogue_dom_after_quick_qa_click(port: int, user_data_dir: Path, markers: tuple[str, ...]) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/dialogue', safe=':/?=&')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        last_dom = ""
        while time.time() < deadline:
            _click_quick_qa(ws_url)
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(1)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue Quick Q&A DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _click_quick_qa(ws_url: str) -> None:
    _evaluate_cdp(
        ws_url,
        """
        const quickButton = Array.from(document.querySelectorAll('button'))
          .find((button) => (button.textContent || '').includes('Quick Q&A'));
        if (quickButton) quickButton.click();
        true;
        """,
    )


def _read_dom_text_content_via_cdp(ws_url: str) -> str:
    value = _evaluate_cdp(ws_url, "document.body ? document.body.textContent : ''")
    return str(value or "")


def _evaluate_cdp(ws_url: str, expression: str) -> Any:
    parsed = urlparse(ws_url)
    if parsed.hostname is None or parsed.port is None:
        raise RuntimeError("Chrome websocket URL is invalid")
    with socket.create_connection((parsed.hostname, parsed.port), timeout=10) as sock:
        _websocket_handshake(sock, parsed.path)
        seq = 0

        def send(method: str, params: dict | None = None) -> int:
            nonlocal seq
            seq += 1
            _websocket_send_json(sock, {"id": seq, "method": method, "params": params or {}})
            return seq

        send("Page.enable")
        send("Runtime.enable")
        send(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False},
        )
        time.sleep(1)
        eval_id = send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
            },
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            message = _websocket_recv_json(sock)
            if message.get("id") != eval_id:
                continue
            result = message.get("result")
            if not isinstance(result, dict):
                break
            value = result.get("result")
            if isinstance(value, dict):
                return value.get("value")
        raise RuntimeError("Chrome CDP did not return evaluation result")


def _has_secret_like_text(text: str) -> bool:
    markers = (
        "Bearer ",
        "BEGIN " + "PRIVATE KEY",
        "BEGIN RSA " + "PRIVATE KEY",
        "BEGIN OPENSSH " + "PRIVATE KEY",
    )
    return any(marker in text for marker in markers)


if __name__ == "__main__":
    raise SystemExit(main())
