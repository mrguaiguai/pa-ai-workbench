"""Live WNX-P2-05 native data source connector management smoke.

The script starts temporary PA backend/frontend services, reads the masked data
source connector overview, verifies connector catalog/list readiness, confirms
sync controls remain confirmation-gated, and checks Capability Center browser
status. It never prints credentials, raw connector config, external resource
names, sync-log error text, raw payloads, private endpoints, local database
paths, or logs.
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


CONFIRM_SYNC_PHRASE = "SYNC_NATIVE_DATA_SOURCE"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    allow_confirmed_sync = "--allow-confirmed-sync" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-data-source-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'data-source.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/data-sources/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-05", "schema version is wnx-p2-05")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") in {"live", "partial"}, "overview is live or partial")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            connector_types = _surface(surfaces, "connector_types")
            data_sources = _surface(surfaces, "data_sources")
            connector_read = _surface(surfaces, "connector_read")
            sync_logs = _surface(surfaces, "sync_logs")
            resources = _surface(surfaces, "resources")
            validation = _surface(surfaces, "validation")
            sync_control = _surface(surfaces, "sync_control")
            mutations = _surface(surfaces, "mutations")
            _assert(connector_types.get("status") == "live", "connector type catalog is live")
            _assert(int(connector_types.get("count") or 0) > 0, "connector type catalog is non-empty")
            _assert(data_sources.get("status") == "live", "data source list is live")
            _assert(mutations.get("status") == "backlog", "credential/mutation surfaces remain backlog")
            _assert(validation.get("status") in {"blocked", "backlog"}, "validation is blocked or backlog")
            _assert(resources.get("status") in {"blocked", "backlog"}, "resources are blocked or backlog")

            data_source_count = int(data_sources.get("count") or 0)
            credential_configured_count = int(data_sources.get("credential_configured_count") or 0)
            detail_status = "not_configured"
            sync_blocked_status = str(sync_control.get("status"))
            confirmed_sync_status = "not_requested"
            coverage_state = "read-only"
            if data_source_count == 0:
                _assert(connector_read.get("status") == "backlog", "connector detail is backlog without data sources")
                _assert(sync_logs.get("status") == "backlog", "sync logs are backlog without data sources")
                _assert(sync_control.get("status") == "backlog", "sync control is backlog without data sources")
            else:
                coverage_state = "live-partial"
                items = data_sources.get("items") if isinstance(data_sources.get("items"), list) else []
                first = items[0] if items and isinstance(items[0], dict) else {}
                data_source_index = int(first.get("safe_index") or 0)
                _assert("id" not in first and "_native_data_source_id" not in first, "data source item does not expose raw id")
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/data-sources/native/sources/by-index/{data_source_index}",
                )
                _assert(detail.get("schema_version") == "wnx-p2-05-data-source", "detail schema is current")
                _assert(_no_secret_shaped_fields(detail), "detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_read = _surface(detail_surfaces, "connector_read")
                detail_logs = _surface(detail_surfaces, "sync_logs")
                detail_sync = _surface(detail_surfaces, "sync_control")
                _assert(detail_read.get("status") == "live", "data source detail read is live")
                _assert(detail_logs.get("status") == "live", "sync-log summary read is live")
                _assert(detail_sync.get("status") == "blocked", "sync control requires confirmation")
                detail_status = "live"
                blocked_sync = _request_json(
                    backend_port,
                    "POST",
                    f"/api/data-sources/native/sources/by-index/{data_source_index}/sync",
                    {"confirm_token": "WRONG"},
                )
                _assert(_no_secret_shaped_fields(blocked_sync), "blocked sync excludes secret-shaped fields")
                blocked_sync_surface = _surface(
                    blocked_sync.get("surfaces") if isinstance(blocked_sync.get("surfaces"), dict) else {},
                    "sync_control",
                )
                _assert(blocked_sync_surface.get("status") == "blocked", "bad phrase blocks native sync")
                sync_blocked_status = str(blocked_sync_surface.get("status"))
                if allow_confirmed_sync:
                    confirmed = _request_json(
                        backend_port,
                        "POST",
                        f"/api/data-sources/native/sources/by-index/{data_source_index}/sync",
                        {"confirm_token": CONFIRM_SYNC_PHRASE},
                    )
                    _assert(_no_secret_shaped_fields(confirmed), "confirmed sync excludes secret-shaped fields")
                    confirmed_surface = _surface(
                        confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                        "sync_control",
                    )
                    _assert(
                        confirmed_surface.get("status") in {"live", "partial"},
                        "confirmed sync returns live or partial",
                    )
                    confirmed_sync_status = str(confirmed_surface.get("status"))

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            data_source_group = (
                groups.get("data_sources_connectors")
                if isinstance(groups.get("data_sources_connectors"), dict)
                else {}
            )
            _assert(
                data_source_group.get("source_endpoint") == "/api/data-sources/native/overview",
                "status center uses data source overview endpoint",
            )
            expected_group_status = "partial" if data_source_count else "live"
            _assert(
                data_source_group.get("status") == expected_group_status,
                "status center classifies data source group from current overview",
            )
            summary = data_source_group.get("summary") if isinstance(data_source_group.get("summary"), dict) else {}
            _assert(
                summary.get("sync_control_status") == sync_control.get("status"),
                "status center exposes sync control status",
            )

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Data sources / connectors",
                    "sync_control_status",
                    "connector_type_count",
                    "/api/data-sources/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native data source connector management readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(f"- coverage_state: {coverage_state}")
            print(
                "- connector_types: status={status} count={count}".format(
                    status=connector_types.get("status"),
                    count=int(connector_types.get("count") or 0),
                )
            )
            print(
                "- data_sources: status={status} count={count} credentials_configured={credentials}".format(
                    status=data_sources.get("status"),
                    count=data_source_count,
                    credentials=credential_configured_count,
                )
            )
            print(f"- connector_read: {connector_read.get('status')} detail={detail_status}")
            print(f"- resources: {resources.get('status')}")
            print(f"- validation: {validation.get('status')}")
            print(
                "- sync_control: overview={overview} blocked_path={blocked} confirmed_path={confirmed}".format(
                    overview=sync_control.get("status"),
                    blocked=sync_blocked_status,
                    confirmed=confirmed_sync_status,
                )
            )
            print("- mutations: backlog")
            if browser_mode:
                print("- browser: Capability Center rendered data source connector readiness")
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
        '"_native_data_source_id":',
        '"tenant_id":',
        '"knowledge_base_id":',
        '"config":',
        '"credentials":',
        '"credential":',
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"access_token":',
        '"refresh_token":',
        '"private_key":',
        '"url":',
        '"external_id":',
        '"resource_ids":',
        '"resources":[',
        '"error_message":',
        '"errors":',
        '"result":{',
        '"payload":',
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
            if "Data sources / connectors" in dom and "sync_control_status" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
