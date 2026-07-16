"""Live WNX-P2-03 native web search management smoke.

The script starts temporary PA backend/frontend services, reads the masked web
search management overview, verifies provider catalog/list readiness, confirms
saved-provider tests remain confirmation-gated, and checks Capability Center
browser status. It never prints API keys, provider parameters, private
endpoints, raw search results, provider payloads, local database paths, or logs.
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


CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    allow_confirmed_test = "--allow-confirmed-test" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-web-search-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'web-search.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/web-search/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-03", "schema version is wnx-p2-03")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") == "partial", "overview is partial until provider tests/mutations are safe")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            provider_types = _surface(surfaces, "provider_types")
            providers = _surface(surfaces, "configured_providers")
            provider_read = _surface(surfaces, "provider_read")
            provider_test = _surface(surfaces, "provider_test")
            agentqa = _surface(surfaces, "agentqa_dependency")
            mutations = _surface(surfaces, "mutations")
            _assert(provider_types.get("status") == "live", "provider type catalog is live")
            _assert(int(provider_types.get("count") or 0) > 0, "provider type catalog is non-empty")
            _assert(providers.get("status") == "live", "configured provider list is live")
            _assert(mutations.get("status") == "backlog", "mutation/credential/raw test surfaces remain backlog")
            _assert(agentqa.get("required_for_agentqa") is False, "AgentQA web search is not overstated as required")

            configured_count = int(providers.get("count") or 0)
            ready_count = int(providers.get("ready_provider_count") or 0)
            detail_status = "not_configured"
            test_status = str(provider_test.get("status"))
            confirmed_test_status = "not_requested"
            if configured_count == 0:
                _assert(provider_read.get("status") == "backlog", "provider detail is backlog without providers")
                _assert(provider_test.get("status") == "backlog", "provider test is backlog without providers")
                _assert(agentqa.get("status") == "optional_unconfigured", "AgentQA dependency is optional_unconfigured")
            else:
                items = providers.get("items") if isinstance(providers.get("items"), list) else []
                first = items[0] if items and isinstance(items[0], dict) else {}
                provider_id = str(first.get("id") or "")
                _assert(bool(provider_id), "first web search provider has an id")
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/web-search/native/providers/{quote(provider_id, safe='')}",
                )
                _assert(detail.get("schema_version") == "wnx-p2-03-provider", "detail schema is current")
                _assert(_no_secret_shaped_fields(detail), "detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_read = _surface(detail_surfaces, "provider_read")
                detail_test = _surface(detail_surfaces, "provider_test")
                _assert(detail_read.get("status") == "live", "provider detail read is live")
                _assert(detail_test.get("status") == "blocked", "provider test requires confirmation")
                detail_status = "live"
                blocked_test = _request_json(
                    backend_port,
                    "POST",
                    f"/api/web-search/native/providers/{quote(provider_id, safe='')}/test",
                    {"confirm_token": "WRONG"},
                )
                _assert(_no_secret_shaped_fields(blocked_test), "blocked test excludes secret-shaped fields")
                blocked_test_surface = _surface(
                    blocked_test.get("surfaces") if isinstance(blocked_test.get("surfaces"), dict) else {},
                    "provider_test",
                )
                _assert(blocked_test_surface.get("status") == "blocked", "bad token blocks provider test")
                test_status = str(blocked_test_surface.get("status"))
                if allow_confirmed_test:
                    confirmed = _request_json(
                        backend_port,
                        "POST",
                        f"/api/web-search/native/providers/{quote(provider_id, safe='')}/test",
                        {"confirm_token": CONFIRM_TOKEN},
                    )
                    _assert(_no_secret_shaped_fields(confirmed), "confirmed test excludes secret-shaped fields")
                    confirmed_surface = _surface(
                        confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                        "provider_test",
                    )
                    _assert(
                        confirmed_surface.get("status") in {"live", "partial"},
                        "confirmed test returns live or partial",
                    )
                    confirmed_test_status = str(confirmed_surface.get("status"))

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            web_group = groups.get("web_search") if isinstance(groups.get("web_search"), dict) else {}
            _assert(web_group.get("source_endpoint") == "/api/web-search/native/overview", "status center uses web search overview endpoint")
            _assert(web_group.get("status") == "partial", "status center marks web search group partial")
            summary = web_group.get("summary") if isinstance(web_group.get("summary"), dict) else {}
            _assert(summary.get("provider_test_status") == provider_test.get("status"), "status center exposes provider test status")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Web search",
                    "provider_test_status",
                    "agentqa_dependency_status",
                    "/api/web-search/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native web search management readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- provider_types: status={status} count={count}".format(
                    status=provider_types.get("status"),
                    count=int(provider_types.get("count") or 0),
                )
            )
            print(
                "- configured_providers: status={status} count={count} ready={ready}".format(
                    status=providers.get("status"),
                    count=configured_count,
                    ready=ready_count,
                )
            )
            print(f"- provider_read: {provider_read.get('status')} detail={detail_status}")
            print(
                "- provider_test: overview={overview} blocked_path={blocked} confirmed_path={confirmed}".format(
                    overview=provider_test.get("status"),
                    blocked=test_status,
                    confirmed=confirmed_test_status,
                )
            )
            print(f"- agentqa_dependency: {agentqa.get('status')}")
            print("- mutations: backlog")
            if browser_mode:
                print("- browser: Capability Center rendered web search management readiness")
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
        '"parameters":',
        '"credentials":',
        '"base_url":',
        '"proxy_url":',
        '"engine_id":',
        '"extra_config":',
        '"docs_url":',
        '"api_url":',
        '"url":',
        '"results":',
        '"payload":',
        '"error":',
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
            if "Web search" in dom and "provider_test_status" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
