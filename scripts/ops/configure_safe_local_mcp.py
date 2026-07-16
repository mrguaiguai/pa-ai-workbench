"""Configure the safe local MCP service through PA's confirmed native MCP path.

The script starts a temporary PA backend so the mutation still goes through the
PA BFF confirmation gate instead of direct native database edits. The native MCP
service itself persists in WeKnora.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = PROJECT_ROOT / "scripts" / "validation"
if str(VALIDATION_ROOT) not in sys.path:
    sys.path.append(str(VALIDATION_ROOT))

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_TOKEN = "CONFIRM_NATIVE_MCP_MUTATION"
TEST_TOKEN = "TEST_NATIVE_MCP_SERVICE"
SAFE_SERVICE_NAME = "PA Safe Local MCP"
SAFE_SERVICE_URL = "http://host.docker.internal:8765/mcp"


def main() -> int:
    backend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-safe-mcp-config-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'safe-mcp-config.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port=_free_port())
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/mcp/native/overview?limit=10")
            services = _services(overview)
            existing = _find_service(services, SAFE_SERVICE_NAME)

            if existing:
                service_id = str(existing.get("id") or "")
                result = _request_json(
                    backend_port,
                    "PUT",
                    f"/api/mcp/native/services/{service_id}",
                    {
                        "name": SAFE_SERVICE_NAME,
                        "description": "Read-only local MCP service for WNID validation.",
                        "enabled": True,
                        "transport_type": "http-streamable",
                        "url": SAFE_SERVICE_URL,
                        "confirm_token": CONFIRM_TOKEN,
                    },
                )
                action = "update"
            else:
                result = _request_json(
                    backend_port,
                    "POST",
                    "/api/mcp/native/services",
                    {
                        "name": SAFE_SERVICE_NAME,
                        "description": "Read-only local MCP service for WNID validation.",
                        "enabled": True,
                        "transport_type": "http-streamable",
                        "url": SAFE_SERVICE_URL,
                        "confirm_token": CONFIRM_TOKEN,
                    },
                )
                action = "create"

            mutation = result.get("surfaces", {}).get("mutation", {}) if isinstance(result, dict) else {}
            _assert(mutation.get("success") is True, "safe local MCP mutation succeeded")
            service = mutation.get("result") if isinstance(mutation.get("result"), dict) else {}
            service_id = str(service.get("id") or (existing.get("id") if existing else "") or "")
            _assert(bool(service_id), "safe local MCP service id is available")

            confirmed = _request_json(
                backend_port,
                "POST",
                f"/api/mcp/native/services/{service_id}/test",
                {"confirm_token": TEST_TOKEN},
            )
            safe_test = confirmed.get("surfaces", {}).get("safe_test", {}) if isinstance(confirmed, dict) else {}
            _assert(safe_test.get("success") is True, "safe local MCP test succeeded")
            _assert(int(safe_test.get("tool_count") or 0) > 0, "safe local MCP exposes tools")
            _assert(int(safe_test.get("resource_count") or 0) > 0, "safe local MCP exposes resources")

            print("PA safe local MCP configured")
            print(f"- action: {action}")
            print("- service: PA Safe Local MCP")
            print("- transport: http-streamable")
            print("- enabled: true")
            print(
                "- live_test: "
                f"success=true tools={int(safe_test.get('tool_count') or 0)} "
                f"resources={int(safe_test.get('resource_count') or 0)}"
            )
            print("- mutation_path: PA BFF confirmed native MCP mutation")
            return 0
        finally:
            _terminate(backend)


def _services(overview: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
    service_surface = surfaces.get("services") if isinstance(surfaces.get("services"), dict) else {}
    items = service_surface.get("items") if isinstance(service_surface.get("items"), list) else []
    return [item for item in items if isinstance(item, dict)]


def _find_service(services: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for service in services:
        if str(service.get("name") or "") == name:
            return service
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
