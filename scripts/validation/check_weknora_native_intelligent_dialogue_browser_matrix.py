"""Live WNID-P8-01 intelligent dialogue browser matrix.

The script starts temporary PA backend/frontend services, prepares a scoped
native Wiki Agent for suggested questions, starts the approved safe local MCP
server when needed, verifies live MCP/Web Search status through PA, and checks
the `#/dialogue` browser surface across desktop and mobile viewports.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.request import urlopen
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_intelligent_dialogue_quick_qa import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_suggested_questions import AGENT_CONFIRM_TOKEN
from check_weknora_native_intelligent_dialogue_suggested_questions import _create_readonly_wiki_agent
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
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


SAFE_MCP_SERVICE_NAME = "PA Safe Local MCP"
SAFE_MCP_TEST_TOKEN = "TEST_NATIVE_MCP_SERVICE"
SAFE_MCP_PORT = 8765
WEB_TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"
BROWSER_AGENT_ID = "builtin-wiki-researcher"


VIEWPORTS = (
    {"name": "desktop", "width": 1440, "height": 900, "mobile": False, "scale": 1},
    {"name": "mobile", "width": 390, "height": 844, "mobile": True, "scale": 3},
)


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    page_title = f"WNID P8 01 Browser Matrix {run_id}"
    page_slug = f"wnid-p8-01-{run_id}"
    agent_name = f"WNID-P8-01 Matrix Agent {run_id}"
    agent_id = ""
    temp_kb_id = ""
    direct_backend = _weknora_backend_from_env()
    mcp_server: subprocess.Popen[str] | None = None
    with tempfile.TemporaryDirectory(prefix="pa-wnid-browser-matrix-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'browser-matrix.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            mcp_server = _ensure_safe_mcp_server()
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            temp_kb_id, agent_id = _prepare_suggested_question_agent(
                direct_backend=direct_backend,
                backend_port=backend_port,
                run_id=run_id,
                page_slug=page_slug,
                page_title=page_title,
                agent_name=agent_name,
            )
            api_summary = _live_api_preflight(backend_port, agent_id, temp_kb_id, page_title)

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")

            viewport_results = []
            for viewport in VIEWPORTS:
                viewport_results.append(
                    _validate_dialogue_viewport(
                        port=frontend_port,
                        user_data_dir=temp_path / f"chrome-{viewport['name']}",
                        viewport=viewport,
                        agent_id=BROWSER_AGENT_ID,
                        kb_id=temp_kb_id,
                        page_title=page_title,
                    )
                )

            print("WeKnora native intelligent dialogue browser matrix")
            print("- decision: PASS")
            print("- task: WNID-P8-01")
            print("- evidence_type: live_browser + live_api + live_service")
            print(
                "- api: "
                f"agents={api_summary['agents']} suggestions={api_summary['suggestions']} "
                f"mcp_tools={api_summary['mcp_tools']} mcp_resources={api_summary['mcp_resources']} "
                f"web_provider={api_summary['web_provider']} web_test={api_summary['web_test']}"
            )
            for result in viewport_results:
                print(
                    "- browser: "
                    f"viewport={result['name']} size={result['width']}x{result['height']} "
                    f"markers={result['markers']} horizontal_overflow={str(result['overflow']).lower()} "
                    f"suggested_questions=panel_visible+api_live hidden_advanced_panel=false"
                )
            return 0
        finally:
            if agent_id:
                _delete_agent(backend_port, agent_id)
            if temp_kb_id:
                try:
                    direct_backend.delete_knowledge_base(temp_kb_id)
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)
            if mcp_server is not None:
                _terminate(mcp_server)


def _weknora_backend_from_env() -> WeKnoraApiBackend:
    settings = Settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _ensure_safe_mcp_server() -> subprocess.Popen[str] | None:
    if _safe_mcp_http_ok():
        return None
    server = subprocess.Popen(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "ops" / "safe_local_mcp_server.py"),
            "--host",
            "0.0.0.0",
            "--port",
            str(SAFE_MCP_PORT),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        if _safe_mcp_http_ok():
            return server
        if server.poll() is not None:
            break
        time.sleep(0.5)
    _terminate(server)
    raise AssertionError("safe local MCP server did not become reachable")


def _safe_mcp_http_ok() -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{SAFE_MCP_PORT}/mcp", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def _prepare_suggested_question_agent(
    *,
    direct_backend: WeKnoraApiBackend,
    backend_port: int,
    run_id: str,
    page_slug: str,
    page_title: str,
    agent_name: str,
) -> tuple[str, str]:
    kb = direct_backend.create_temporary_wiki_knowledge_base(
        name=f"WNID-P8-01 browser matrix KB {run_id}",
        description="Temporary KB for WNID browser matrix suggested questions.",
    )
    kb_id = str(kb.get("_native_kb_id") or "")
    _assert(bool(kb_id), "temporary browser-matrix Wiki KB was created")
    direct_backend.create_wiki_page(
        {
            "slug": page_slug,
            "title": page_title,
            "summary": "WNID browser matrix validation page.",
            "content": (
                "This page exists to validate the intelligent dialogue browser matrix. "
                "It supplies scoped Wiki evidence for native suggested questions."
            ),
            "page_type": "concept",
            "status": "published",
        },
        kb_id=kb_id,
    )
    agent_id = _create_readonly_wiki_agent(backend_port, agent_name, kb_id, run_id)
    return kb_id, agent_id


def _live_api_preflight(port: int, agent_id: str, kb_id: str, page_title: str) -> dict[str, Any]:
    catalog = _request_json(port, "GET", "/api/analysis/native-agents")
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    _assert(catalog.get("source") == "weknora_api", "native Agent catalog uses WeKnora")
    _assert(len(agents) > 0, "native Agent catalog returned agents")

    suggestions = _request_json(
        port,
        "GET",
        "/api/analysis/native-agents/{agent_id}/suggested-questions?knowledge_base_ids={kb_id}&limit=6".format(
            agent_id=quote(agent_id, safe=""),
            kb_id=quote(kb_id, safe=""),
        ),
    )
    questions = suggestions.get("questions") if isinstance(suggestions.get("questions"), list) else []
    _assert(any(page_title in str(item.get("question") or "") for item in questions if isinstance(item, dict)),
            "native suggested questions include scoped Wiki page")

    mcp_overview = _request_json(port, "GET", "/api/mcp/native/overview?limit=10")
    mcp_service_id = _safe_mcp_service_id(mcp_overview)
    _assert(bool(mcp_service_id), "safe local MCP service is listed")
    mcp_test = _request_json(
        port,
        "POST",
        f"/api/mcp/native/services/{quote(mcp_service_id, safe='')}/test",
        {"confirm_token": SAFE_MCP_TEST_TOKEN},
    )
    safe_test = _surface(mcp_test, "safe_test")
    _assert(safe_test.get("success") is True, "safe local MCP live test succeeds")

    web_overview = _request_json(port, "GET", "/api/web-search/native/overview?limit=10")
    web_provider_id = _duckduckgo_provider_id(web_overview)
    _assert(bool(web_provider_id), "DuckDuckGo Web Search provider is configured")
    web_test = _request_json(
        port,
        "POST",
        f"/api/web-search/native/providers/{quote(web_provider_id, safe='')}/test",
        {"confirm_token": WEB_TEST_CONFIRM_TOKEN},
    )
    provider_test = _surface(web_test, "provider_test")
    _assert(provider_test.get("success") is True, "DuckDuckGo provider saved test succeeds")

    _assert(_no_secret_payload(catalog), "Agent catalog is sanitized")
    _assert(_no_secret_payload(mcp_test), "MCP test payload is sanitized")
    _assert(_no_secret_payload(web_test), "Web Search test payload is sanitized")
    return {
        "agents": len(agents),
        "suggestions": len(questions),
        "mcp_tools": int(safe_test.get("tool_count") or 0),
        "mcp_resources": int(safe_test.get("resource_count") or 0),
        "web_provider": "duckduckgo",
        "web_test": "live",
    }


def _validate_dialogue_viewport(
    *,
    port: int,
    user_data_dir: Path,
    viewport: dict[str, Any],
    agent_id: str,
    kb_id: str,
    page_title: str,
) -> dict[str, Any]:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/', safe=':/?=&')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        _assert(bool(ws_url), "Chrome returned a page websocket")
        _set_viewport(ws_url, viewport)
        _wait_for_markers(
            ws_url,
            markers=[
                "智能对话",
                "智能问答对话",
                "资料库",
                "检索",
                "Wiki",
                "对话",
                "问题",
            ],
            timeout=60,
        )
        _select_agent_scope(ws_url, agent_id=agent_id, kb_id=kb_id)
        dom = _wait_for_markers(
            ws_url,
            markers=[
                "运行",
                "高级范围",
                "引用",
                "工具过程",
                "mode",
                "answer",
                "tools",
                "kb",
            ],
            timeout=90,
        )
        scope = _scope_metrics(ws_url)
        _assert(scope.get("agent_scope") == agent_id, f"{viewport['name']} selected built-in Wiki Agent")
        _assert(scope.get("kb_scope") == kb_id, f"{viewport['name']} KB selector is populated")
        _assert(scope.get("details_open") is True, f"{viewport['name']} source details are open")
        _assert("高级工具" not in dom, "dialogue browser matrix is not hidden behind advanced tools")
        _assert(not _has_secret_like_text(dom), "dialogue browser matrix does not render secrets")
        metrics = _layout_metrics(ws_url)
        overflow = bool(metrics.get("horizontal_overflow"))
        _assert(not overflow, f"{viewport['name']} viewport has no horizontal overflow: {metrics}")
        return {
            "name": viewport["name"],
            "width": viewport["width"],
            "height": viewport["height"],
            "markers": 15,
            "overflow": overflow,
        }
    finally:
        _terminate(chrome)


def _set_viewport(ws_url: str, viewport: dict[str, Any]) -> None:
    _evaluate_cdp(
        ws_url,
        "true",
        before_eval={
            "method": "Emulation.setDeviceMetricsOverride",
            "params": {
                "width": int(viewport["width"]),
                "height": int(viewport["height"]),
                "deviceScaleFactor": int(viewport["scale"]),
                "mobile": bool(viewport["mobile"]),
            },
        },
    )


def _wait_for_markers(ws_url: str, *, markers: list[str], timeout: float) -> str:
    deadline = time.time() + timeout
    last_dom = ""
    while time.time() < deadline:
        last_dom = _read_dom_text(ws_url)
        if all(marker in last_dom for marker in markers):
            return last_dom
        time.sleep(1)
    missing = [marker for marker in markers if marker not in last_dom]
    raise AssertionError(f"dialogue viewport missing markers: {', '.join(missing)}")


def _select_agent_scope(ws_url: str, *, agent_id: str, kb_id: str) -> None:
    deadline = time.time() + 60
    selected = False
    while time.time() < deadline:
        script = f"""
        const selectOption = (selector, predicate) => {{
          const element = document.querySelector(selector);
          if (!element) return false;
          const option = Array.from(element.options).find(predicate);
          if (!option) return false;
          element.value = option.value;
          element.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return true;
        }};
        const agentSelected = selectOption(
          'select[aria-label="Agent"]',
          (option) => option.value === {json.dumps(agent_id)}
        );
        const kbSelected = selectOption(
          'select[aria-label="知识库"]',
          (option) => option.value === {json.dumps(kb_id)}
        );
        const details = document.querySelector('button[title="来源详情"]');
        if (agentSelected && kbSelected && details && !document.querySelector('.dialogue-inspector')) details.click();
        agentSelected && kbSelected;
        """
        selected = bool(_evaluate_cdp(ws_url, script))
        if selected:
            break
        time.sleep(1)
    _assert(selected, "browser selected the scoped WNID matrix Agent and KB")


def _layout_metrics(ws_url: str) -> dict[str, Any]:
    value = _evaluate_cdp(
        ws_url,
        """
        (() => {
          const root = document.documentElement;
          const body = document.body;
          const scrollWidth = Math.max(root.scrollWidth, body ? body.scrollWidth : 0);
          const clientWidth = root.clientWidth;
          const offenders = Array.from(document.querySelectorAll('*'))
            .map((element) => {
              const rect = element.getBoundingClientRect();
              return {
                tag: element.tagName,
                className: String(element.className || ''),
                text: (element.textContent || '').trim().slice(0, 80),
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width)
              };
            })
            .filter((item) => item.right > clientWidth + 4 || item.left < -4)
            .sort((a, b) => Math.abs(b.right - clientWidth) - Math.abs(a.right - clientWidth))
            .slice(0, 5);
          return {
            scrollWidth,
            clientWidth,
            horizontal_overflow: scrollWidth > clientWidth + 4,
            offenders,
            containers: ['.workbench-shell', '.main-panel', '.page-surface', '.dialogue-page', '.dialogue-inspector']
              .map((selector) => {
                const element = document.querySelector(selector);
                if (!element) return { selector, missing: true };
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                return {
                  selector,
                  left: Math.round(rect.left),
                  right: Math.round(rect.right),
                  width: Math.round(rect.width),
                  minWidth: style.minWidth,
                  maxWidth: style.maxWidth,
                  display: style.display,
                  gridTemplateColumns: style.gridTemplateColumns
                };
              })
          };
        })()
        """,
    )
    return value if isinstance(value, dict) else {}


def _scope_metrics(ws_url: str) -> dict[str, Any]:
    value = _evaluate_cdp(
        ws_url,
        """
        (() => {
          const agent = document.querySelector('select[aria-label="Agent"]');
          const kb = document.querySelector('select[aria-label="知识库"]');
          return {
            agent_scope: agent ? agent.value : '',
            kb_scope: kb ? kb.value : '',
            details_open: Boolean(document.querySelector('.dialogue-inspector'))
          };
        })()
        """,
    )
    return value if isinstance(value, dict) else {}


def _read_dom_text(ws_url: str) -> str:
    value = _evaluate_cdp(ws_url, "document.body ? document.body.textContent : ''")
    return str(value or "")


def _evaluate_cdp(
    ws_url: str,
    expression: str,
    *,
    before_eval: dict[str, Any] | None = None,
) -> Any:
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
        if before_eval:
            send(str(before_eval["method"]), before_eval.get("params") if isinstance(before_eval.get("params"), dict) else {})
        time.sleep(0.6)
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


def _safe_mcp_service_id(overview: dict[str, Any]) -> str:
    services = _surface(overview, "services")
    items = services.get("items") if isinstance(services.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and item.get("name") == SAFE_MCP_SERVICE_NAME:
            service_id = str(item.get("id") or "")
            if service_id:
                return service_id
    return ""


def _duckduckgo_provider_id(overview: dict[str, Any]) -> str:
    configured = _surface(overview, "configured_providers")
    items = configured.get("items") if isinstance(configured.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("provider") or "") == "duckduckgo":
            provider_id = str(item.get("id") or "")
            if provider_id:
                return provider_id
    return ""


def _surface(payload: dict[str, Any], name: str) -> dict[str, Any]:
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), dict) else {}
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _delete_agent(port: int, agent_id: str) -> None:
    try:
        _request_json(
            port,
            "DELETE",
            f"/api/analysis/native-agents/{quote(agent_id, safe='')}",
            {"confirm_token": AGENT_CONFIRM_TOKEN},
        )
    except Exception:
        pass


def _no_secret_payload(value: Any) -> bool:
    serialized = json.dumps(value, ensure_ascii=False, default=str)
    forbidden = (
        "Bearer ",
        "BEGIN " + "PRIVATE KEY",
        "BEGIN RSA " + "PRIVATE KEY",
        "BEGIN OPENSSH " + "PRIVATE KEY",
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"service_token":',
    )
    return not any(marker in serialized for marker in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
