"""Live WNFC-P6-01 local productivity browser matrix.

The script starts temporary PA backend/frontend services, validates live PA and
WeKnora status APIs, runs the WNFC acceptance checker in in-progress mode, and
opens the local workbench routes in headless Chrome across desktop/mobile
viewports. Output is intentionally sanitized: it prints route names, counts, and
status summaries only.
"""

from __future__ import annotations

from pathlib import Path
import socket
import subprocess
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_SCRIPT = PROJECT_ROOT / "scripts" / "validation" / "check_weknora_native_full_completion_acceptance.py"

VIEWPORTS = (
    {"name": "Desktop", "width": 1440, "height": 900, "mobile": False},
    {"name": "Mobile", "width": 390, "height": 844, "mobile": True},
)

ROUTES = (
    {
        "name": "home",
        "hash": "/",
        "markers": ("工作台首页", "常用功能", "管理资料", "设置与调试"),
        "backend_marker": "选择要处理的事项",
    },
    {
        "name": "library",
        "hash": "/library",
        "markers": ("资料库", "知识库管理", "目标知识库", "全部知识库"),
        "backend_marker": "当前活动",
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
        "markers": ("Wiki 知识库", "搜索", "页面"),
        "backend_marker": "阅读",
    },
    {
        "name": "history",
        "hash": "/history",
        "markers": ("生成历史", "筛选", "结果列表"),
        "backend_marker": "结果",
    },
    {
        "name": "capabilities",
        "hash": "/capabilities",
        "markers": ("设置与调试", "Native 状态", "运行配置", "高级调试"),
        "backend_marker": "pa_backend_bff",
        "required_text": ("数据源调试", "告警", "wnx-p0-02"),
    },
)


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-browser-matrix-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'wnfc-browser-matrix.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            api_summary = _validate_live_api_contract(backend_port)
            acceptance_summary = _run_acceptance_checker()

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            results = _run_browser_matrix(frontend_port, Path(temp_dir) / "chrome-profile")
            route_count = len({result["route"] for result in results})
            check_count = len(results)

            print("WeKnora native full-completion local productivity browser matrix")
            print("- decision: PASS")
            print("- task: WNFC-P6-01")
            print("- evidence_type: live_api + live_browser + checker_execution")
            print(
                "- api: "
                f"native_schema={api_summary['native_schema']} "
                f"groups={api_summary['native_groups']} "
                f"model_backend={api_summary['model_backend']} "
                f"audit_endpoint={api_summary['audit_endpoint']}"
            )
            print(
                "- acceptance: "
                f"score={acceptance_summary['score']} "
                f"final_ready={acceptance_summary['final_ready']}"
            )
            print(f"- browser: routes={route_count} viewport_checks={check_count}")
            for viewport in VIEWPORTS:
                viewport_results = [result for result in results if result["viewport"] == viewport["name"]]
                print(f"- {viewport['name'].lower()}: pass={len(viewport_results)} overflow=0 visible_overlap=0")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _validate_live_api_contract(port: int) -> dict[str, str]:
    status = _request_json(port, "GET", "/api/status")
    capabilities = status.get("backend_capabilities") if isinstance(status, dict) else None
    _assert(isinstance(capabilities, dict), "PA status exposes backend capabilities")
    _assert(capabilities.get("active_backend") == "weknora_api", "PA active backend is WeKnora API")

    model_status = _request_json(port, "GET", "/api/model/status")
    _assert(isinstance(model_status, dict), "model status response is an object")
    _assert(bool(model_status.get("configured")), "model status is configured")
    _assert(model_status.get("mock_mode") is False, "model status is not mock mode")
    model_backend = str(model_status.get("chat_provider") or model_status.get("bridge_status") or "unknown")

    native_status = _request_json(port, "GET", "/api/native/status?limit=20")
    _assert(native_status.get("schema_version") == "wnx-p0-02", "native status schema is current")
    _assert(native_status.get("source") == "pa_backend_bff", "native status uses PA BFF")
    _assert(native_status.get("evidence_type") == "live_api", "native status uses live API evidence")
    _assert(bool(native_status.get("masked")), "native status is masked")
    _assert(int(native_status.get("group_count") or 0) == 15, "native status has 15 groups")
    groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
    for group_id in ("mcp", "vector_store", "faq_tags_favorites_skills"):
        _assert(group_id in groups, f"native status includes {group_id}")
    _assert(str(groups["mcp"].get("status")) in {"partial", "blocked", "live"}, "MCP status is explicit")
    _assert(str(groups["vector_store"].get("status")) in {"partial", "blocked", "live"}, "vector status is explicit")

    audit_events = _request_json(port, "GET", "/api/native-audit/events?limit=1")
    _assert(isinstance(audit_events, dict), "native audit events response is an object")
    _assert("items" in audit_events and "total" in audit_events, "native audit event list is available")

    return {
        "native_schema": str(native_status.get("schema_version")),
        "native_groups": str(int(native_status.get("group_count") or 0)),
        "model_backend": model_backend,
        "audit_endpoint": "available",
    }


def _run_acceptance_checker() -> dict[str, str]:
    completed = subprocess.run(
        [str(PROJECT_ROOT / "apps" / "pa-api" / ".venv" / "bin" / "python"), str(ACCEPTANCE_SCRIPT)],
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    output = "\n".join([completed.stdout, completed.stderr])
    if completed.returncode != 0:
        raise AssertionError(f"WNFC acceptance checker failed: {_safe_line(output)}")
    score = "unknown"
    final_ready = "unknown"
    for line in completed.stdout.splitlines():
        if line.startswith("- current score:"):
            score = line.split(":", 1)[1].strip()
        if line.startswith("- final_ready:"):
            final_ready = line.split(":", 1)[1].strip()
    _assert(score != "unknown", "acceptance checker reports current score")
    _assert(final_ready in {"true", "false"}, "acceptance checker reports final readiness")
    return {"score": score, "final_ready": final_ready}


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
        route_markers = tuple(route["markers"]) + tuple(route.get("required_text", ()))
        if all(marker in text for marker in route_markers):
            _assert(route["backend_marker"] in text, f"{route['name']} route shows backend-backed state")
            _assert(bool(state.get("ready")), f"{route['name']} route is visually ready")
            _assert(not state.get("horizontalOverflow"), f"{route['name']} route has no horizontal overflow")
            _assert(not state.get("visibleOverlap"), f"{route['name']} route has no incoherent visible overlap")
            _assert(not state.get("secretLikeText"), f"{route['name']} route does not render secret-like text")
            _assert(not state.get("unsafePassClaim"), f"{route['name']} route has no unverified PASS claim")
            return {"viewport": str(viewport["name"]), "route": str(route["name"])}
        time.sleep(1)
    route_markers = tuple(route["markers"]) + tuple(route.get("required_text", ()))
    missing = [marker for marker in route_markers if marker not in str(last_state.get("text") or "")]
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


def _safe_line(text: str) -> str:
    line = " ".join(text.split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        line = line.replace(marker, "[redacted]")
    return line[:260]


if __name__ == "__main__":
    raise SystemExit(main())
