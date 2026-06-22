"""Live WF-P2-01 smoke for read-only WeKnora MCP visibility through PA.

This smoke starts a temporary PA API, reads /api/mcp/native/overview, and
verifies that PA exposes sanitized read-only MCP readiness without credentials,
tool execution, or mutation flows. It never prints service tokens, URLs,
headers, env vars, provider payloads, local database paths, or logs.
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when MCP visibility cannot prove the declared contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora MCP visibility smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora MCP visibility smoke passed (live)")
    print("- PA endpoint: /api/mcp/native/overview")
    print(f"- overview status: {result['overview_status']}")
    print(f"- services status/count/enabled: {result['services_status']}/{result['services_count']}/{result['enabled_count']}")
    print(f"- tools status/count: {result['tools_status']}/{result['tools_count']}")
    print(f"- resources status/count: {result['resources_status']}/{result['resources_count']}")
    print(f"- approval status/count/required: {result['approval_status']}/{result['approval_count']}/{result['approval_required_count']}")
    print(f"- mutations status: {result['mutations_status']}")
    print(f"- sanitized response: {result['sanitized_response']}")
    return 0


def _validate_config(settings: Settings) -> None:
    missing: list[str] = []
    if settings.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if settings.mock_mode:
        missing.append("MOCK_MODE=false")
    if not settings.weknora_base_url:
        missing.append("WEKNORA_BASE_URL")
    if settings.weknora_base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if not settings.weknora_service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke() -> dict[str, Any]:
    endpoint = "/api/mcp/native/overview"
    port = _free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(BACKEND_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_pa_api(port, server)
        data = _get_json(port, f"{endpoint}?limit=5")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    if data.get("source") != "weknora_api":
        raise SmokeError("PA MCP overview did not use weknora_api")
    if data.get("status") not in {"live", "partial"}:
        raise SmokeError("PA MCP overview is not live or explicitly partial")
    surfaces = _dict(data.get("surfaces"), "surfaces")
    services = _surface(surfaces, "services")
    if services.get("status") != "live":
        raise SmokeError("MCP service list is not live")
    mutations = _surface(surfaces, "mutations")
    if mutations.get("status") != "backlog":
        raise SmokeError("MCP mutation/execution surfaces must remain backlog")
    forbidden = _forbidden_secret_paths(data)
    if forbidden:
        raise SmokeError("MCP overview leaked forbidden fields: " + ",".join(forbidden[:5]))

    tools = _surface(surfaces, "tools")
    resources = _surface(surfaces, "resources")
    approval = _surface(surfaces, "approval")
    for name, surface in (
        ("tools", tools),
        ("resources", resources),
        ("approval", approval),
    ):
        if surface.get("status") not in {"live", "partial", "backlog"}:
            raise SmokeError(f"{name} surface has unsafe status")

    return {
        "overview_status": data.get("status"),
        "services_status": services.get("status"),
        "services_count": int(services.get("count") or 0),
        "enabled_count": int(services.get("enabled_count") or 0),
        "tools_status": tools.get("status"),
        "tools_count": int(tools.get("count") or 0),
        "resources_status": resources.get("status"),
        "resources_count": int(resources.get("count") or 0),
        "approval_status": approval.get("status"),
        "approval_count": int(approval.get("count") or 0),
        "approval_required_count": int(approval.get("approval_required_count") or 0),
        "mutations_status": mutations.get("status"),
        "sanitized_response": True,
    }


def _get_json(port: int, path: str) -> dict[str, Any]:
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=45) as response:
        if response.status != 200:
            raise SmokeError(f"{path} returned HTTP {response.status}")
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise SmokeError(f"{path} returned non-object JSON")
    return parsed


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    value = surfaces.get(name)
    if not isinstance(value, dict):
        raise SmokeError(f"{name} surface is missing")
    return value


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SmokeError(f"{label} is missing")
    return value


def _forbidden_secret_paths(value: object, prefix: str = "$") -> list[str]:
    forbidden_names = {
        "api_key",
        "token",
        "headers",
        "auth_config",
        "url",
        "env_vars",
        "stdio_config",
        "inputSchema",
        "input_schema",
    }
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if key in forbidden_names:
                paths.append(path)
            paths.extend(_forbidden_secret_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_secret_paths(item, f"{prefix}[{index}]"))
    return paths


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_pa_api(port: int, server: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 30
    last_error = ""
    while time.monotonic() < deadline:
        if server.poll() is not None:
            stderr = ""
            if server.stderr is not None:
                stderr = server.stderr.read()
            raise SmokeError(f"temporary PA API exited early: {_safe_reason(RuntimeError(stderr))}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = _safe_reason(exc)
        time.sleep(0.25)
    raise SmokeError(f"temporary PA API did not become healthy: {last_error}")


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password"):
        text = text.replace(marker, "[redacted]")
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
