"""Live WNFC-P2-03 MCP approval-gated tool execution blocker smoke.

This script does not execute MCP tools and does not mark WNFC-P2-03 complete.
It captures current-run blocker evidence: native approval/execution primitives
exist in WeKnora, but the current configured MCP service does not initialize
with a real tool list, so PA cannot prove a low-risk approval-gated tool
execution with timeout, audit, and history.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import quote

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE"


def main() -> int:
    backend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-mcp-p2-03-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'mcp-p2-03.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, None)
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes secret-shaped fields")

            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            services = _surface(surfaces, "services")
            tool_execution = _surface(surfaces, "tool_execution")
            approval = _surface(surfaces, "approval")
            _assert(services.get("status") == "live", "MCP service list is live")
            _assert(tool_execution.get("status") == "blocked", "tool execution is blocked")
            _assert(
                tool_execution.get("reason") == "requires_live_mcp_tool_and_confirmed_execution_path",
                "overview exposes tool execution blocker reason",
            )

            items = services.get("items") if isinstance(services.get("items"), list) else []
            service_id = str((items[0] if items else {}).get("id") or "")
            confirmed_status = "not_configured"
            confirmed_success = False
            tool_count = 0
            execution_reason = str(tool_execution.get("reason") or "")
            current_service_blocker = ""
            if service_id:
                detail = _request_json(
                    backend_port,
                    "GET",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}",
                )
                _assert(_no_secret_payload(detail), "service detail excludes secret-shaped fields")
                detail_surfaces = detail.get("surfaces") if isinstance(detail.get("surfaces"), dict) else {}
                detail_execution = _surface(detail_surfaces, "tool_execution")
                _assert(detail_execution.get("status") == "blocked", "detail exposes tool execution blocker")

                confirmed = _request_json(
                    backend_port,
                    "POST",
                    f"/api/mcp/native/services/{quote(service_id, safe='')}/test",
                    {"confirm_token": CONFIRM_TOKEN},
                )
                _assert(_no_secret_payload(confirmed), "confirmed test response excludes secret-shaped fields")
                confirmed_surfaces = confirmed.get("surfaces") if isinstance(confirmed.get("surfaces"), dict) else {}
                safe_test = _surface(confirmed_surfaces, "safe_test")
                confirmed_execution = _surface(confirmed_surfaces, "tool_execution")
                confirmed_status = str(safe_test.get("status"))
                confirmed_success = bool(safe_test.get("success"))
                tool_count = int(safe_test.get("tool_count") or 0)
                execution_reason = str(confirmed_execution.get("reason") or "")
                current_service_blocker = str(safe_test.get("reason") or "")
                _assert(confirmed_status == "partial", "confirmed MCP test is partial")
                _assert(confirmed_success is False, "confirmed MCP test is not successful")
                _assert(tool_count == 0, "current service exposes no live tools")
                _assert(execution_reason == "no_live_mcp_tool_available", "confirmed test explains no live MCP tool")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            summary = (
                native_status.get("groups", {})
                .get("mcp", {})
                .get("summary", {})
                if isinstance(native_status.get("groups"), dict)
                else {}
            )
            _assert(summary.get("tool_execution_status") == "blocked", "status center exposes tool execution blocker")
            _assert(_no_secret_payload(native_status), "native status excludes secret-shaped fields")

            print("WeKnora native MCP approval-gated tool execution")
            print("- decision: BLOCKED")
            print("- evidence_type: blocked evidence plus live api")
            print(
                "- services: status={status} count={count} approval={approval_status}".format(
                    status=services.get("status"),
                    count=int(services.get("count") or 0),
                    approval_status=approval.get("status"),
                )
            )
            print(
                "- confirmed_test: status={status} success={success} tools={tools_count}".format(
                    status=confirmed_status,
                    success=str(confirmed_success).lower(),
                    tools_count=tool_count,
                )
            )
            print(f"- tool_execution: blocked reason={execution_reason}")
            if current_service_blocker:
                print(f"- current_service_blocker: {current_service_blocker[:220]}")
            return 0
        finally:
            _terminate(backend)


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


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
    return not any(token in serialized for token in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
