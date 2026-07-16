"""Live WNX-P0-02 smoke for the masked native config/status center.

This smoke starts a temporary PA API, reads /api/native/status, and verifies
that the response aggregates native readiness without leaking secret values,
provider payloads, raw URLs, logs, local database paths, chunks, or vectors.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
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


EXPECTED_GROUPS = {
    "system_health_status_deployment",
    "workspace_knowledge_base",
    "document_lifecycle",
    "chunk_management",
    "knowledge_search_rag",
    "knowledge_chat_session_chat",
    "agentqa_custom_agent",
    "native_wiki",
    "mcp",
    "web_search",
    "vector_store",
    "model_embedding_rerank_parser",
    "data_sources_connectors",
    "faq_tags_favorites_skills",
    "history_citation_product_shell",
}


class SmokeError(RuntimeError):
    """Raised when the status center cannot prove the declared contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native status center smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora native status center smoke passed (live)")
    print("- PA endpoint: /api/native/status")
    print(f"- overview status: {result['status']}")
    print(f"- group count: {result['group_count']}")
    print(f"- live groups: {result['live_count']}")
    print(f"- partial groups: {result['partial_count']}")
    print(f"- blocked/backlog groups: {result['blocked_backlog_count']}")
    print(f"- MCP/web/vector: {result['mcp_status']}/{result['web_search_status']}/{result['vector_store_status']}")
    print(f"- model status: {result['model_status']}")
    print(f"- masked response: {result['masked_response']}")
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
    endpoint = "/api/native/status"
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

    if data.get("schema_version") != "wnx-p0-02":
        raise SmokeError("status center schema_version is not wnx-p0-02")
    if data.get("source") != "pa_backend_bff":
        raise SmokeError("status center source is not pa_backend_bff")
    if data.get("evidence_type") != "live_api":
        raise SmokeError("status center evidence_type is not live_api")
    if data.get("masked") is not True:
        raise SmokeError("status center is not explicitly masked")

    groups = _dict(data.get("groups"), "groups")
    missing = sorted(EXPECTED_GROUPS - set(groups))
    if missing:
        raise SmokeError("status center missing groups: " + ",".join(missing))
    if int(data.get("group_count") or 0) != len(EXPECTED_GROUPS):
        raise SmokeError("status center group_count is wrong")

    for group_id, group in groups.items():
        _validate_group(group_id, _dict(group, group_id))

    if groups["mcp"].get("status") != "live":
        raise SmokeError("MCP status is not live")
    if groups["web_search"].get("status") != "live":
        raise SmokeError("web search status is not live")
    if groups["vector_store"].get("status") != "live":
        raise SmokeError("vector store status is not live")
    if groups["model_embedding_rerank_parser"].get("status") != "live":
        raise SmokeError("model/embedding/parser status is not live")
    if groups["data_sources_connectors"].get("status") != "backlog":
        raise SmokeError("data source connectors must remain backlog in WNX-P0-02")
    if groups["faq_tags_favorites_skills"].get("status") != "backlog":
        raise SmokeError("FAQ/tag/favorite/skill group must remain backlog in WNX-P0-02")

    forbidden = _forbidden_paths(data)
    if forbidden:
        raise SmokeError("status center leaked forbidden fields: " + ",".join(forbidden[:5]))

    status_counts = _status_counts(groups)
    return {
        "status": data.get("status"),
        "group_count": data.get("group_count"),
        "live_count": status_counts.get("live", 0),
        "partial_count": status_counts.get("partial", 0),
        "blocked_backlog_count": status_counts.get("blocked", 0) + status_counts.get("backlog", 0),
        "mcp_status": groups["mcp"].get("status"),
        "web_search_status": groups["web_search"].get("status"),
        "vector_store_status": groups["vector_store"].get("status"),
        "model_status": groups["model_embedding_rerank_parser"].get("status"),
        "masked_response": True,
    }


def _validate_group(group_id: str, group: dict[str, Any]) -> None:
    for key in ("id", "label", "status", "configured", "masked", "source_endpoint", "next_action", "summary"):
        if key not in group:
            raise SmokeError(f"{group_id} missing {key}")
    if group.get("id") != group_id:
        raise SmokeError(f"{group_id} has mismatched id")
    if group.get("status") not in {"live", "partial", "blocked", "backlog"}:
        raise SmokeError(f"{group_id} has unsafe status")
    if group.get("masked") is not True:
        raise SmokeError(f"{group_id} is not masked")
    if not str(group.get("source_endpoint") or "").startswith("/api/"):
        raise SmokeError(f"{group_id} source_endpoint is not a PA/API route")
    if not str(group.get("next_action") or "").startswith("WNX-"):
        raise SmokeError(f"{group_id} next_action is not a WNX task")


def _get_json(port: int, path: str) -> dict[str, Any]:
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=45) as response:
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


def _status_counts(groups: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in groups.values():
        status = str(group.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _forbidden_paths(value: object, prefix: str = "$") -> list[str]:
    forbidden_names = {
        "api_key",
        "token",
        "password",
        "secret",
        "headers",
        "auth_config",
        "base_url",
        "url",
        "env_vars",
        "connection_config",
        "provider_payload",
        "raw",
        "records",
        "vectors",
        "chunks",
        "logs",
        "database_url",
    }
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if key in forbidden_names:
                paths.append(path)
            paths.extend(_forbidden_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_paths(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        if _looks_like_private_value(value):
            paths.append(prefix)
    return paths


def _looks_like_private_value(value: str) -> bool:
    if re.search(r"https?://", value):
        return True
    return bool(re.search(r"(sk-[A-Za-z0-9]|Bearer\\s+|BEGIN .*PRIVATE KEY)", value))


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
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        text = text.replace(marker, "[redacted]")
    return text[:220]


if __name__ == "__main__":
    raise SystemExit(main())
