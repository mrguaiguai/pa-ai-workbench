"""Live WNX-P2-02 native MCP management smoke.

The script starts temporary PA backend/frontend services, reads the masked MCP
management overview, verifies that service list/read status is live where
configured, and confirms external MCP tests remain confirmation-gated. It never
prints service URLs, headers, env vars, credentials, raw tool schemas, raw MCP
test messages, provider payloads, or local database paths.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote

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


CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    allow_confirmed_test = "--allow-confirmed-test" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-mcp-management-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'mcp-management.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-02", "schema version is wnx-p2-02")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") == "partial", "overview is partial until mutations/execution are safe")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            services = _surface(surfaces, "services")
            service_read = _surface(surfaces, "service_read")
            tools = _surface(surfaces, "tools")
            resources = _surface(surfaces, "resources")
            approval = _surface(surfaces, "approval")
            safe_test = _surface(surfaces, "safe_test")
            mutations = _surface(surfaces, "mutations")
            _assert(services.get("status") == "live", "service list is live")
            _assert(mutations.get("status") == "backlog", "mutation/execution remains backlog")

            service_count = int(services.get("count") or 0)
            enabled_count = int(services.get("enabled_count") or 0)
            detail_status = "not_configured"
            test_status = str(safe_test.get("status"))
            confirmed_test_status = "not_requested"
            if service_count == 0:
                _assert(service_read.get("status") == "backlog", "service detail is backlog without services")
                _assert(tools.get("status") == "backlog", "tools are backlog without services")
                _assert(resources.get("status") == "backlog", "resources are backlog without services")
                _assert(approval.get("status") == "backlog", "approval is backlog without services")
                _assert(safe_test.get("status") == "backlog", "test is backlog without services")
            else:
                items = services.get("items") if isinstance(services.get("items"), list) else []
                first = items[0] if items and isinstance(items[0], dict) else {}
                service_id = str(first.get("id") or "")
                _assert(bool(service_id), "first MCP service has an id")
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}",
                )
                _assert(detail.get("schema_version") == "wnx-p2-02-service", "detail schema is current")
                _assert(_no_secret_shaped_fields(detail), "detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_read = _surface(detail_surfaces, "service_read")
                detail_safe_test = _surface(detail_surfaces, "safe_test")
                _assert(detail_read.get("status") == "live", "service detail read is live")
                _assert(detail_safe_test.get("status") == "blocked", "service test requires confirmation")
                detail_status = "live"
                blocked_test = _request_json(
                    backend_port,
                    "POST",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                    {"confirm_token": "WRONG"},
                )
                _assert(_no_secret_shaped_fields(blocked_test), "blocked test excludes secret-shaped fields")
                blocked_test_surface = _surface(
                    blocked_test.get("surfaces") if isinstance(blocked_test.get("surfaces"), dict) else {},
                    "safe_test",
                )
                _assert(blocked_test_surface.get("status") == "blocked", "bad token blocks native MCP test")
                test_status = str(blocked_test_surface.get("status"))
                if allow_confirmed_test:
                    confirmed = _request_json(
                        backend_port,
                        "POST",
                        f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                        {"confirm_token": CONFIRM_TOKEN},
                    )
                    _assert(_no_secret_shaped_fields(confirmed), "confirmed test excludes secret-shaped fields")
                    confirmed_surface = _surface(
                        confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                        "safe_test",
                    )
                    _assert(
                        confirmed_surface.get("status") in {"live", "partial"},
                        "confirmed test returns live or partial",
                    )
                    confirmed_test_status = str(confirmed_surface.get("status"))

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            mcp_group = groups.get("mcp") if isinstance(groups.get("mcp"), dict) else {}
            _assert(mcp_group.get("source_endpoint") == "/api/mcp/native/overview", "status center uses MCP overview endpoint")
            _assert(mcp_group.get("status") == "partial", "status center marks MCP group partial")
            summary = mcp_group.get("summary") if isinstance(mcp_group.get("summary"), dict) else {}
            _assert(summary.get("safe_test_status") == safe_test.get("status"), "status center exposes safe test status")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "MCP",
                    "services_count",
                    "safe_test_status",
                    "/api/mcp/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native MCP management readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- services: status={status} count={count} enabled={enabled}".format(
                    status=services.get("status"),
                    count=service_count,
                    enabled=enabled_count,
                )
            )
            print(f"- service_read: {service_read.get('status')} detail={detail_status}")
            print(
                "- safe_test: overview={overview} blocked_path={blocked} confirmed_path={confirmed}".format(
                    overview=safe_test.get("status"),
                    blocked=test_status,
                    confirmed=confirmed_test_status,
                )
            )
            print("- mutations: backlog")
            if browser_mode:
                print("- browser: Capability Center rendered MCP management readiness")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _no_secret_shaped_fields(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        '"api_key":',
        '"token":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"headers":',
        '"auth_config":',
        '"url":',
        '"env_vars":',
        '"stdio_config":',
        '"inputschema":',
        '"input_schema":',
        '"message":',
    ]
    return not any(token in serialized for token in forbidden)


def _dump_capability_dom(port: int, user_data_dir: Path) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/capabilities', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 35
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if "MCP" in dom and "safe_test_status" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
