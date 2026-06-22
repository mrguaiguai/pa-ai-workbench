"""Live WF-P1-03 smoke for PA active WeKnora workspace/KB mapping.

The smoke starts a temporary PA API, reads /api/status and /api/model/status,
and verifies that the active workspace/knowledge-base mapping is visible and
validated through live WeKnora API state. It never prints service tokens, base
URLs, provider payloads, raw documents, local database paths, or logs.
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
    """Raised when live KB mapping cannot be proven."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke(settings)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora KB mapping smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora KB mapping smoke passed (live)")
    print("- PA endpoint: /api/status")
    print(f"- knowledge backend: {result['knowledge_backend']}")
    print(f"- mock mode: {result['mock_mode']}")
    print(f"- WeKnora status: {result['weknora_status']}")
    print(f"- mapping status: {result['mapping_status']}")
    print(f"- mapping validated: {result['mapping_validated']}")
    print(f"- selection source: {result['selection_source']}")
    print(f"- default used: {result['default_used']}")
    print(f"- workspace id: {result['workspace_id']}")
    print(f"- knowledge base id: {result['kb_id']}")
    print(f"- knowledge base type: {result['kb_type']}")
    print(f"- chat mock: {result['chat_mock']}")
    print(f"- embedding mock: {result['embedding_mock']}")
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
    if not settings.weknora_workspace_id:
        missing.append("WEKNORA_WORKSPACE_ID")
    if not settings.weknora_default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(settings: Settings) -> dict[str, Any]:
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
        status = _get_json(port, "/api/status")
        model_status = _get_json(port, "/api/model/status")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    if status.get("knowledge_backend") != "weknora_api":
        raise SmokeError("PA status is not using weknora_api")
    if status.get("mock_mode") is True:
        raise SmokeError("PA status reports mock_mode=true")
    weknora = _dict(status.get("weknora"), "weknora status")
    if weknora.get("status") != "connected" or not weknora.get("connected"):
        raise SmokeError("WeKnora status is not connected")
    mapping = _dict(weknora.get("kb_mapping"), "kb_mapping")
    if mapping.get("status") != "validated" or mapping.get("validated") is not True:
        raise SmokeError("active KB mapping is not live validated")
    if mapping.get("workspace_id") != settings.weknora_workspace_id:
        raise SmokeError("workspace id mismatch")
    if mapping.get("kb_id") != settings.weknora_default_kb_id:
        raise SmokeError("knowledge base id mismatch")
    kb = _dict(mapping.get("knowledge_base"), "knowledge_base")
    workspace = _dict(mapping.get("workspace"), "workspace")
    if kb.get("id") != settings.weknora_default_kb_id:
        raise SmokeError("validated knowledge base id mismatch")
    if workspace.get("id") != settings.weknora_workspace_id:
        raise SmokeError("validated workspace id mismatch")
    if mapping.get("blocked_reason"):
        raise SmokeError("mapping unexpectedly reports a blocker")

    chat = _dict(model_status.get("chat"), "chat model status")
    embedding = _dict(model_status.get("embedding"), "embedding model status")
    if chat.get("mock") is True:
        raise SmokeError("chat model status is mock")
    if embedding.get("mock") is True:
        raise SmokeError("embedding model status is mock")

    return {
        "knowledge_backend": status.get("knowledge_backend"),
        "mock_mode": status.get("mock_mode"),
        "weknora_status": weknora.get("status"),
        "mapping_status": mapping.get("status"),
        "mapping_validated": mapping.get("validated"),
        "selection_source": mapping.get("selection_source"),
        "default_used": mapping.get("default_used"),
        "workspace_id": mapping.get("workspace_id"),
        "kb_id": mapping.get("kb_id"),
        "kb_type": kb.get("type"),
        "chat_mock": chat.get("mock"),
        "embedding_mock": embedding.get("mock"),
    }


def _get_json(port: int, path: str) -> dict[str, Any]:
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=30) as response:
        if response.status != 200:
            raise SmokeError(f"{path} returned HTTP {response.status}")
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise SmokeError(f"{path} returned non-object JSON")
    return parsed


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SmokeError(f"{label} is missing")
    return value


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
