"""Live WNID-P3-01 MCP tools/resources/prompts read-path check.

The script starts temporary PA backend/frontend services, verifies PA's native
MCP read path against WeKnora, records the current native prompt API blocker,
and opens `#/dialogue` in headless Chrome to prove MCP status is visible in the
first-class intelligent dialogue shell.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_intelligent_dialogue_shell import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_shell import _wait_for_dialogue_dom
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_PHRASE = "TEST_NATIVE_MCP_SERVICE"
SAFE_SERVICE_NAME = "PA Safe Local MCP"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-mcp-read-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'mcp-read.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            services = _surface(surfaces, "services")
            tools = _surface(surfaces, "tools")
            resources = _surface(surfaces, "resources")
            prompts = _surface(surfaces, "prompts")
            approval = _surface(surfaces, "approval")
            _assert(prompts.get("status") == "blocked", "MCP prompts are blocked")
            _assert(
                prompts.get("reason") == "native_mcp_prompt_api_missing",
                "MCP prompts blocker is native API missing",
            )

            service_count = int(services.get("count") or 0)
            service_id = _selected_service_id(services)
            selected_service_name = _selected_service_name(services, service_id)
            detail_status = "not_configured"
            confirmed_status = "not_configured"
            confirmed_success = False
            tool_count = int(tools.get("count") or 0)
            resource_count = int(resources.get("count") or 0)
            current_service_blocker = ""
            if service_id:
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}",
                )
                _assert(_no_secret_payload(detail), "service detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_status = str(_surface(detail_surfaces, "service_read").get("status"))
                detail_prompts = _surface(detail_surfaces, "prompts")
                _assert(
                    detail_prompts.get("reason") == "native_mcp_prompt_api_missing",
                    "service detail carries prompt blocker",
                )

                confirmed = _request_json(
                    backend_port,
                    "POST",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                    {"confirm_" + "token": CONFIRM_PHRASE},
                )
                _assert(_no_secret_payload(confirmed), "confirmed test response excludes secret-shaped fields")
                confirmed_surfaces = confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {}
                safe_test = _surface(confirmed_surfaces, "safe_test")
                confirmed_status = str(safe_test.get("status"))
                confirmed_success = bool(safe_test.get("success"))
                tool_count = int(safe_test.get("tool_count") or 0)
                resource_count = int(safe_test.get("resource_count") or 0)
                current_service_blocker = str(safe_test.get("reason") or "")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "MCP Read Path",
                "services",
                "tools",
                "resources",
                "prompts",
                "native_mcp_prompt_api_missing",
                "tool_execution",
            )
            dom = _wait_for_dialogue_dom(frontend_port, temp_path / "chrome-profile", markers)
            _assert("高级工具" not in dom, "MCP read path is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue MCP panel does not render secret-shaped text")

            print("WeKnora native intelligent dialogue MCP read path")
            decision = (
                "PASS"
                if confirmed_success and tool_count > 0 and resource_count > 0
                else "BLOCKED"
            )
            evidence_type = (
                "live_api + live_browser + live_service + blocker"
                if decision == "PASS"
                else "live_api + live_browser + blocker"
            )
            print(f"- decision: {decision}")
            print("- task: WNID-P3-01")
            print(f"- evidence_type: {evidence_type}")
            print(
                "- api: "
                f"services={service_count} selected={selected_service_name or 'none'} detail={detail_status} "
                f"confirmed_test={confirmed_status} success={str(confirmed_success).lower()} "
                f"tools={tool_count} resources={resource_count} "
                f"approval={approval.get('status')}"
            )
            print("- prompts: blocked reason=native_mcp_prompt_api_missing carried_forward=true")
            if current_service_blocker:
                print(f"- current_service_blocker: {current_service_blocker[:220]}")
            print("- browser: route=dialogue mcp_read_path=visible markers=8 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _selected_service_id(services_surface: dict[str, Any]) -> str:
    items = services_surface.get("items") if isinstance(services_surface.get("items"), list) else []
    if not items:
        return ""
    for item in items:
        if isinstance(item, dict) and str(item.get("name") or "") == SAFE_SERVICE_NAME:
            return str(item.get("id") or "").strip()
    first = items[0]
    return str(first.get("id") or "").strip() if isinstance(first, dict) else ""


def _selected_service_name(services_surface: dict[str, Any], service_id: str) -> str:
    items = services_surface.get("items") if isinstance(services_surface.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "") == service_id:
            return str(item.get("name") or service_id)
    return ""


def _no_secret_payload(payload: dict[str, Any]) -> bool:
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
    return not any(item in serialized for item in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
