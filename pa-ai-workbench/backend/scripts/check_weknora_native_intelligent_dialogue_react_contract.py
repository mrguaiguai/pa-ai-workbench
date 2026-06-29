"""Live WNID-P2-02 native AgentQA ReACT run-contract check.

The script starts temporary PA backend/frontend services, uploads a sanitized
document into WeKnora, runs native AgentQA through PA, verifies the structured
stream contract plus continuity/citation persistence, and drives `#/dialogue`
in headless Chrome until the Run Contract UI is visible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_document_lifecycle import _active_or_first_kb_id
from check_weknora_native_document_lifecycle import _multipart_request
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_intelligent_dialogue_quick_qa import _evaluate_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_quick_qa import _read_dom_text_content_via_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _request_json_timeout
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


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    marker = f"WNID-P2-02 marker {run_id}"
    query = f"Use the native AgentQA tools to answer what validates {marker}."
    with tempfile.TemporaryDirectory(prefix="pa-wnid-react-contract-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'react-contract.db'}"
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

            document = _upload_react_contract_document(backend_port, selected_kb_id, run_id, marker)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            indexed = _wait_until_indexed(backend_port, document_id)
            external_doc_id = str(indexed.get("external_doc_id") or "")
            _assert(bool(external_doc_id), "native document id saved")

            catalog = _request_json(backend_port, "GET", "/api/analysis/native-agents")
            agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
            agent_id = _select_agent_id(catalog, agents)
            _assert(bool(agent_id), "selected native Agent id is available")

            result = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": query,
                    "title": f"WNID-P2-02 ReACT contract {run_id}",
                    "agent_id": agent_id,
                    "knowledge_ids": [external_doc_id],
                },
                timeout=180,
            )
            runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
            output = result.get("output") if isinstance(result.get("output"), dict) else {}
            citations = result.get("citations") if isinstance(result.get("citations"), list) else []
            contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
            selected_agent = runtime.get("selected_agent") if isinstance(runtime.get("selected_agent"), dict) else {}
            continuity = (
                runtime.get("conversation_continuity")
                if isinstance(runtime.get("conversation_continuity"), dict)
                else {}
            )
            _assert(output.get("status") == "completed", "native AgentQA output completed")
            _assert(runtime.get("agent_id") == agent_id, "runtime records selected Agent id")
            _assert(selected_agent.get("id") == agent_id, "selected Agent contract is present")
            _assert(bool(runtime.get("native_session_id")), "native session id returned")
            _assert(_event_count(contract, "answer") > 0, "native AgentQA streamed answer events")
            _assert(bool(contract.get("complete_seen")), "native AgentQA emitted complete event")
            _assert(bool(contract.get("react_trace_seen")), "native AgentQA emitted ReACT trace events")
            _assert(_event_count(contract, "tool_call") > 0, "native AgentQA emitted tool_call events")
            _assert(_event_count(contract, "tool_result") > 0, "native AgentQA emitted tool_result events")
            _assert(int(runtime.get("reference_count") or 0) > 0, "native AgentQA returned references")
            _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved AgentQA citations")
            _assert(bool(continuity.get("user_message_persisted")), "user message persisted")
            _assert(bool(continuity.get("assistant_message_persisted")), "assistant message persisted")
            _assert(int(continuity.get("message_count") or 0) >= 2, "conversation continuity has messages")
            _assert(_no_secret_payload(result), "AgentQA contract response is sanitized")

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_agentqa")
            _assert(int(history.get("total") or 0) > 0, "history lists native AgentQA output")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "Tool Trace",
                "Run Contract",
                "selected_agent",
                "conversation_continuity",
                "thinking",
                "tool_call",
                "tool_result",
                "answer",
                "complete",
            )
            dom = _dialogue_dom_after_agentqa_run(
                frontend_port,
                temp_path / "chrome-profile",
                query,
                f"WNID-P2-02 browser {run_id}",
                external_doc_id,
                markers,
            )
            _assert("高级工具" not in dom, "Run Contract is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue contract UI does not render secret-shaped text")

            print("WeKnora native intelligent dialogue ReACT contract")
            print("- decision: PASS")
            print("- task: WNID-P2-02")
            print("- evidence_type: live_api + live_browser")
            print(
                "- api: "
                f"agentqa=live thinking={_event_count(contract, 'thinking')} "
                f"tool_call={_event_count(contract, 'tool_call')} "
                f"tool_result={_event_count(contract, 'tool_result')} "
                f"references={int(runtime.get('reference_count') or 0)} "
                f"answer={_event_count(contract, 'answer')} complete=true "
                f"citations={int(runtime.get('saved_citation_count') or 0)} "
                "continuity=passed selected_agent=present"
            )
            print("- browser: route=dialogue run_contract=visible markers=10 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _upload_react_contract_document(port: int, kb_id: str, run_id: str, marker: str) -> dict[str, Any]:
    body = (
        f"# WNID-P2-02 native AgentQA ReACT contract {run_id}\n\n"
        f"{marker} validates the native AgentQA ReACT run contract in PA.\n\n"
        "The expected evidence is thinking/tool_call/tool_result/answer/complete stream metadata, "
        "conversation continuity, and saved traceable citations.\n"
    ).encode("utf-8")
    response = _multipart_request(
        port=port,
        path="/api/documents",
        file_name=f"wnid-p2-02-{run_id}.md",
        file_content=body,
        fields={
            "title": f"WNID-P2-02 ReACT contract {run_id}",
            "document_type": "wnid_react_contract",
            "source": "wnid_p2_02_file",
            "knowledge_base_id": kb_id,
        },
    )
    document = response.get("document") if isinstance(response.get("document"), dict) else {}
    return document


def _select_agent_id(catalog: dict[str, Any], agents: list[Any]) -> str:
    selected = str(catalog.get("selected_agent_id") or "").strip()
    if selected:
        return selected
    for preferred in ("builtin-wiki-researcher", "builtin-smart-reasoning", "builtin-document-assistant"):
        if any(isinstance(agent, dict) and agent.get("id") == preferred for agent in agents):
            return preferred
    for agent in agents:
        if isinstance(agent, dict):
            agent_id = str(agent.get("id") or "").strip()
            if agent_id:
                return agent_id
    return ""


def _event_count(contract: dict[str, Any], event_type: str) -> int:
    try:
        return int(contract.get(f"{event_type}_count") or 0)
    except (TypeError, ValueError):
        return 0


def _dialogue_dom_after_agentqa_run(
    port: int,
    user_data_dir: Path,
    query: str,
    title: str,
    external_doc_id: str,
    markers: tuple[str, ...],
) -> str:
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
        deadline = time.time() + 45
        while time.time() < deadline:
            dom = _read_dom_text_content_via_cdp(ws_url)
            if "运行 AgentQA" in dom:
                break
            time.sleep(1)
        _fill_and_submit_agentqa(ws_url, query, title, external_doc_id)
        deadline = time.time() + 180
        last_dom = ""
        while time.time() < deadline:
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(2)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue ReACT contract DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _fill_and_submit_agentqa(ws_url: str, query: str, title: str, external_doc_id: str) -> None:
    script = f"""
    const setValue = (element, value) => {{
      const setter = Object.getOwnPropertyDescriptor(element.__proto__, 'value').set;
      setter.call(element, value);
      element.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }};
    const queryArea = document.querySelector('.dialogue-query-field textarea');
    if (queryArea) setValue(queryArea, {json.dumps(query)});
    const inputs = Array.from(document.querySelectorAll('.dialogue-control-grid input'));
    if (inputs[0]) setValue(inputs[0], {json.dumps(title)});
    if (inputs[2]) setValue(inputs[2], {json.dumps(external_doc_id)});
    const submit = Array.from(document.querySelectorAll('button'))
      .find((button) => (button.textContent || '').includes('运行 AgentQA'));
    if (submit) submit.click();
    true;
    """
    _evaluate_cdp(ws_url, script)


def _no_secret_payload(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, default=str)
    blocked = (
        "Bearer ",
        "BEGIN " + "PRIVATE" + " KEY",
        "BEGIN RSA " + "PRIVATE" + " KEY",
        "BEGIN OPENSSH " + "PRIVATE" + " KEY",
    )
    return not any(marker in text for marker in blocked)


if __name__ == "__main__":
    raise SystemExit(main())
