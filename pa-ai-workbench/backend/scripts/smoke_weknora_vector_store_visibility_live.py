"""Live WF-P2-03 smoke for read-only WeKnora vector store visibility through PA.

This smoke starts a temporary PA API, reads /api/vector-stores/native/overview,
and verifies that PA exposes sanitized vector-store readiness, active KB
binding state, and embedding readiness without connection strings,
credentials, raw health payloads, vector records, or local DB contents.
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
    """Raised when vector store visibility cannot prove the declared contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora vector store visibility smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora vector store visibility smoke passed (live)")
    print("- PA endpoint: /api/vector-stores/native/overview")
    print(f"- overview status: {result['overview_status']}")
    print(f"- store types status/count: {result['store_types_status']}/{result['store_types_count']}")
    print(f"- stores status/count/env/user: {result['stores_status']}/{result['stores_count']}/{result['env_count']}/{result['user_count']}")
    print(f"- KB binding status/source/engine: {result['kb_status']}/{result['kb_source']}/{result['kb_engine']}")
    print(f"- embedding status/provider/mock: {result['embedding_status']}/{result['embedding_provider']}/{result['embedding_mock']}")
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
    endpoint = "/api/vector-stores/native/overview"
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
        raise SmokeError("PA vector store overview did not use weknora_api")
    if data.get("status") != "live":
        raise SmokeError("PA vector store overview is not live")
    surfaces = _dict(data.get("surfaces"), "surfaces")
    store_types = _surface(surfaces, "store_types")
    stores = _surface(surfaces, "stores")
    kb_binding = _surface(surfaces, "kb_binding")
    embedding = _surface(surfaces, "embedding")
    mutations = _surface(surfaces, "mutations")
    if store_types.get("status") != "live":
        raise SmokeError("vector store type catalog is not live")
    if stores.get("status") != "live":
        raise SmokeError("vector store list is not live")
    if kb_binding.get("status") not in {"live", "blocked", "configured_unknown"}:
        raise SmokeError("KB binding status is not explicit")
    if embedding.get("status") != "live" or embedding.get("mock") is not False:
        raise SmokeError("embedding readiness is not live non-mock")
    if mutations.get("status") != "backlog":
        raise SmokeError("vector store mutation/test surfaces must remain backlog")
    forbidden = _forbidden_secret_paths(data)
    if forbidden:
        raise SmokeError(
            "vector store overview leaked forbidden fields: " + ",".join(forbidden[:5])
        )

    return {
        "overview_status": data.get("status"),
        "store_types_status": store_types.get("status"),
        "store_types_count": int(store_types.get("count") or 0),
        "stores_status": stores.get("status"),
        "stores_count": int(stores.get("count") or 0),
        "env_count": int(stores.get("env_count") or 0),
        "user_count": int(stores.get("user_count") or 0),
        "kb_status": kb_binding.get("binding_status") or kb_binding.get("status"),
        "kb_source": kb_binding.get("binding_source") or "unknown",
        "kb_engine": kb_binding.get("engine_type") or "unknown",
        "embedding_status": embedding.get("status"),
        "embedding_provider": embedding.get("provider"),
        "embedding_mock": embedding.get("mock"),
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
        "id",
        "tenant_id",
        "vector_store_id",
        "connection_config",
        "index_config",
        "addr",
        "host",
        "port",
        "grpc_address",
        "scheme",
        "database",
        "username",
        "password",
        "api_key",
        "token",
        "endpoint",
        "index_name",
        "collection_name",
        "collection_prefix",
        "raw",
        "records",
        "vectors",
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
