"""Live WNX-P1-05 native AgentQA/custom Agent workflow smoke.

The script starts temporary PA backend/frontend services, validates the native
custom Agent catalog through PA, runs native AgentQA through PA, verifies output
history plus the explicit citation blocker when native references are absent,
and checks the Analysis browser workflow. It prints only statuses/counts and
never raw answers, prompts, provider payloads, service tokens, logs, or private
endpoints.
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
    query = f"用一句话回答：WNX-P1-05 native AgentQA workflow {run_id} 是否可运行？"
    with tempfile.TemporaryDirectory(prefix="pa-wnx-agentqa-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'agentqa.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            catalog = _request_json(
                backend_port,
                "GET",
                "/api/analysis/native-agents",
            )
            agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
            surfaces = catalog.get("surfaces") if isinstance(catalog.get("surfaces"), dict) else {}
            _assert(catalog.get("source") == "weknora_api", "agent catalog uses WeKnora source")
            _assert(len(agents) > 0, "native agent catalog returned agents")
            _assert(surfaces.get("list") == "live", "agent list surface is live")
            _assert(surfaces.get("copy") == "backlog", "agent copy is explicit backlog")
            agent_id = _select_agent_id(catalog, agents)
            _assert(bool(agent_id), "selected native agent id is available")

            result = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": query,
                    "title": f"WNX-P1-05 native AgentQA {run_id}",
                    "agent_id": agent_id,
                },
                timeout=180,
            )
            runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
            output = result.get("output") if isinstance(result.get("output"), dict) else {}
            citations = result.get("citations") if isinstance(result.get("citations"), list) else []
            warnings = runtime.get("warnings") if isinstance(runtime.get("warnings"), list) else []
            _assert(output.get("status") == "completed", "native AgentQA output completed")
            _assert(runtime.get("agent_id") == agent_id, "runtime records selected agent id")
            _assert(bool(runtime.get("native_session_id")), "native session id returned")
            _assert(int(_event_count(runtime, "answer")) > 0, "native AgentQA streamed answer events")
            _assert("complete" in (runtime.get("event_counts") or {}), "native AgentQA emitted complete event")
            if int(runtime.get("reference_count") or 0) == 0:
                _assert(bool(runtime.get("citation_blocked")), "citation blocker is explicit")
                _assert(_has_citation_blocker(warnings), "citation blocker warning is persisted")
            else:
                _assert(len(citations) > 0, "traceable references were saved as citations")

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_agentqa")
            _assert(int(history.get("total") or 0) > 0, "history lists native AgentQA output")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_analysis_dom(frontend_port, temp_path / "chrome-profile")
                for marker in ("智能分析", "原生 AGENTQA", "运行原生 Agent"):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native AgentQA/custom Agent workflow")
            print("- decision: PASS")
            print("- evidence_type: live_api")
            print(f"- catalog: agents={len(agents)} presets={len(catalog.get('presets') or [])} copy=backlog")
            print(
                "- agentqa: answer_events={answers} references={refs} saved_citations={citations} citation_blocked={blocked}".format(
                    answers=int(_event_count(runtime, "answer")),
                    refs=int(runtime.get("reference_count") or 0),
                    citations=len(citations),
                    blocked=str(bool(runtime.get("citation_blocked"))).lower(),
                )
            )
            print("- history: native_agentqa output listed")
            if browser_mode:
                print("- browser: Analysis page rendered native AgentQA workflow")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _select_agent_id(catalog: dict[str, Any], agents: list[Any]) -> str:
    selected = str(catalog.get("selected_agent_id") or "").strip()
    if selected:
        return selected
    for agent in agents:
        if isinstance(agent, dict):
            agent_id = str(agent.get("id") or "").strip()
            if agent_id:
                return agent_id
    return ""


def _event_count(runtime: dict[str, Any], event_type: str) -> int:
    counts = runtime.get("event_counts")
    if not isinstance(counts, dict):
        return 0
    try:
        return int(counts.get(event_type) or 0)
    except (TypeError, ValueError):
        return 0


def _has_citation_blocker(warnings: list[Any]) -> bool:
    return any("CITATION_BLOCKED" in str(warning) for warning in warnings)


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


def _dump_analysis_dom(port: int, user_data_dir: Path) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/analysis', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if "原生 AGENTQA" in dom and "运行原生 Agent" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
