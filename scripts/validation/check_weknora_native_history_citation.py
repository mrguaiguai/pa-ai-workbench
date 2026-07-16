"""Live WNX-P1-07 native history/citation unification smoke.

The script starts temporary PA backend/frontend services, creates current-run
native document evidence, verifies native knowledge-chat history/citation
locators, verifies native AgentQA either has locatable citations or fails closed
with a visible citation blocker, and checks the History browser workflow. It
prints only statuses/counts and never raw answers, raw chunks, prompts, provider
payloads, tokens, logs, or private endpoints.
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

from check_weknora_native_agentqa_workflow import _select_agent_id
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
    marker = f"WNX-P1-07 marker {run_id}"
    query = f"What validates {marker}?"
    with tempfile.TemporaryDirectory(prefix="pa-wnx-history-citation-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'history-citation.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            selected_kb_id = _selected_kb_id(backend_port)
            document = _upload_document(backend_port, selected_kb_id, run_id, marker)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            indexed = _wait_until_indexed(backend_port, document_id)
            external_doc_id = str(indexed.get("external_doc_id") or "")
            _assert(bool(external_doc_id), "native document id saved")

            chat_result = _run_knowledge_chat(
                backend_port=backend_port,
                run_id=run_id,
                query=query,
                external_doc_id=external_doc_id,
            )
            chat_history = _history_detail(backend_port, chat_result)
            chat_citations = _detail_citations(chat_history)
            _assert(chat_history["output"].get("evidence_state") == "weknora", "knowledge-chat history evidence is WeKnora")
            _assert(int(chat_history["output"].get("traceable_citation_count") or 0) > 0, "knowledge-chat citations are traceable")
            chat_location = _locate_first_citation(backend_port, chat_citations)
            _assert(bool(chat_location.get("located")), "knowledge-chat citation locator succeeded")

            agent_result = _run_agentqa(backend_port=backend_port, run_id=run_id)
            agent_history = _history_detail(backend_port, agent_result)
            agent_citations = _detail_citations(agent_history)
            agent_blocked = bool(agent_history["output"].get("citation_blocked"))
            if agent_citations:
                _assert(int(agent_history["output"].get("traceable_citation_count") or 0) > 0, "AgentQA citations are traceable")
                agent_location = _locate_first_citation(backend_port, agent_citations)
                _assert(bool(agent_location.get("located")), "AgentQA citation locator succeeded")
            else:
                _assert(agent_blocked, "AgentQA citation blocker is visible in history")
                _assert(
                    agent_history["output"].get("evidence_state") == "citation_blocked",
                    "AgentQA history evidence_state is citation_blocked",
                )
                _assert(
                    bool(agent_history["output"].get("citation_blocker")),
                    "AgentQA blocker reason is persisted",
                )
                blocked_history = _request_json(
                    backend_port,
                    "GET",
                    "/api/history?evidence_state=citation_blocked",
                )
                _assert(
                    _history_contains(blocked_history, str(agent_history["output"].get("id") or "")),
                    "history filter finds citation-blocked output",
                )

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_history_dom(
                    port=frontend_port,
                    user_data_dir=temp_path / "chrome-profile",
                    expect_blocked=agent_blocked,
                )
                for marker_text in ("历史", "Native 知识对话", "Native AgentQA", "可定位"):
                    _assert(marker_text in dom, f"browser DOM contains {marker_text}")
                if agent_blocked:
                    _assert("引用阻断" in dom, "browser DOM shows citation blocker")

            print("WeKnora native history/citation unification")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- knowledge_chat: saved_citations={citations} traceable={traceable} locator=located".format(
                    citations=len(chat_citations),
                    traceable=int(chat_history["output"].get("traceable_citation_count") or 0),
                )
            )
            print(
                "- agentqa: saved_citations={citations} traceable={traceable} citation_blocked={blocked}".format(
                    citations=len(agent_citations),
                    traceable=int(agent_history["output"].get("traceable_citation_count") or 0),
                    blocked=str(agent_blocked).lower(),
                )
            )
            print("- history: filters distinguish WeKnora and citation_blocked outputs")
            if browser_mode:
                print("- browser: History page rendered native workflow evidence states")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _selected_kb_id(port: int) -> str:
    overview = _request_json(port, "GET", "/api/knowledge-bases/native/overview?limit=10")
    selected_kb_id = _active_or_first_kb_id(overview)
    _assert(bool(selected_kb_id), "active KB id is available internally")
    return selected_kb_id


def _upload_document(port: int, kb_id: str, run_id: str, marker: str) -> dict[str, Any]:
    body = (
        f"# WNX-P1-07 history citation {run_id}\n\n"
        f"{marker} validates native history persistence and citation locators.\n\n"
        "The workflow must expose traceable citations or a visible citation blocker.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnx-p1-07-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNX-P1-07 history citation {run_id}",
            "document_type": "wnx_history_citation",
            "source": "wnx_p1_07_file",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _run_knowledge_chat(
    *,
    backend_port: int,
    run_id: str,
    query: str,
    external_doc_id: str,
) -> dict[str, Any]:
    result = _request_json_timeout(
        backend_port,
        "POST",
        "/api/rag/knowledge-chat",
        {
            "query": query,
            "title": f"WNX-P1-07 native chat {run_id}",
            "knowledge_ids": [external_doc_id],
            "current_run": {"expected_external_doc_ids": [external_doc_id]},
        },
        timeout=180,
    )
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    _assert(output.get("status") == "completed", "native knowledge-chat output completed")
    _assert(int(runtime.get("saved_citation_count") or 0) > 0, "knowledge-chat saved citations")
    return result


def _run_agentqa(*, backend_port: int, run_id: str) -> dict[str, Any]:
    catalog = _request_json(backend_port, "GET", "/api/analysis/native-agents")
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    _assert(catalog.get("source") == "weknora_api", "agent catalog uses WeKnora source")
    _assert(len(agents) > 0, "native agent catalog returned agents")
    agent_id = _select_agent_id(catalog, agents)
    _assert(bool(agent_id), "selected native agent id is available")
    result = _request_json_timeout(
        backend_port,
        "POST",
        "/api/analysis/native-agentqa",
        {
            "query": f"用一句话回答：WNX-P1-07 history citation {run_id} 是否可运行？",
            "title": f"WNX-P1-07 native AgentQA {run_id}",
            "agent_id": agent_id,
        },
        timeout=180,
    )
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    _assert(output.get("status") == "completed", "native AgentQA output completed")
    _assert(bool(runtime.get("native_session_id")), "native AgentQA session id returned")
    return result


def _history_detail(port: int, result: dict[str, Any]) -> dict[str, Any]:
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    output_id = str(output.get("id") or "")
    _assert(bool(output_id), "output id returned")
    detail = _request_json(port, "GET", f"/api/history/{output_id}")
    detail_output = detail.get("output") if isinstance(detail.get("output"), dict) else {}
    _assert(detail_output.get("id") == output_id, "history detail returns output")
    return detail


def _detail_citations(detail: dict[str, Any]) -> list[dict[str, Any]]:
    citations = detail.get("citations")
    return [item for item in citations if isinstance(item, dict)] if isinstance(citations, list) else []


def _locate_first_citation(port: int, citations: list[dict[str, Any]]) -> dict[str, Any]:
    _assert(len(citations) > 0, "citation is available for locator")
    citation = citations[0]
    return _request_json(
        port,
        "POST",
        "/api/citations/locate",
        {
            "id": citation.get("id"),
            "document_id": citation.get("document_id"),
            "external_doc_id": citation.get("external_doc_id"),
            "chunk_id": citation.get("chunk_id"),
            "evidence_id": citation.get("evidence_id"),
            "source_type": citation.get("source_type"),
            "wiki_page_id": citation.get("wiki_page_id"),
            "source": citation.get("source"),
            "metadata_json": citation.get("metadata_json"),
        },
    )


def _history_contains(history: dict[str, Any], output_id: str) -> bool:
    items = history.get("items")
    if not isinstance(items, list):
        return False
    return any(isinstance(item, dict) and item.get("id") == output_id for item in items)


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


def _dump_history_dom(port: int, user_data_dir: Path, expect_blocked: bool) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/history', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        required = ["Native 知识对话", "Native AgentQA", "可定位"]
        if expect_blocked:
            required.append("引用阻断")
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if all(marker in dom for marker in required):
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
