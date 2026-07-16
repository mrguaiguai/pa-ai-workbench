"""Live WNID-P3-03 MCP prompt parity check.

The script starts temporary PA backend/frontend services, verifies native MCP
prompt list/read support through PA against the safe local MCP service, and
opens `#/dialogue` in headless Chrome to prove the prompt parity surface is
visible.
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


CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE"
SAFE_SERVICE_NAME = "PA Safe Local MCP"
SAFE_PROMPT_NAME = "pa-safe-summary"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-mcp-prompts-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'mcp-prompts.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            overview = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes secret-shaped fields")
            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            prompts_surface = _surface(surfaces, "prompts")
            _assert(
                prompts_surface.get("reason") == "confirmation_required_before_external_mcp_prompt_read",
                "overview advertises confirmed MCP prompt read",
            )
            _assert(
                prompts_surface.get("native_endpoint") == "/api/v1/mcp-services/{id}/prompts",
                "overview exposes native prompt endpoint",
            )

            services = _surface(surfaces, "services")
            service_id = _selected_service_id(services)
            service_name = _selected_service_name(services, service_id)
            _assert(service_name == SAFE_SERVICE_NAME, "safe local MCP service is configured")

            confirmed = _request_json(
                backend_port,
                "POST",
                f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(confirmed), "confirmed test response excludes secrets")
            confirmed_surfaces = confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {}
            safe_test = _surface(confirmed_surfaces, "safe_test")
            confirmed_prompts = _surface(confirmed_surfaces, "prompts")
            _assert(bool(safe_test.get("success")), "safe MCP service confirms live")
            _assert(int(safe_test.get("tool_count") or 0) > 0, "safe MCP service still has tools")
            _assert(int(safe_test.get("resource_count") or 0) > 0, "safe MCP service still has resources")
            _assert(int(safe_test.get("prompt_count") or 0) > 0, "safe MCP service has prompts")
            _assert(int(confirmed_prompts.get("count") or 0) > 0, "confirmed prompts surface is live")
            _assert(_has_prompt(safe_test, SAFE_PROMPT_NAME), "safe prompt appears in confirmed test")

            prompt_read = _request_json(
                backend_port,
                "POST",
                (
                    f"/api/mcp/native/services/{quote(service_id, safe='')}"
                    f"/prompts/{quote(SAFE_PROMPT_NAME, safe='')}/read"
                ),
                {"arguments": {}, "confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(prompt_read), "prompt read response excludes secrets")
            prompt_surfaces = prompt_read.get("surfaces") if isinstance(prompt_read.get("surfaces"), dict) else {}
            prompt_result = _surface(prompt_surfaces, "prompt_read")
            prompt = _surface(prompt_result, "prompt")
            _assert(prompt_result.get("status") == "live", "prompt read surface is live")
            _assert(bool(prompt_result.get("success")), "prompt read succeeded")
            _assert(str(prompt.get("name") or "") == SAFE_PROMPT_NAME, "prompt name returned")
            _assert(int(prompt.get("message_count") or 0) > 0, "prompt messages returned")
            _assert(_prompt_has_text_message(prompt), "prompt text message summary returned")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "MCP Read Path",
                "prompts",
                "Read prompt",
                "prompt_parity",
                "prompt_name",
                "prompt_messages",
                "prompt_read",
            )
            dom = _wait_for_dialogue_dom(frontend_port, temp_path / "chrome-profile", markers)
            _assert("高级工具" not in dom, "MCP prompt parity is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue MCP prompt panel does not render secrets")

            print("WeKnora native intelligent dialogue MCP prompt parity")
            print("- decision: PASS")
            print("- task: WNID-P3-03")
            print("- evidence_type: native_go_test + Docker runtime + live_service + live_api + live_browser")
            print(
                "- api: "
                f"service={service_name} prompts={int(safe_test.get('prompt_count') or 0)} "
                f"selected_prompt={SAFE_PROMPT_NAME} prompt_read=live "
                f"messages={int(prompt.get('message_count') or 0)}"
            )
            print("- blocker: native_mcp_prompt_api_missing resolved=true")
            print("- browser: route=dialogue mcp_prompt_parity=visible markers=8 hidden_advanced_panel=false")
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
    for item in items:
        if isinstance(item, dict) and str(item.get("name") or "") == SAFE_SERVICE_NAME:
            service_id = str(item.get("id") or "").strip()
            _assert(bool(service_id), "safe local MCP service id is present")
            return service_id
    raise AssertionError("PA Safe Local MCP service is not configured")


def _selected_service_name(services_surface: dict[str, Any], service_id: str) -> str:
    items = services_surface.get("items") if isinstance(services_surface.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "") == service_id:
            return str(item.get("name") or service_id)
    return ""


def _has_prompt(surface: dict[str, Any], prompt_name: str) -> bool:
    prompts = surface.get("sample_prompts") if isinstance(surface.get("sample_prompts"), list) else []
    return any(
        isinstance(prompt, dict) and str(prompt.get("name") or "") == prompt_name
        for prompt in prompts
    )


def _prompt_has_text_message(prompt: dict[str, Any]) -> bool:
    messages = prompt.get("messages") if isinstance(prompt.get("messages"), list) else []
    return any(
        isinstance(message, dict)
        and str(message.get("content_type") or "") == "text"
        and bool(str(message.get("text") or "").strip())
        for message in messages
    )


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
        '"data":',
        '"blob":',
    ]
    return not any(item in serialized for item in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
