"""Live WNX-P2-01 native model/config/parser readiness smoke.

The script starts temporary PA backend/frontend services, reads masked native
model provider/model catalog plus parser/storage readiness through PA, verifies
Admin-only remote tests remain visibly blocked, and checks the Capability Center
browser workflow. It prints only statuses/counts and never raw endpoints, API
keys, provider payloads, prompts, model test responses, docreader addresses, or
private config values.
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
from check_weknora_native_chunk_management import _start_backend_with_cors


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-model-config-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'model-config.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/model/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-01", "schema version is wnx-p2-01")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") in {"partial", "live"}, "overview status is live or partial")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            provider_catalog = _surface(surfaces, "provider_catalog")
            model_catalog = _surface(surfaces, "model_catalog")
            parser_engines = _surface(surfaces, "parser_engines")
            storage_engines = _surface(surfaces, "storage_engines")
            pa_runtime = _surface(surfaces, "pa_runtime")
            admin_tests = _surface(surfaces, "admin_tests")
            _assert(provider_catalog.get("status") == "live", "provider catalog is live")
            _assert(int(provider_catalog.get("count") or 0) > 0, "provider catalog is non-empty")
            _assert(model_catalog.get("status") == "live", "model catalog is live")
            _assert(int(model_catalog.get("count") or 0) > 0, "model catalog is non-empty")
            _assert(parser_engines.get("status") == "live", "parser engines are live")
            _assert(int(parser_engines.get("count") or 0) > 0, "parser engine list is non-empty")
            _assert(storage_engines.get("status") == "live", "storage engine status is live")
            _assert(int(storage_engines.get("count") or 0) > 0, "storage engine list is non-empty")
            _assert(pa_runtime.get("status") == "live", "PA chat/embedding runtime is live")
            _assert(admin_tests.get("status") == "blocked", "Admin-only test surface is blocked")
            _assert(
                admin_tests.get("embedding_test") == "blocked_admin_only",
                "embedding remote test is blocked without admin confirmation",
            )
            _assert(
                admin_tests.get("rerank_check") == "blocked_admin_only",
                "rerank remote test is blocked without admin confirmation",
            )

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            model_group = groups.get("model_embedding_rerank_parser")
            model_group = model_group if isinstance(model_group, dict) else {}
            _assert(model_group.get("source_endpoint") == "/api/model/native/overview", "status center uses model overview endpoint")
            _assert(model_group.get("status") == "partial", "status center marks model/config group partial")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Model / embedding / rerank / parser",
                    "provider_count",
                    "parser_engine_count",
                    "/api/model/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native model/config readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- catalog: providers={providers} models={models}".format(
                    providers=int(provider_catalog.get("count") or 0),
                    models=int(model_catalog.get("count") or 0),
                )
            )
            print(
                "- parser_storage: parser_engines={parsers} storage_engines={storage}".format(
                    parsers=int(parser_engines.get("count") or 0),
                    storage=int(storage_engines.get("count") or 0),
                )
            )
            print("- runtime: chat_embedding=live admin_tests=blocked_admin_only")
            if browser_mode:
                print("- browser: Capability Center rendered model/config readiness")
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
        '"app_secret":',
        '"authorization":',
        '"password":',
        '"secret_access_key":',
        '"docreader_addr":',
        '"base_url":',
        '"defaulturls":',
        '"custom_headers":',
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
            if "Model / embedding / rerank / parser" in dom and "provider_count" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
