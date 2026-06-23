"""Live WNX-P2-04 native vector store management smoke.

The script starts temporary PA backend/frontend services, reads the masked
vector-store management overview, verifies safe store read and KB binding, and
confirms external vector-store tests remain confirmation-gated by default. It
never prints raw vector store IDs, DSNs, hosts, ports, credentials, connection
config, index config, vector rows, provider payloads, local database paths, or
logs.
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


CONFIRM_TOKEN = "TEST_NATIVE_VECTOR_STORE"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    allow_confirmed_test = "--allow-confirmed-test" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-vector-store-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'vector-store.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/vector-stores/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-04", "schema version is wnx-p2-04")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") == "partial", "overview is partial until tests/mutations are safe")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            store_types = _surface(surfaces, "store_types")
            stores = _surface(surfaces, "stores")
            store_read = _surface(surfaces, "store_read")
            store_test = _surface(surfaces, "store_test")
            kb_binding = _surface(surfaces, "kb_binding")
            embedding = _surface(surfaces, "embedding")
            mutations = _surface(surfaces, "mutations")
            _assert(store_types.get("status") == "live", "store type catalog is live")
            _assert(int(store_types.get("count") or 0) > 0, "store type catalog is non-empty")
            _assert(stores.get("status") == "live", "store list is live")
            _assert(embedding.get("status") == "live", "embedding readiness is live")
            _assert(embedding.get("mock") is False, "embedding is not mock")
            _assert(mutations.get("status") == "backlog", "mutations remain backlog")
            _assert(
                kb_binding.get("status") in {"live", "blocked", "configured_unknown"},
                "KB binding is classified",
            )

            store_count = int(stores.get("count") or 0)
            env_count = int(stores.get("env_count") or 0)
            user_count = int(stores.get("user_count") or 0)
            read_detail_status = "not_configured"
            blocked_test_status = str(store_test.get("status"))
            confirmed_test_status = "not_requested"
            if store_count == 0:
                _assert(store_read.get("status") == "backlog", "store detail is backlog without stores")
                _assert(store_test.get("status") == "backlog", "store test is backlog without stores")
            else:
                items = stores.get("items") if isinstance(stores.get("items"), list) else []
                first = items[0] if items and isinstance(items[0], dict) else {}
                store_index = int(first.get("safe_index") or 0)
                _assert("id" not in first and "_native_store_id" not in first, "store item does not expose raw id")
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/vector-stores/native/stores/by-index/{store_index}",
                )
                _assert(detail.get("schema_version") == "wnx-p2-04-store", "detail schema is current")
                _assert(_no_secret_shaped_fields(detail), "detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_read = _surface(detail_surfaces, "store_read")
                detail_test = _surface(detail_surfaces, "store_test")
                _assert(detail_read.get("status") == "live", "store detail read is live")
                _assert(detail_test.get("status") == "blocked", "store test requires confirmation")
                read_detail_status = "live"
                blocked_test = _request_json(
                    backend_port,
                    "POST",
                    f"/api/vector-stores/native/stores/by-index/{store_index}/test",
                    {"confirm_token": "WRONG"},
                )
                _assert(_no_secret_shaped_fields(blocked_test), "blocked test excludes secret-shaped fields")
                blocked_test_surface = _surface(
                    blocked_test.get("surfaces") if isinstance(blocked_test.get("surfaces"), dict) else {},
                    "store_test",
                )
                _assert(blocked_test_surface.get("status") == "blocked", "bad token blocks vector store test")
                blocked_test_status = str(blocked_test_surface.get("status"))
                if allow_confirmed_test:
                    confirmed = _request_json(
                        backend_port,
                        "POST",
                        f"/api/vector-stores/native/stores/by-index/{store_index}/test",
                        {"confirm_token": CONFIRM_TOKEN},
                    )
                    _assert(_no_secret_shaped_fields(confirmed), "confirmed test excludes secret-shaped fields")
                    confirmed_surface = _surface(
                        confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                        "store_test",
                    )
                    _assert(
                        confirmed_surface.get("status") in {"live", "partial"},
                        "confirmed test returns live or partial",
                    )
                    confirmed_test_status = str(confirmed_surface.get("status"))

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            vector_group = groups.get("vector_store") if isinstance(groups.get("vector_store"), dict) else {}
            _assert(
                vector_group.get("source_endpoint") == "/api/vector-stores/native/overview",
                "status center uses vector store overview endpoint",
            )
            _assert(vector_group.get("status") == "partial", "status center marks vector store group partial")
            summary = vector_group.get("summary") if isinstance(vector_group.get("summary"), dict) else {}
            _assert(summary.get("store_test_status") == store_test.get("status"), "status center exposes store test status")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Vector store",
                    "store_test_status",
                    "store_read_status",
                    "/api/vector-stores/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native vector store management readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- store_types: status={status} count={count}".format(
                    status=store_types.get("status"),
                    count=int(store_types.get("count") or 0),
                )
            )
            print(
                "- stores: status={status} count={count} env={env} user={user}".format(
                    status=stores.get("status"),
                    count=store_count,
                    env=env_count,
                    user=user_count,
                )
            )
            print(f"- store_read: {store_read.get('status')} detail={read_detail_status}")
            print(
                "- store_test: overview={overview} blocked_path={blocked} confirmed_path={confirmed}".format(
                    overview=store_test.get("status"),
                    blocked=blocked_test_status,
                    confirmed=confirmed_test_status,
                )
            )
            print(
                "- kb_binding: status={status} source={source} engine={engine}".format(
                    status=kb_binding.get("binding_status") or kb_binding.get("status"),
                    source=kb_binding.get("binding_source") or "unknown",
                    engine=kb_binding.get("engine_type") or "unknown",
                )
            )
            print(
                "- embedding: status={status} provider={provider} mock={mock}".format(
                    status=embedding.get("status"),
                    provider=embedding.get("provider"),
                    mock=embedding.get("mock"),
                )
            )
            print("- mutations: backlog")
            if browser_mode:
                print("- browser: Capability Center rendered vector store management readiness")
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
        '"id":',
        '"_native_store_id":',
        '"tenant_id":',
        '"connection_config":',
        '"index_config":',
        '"addr":',
        '"host":',
        '"port":',
        '"username":',
        '"password":',
        '"api_key":',
        '"authorization":',
        '"secret":',
        '"database":',
        '"dsn":',
        '"endpoint":',
        '"base_url":',
        '"collection":',
        '"index_name":',
        '"version":',
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
            if "Vector store" in dom and "store_test_status" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
