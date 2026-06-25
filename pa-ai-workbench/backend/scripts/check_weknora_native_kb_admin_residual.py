"""Live WNFC-P5-01 native KB admin residual smoke.

The script drives KB create/update/delete/pin through PA BFF endpoints with
confirmation tokens and NativeMutationAudit. It creates one isolated validation
KB and deletes it before exit; output never prints service tokens, raw KB ids, or
upstream payloads.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import quote
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_faq_workflow import _dump_capability_dom
from check_weknora_native_faq_workflow import _no_raw_confirm_token
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_TOKEN = "CONFIRM_NATIVE_KB_MUTATION"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    temp_kb_id = ""
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-kb-admin-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'kb-p5-01.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            overview = _request_json(backend_port, "GET", "/api/knowledge-bases/native/overview?limit=10")
            _assert(overview.get("status") == "live", "KB overview is live")
            _assert(_no_secret_payload(overview), "KB overview is sanitized")
            mutations = _surface(overview.get("surfaces", {}), "mutations")
            _assert(mutations.get("status") == "live", "KB mutation status is live")
            _assert(mutations.get("kb_mutations") == "live", "KB create/update/delete status is live")
            _assert(mutations.get("pin_mutations") == "live", "KB pin mutation status is live")

            blocked = _request_json(
                backend_port,
                "POST",
                "/api/knowledge-bases/native",
                {
                    "name": f"WNFC P5 01 blocked {run_id}",
                    "type": "document",
                    "confirm_token": "WRONG",
                },
            )
            _assert(_surface(blocked.get("surfaces", {}), "create").get("status") == "blocked", "bad token blocks KB create")

            created = _request_json(
                backend_port,
                "POST",
                "/api/knowledge-bases/native",
                {
                    "name": f"WNFC P5 01 KB {run_id}",
                    "description": "WNFC P5 01 isolated KB admin validation",
                    "type": "document",
                    "is_temporary": False,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(created, "weknora_kb_create"), "KB create audit succeeded")
            created_kb = _surface(created.get("surfaces", {}), "create").get("knowledge_base")
            _assert(isinstance(created_kb, dict), "KB create returned safe KB")
            temp_kb_id = str(created_kb.get("id") or "")
            _assert(bool(temp_kb_id), "created KB id is available internally")

            updated = _request_json(
                backend_port,
                "PUT",
                f"/api/knowledge-bases/native/{quote(temp_kb_id, safe='')}",
                {
                    "name": f"WNFC P5 01 KB updated {run_id}",
                    "description": "WNFC P5 01 updated KB admin validation",
                    "type": "document",
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(updated, "weknora_kb_update"), "KB update audit succeeded")

            pinned = _request_json(
                backend_port,
                "POST",
                f"/api/knowledge-bases/native/{quote(temp_kb_id, safe='')}/pin-toggle",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(pinned, "weknora_kb_pin_toggle"), "KB pin audit succeeded")
            pinned_kb = _surface(pinned.get("surfaces", {}), "pin_toggle").get("knowledge_base")
            _assert(isinstance(pinned_kb, dict), "KB pin returned safe KB")
            _assert(pinned_kb.get("is_pinned") is True, "KB pin toggle is live")

            audits = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?capability=knowledge_base&limit=20",
            )
            _assert(
                _audit_log_contains(
                    audits,
                    {"weknora_kb_create", "weknora_kb_update", "weknora_kb_pin_toggle"},
                ),
                "audit API contains KB mutation events before delete",
            )
            _assert(_no_raw_confirm_token(audits), "audit API hides KB confirm token")
            _assert(_no_secret_payload(audits), "audit API sanitizes KB mutation events")

            deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/knowledge-bases/native/{quote(temp_kb_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(deleted, "weknora_kb_delete"), "KB delete audit succeeded")
            _assert(_surface(deleted.get("surfaces", {}), "delete").get("deleted") is True, "KB delete is live")
            temp_kb_id = ""

            final_audits = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?capability=knowledge_base&limit=20",
            )
            _assert(
                _audit_log_contains(
                    final_audits,
                    {
                        "weknora_kb_create",
                        "weknora_kb_update",
                        "weknora_kb_pin_toggle",
                        "weknora_kb_delete",
                    },
                ),
                "audit API contains full KB admin mutation loop",
            )

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "Workspace / knowledge base",
                    "mutations_status: live",
                    "kb_mutations: live",
                    "pin_mutations: live",
                    "tag_mutations: live",
                    "/api/knowledge-bases/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native KB admin residual closure")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus audit proof"
                if browser_mode
                else "- evidence_type: live api plus audit proof"
            )
            print("- kb_admin: create=live update=live pin=live delete=live")
            print("- tags: create/update/delete covered by WNFC-P4-02")
            print("- audit: knowledge_base mutations succeeded")
            if browser_mode:
                print("- browser: Capability Center rendered KB mutation status")
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


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_succeeded(response: dict[str, Any], operation: str) -> bool:
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return audit.get("operation") == operation and audit.get("status") == "succeeded"


def _audit_log_contains(response: dict[str, Any], operations: set[str]) -> bool:
    items = response.get("items") if isinstance(response.get("items"), list) else []
    found = {
        str(item.get("operation") or "")
        for item in items
        if isinstance(item, dict) and item.get("status") == "succeeded"
    }
    return operations.issubset(found)


if __name__ == "__main__":
    raise SystemExit(main())
