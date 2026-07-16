"""Live WNX-P1-06 smoke for native WeKnora Wiki workflow.

The smoke proves PA reaches WeKnora native Wiki pages/search/read/index/log/
graph/stats/lint/issues and performs a safe mutation cycle on a temporary page:
create, update, and soft delete. It prints only status/count/slug evidence, not
raw Wiki content, provider payloads, tokens, logs, or local database paths.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


CONFIRM_CREATE = "CREATE_NATIVE_WIKI_PAGE"
CONFIRM_UPDATE = "UPDATE_NATIVE_WIKI_PAGE"
CONFIRM_DELETE = "DELETE_NATIVE_WIKI_PAGE"


class SmokeError(RuntimeError):
    """Raised when the native Wiki workflow smoke cannot prove the contract."""


def main() -> int:
    settings = Settings()
    try:
        _validate_config(settings)
        result = _run_live_smoke(settings)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native Wiki workflow smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora native Wiki workflow smoke passed (live)")
    print(f"- PA endpoint: {result['endpoint']}")
    print(f"- knowledge base: {result['kb_id']}")
    print(f"- overview status/mutations: {result['overview_status']}/{result['mutations_status']}")
    print(f"- pages status/count: {result['pages_status']}/{result['pages_count']}")
    print(f"- search count: {result['search_count']}")
    print(f"- read traceable: {result['read_traceable']}")
    print(f"- index groups/entries: {result['index_groups']}/{result['index_entries']}")
    print(f"- log entries: {result['log_entries']}")
    print(f"- graph nodes/edges: {result['graph_nodes']}/{result['graph_edges']}")
    print(f"- stats total_pages: {result['stats_total_pages']}")
    print(f"- lint issue_count: {result['lint_issue_count']}")
    print(f"- issues count: {result['issues_count']}")
    print(f"- mutation cycle: {result['mutation_cycle']}")
    print(f"- temp slug: {result['temp_slug']}")
    return 0


def _validate_config(settings: Settings) -> None:
    missing: list[str] = []
    if settings.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if settings.mock_mode:
        missing.append("MOCK_MODE=false")
    if not settings.weknora_base_url or settings.weknora_base_url.startswith("fixture://"):
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
    endpoint = "/api/wiki/native"
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
    temp_slug = f"pa-wnx-p1-06-{int(time.time())}-{os.getpid()}"
    deleted = False
    try:
        _wait_for_pa_api(port, server)
        base_url = f"http://127.0.0.1:{port}"
        kb_id = settings.weknora_default_kb_id
        create_payload = {
            "confirm_token": CONFIRM_CREATE,
            "slug": temp_slug,
            "title": "PA WNX P1 06 temporary native Wiki page",
            "summary": "Temporary live validation page for WNX-P1-06.",
            "content_markdown": "Temporary validation content for native Wiki workflow.",
            "page_type": "concept",
            "status": "draft",
            "metadata": {"test_scope": "WNX-P1-06"},
        }
        created = _json_request(
            f"{base_url}{endpoint}/pages?{urlencode({'kb_id': kb_id})}",
            method="POST",
            payload=create_payload,
        )
        _assert_slug(created, temp_slug, "create")

        update_payload = {**create_payload, "confirm_token": CONFIRM_UPDATE}
        update_payload["summary"] = "Updated temporary live validation page for WNX-P1-06."
        updated = _json_request(
            f"{base_url}{endpoint}/page?{urlencode({'kb_id': kb_id, 'slug': temp_slug})}",
            method="PUT",
            payload=update_payload,
        )
        _assert_slug(updated, temp_slug, "update")

        pages = _json_request(
            f"{base_url}{endpoint}/pages?{urlencode({'kb_id': kb_id, 'page_size': 8})}",
        )
        search = _json_request(
            f"{base_url}{endpoint}/search?{urlencode({'kb_id': kb_id, 'query': temp_slug, 'limit': 5})}",
        )
        read = _json_request(
            f"{base_url}{endpoint}/page?{urlencode({'kb_id': kb_id, 'slug': temp_slug})}",
        )
        _assert_slug(read, temp_slug, "read")
        if read.get("source_type") != "wiki_page" or not read.get("evidence_id"):
            raise SmokeError("native Wiki read did not preserve traceable Wiki evidence fields")

        index = _json_request(
            f"{base_url}{endpoint}/index?{urlencode({'kb_id': kb_id, 'limit': 8})}",
        )
        log = _json_request(
            f"{base_url}{endpoint}/log?{urlencode({'kb_id': kb_id, 'limit': 8})}",
        )
        graph = _json_request(
            f"{base_url}{endpoint}/graph?{urlencode({'kb_id': kb_id, 'limit': 30})}",
        )
        stats = _json_request(f"{base_url}{endpoint}/stats?{urlencode({'kb_id': kb_id})}")
        lint = _json_request(f"{base_url}{endpoint}/lint?{urlencode({'kb_id': kb_id})}")
        issues = _json_request(f"{base_url}{endpoint}/issues?{urlencode({'kb_id': kb_id})}")
        overview = _json_request(
            f"{base_url}{endpoint}/overview?{urlencode({'kb_id': kb_id, 'query': temp_slug, 'limit': 5})}",
        )

        deleted_payload = {"confirm_token": CONFIRM_DELETE, "slug": temp_slug}
        deleted_result = _json_request(
            f"{base_url}{endpoint}/page/delete?{urlencode({'kb_id': kb_id})}",
            method="POST",
            payload=deleted_payload,
        )
        deleted = True
        if deleted_result.get("status") != "deleted":
            raise SmokeError("native Wiki delete did not return deleted status")

        surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
        mutations = surfaces.get("mutations") if isinstance(surfaces.get("mutations"), dict) else {}
        if mutations.get("status") != "live" or not mutations.get("confirmation_required"):
            raise SmokeError("native Wiki mutation surface is not live with confirmation_required")

        groups = [item for item in index.get("groups") or [] if isinstance(item, dict)]
        graph_meta = graph.get("meta") if isinstance(graph.get("meta"), dict) else {}
        issue_items = issues.get("items") if isinstance(issues.get("items"), list) else []
        return {
            "endpoint": endpoint,
            "kb_id": kb_id,
            "overview_status": overview.get("status"),
            "mutations_status": mutations.get("status"),
            "pages_status": pages.get("source"),
            "pages_count": len(pages.get("pages") or []),
            "search_count": len(search.get("items") or []),
            "read_traceable": bool(read.get("wiki_page_id") and read.get("evidence_id")),
            "index_groups": len(groups),
            "index_entries": sum(len(group.get("items") or []) for group in groups),
            "log_entries": int(log.get("count") or 0),
            "graph_nodes": int(graph.get("nodes_count") or graph_meta.get("returned") or 0),
            "graph_edges": int(graph.get("edges_count") or 0),
            "stats_total_pages": int(stats.get("total_pages") or 0),
            "lint_issue_count": int(lint.get("issue_count") or 0),
            "issues_count": len(issue_items),
            "mutation_cycle": "create/update/delete",
            "temp_slug": temp_slug,
        }
    finally:
        if not deleted:
            try:
                _json_request(
                    f"http://127.0.0.1:{port}{endpoint}/page/delete?{urlencode({'kb_id': settings.weknora_default_kb_id})}",
                    method="POST",
                    payload={"confirm_token": CONFIRM_DELETE, "slug": temp_slug},
                    timeout=15,
                )
            except Exception:
                pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:
        if response.status not in {200, 201}:
            raise SmokeError(f"PA API returned HTTP {response.status}")
        data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise SmokeError("PA API returned non-object JSON")
        return data


def _assert_slug(payload: dict[str, Any], expected_slug: str, action: str) -> None:
    if payload.get("slug") != expected_slug:
        raise SmokeError(f"native Wiki {action} returned unexpected slug")


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
    text = str(exc).replace("\n", " ").strip()
    for marker in ("Bearer ", "WEKNORA_SERVICE_TOKEN", "api_key", "password", "secret"):
        text = text.replace(marker, "[redacted]")
    return text[:240] or exc.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
