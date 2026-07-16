"""Live WF-P2-02 smoke for read-only WeKnora web search visibility through PA.

This smoke starts a temporary PA API, reads /api/web-search/native/overview,
and verifies that PA exposes sanitized provider readiness without credentials,
provider endpoints, raw payloads, connection tests, or mutation flows.
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
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when web search visibility cannot prove the declared contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora web search visibility smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora web search visibility smoke passed (live)")
    print("- PA endpoint: /api/web-search/native/overview")
    print(f"- overview status: {result['overview_status']}")
    print(f"- provider types status/count: {result['provider_types_status']}/{result['provider_types_count']}")
    print(f"- configured providers status/count/default: {result['configured_status']}/{result['configured_count']}/{result['default_count']}")
    print(f"- credentials configured count: {result['credentials_configured_count']}")
    print(f"- AgentQA web search status: {result['agentqa_status']}")
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
    endpoint = "/api/web-search/native/overview"
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
        raise SmokeError("PA web search overview did not use weknora_api")
    if data.get("status") != "live":
        raise SmokeError("PA web search overview is not live")
    surfaces = _dict(data.get("surfaces"), "surfaces")
    provider_types = _surface(surfaces, "provider_types")
    configured = _surface(surfaces, "configured_providers")
    agentqa = _surface(surfaces, "agentqa_dependency")
    mutations = _surface(surfaces, "mutations")
    if provider_types.get("status") != "live":
        raise SmokeError("web search provider type catalog is not live")
    if configured.get("status") != "live":
        raise SmokeError("web search configured provider list is not live")
    if mutations.get("status") != "backlog":
        raise SmokeError("web search mutation/test surfaces must remain backlog")
    if agentqa.get("required_for_agentqa") is not False:
        raise SmokeError("AgentQA web search dependency was overstated")
    if agentqa.get("status") not in {"optional", "optional_unconfigured"}:
        raise SmokeError("AgentQA web search status is not explicit optional state")
    forbidden = _forbidden_secret_paths(data)
    if forbidden:
        raise SmokeError(
            "web search overview leaked forbidden fields: " + ",".join(forbidden[:5])
        )

    return {
        "overview_status": data.get("status"),
        "provider_types_status": provider_types.get("status"),
        "provider_types_count": int(provider_types.get("count") or 0),
        "configured_status": configured.get("status"),
        "configured_count": int(configured.get("count") or 0),
        "default_count": int(configured.get("default_count") or 0),
        "credentials_configured_count": int(
            configured.get("credentials_configured_count") or 0
        ),
        "agentqa_status": agentqa.get("status"),
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
        "parameters",
        "credentials",
        "base_url",
        "proxy_url",
        "engine_id",
        "extra_config",
        "docs_url",
        "api_url",
        "url",
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
