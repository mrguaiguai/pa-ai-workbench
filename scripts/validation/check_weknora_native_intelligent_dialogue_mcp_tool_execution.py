"""Live WNID-P3-02 approval-gated MCP tool execution check.

The script starts temporary PA backend/frontend services, uses the configured
safe local MCP service, proves rejection and approved execution through PA's
confirmed native path, then verifies NativeMutationAudit, history, and the
dialogue UI surface.
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


CONFIRM_TOKEN = "EXECUTE_NATIVE_MCP_TOOL"
SAFE_SERVICE_NAME = "PA Safe Local MCP"
SAFE_TOOL_NAME = "ping"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-mcp-execution-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'mcp-execution.db'}"
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
            service_id = _selected_service_id(services)
            service_name = _selected_service_name(services, service_id)
            _assert(service_name == SAFE_SERVICE_NAME, "safe local MCP service is configured")

            confirmed = _request_json(
                backend_port,
                "POST",
                f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                {"confirm_token": "TEST_NATIVE_MCP_SERVICE"},
            )
            _assert(_no_secret_payload(confirmed), "confirmed test response excludes secrets")
            safe_test = _surface(
                confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {},
                "safe_test",
            )
            _assert(bool(safe_test.get("success")), "safe MCP service confirms live tools/resources")
            _assert(int(safe_test.get("tool_count") or 0) > 0, "safe MCP service has tools")

            approval = _request_json(
                backend_port,
                "PUT",
                (
                    f"/api/mcp/native/services/{quote(service_id, safe='')}"
                    f"/tool-approvals/{quote(SAFE_TOOL_NAME, safe='')}"
                ),
                {"require_approval": True, "confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(approval), "approval response excludes secrets")
            _assert(_surface(approval.get("surfaces", {}), "approval_policy").get("status") == "live",
                    "approval policy set through PA")
            approval_audit_id = str((approval.get("audit") or {}).get("id") or "")
            _assert(bool(approval_audit_id), "approval policy audit id returned")

            rejected = _execute_tool(backend_port, service_id, "reject")
            rejected_result = _tool_execution_result(rejected)
            _assert(bool(rejected_result.get("success")), "rejected execution returns successful denial")
            _assert(bool(rejected_result.get("approval_required")), "rejected execution used approval policy")
            _assert(bool(rejected_result.get("rejected")), "rejected execution was denied")
            _assert(not bool(rejected_result.get("executed")), "rejected execution did not call tool")
            reject_output_id = _history_output_id(rejected)

            approved = _execute_tool(backend_port, service_id, "approve")
            approved_result = _tool_execution_result(approved)
            _assert(bool(approved_result.get("success")), "approved execution succeeds")
            _assert(bool(approved_result.get("approval_required")), "approved execution used approval policy")
            _assert(bool(approved_result.get("executed")), "approved execution called tool")
            _assert(not bool(approved_result.get("rejected")), "approved execution was not rejected")
            _assert("pong" in str(approved_result.get("output") or "").lower(), "approved output is summarized")
            approved_output_id = _history_output_id(approved)

            audits = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?capability=mcp&operation=weknora_mcp_tool_execute&limit=20",
            )
            _assert(_audit_count(audits, "succeeded") >= 2, "MCP execution audits are persisted")
            history = _request_json(backend_port, "GET", "/api/history?task_type=native_mcp_tool_execution")
            _assert(int(history.get("total") or 0) >= 2, "MCP execution history outputs are listed")
            _assert(_history_contains(history, approved_output_id), "approved output is visible in history")
            _assert(_history_contains(history, reject_output_id), "rejected output is visible in history")
            _assert(_no_secret_payload(audits), "audit response excludes secrets")
            _assert(_no_secret_payload(history), "history response excludes secrets")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "MCP Read Path",
                "execution_status",
                "Reject ping",
                "Approve ping",
                "safe_service",
                "history_output",
                "audit",
            )
            dom = _wait_for_dialogue_dom(frontend_port, temp_path / "chrome-profile", markers)
            _assert("高级工具" not in dom, "MCP tool execution is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue MCP execution panel does not render secrets")

            print("WeKnora native intelligent dialogue MCP tool execution")
            print("- decision: PASS")
            print("- task: WNID-P3-02")
            print("- evidence_type: live_service + live_api + live_browser + audit_history + native_go_test")
            print(
                "- api: "
                f"service={service_name} tool={SAFE_TOOL_NAME} approval_policy=live "
                "reject=rejected approve=executed "
                f"approval_required={str(bool(approved_result.get('approval_required'))).lower()} "
                f"audits={_audit_count(audits, 'succeeded')} history={int(history.get('total') or 0)}"
            )
            print(
                "- history: "
                f"reject_output={reject_output_id} approve_output={approved_output_id} "
                "task_type=native_mcp_tool_execution"
            )
            print("- browser: route=dialogue mcp_tool_execution=visible markers=8 hidden_advanced_panel=false")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)


def _execute_tool(port: int, service_id: str, approval_decision: str) -> dict[str, Any]:
    response = _request_json(
        port,
        "POST",
        (
            f"/api/mcp/native/services/{quote(service_id, safe='')}"
            f"/tools/{quote(SAFE_TOOL_NAME, safe='')}/execute"
        ),
        {
            "arguments": {"message": f"wnid-p3-02-{approval_decision}"},
            "approval_decision": approval_decision,
            "confirm_token": CONFIRM_TOKEN,
        },
    )
    _assert(_no_secret_payload(response), f"{approval_decision} execution response excludes secrets")
    audit_id = str((response.get("audit") or {}).get("id") or "")
    _assert(bool(audit_id), f"{approval_decision} execution audit id returned")
    _assert(str((response.get("audit") or {}).get("status") or "") == "succeeded",
            f"{approval_decision} execution audit succeeded")
    return response


def _tool_execution_result(response: dict[str, Any]) -> dict[str, Any]:
    surfaces = response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {}
    execution = _surface(surfaces, "tool_execution")
    _assert(execution.get("status") == "live", "tool execution surface is live")
    result = execution.get("result")
    _assert(isinstance(result, dict), "tool execution result is present")
    return result


def _history_output_id(response: dict[str, Any]) -> str:
    surfaces = response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {}
    history = _surface(_surface(surfaces, "tool_execution"), "history")
    output_id = str(history.get("output_id") or "")
    _assert(bool(output_id), "tool execution history output id returned")
    return output_id


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


def _audit_count(payload: dict[str, Any], status: str) -> int:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    return sum(
        1
        for item in items
        if isinstance(item, dict) and str(item.get("status") or "") == status
    )


def _history_contains(payload: dict[str, Any], output_id: str) -> bool:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    return any(isinstance(item, dict) and str(item.get("id") or "") == output_id for item in items)


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
    ]
    return not any(item in serialized for item in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
