"""Live browser check for the WNID first-class dialogue shell.

The script starts temporary PA backend/frontend services, verifies the native
Agent catalog through PA, opens the `#/dialogue` route in headless Chrome, and
checks that Agent picker, run controls, strategy summary, tool trace, citations,
and history are visible without opening a hidden advanced panel.
"""

from __future__ import annotations

from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.parse import quote
from urllib.parse import urlparse

from check_weknora_native_chunk_management import _start_backend_with_cors
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
    with tempfile.TemporaryDirectory(prefix="pa-wnid-dialogue-shell-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'dialogue-shell.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            catalog_summary = _validate_agent_catalog(backend_port)
            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "智能对话",
                "Native Intelligent Dialogue",
                "Agent",
                "History",
                "Strategy",
                "Tool Trace",
                "Citations",
                "运行 AgentQA",
            )
            dom = _wait_for_dialogue_dom(frontend_port, Path(temp_dir) / "chrome-profile", markers)
            _assert("高级工具" not in dom, "dialogue shell is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue shell does not render secret-shaped text")
            print("WeKnora native intelligent dialogue shell")
            print("- decision: PASS")
            print("- task: WNID-P1-01")
            print("- evidence_type: live_api + live_browser")
            print(
                "- api: "
                f"agents={catalog_summary['agents']} "
                f"catalog_status={catalog_summary['status']} "
                f"suggestions={catalog_summary['suggestions']} "
                f"active_kb={catalog_summary['active_kb']}"
            )
            print("- browser: route=dialogue markers=8 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _validate_agent_catalog(port: int) -> dict[str, str]:
    catalog = _request_json(port, "GET", "/api/analysis/native-agents")
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    suggestions = (
        catalog.get("suggested_questions")
        if isinstance(catalog.get("suggested_questions"), list)
        else []
    )
    surfaces = catalog.get("surfaces") if isinstance(catalog.get("surfaces"), dict) else {}
    _assert(catalog.get("source") == "weknora_api", "native Agent catalog uses WeKnora API")
    _assert(str(catalog.get("status")) in {"live", "partial"}, "native Agent catalog status is explicit")
    _assert(len(agents) > 0, "native Agent catalog has at least one agent")
    _assert("suggested_questions" in surfaces, "suggested-question surface is reported")
    return {
        "agents": str(len(agents)),
        "status": str(catalog.get("status")),
        "suggestions": str(len(suggestions)),
        "active_kb": "configured" if catalog.get("active_knowledge_base_id") else "not_configured",
    }


def _wait_for_dialogue_dom(port: int, user_data_dir: Path, markers: tuple[str, ...]) -> str:
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
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(1)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _has_secret_like_text(text: str) -> bool:
    markers = (
        "Bearer ",
        "BEGIN " + "PRIVATE KEY",
        "BEGIN RSA " + "PRIVATE KEY",
        "BEGIN OPENSSH " + "PRIVATE KEY",
    )
    return any(marker in text for marker in markers)


def _read_dom_text_content_via_cdp(ws_url: str) -> str:
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
                "expression": "document.body ? document.body.textContent : ''",
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
                return str(value.get("value") or "")
        raise RuntimeError("Chrome CDP did not return DOM text")


if __name__ == "__main__":
    raise SystemExit(main())
