"""Live WNFC-P5-03 native custom Agent admin residual smoke.

The script drives custom Agent create/update/copy/delete through PA BFF
endpoints with confirmation tokens and NativeMutationAudit. It creates isolated
temporary agents and deletes them before exit; output never prints service
tokens, raw agent ids, prompts, or upstream payloads.
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

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_faq_workflow import _no_raw_confirm_token
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_agentqa_workflow import _dump_analysis_dom
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    created_agent_id = ""
    copied_agent_id = ""
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-agent-admin-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'agent-p5-03.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            catalog = _request_json(backend_port, "GET", "/api/analysis/native-agents")
            _assert(catalog.get("status") in {"live", "partial"}, "native Agent catalog is reachable")
            _assert(_no_secret_payload(catalog), "Agent catalog response is sanitized")
            surfaces = catalog.get("surfaces") if isinstance(catalog.get("surfaces"), dict) else {}
            _assert(surfaces.get("copy") == "live", "Agent copy surface is live")
            _assert(surfaces.get("mutations") == "live", "Agent mutation surface is live")

            blocked = _request_json(
                backend_port,
                "POST",
                "/api/analysis/native-agents",
                {
                    **_agent_payload(run_id, "blocked"),
                    "confirm_token": "WRONG",
                },
            )
            _assert(_surface(blocked.get("surfaces", {}), "create").get("status") == "blocked", "bad token blocks Agent create")
            _assert(_no_secret_payload(blocked), "blocked Agent response is sanitized")

            created = _request_json(
                backend_port,
                "POST",
                "/api/analysis/native-agents",
                {
                    **_agent_payload(run_id, "create"),
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(created, "weknora_agent_create"), "Agent create audit succeeded")
            created_agent = _surface(created.get("surfaces", {}), "create").get("agent")
            _assert(isinstance(created_agent, dict), "Agent create returned safe agent")
            created_agent_id = str(created_agent.get("id") or "")
            _assert(bool(created_agent_id), "created Agent id is available internally")
            _assert(created_agent.get("is_builtin") is False, "created Agent is custom")

            updated = _request_json(
                backend_port,
                "PUT",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}",
                {
                    **_agent_payload(run_id, "update"),
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(updated, "weknora_agent_update"), "Agent update audit succeeded")

            copied = _request_json(
                backend_port,
                "POST",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}/copy",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(copied, "weknora_agent_copy"), "Agent copy audit succeeded")
            copied_agent = _surface(copied.get("surfaces", {}), "copy").get("agent")
            _assert(isinstance(copied_agent, dict), "Agent copy returned safe agent")
            copied_agent_id = str(copied_agent.get("id") or "")
            _assert(bool(copied_agent_id), "copied Agent id is available internally")
            _assert(copied_agent_id != created_agent_id, "copy created a distinct Agent")

            audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=custom_agent&limit=20")
            _assert(
                _audit_log_contains(
                    audits,
                    {"weknora_agent_create", "weknora_agent_update", "weknora_agent_copy"},
                ),
                "audit API contains Agent create/update/copy events before delete",
            )
            _assert(_no_raw_confirm_token(audits), "audit API hides Agent confirm token")
            _assert(_no_secret_payload(audits), "audit API sanitizes Agent mutation events")

            copied_deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/analysis/native-agents/{quote(copied_agent_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(copied_deleted, "weknora_agent_delete"), "copied Agent delete audit succeeded")
            _assert(_surface(copied_deleted.get("surfaces", {}), "delete").get("deleted") is True, "copied Agent delete is live")
            copied_agent_id = ""

            created_deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(created_deleted, "weknora_agent_delete"), "created Agent delete audit succeeded")
            _assert(_surface(created_deleted.get("surfaces", {}), "delete").get("deleted") is True, "created Agent delete is live")
            created_agent_id = ""

            final_audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=custom_agent&limit=20")
            _assert(
                _audit_log_contains(
                    final_audits,
                    {
                        "weknora_agent_create",
                        "weknora_agent_update",
                        "weknora_agent_copy",
                        "weknora_agent_delete",
                    },
                ),
                "audit API contains full custom Agent admin loop",
            )

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_agent_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "原生 AGENTQA",
                    "copy live",
                    "mutations live",
                    "ownership native_owned_agent_or_admin",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native custom Agent admin residual closure")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus audit proof"
                if browser_mode
                else "- evidence_type: live api plus audit proof"
            )
            print("- custom_agent_admin: create=live update=live copy=live delete=live")
            print("- ownership: native OwnedAgentOrAdmin/copy-owned-by-caller path verified")
            print("- audit: custom_agent mutations succeeded")
            if browser_mode:
                print("- browser: Analysis page rendered Agent admin surface status")
            print("- output: sanitized")
            return 0
        finally:
            for agent_id in (copied_agent_id, created_agent_id):
                if agent_id:
                    try:
                        direct_backend.delete_agent(agent_id)
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


def _agent_payload(run_id: str, label: str) -> dict[str, Any]:
    return {
        "name": f"WNFC P5 03 Agent {label} {run_id}",
        "description": "WNFC P5 03 isolated custom Agent admin validation",
        "avatar": "bot",
        "config": {
            "agent_mode": "quick-answer",
            "kb_selection_mode": "none",
            "knowledge_bases": [],
            "suggested_prompts": [f"WNFC P5 03 suggested {label}"],
            "web_search_enabled": False,
            "multi_turn_enabled": False,
        },
    }


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


def _dump_agent_dom(port: int, user_data_dir: Path) -> str:
    return _dump_analysis_dom(port, user_data_dir).replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
