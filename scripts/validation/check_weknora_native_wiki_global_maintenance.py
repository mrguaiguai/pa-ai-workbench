"""Live WNFC-P5-04 native Wiki global maintenance smoke.

The script creates an isolated temporary wiki-enabled KB, creates a temporary
native Wiki page in it, then drives rebuild-links and auto-fix through PA BFF
with confirmation tokens and NativeMutationAudit. It then creates a real native
Wiki issue through the confirmation-gated PA BFF route and resolves it through
the native issue-status route, proving the full issue maintenance loop.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_faq_workflow import _no_raw_confirm_token
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_CREATE = "CREATE_NATIVE_WIKI_PAGE"
CONFIRM_REBUILD = "REBUILD_NATIVE_WIKI_LINKS"
CONFIRM_AUTO_FIX = "AUTO_FIX_NATIVE_WIKI"
CONFIRM_CREATE_ISSUE = "CREATE_NATIVE_WIKI_ISSUE"
CONFIRM_ISSUE_STATUS = "UPDATE_NATIVE_WIKI_ISSUE_STATUS"


def main() -> int:
    backend_port = _free_port()
    direct_backend = _weknora_backend_from_env()
    run_id = uuid4().hex[:8]
    temp_kb_id = ""
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-wiki-global-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'wiki-p5-04.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, None)
        try:
            temp_kb = direct_backend.create_temporary_wiki_knowledge_base(
                name=f"WNFC-P5-04 temporary Wiki {run_id}",
                description="WNFC temporary Wiki global maintenance validation KB",
            )
            temp_kb_id = str(temp_kb.get("_native_kb_id") or "")
            _assert(bool(temp_kb_id), "temporary wiki KB was created")

            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(
                backend_port,
                "GET",
                f"/api/wiki/native/overview?{urlencode({'kb_id': temp_kb_id, 'limit': 5})}",
            )
            _assert(_no_secret_payload(overview), "native Wiki overview is sanitized")
            mutations = _surface(overview.get("surfaces", {}), "mutations")
            _assert(mutations.get("status") == "live", "native Wiki mutation surface is live")
            _assert(mutations.get("confirmation_required") is True, "native Wiki mutations require confirmation")

            blocked = _request_json_allow_error(
                backend_port,
                "POST",
                f"/api/wiki/native/rebuild-links?{urlencode({'kb_id': temp_kb_id})}",
                {"confirm_token": "WRONG"},
            )
            _assert(blocked.get("_http_status") == 400, "bad token blocks rebuild-links")
            _assert(_no_secret_payload(blocked), "blocked rebuild response is sanitized")

            slug = f"wnfc-p5-04-{run_id}"
            created = _request_json(
                backend_port,
                "POST",
                f"/api/wiki/native/pages?{urlencode({'kb_id': temp_kb_id})}",
                {
                    "confirm_token": CONFIRM_CREATE,
                    "slug": slug,
                    "title": f"WNFC P5 04 Wiki {run_id}",
                    "summary": "Temporary Wiki global maintenance validation page.",
                    "content_markdown": "Temporary page with an isolated [[missing-target]] link.",
                    "page_type": "concept",
                    "status": "draft",
                    "metadata": {"test_scope": "WNFC-P5-04"},
                },
            )
            _assert(created.get("slug") == slug, "temporary native Wiki page was created")

            rebuilt = _request_json(
                backend_port,
                "POST",
                f"/api/wiki/native/rebuild-links?{urlencode({'kb_id': temp_kb_id})}",
                {"confirm_token": CONFIRM_REBUILD},
            )
            _assert(_audit_succeeded(rebuilt, "weknora_wiki_rebuild_links"), "rebuild-links audit succeeded")
            _assert(rebuilt.get("status") == "completed", "rebuild-links completed")

            fixed = _request_json(
                backend_port,
                "POST",
                f"/api/wiki/native/auto-fix?{urlencode({'kb_id': temp_kb_id})}",
                {"confirm_token": CONFIRM_AUTO_FIX},
            )
            _assert(_audit_succeeded(fixed, "weknora_wiki_auto_fix"), "auto-fix audit succeeded")
            _assert(fixed.get("status") == "completed", "auto-fix completed")

            created_issue = _request_json(
                backend_port,
                "POST",
                f"/api/wiki/native/issues?{urlencode({'kb_id': temp_kb_id})}",
                {
                    "confirm_token": CONFIRM_CREATE_ISSUE,
                    "slug": slug,
                    "issue_type": "wnfc_validation",
                    "description": "WNFC-P5-04 live validation issue for native Wiki maintenance.",
                    "status": "pending",
                    "reported_by": "wnfc_p5_04",
                },
            )
            _assert(_audit_succeeded(created_issue, "weknora_wiki_create_issue"), "create-issue audit succeeded")
            issue_id = str(created_issue.get("id") or "")
            _assert(bool(issue_id), "created native Wiki issue id is present")

            issues = _request_json(
                backend_port,
                "GET",
                f"/api/wiki/native/issues?{urlencode({'kb_id': temp_kb_id, 'slug': slug})}",
            )
            issue_items = issues.get("items") if isinstance(issues.get("items"), list) else []
            _assert(any(str(item.get("id") or "") == issue_id for item in issue_items), "created issue is listed")

            issue_update = _request_json(
                backend_port,
                "PUT",
                f"/api/wiki/native/issues/{quote(issue_id, safe='')}/status?{urlencode({'kb_id': temp_kb_id})}",
                {"confirm_token": CONFIRM_ISSUE_STATUS, "status": "resolved"},
            )
            _assert(_audit_succeeded(issue_update, "weknora_wiki_issue_status"), "issue-status audit succeeded")

            audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=wiki&limit=20")
            required_operations = {
                "weknora_wiki_rebuild_links",
                "weknora_wiki_auto_fix",
                "weknora_wiki_create_issue",
                "weknora_wiki_issue_status",
            }
            _assert(_audit_log_contains(audits, required_operations), "audit API contains Wiki global maintenance events")
            _assert(_no_raw_confirm_token(audits), "audit API hides Wiki confirm tokens")
            _assert(_no_secret_payload(audits), "audit API sanitizes Wiki audit events")

            print("WeKnora native Wiki global maintenance closure")
            print("- decision: PASS")
            print("- evidence_type: live api plus audit proof")
            print("- rebuild_links: live audit=succeeded")
            print("- auto_fix: live audit=succeeded")
            print("- create_issue: live audit=succeeded")
            print("- issue_status: live audit=succeeded")
            print("- output: sanitized")
            return 0
        finally:
            if temp_kb_id:
                try:
                    direct_backend.delete_knowledge_base(temp_kb_id)
                except Exception:
                    pass
            _terminate(backend)


def _weknora_backend_from_env() -> WeKnoraApiBackend:
    settings = Settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _request_json(port: int, method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
    data = _request_json_allow_error(port, method, path, payload)
    status = int(data.get("_http_status") or 200)
    if status >= 400:
        raise AssertionError(f"{method} {path} failed status={status} detail={data.get('detail')!r}")
    return data


def _request_json_allow_error(port: int, method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = _json_or_error(response.read().decode("utf-8"))
            status = response.status
    except HTTPError as exc:
        data = _json_or_error(exc.read().decode("utf-8"))
        status = exc.code
    if not isinstance(data, dict):
        raise AssertionError(f"{method} {path} returned non-object JSON")
    data["_http_status"] = status
    return data


def _json_or_error(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"detail": raw[:500] or "empty response"}
    if isinstance(parsed, dict):
        return parsed
    return {"detail": parsed}


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_succeeded(response: dict[str, Any], operation: str) -> bool:
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return audit.get("operation") == operation and audit.get("status") == "succeeded"


def _audit_log_contains(response: dict[str, Any], operations: set[str]) -> bool:
    items = response.get("items") if isinstance(response.get("items"), list) else []
    found = {
        str(item.get("operation") or "")
        for item in items
        if isinstance(item, dict) and item.get("status") == "succeeded"
    }
    return operations.issubset(found)


if __name__ == "__main__":
    raise SystemExit(main())
