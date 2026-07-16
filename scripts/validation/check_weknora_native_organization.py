"""Live WNX-P2-06 native workbench organization smoke.

The script starts temporary PA backend/frontend services, reads the masked
organization overview, verifies safe native tags/skills/favorites/FAQ status,
and checks Capability Center browser status. It never prints raw FAQ content,
user IDs, tenant IDs, local database paths, prompts, provider payloads, logs,
or secret-shaped values.
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


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    with tempfile.TemporaryDirectory(prefix="pa-wnx-organization-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'organization.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/organization/native/overview?limit=10")
            _assert(overview.get("schema_version") == "wnx-p2-06", "schema version is wnx-p2-06")
            _assert(overview.get("source") == "weknora_api", "overview uses WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(overview.get("status") == "partial", "overview is partial for safe organization visibility")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            tags = _surface(surfaces, "tags")
            faq = _surface(surfaces, "faq")
            favorites = _surface(surfaces, "favorites")
            skills = _surface(surfaces, "skills")
            mutations = _surface(surfaces, "mutations")
            _assert(
                tags.get("status") == "live" or skills.get("status") == "live",
                "at least one organization surface is live",
            )
            _assert(mutations.get("status") == "backlog", "organization mutations remain backlog")
            _assert(faq.get("status") in {"live", "blocked", "backlog"}, "FAQ surface is classified")
            _assert(favorites.get("status") in {"live", "partial", "blocked", "backlog"}, "favorites surface is classified")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            organization_group = (
                groups.get("faq_tags_favorites_skills")
                if isinstance(groups.get("faq_tags_favorites_skills"), dict)
                else {}
            )
            _assert(
                organization_group.get("source_endpoint") == "/api/organization/native/overview",
                "status center uses organization overview endpoint",
            )
            _assert(organization_group.get("status") == "partial", "status center marks organization partial")
            summary = organization_group.get("summary") if isinstance(organization_group.get("summary"), dict) else {}
            _assert(summary.get("skills_status") == skills.get("status"), "status center exposes skills status")
            _assert(summary.get("tags_status") == tags.get("status"), "status center exposes tags status")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "FAQ / tags / favorites / skills",
                    "skills_count",
                    "tags_status",
                    "/api/organization/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native workbench organization readiness")
            print("- decision: PASS")
            print("- evidence_type: live_api+browser_current_run" if browser_mode else "- evidence_type: live_api")
            print(
                "- tags: status={status} count={count}".format(
                    status=tags.get("status"),
                    count=int(tags.get("count") or 0),
                )
            )
            print(
                "- skills: status={status} count={count} available={available}".format(
                    status=skills.get("status"),
                    count=int(skills.get("count") or 0),
                    available=skills.get("skills_available"),
                )
            )
            print(f"- faq: status={faq.get('status')} count={int(faq.get('count') or 0)}")
            print(f"- favorites: status={favorites.get('status')} count={int(favorites.get('count') or 0)}")
            print("- mutations: backlog")
            if browser_mode:
                print("- browser: Capability Center rendered organization readiness")
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
        '"tenant_id":',
        '"user_id":',
        '"resource_id":',
        '"knowledge_base_id":',
        '"chunk_id":',
        '"standard_question":',
        '"similar_questions":',
        '"negative_questions":',
        '"answers":',
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"token":',
        '"private_key":',
        '"prompt":',
        '"payload":',
        '"raw":',
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
            if "FAQ / tags / favorites / skills" in dom and "skills_count" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
