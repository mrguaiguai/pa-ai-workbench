"""Live WNFC-P4-01 native FAQ workflow smoke.

The script creates a temporary native FAQ knowledge base as an isolated test
container, then drives the FAQ workflow through PA BFF endpoints:
create/read/update/search/import-progress/delete with confirmation-gated
mutations and NativeMutationAudit. It prints only statuses and counts; it never
prints raw questions, answers, service tokens, KB ids, chunks, or provider
payloads.
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
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

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
from app.config import Settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_TOKEN = "CONFIRM_NATIVE_FAQ_MUTATION"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    direct_backend = _weknora_backend_from_env()
    run_id = uuid4().hex[:8]
    temp_kb_id = ""
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-faq-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'faq-p4-01.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            temp_kb = direct_backend.create_temporary_faq_knowledge_base(
                name=f"WNFC-P4-01 temporary FAQ {run_id}",
                description="WNFC temporary FAQ validation KB",
            )
            temp_kb_id = str(temp_kb.get("_native_kb_id") or "")
            _assert(bool(temp_kb_id), "temporary FAQ KB was created")

            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/organization/native/overview?limit=10")
            _assert(_no_secret_payload(overview), "organization overview is sanitized")
            faq_surface = _surface(
                overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {},
                "faq",
            )
            _assert(faq_surface.get("status") == "live", "FAQ overview is live with temporary FAQ KB")

            blocked = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries",
                {**_faq_payload(run_id, "blocked"), "confirm_token": "WRONG"},
            )
            _assert(_no_secret_payload(blocked), "blocked create response is sanitized")
            _assert(_surface(blocked.get("surfaces", {}), "create").get("status") == "blocked", "bad token blocks create")

            created = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries",
                {**_faq_payload(run_id, "create"), "confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(created), "create response is sanitized")
            _assert(_audit_succeeded(created, "weknora_faq_create"), "create audit succeeded")
            created_entry = _surface(created.get("surfaces", {}), "create").get("entry")
            _assert(isinstance(created_entry, dict), "create returned safe entry")
            entry_id = int(created_entry.get("entry_id") or 0)
            _assert(entry_id > 0, "created entry id is available internally")

            listed = _request_json(
                backend_port,
                "GET",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries?limit=10",
            )
            _assert(_surface(listed.get("surfaces", {}), "entries").get("count", 0) >= 1, "list returns FAQ entry")

            read = _request_json(
                backend_port,
                "GET",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries/{entry_id}",
            )
            _assert(_surface(read.get("surfaces", {}), "entry_read").get("status") == "live", "read returns FAQ entry")

            updated = _request_json(
                backend_port,
                "PUT",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries/{entry_id}",
                {**_faq_payload(run_id, "update"), "confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(updated, "weknora_faq_update"), "update audit succeeded")

            search = _wait_for_search(backend_port, temp_kb_id, run_id)
            _assert(int(_surface(search.get("surfaces", {}), "search").get("count") or 0) >= 1, "search returns FAQ entry")

            imported = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/import",
                {
                    "entries": [_faq_payload(run_id, "import")],
                    "dry_run": False,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(imported, "weknora_faq_import"), "import audit succeeded")
            import_surface = _surface(imported.get("surfaces", {}), "import")
            task_id = str(import_surface.get("task_id") or "")
            _assert(bool(task_id), "import task id is available internally")
            progress = _wait_for_import_progress(backend_port, task_id)
            progress_surface = _surface(progress.get("surfaces", {}), "import_progress")
            _assert(progress_surface.get("status") == "live", "import progress is live")
            _assert(progress_surface.get("task_id_present") is True, "progress confirms task id presence")

            after_import = _request_json(
                backend_port,
                "GET",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries?limit=10",
            )
            entry_ids = _entry_ids(after_import)
            _assert(len(entry_ids) >= 2, "import produced an additional FAQ entry")

            deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/organization/native/faq/{quote(temp_kb_id, safe='')}/entries",
                {"entry_ids": entry_ids, "confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(deleted, "weknora_faq_delete"), "delete audit succeeded")
            _assert(
                int(_surface(deleted.get("surfaces", {}), "delete").get("deleted_count") or 0) >= 2,
                "delete removed FAQ entries",
            )

            audit_events = _request_json(backend_port, "GET", "/api/native-audit/events?capability=faq&limit=20")
            _assert(_audit_log_contains(audit_events), "audit API contains FAQ mutation events")
            _assert(_no_raw_confirm_token(audit_events), "audit API does not expose raw confirm token")
            _assert(_no_secret_payload(audit_events), "audit API is sanitized")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "FAQ / tags / favorites / skills",
                    "faq_status: live",
                    "faq_count:",
                    "/api/organization/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native FAQ full workflow")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus audit proof"
                if browser_mode
                else "- evidence_type: live api plus audit proof"
            )
            print("- faq_kb: temporary=true cleanup=scheduled")
            print("- workflow: create=live read=live update=live search=live import_progress=live delete=live")
            print("- audit: create/update/import/delete succeeded")
            if browser_mode:
                print("- browser: Capability Center rendered FAQ status")
            print("- output: sanitized")
            return 0
        finally:
            if temp_kb_id:
                try:
                    direct_backend.delete_knowledge_base(temp_kb_id)
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)


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


def _faq_payload(run_id: str, label: str) -> dict[str, Any]:
    return {
        "standard_question": f"WNFC P4 01 {label} question {run_id}",
        "similar_questions": [f"WNFC P4 01 {label} similar {run_id}"],
        "negative_questions": [],
        "answers": [f"WNFC P4 01 {label} answer {run_id}"],
        "answer_strategy": "all",
        "tag_name": "WNFC-P4-01",
        "is_enabled": True,
        "is_recommended": True,
    }


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_succeeded(response: dict[str, Any], operation: str) -> bool:
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return audit.get("operation") == operation and audit.get("status") == "succeeded"


def _entry_ids(response: dict[str, Any]) -> list[int]:
    surface = _surface(response.get("surfaces", {}), "entries")
    items = surface.get("items") if isinstance(surface.get("items"), list) else []
    return [int(item.get("entry_id") or 0) for item in items if isinstance(item, dict) and int(item.get("entry_id") or 0) > 0]


def _wait_for_search(port: int, kb_id: str, run_id: str) -> dict[str, Any]:
    deadline = time.time() + 45
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _request_json(
            port,
            "POST",
            f"/api/organization/native/faq/{quote(kb_id, safe='')}/search",
            {"query_text": f"WNFC P4 01 update question {run_id}", "match_count": 5},
        )
        surface = _surface(last.get("surfaces", {}), "search")
        if int(surface.get("count") or 0) > 0:
            return last
        time.sleep(2)
    return last


def _wait_for_import_progress(port: int, task_id: str) -> dict[str, Any]:
    deadline = time.time() + 90
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = _request_json(port, "GET", f"/api/organization/native/faq/import/progress/{quote(task_id, safe='')}")
        surface = _surface(last.get("surfaces", {}), "import_progress")
        if surface.get("status") == "live":
            import_status = str(surface.get("import_status") or "")
            if import_status in {"completed", "failed"}:
                return last
        time.sleep(2)
    return last


def _audit_log_contains(response: dict[str, Any]) -> bool:
    items = response.get("items") if isinstance(response.get("items"), list) else []
    operations = {item.get("operation") for item in items if isinstance(item, dict)}
    return {"weknora_faq_create", "weknora_faq_update", "weknora_faq_import", "weknora_faq_delete"}.issubset(operations)


def _no_raw_confirm_token(response: dict[str, Any]) -> bool:
    return CONFIRM_TOKEN not in json.dumps(response, ensure_ascii=False, sort_keys=True)


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        "wnfc p4 01",
        '"standard_question":',
        '"answers":',
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"service_token":',
        '"raw":',
        '"content":',
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
            if "FAQ / tags / favorites / skills" in dom and "faq_status: live" in dom:
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


if __name__ == "__main__":
    raise SystemExit(main())
