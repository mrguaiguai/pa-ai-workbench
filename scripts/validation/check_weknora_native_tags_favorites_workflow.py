"""Live WNFC-P4-02 native tags and favorites workflow smoke.

The script creates an isolated temporary native KB, then drives tag
create/update/delete and favorite add/remove/toggle through PA BFF endpoints
with confirmation tokens and NativeMutationAudit. Output is limited to status
and counts; it never prints service tokens, raw KB ids, user ids, or provider
payloads.
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
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

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
from app.config import Settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_TOKEN = "CONFIRM_NATIVE_ORGANIZATION_MUTATION"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    direct_backend = _weknora_backend_from_env()
    run_id = uuid4().hex[:8]
    temp_kb_id = ""
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-organization-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'organization-p4-02.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            temp_kb = direct_backend.create_temporary_faq_knowledge_base(
                name=f"WNFC-P4-02 temporary organization {run_id}",
                description="WNFC temporary tag/favorite validation KB",
            )
            temp_kb_id = str(temp_kb.get("_native_kb_id") or "")
            _assert(bool(temp_kb_id), "temporary KB was created")

            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/organization/native/overview?limit=10")
            _assert(_no_secret_payload(overview), "organization overview is sanitized")
            mutations = _surface(overview.get("surfaces", {}), "mutations")
            _assert(mutations.get("tag_mutations") == "live", "tag mutation status is live")
            _assert(mutations.get("favorite_mutations") == "live", "favorite mutation status is live")

            blocked = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/tags/{quote(temp_kb_id, safe='')}",
                {"name": f"WNFC P4 02 blocked {run_id}", "confirm_token": "WRONG"},
            )
            _assert(_surface(blocked.get("surfaces", {}), "create").get("status") == "blocked", "bad token blocks tag create")

            created = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/tags/{quote(temp_kb_id, safe='')}",
                {
                    "name": f"WNFC P4 02 tag {run_id}",
                    "color": "#2f6fed",
                    "sort_order": 41,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(created, "weknora_tag_create"), "tag create audit succeeded")
            created_tag = _surface(created.get("surfaces", {}), "create").get("tag")
            _assert(isinstance(created_tag, dict), "tag create returned safe tag")
            tag_id = str(created_tag.get("tag_id") or "")
            _assert(bool(tag_id), "created tag id is available internally")

            listed = _request_json(
                backend_port,
                "GET",
                f"/api/organization/native/tags/{quote(temp_kb_id, safe='')}?limit=10",
            )
            _assert(int(_surface(listed.get("surfaces", {}), "tags").get("count") or 0) >= 1, "tag list sees created tag")

            updated = _request_json(
                backend_port,
                "PUT",
                f"/api/organization/native/tags/{quote(temp_kb_id, safe='')}/{quote(tag_id, safe='')}",
                {
                    "name": f"WNFC P4 02 tag updated {run_id}",
                    "color": "#19a974",
                    "sort_order": 42,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(updated, "weknora_tag_update"), "tag update audit succeeded")

            favorite_add = _request_json(
                backend_port,
                "POST",
                "/api/organization/native/favorites/toggle",
                {
                    "resource_type": "kb",
                    "resource_id": temp_kb_id,
                    "favorited": True,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(favorite_add, "weknora_favorite_favorite_add"), "favorite add audit succeeded")
            _assert(_surface(favorite_add.get("surfaces", {}), "favorite_add").get("favorited") is True, "favorite add is live")

            favorite_remove = _request_json(
                backend_port,
                "POST",
                "/api/organization/native/favorites/toggle",
                {
                    "resource_type": "kb",
                    "resource_id": temp_kb_id,
                    "favorited": False,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(favorite_remove, "weknora_favorite_favorite_remove"), "favorite remove audit succeeded")
            _assert(
                _surface(favorite_remove.get("surfaces", {}), "favorite_remove").get("favorited") is False,
                "favorite remove is live",
            )

            deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/organization/native/tags/{quote(temp_kb_id, safe='')}/{quote(tag_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(deleted, "weknora_tag_delete"), "tag delete audit succeeded")
            _assert(_surface(deleted.get("surfaces", {}), "delete").get("deleted") is True, "tag delete is live")

            for capability in ("tag", "favorite"):
                audit_events = _request_json(
                    backend_port,
                    "GET",
                    f"/api/native-audit/events?capability={capability}&limit=20",
                )
                expected_operations = (
                    {"weknora_tag_create", "weknora_tag_update", "weknora_tag_delete"}
                    if capability == "tag"
                    else {"weknora_favorite_favorite_add", "weknora_favorite_favorite_remove"}
                )
                _assert(
                    _audit_log_contains(audit_events, expected_operations),
                    f"audit API contains {capability} mutation events",
                )
                _assert(_no_raw_confirm_token(audit_events), f"audit API hides {capability} confirm token")
                _assert(_no_secret_payload(audit_events), f"audit API sanitizes {capability} events")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "FAQ / tags / favorites / skills",
                    "tag_mutations: live",
                    "favorite_mutations: live",
                    "mutations_status: partial",
                    "/api/organization/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native tags and favorites mutations")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus audit proof"
                if browser_mode
                else "- evidence_type: live api plus audit proof"
            )
            print("- tags: create=live update=live delete=live")
            print("- favorites: add=live remove=live toggle=live")
            print("- audit: tag/favorite mutations succeeded")
            if browser_mode:
                print("- browser: Capability Center rendered mutation status")
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
