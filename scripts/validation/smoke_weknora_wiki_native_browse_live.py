"""Live WF-P1-02 smoke for native WeKnora Wiki browse/search/index surfaces.

This smoke calls the PA API wrapper for native Wiki overview. It proves the
read-only PA slice reaches WeKnora native Wiki pages/search/read/index/stats and
records graph/lint/issues as live or explicit partial/blocked surfaces. It never
prints service tokens, raw page content, provider payloads, local database paths,
or logs.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the native Wiki browse smoke cannot prove the contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke(settings)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native Wiki browse smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora native Wiki browse smoke passed (live)")
    print(f"- PA endpoint: {result['endpoint']}")
    print(f"- knowledge base: {result['kb_id']}")
    print(f"- overview status: {result['overview_status']}")
    print(f"- pages status/count/total: {result['pages_status']}/{result['pages_count']}/{result['pages_total']}")
    print(f"- search status/count: {result['search_status']}/{result['search_count']}")
    print(f"- read status/slug: {result['read_status']}/{result['read_slug']}")
    print(f"- read traceable: {result['read_traceable']}")
    print(f"- index status/groups/entries: {result['index_status']}/{result['index_groups']}/{result['index_entries']}")
    print(f"- stats status/total_pages: {result['stats_status']}/{result['stats_total_pages']}")
    print(f"- graph status/nodes: {result['graph_status']}/{result['graph_nodes']}")
    print(f"- lint status/issues: {result['lint_status']}/{result['lint_issues']}")
    print(f"- issues status/count: {result['issues_status']}/{result['issues_count']}")
    print(f"- mutations status: {result['mutations_status']}")
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
    if settings.weknora_timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(settings: Settings) -> dict[str, Any]:
    endpoint = "/api/wiki/native/overview"
    query = os.getenv("WEKNORA_WIKI_NATIVE_QUERY", "")
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
        params = urlencode(
            {"kb_id": settings.weknora_default_kb_id, "query": query, "limit": 5}
        )
        with urlopen(f"http://127.0.0.1:{port}{endpoint}?{params}", timeout=60) as response:
            if response.status != 200:
                raise SmokeError(f"PA native Wiki overview returned HTTP {response.status}")
            data = json_loads(response.read().decode("utf-8"))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    if data.get("source") != "weknora_api":
        raise SmokeError("PA native Wiki overview did not use weknora_api")

    surfaces = data.get("surfaces")
    if not isinstance(surfaces, dict):
        raise SmokeError("PA native Wiki overview returned no surfaces")
    core = {name: _surface(surfaces, name) for name in ("pages", "search", "read", "index", "stats")}
    blocked_core = [name for name, surface in core.items() if surface.get("status") != "live"]
    if blocked_core:
        raise SmokeError("core native Wiki surfaces blocked: " + ",".join(blocked_core))

    pages = core["pages"]
    search = core["search"]
    read = core["read"]
    index = core["index"]
    stats = core["stats"]
    mutations = _surface(surfaces, "mutations")
    if int(pages.get("count") or 0) <= 0:
        raise SmokeError("native Wiki pages returned no items")
    if int(search.get("count") or 0) <= 0:
        raise SmokeError("native Wiki search returned no items")
    if read.get("source_type") != "wiki_page":
        raise SmokeError("native Wiki read did not preserve source_type=wiki_page")
    if not read.get("wiki_page_id") or not read.get("evidence_id"):
        raise SmokeError("native Wiki read lost wiki_page_id or evidence_id")
    if int(index.get("group_count") or 0) <= 0:
        raise SmokeError("native Wiki index returned no groups")
    if int(stats.get("total_pages") or 0) <= 0:
        raise SmokeError("native Wiki stats returned zero total pages")
    if mutations.get("status") != "backlog":
        raise SmokeError("native Wiki mutation surfaces must remain backlog in WF-P1-02")

    graph = _surface(surfaces, "graph")
    lint = _surface(surfaces, "lint")
    issues = _surface(surfaces, "issues")
    return {
        "endpoint": endpoint,
        "port": port,
        "kb_id": data.get("kb_id"),
        "overview_status": data.get("status"),
        "pages_status": pages.get("status"),
        "pages_count": pages.get("count"),
        "pages_total": pages.get("total"),
        "search_status": search.get("status"),
        "search_count": search.get("count"),
        "read_status": read.get("status"),
        "read_slug": read.get("slug"),
        "read_traceable": bool(read.get("wiki_page_id") and read.get("evidence_id")),
        "index_status": index.get("status"),
        "index_groups": index.get("group_count"),
        "index_entries": index.get("entry_count"),
        "stats_status": stats.get("status"),
        "stats_total_pages": stats.get("total_pages"),
        "graph_status": graph.get("status", "missing"),
        "graph_nodes": graph.get("nodes_count", 0),
        "lint_status": lint.get("status", "missing"),
        "lint_issues": lint.get("issue_count", 0),
        "issues_status": issues.get("status", "missing"),
        "issues_count": issues.get("count", 0),
        "mutations_status": mutations.get("status"),
    }


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    value = surfaces.get(name)
    if not isinstance(value, dict):
        raise SmokeError(f"missing native Wiki surface: {name}")
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


def json_loads(value: str) -> dict[str, Any]:
    import json

    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise SmokeError("PA native Wiki overview returned non-object JSON")
    return parsed


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password"):
        text = text.replace(marker, "[redacted]")
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
