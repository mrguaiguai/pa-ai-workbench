"""Live WNX-P3-01 product workflow browser matrix.

The script starts temporary PA backend/frontend services, opens the internal
production workbench routes in local Chrome, and validates desktop/mobile DOM
and layout safety. It prints only route names, viewport names, counts, and
status summaries; it never prints raw provider payloads, credentials, ids, logs,
screenshots, or local database paths.
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
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


VIEWPORTS = (
    {"name": "Desktop", "width": 1440, "height": 900, "mobile": False},
    {"name": "Mobile", "width": 390, "height": 844, "mobile": True},
)

ROUTES = (
    {
        "name": "home",
        "hash": "/",
        "markers": ("工作台首页", "WeKnora", "能力"),
        "backend_marker": "weknora_api",
    },
    {
        "name": "library",
        "hash": "/library",
        "markers": ("资料库", "活动知识库", "上传目标"),
        "backend_marker": "活动知识库",
    },
    {
        "name": "analysis",
        "hash": "/analysis",
        "markers": ("智能分析台", "分析流", "运行分析"),
        "backend_marker": "暂无会话",
    },
    {
        "name": "rag-debug",
        "hash": "/rag-debug",
        "markers": ("RAG 检索调试", "原生知识问答", "暂无调试轨迹"),
        "backend_marker": "运行问答",
    },
    {
        "name": "wiki",
        "hash": "/wiki",
        "markers": ("Wiki 知识库", "workflow", "pages"),
        "backend_marker": "read",
    },
    {
        "name": "history",
        "hash": "/history",
        "markers": ("生成历史", "结果", "警告"),
        "backend_marker": "证据状态",
    },
    {
        "name": "capabilities",
        "hash": "/capabilities",
        "markers": ("能力中心", "wnx-p0-02", "Data sources / connectors"),
        "backend_marker": "pa_backend_bff",
    },
)


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnx-product-matrix-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'product-matrix.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            _assert(status.get("schema_version") == "wnx-p0-02", "native status schema is current")
            _assert(status.get("source") == "pa_backend_bff", "native status uses PA BFF")
            _assert(status.get("evidence_type") == "live_api", "native status uses live API evidence")
            _assert(bool(status.get("masked")), "native status is masked")
            _assert(int(status.get("group_count") or 0) == 15, "native status has 15 groups")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            results = _run_browser_matrix(frontend_port, Path(temp_dir) / "chrome-profile")
            route_count = len({result["route"] for result in results})
            check_count = len(results)

            print("WeKnora native product workflow browser matrix")
            print("- decision: PASS")
            print("- evidence_type: live_browser_evidence")
            print(f"- api: native_status_schema={status.get('schema_version')} groups={int(status.get('group_count') or 0)}")
            print(f"- browser: routes={route_count} viewport_checks={check_count}")
            for viewport in VIEWPORTS:
                viewport_results = [result for result in results if result["viewport"] == viewport["name"]]
                print(f"- {viewport['name'].lower()}: pass={len(viewport_results)} overflow=0 visible_overlap=0")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _run_browser_matrix(port: int, user_data_dir: Path) -> list[dict[str, str]]:
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
        results: list[dict[str, str]] = []
        for viewport in VIEWPORTS:
            for route in ROUTES:
                result = _validate_route(debug_port, port, route, viewport)
                results.append(result)
        return results
    finally:
        _terminate(chrome)


def _validate_route(
    debug_port: int,
    frontend_port: int,
    route: dict[str, Any],
    viewport: dict[str, Any],
) -> dict[str, str]:
    target_url = f"http://127.0.0.1:{frontend_port}/#{route['hash']}"
    target = _request_chrome_json(
        debug_port,
        "PUT",
        f"/json/new?{quote(target_url, safe=':/?=&')}",
    )
    ws_url = str(target.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise RuntimeError("Chrome did not return a page websocket")

    deadline = time.time() + 45
    last_state: dict[str, Any] = {}
    while time.time() < deadline:
        state = _evaluate_page_state(ws_url, viewport)
        last_state = state
        text = str(state.get("text") or "")
        if all(marker in text for marker in route["markers"]):
            _assert(route["backend_marker"] in text, f"{route['name']} route shows backend-backed state")
            _assert(bool(state.get("ready")), f"{route['name']} route is visually ready")
            _assert(not state.get("horizontalOverflow"), f"{route['name']} route has no horizontal overflow")
            _assert(not state.get("visibleOverlap"), f"{route['name']} route has no incoherent visible overlap")
            _assert(not state.get("secretLikeText"), f"{route['name']} route does not render secret-like text")
            _assert(not state.get("unsafePassClaim"), f"{route['name']} route has no unverified PASS claim")
            return {"viewport": str(viewport["name"]), "route": str(route["name"])}
        time.sleep(1)
    missing = [marker for marker in route["markers"] if marker not in str(last_state.get("text") or "")]
    raise AssertionError(f"{route['name']} route missing markers: {', '.join(missing)}")


def _evaluate_page_state(ws_url: str, viewport: dict[str, Any]) -> dict[str, Any]:
    expression = r"""
(() => {
  const text = document.body ? document.body.innerText : "";
  const width = window.innerWidth;
  const visible = Array.from(document.querySelectorAll("button, a, input, textarea, select, [role='button'], h1, h2, h3, p, span, strong, label"))
    .filter((node) => {
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return style.visibility !== "hidden" &&
        style.display !== "none" &&
        rect.width > 1 &&
        rect.height > 1 &&
        rect.bottom >= 0 &&
        rect.right >= 0 &&
        rect.top <= window.innerHeight &&
        rect.left <= window.innerWidth;
    });
  let visibleOverlap = false;
  for (let index = 0; index < visible.length && !visibleOverlap; index += 1) {
    const a = visible[index].getBoundingClientRect();
    for (let other = index + 1; other < visible.length; other += 1) {
      const b = visible[other].getBoundingClientRect();
      const area = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
        Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
      const minArea = Math.min(a.width * a.height, b.width * b.height);
      if (area > 24 && minArea > 0 && area / minArea > 0.65) {
        if (!visible[index].contains(visible[other]) && !visible[other].contains(visible[index])) {
          visibleOverlap = true;
          break;
        }
      }
    }
  }
  const secretLikeText = /Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{14,}|BEGIN .*PRIVATE KEY/i.test(text);
  const unsafePassClaim = /(fixture-only|mock|cached|static UI)\s+PASS\s+(allowed|counts|accepted)/i.test(text);
  return {
    text,
    ready: Boolean(document.querySelector(".workbench-shell")) && document.readyState === "complete",
    horizontalOverflow: document.documentElement.scrollWidth > width + 3 || document.body.scrollWidth > width + 3,
    visibleOverlap,
    secretLikeText,
    unsafePassClaim
  };
})()
"""
    result = _cdp_eval(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
        },
        viewport,
    )
    if not isinstance(result, dict):
        raise RuntimeError("Chrome returned non-object page state")
    return result


def _cdp_eval(
    ws_url: str,
    method: str,
    params: dict[str, Any],
    viewport: dict[str, Any],
) -> Any:
    parsed = urlparse(ws_url)
    if parsed.hostname is None or parsed.port is None:
        raise RuntimeError("Chrome websocket URL is invalid")
    with socket.create_connection((parsed.hostname, parsed.port), timeout=10) as sock:
        _websocket_handshake(sock, parsed.path)
        seq = 0

        def send(send_method: str, send_params: dict[str, Any] | None = None) -> int:
            nonlocal seq
            seq += 1
            _websocket_send_json(sock, {"id": seq, "method": send_method, "params": send_params or {}})
            return seq

        send("Page.enable")
        send("Runtime.enable")
        send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": viewport["width"],
                "height": viewport["height"],
                "deviceScaleFactor": 1,
                "mobile": viewport["mobile"],
            },
        )
        time.sleep(2)
        eval_id = send(method, params)
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
        raise RuntimeError("Chrome CDP did not return an evaluation result")


if __name__ == "__main__":
    raise SystemExit(main())
