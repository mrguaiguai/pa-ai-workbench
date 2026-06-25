"""Live WNFC-0-03 credential/approval/audit foundation smoke.

The script proves the shared PA safety foundation on one low-risk native
mutation path: a WeKnora chunk toggle. It uses a confirmation token, verifies
the API response includes a native mutation audit record, queries the safe audit
BFF, and optionally checks the Library browser flow. It prints only statuses,
counts, audit ids, and sanitized state.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from app.services.native_audit_service import NATIVE_CHUNK_CONFIRM_PHRASE
from check_weknora_native_chunk_management import _dump_library_chunk_dom
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_chunk_management import _upload_chunk_document
from check_weknora_native_document_lifecycle import _active_or_first_kb_id
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-foundation-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'foundation.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(
                backend_port,
                "GET",
                "/api/knowledge-bases/native/overview?limit=10",
            )
            selected_kb_id = _active_or_first_kb_id(overview)
            _assert(bool(selected_kb_id), "active KB id is available internally")

            document = _upload_chunk_document(backend_port, selected_kb_id, run_id)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            _assert(document.get("knowledge_backend") == "weknora_api", "document uses WeKnora")
            _assert(bool(document.get("external_doc_id")), "native document id saved")

            indexed = _wait_until_indexed(backend_port, document_id)
            _assert(indexed.get("status") == "indexed", "document reached indexed status")

            chunks = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
            items = chunks.get("items")
            _assert(isinstance(items, list) and bool(items), "chunk list contains items")
            first_chunk = items[0]
            _assert(isinstance(first_chunk, dict), "first chunk is object")
            chunk_id = str(first_chunk.get("id") or "")
            _assert(bool(chunk_id), "native chunk id is present")

            disabled = _request_json(
                backend_port,
                "PATCH",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/enabled",
                {
                    "confirm_token": NATIVE_CHUNK_CONFIRM_PHRASE,
                    "is_enabled": False,
                    "reason": "wnfc_0_03_token_toggle_off",
                },
            )
            audit = _audit_from_action(disabled)
            _assert(audit.get("operation") == "weknora_chunk_toggle", "audit operation recorded")
            _assert(audit.get("status") == "succeeded", "audit status succeeded")
            _assert(
                audit.get("confirmation_method") == "confirm_token",
                "confirm token method recorded",
            )
            _assert(
                audit.get("confirm_token_id") == "native_chunk_mutation",
                "confirm token id recorded",
            )
            _assert(disabled.get("confirmation", {}).get("method") == "confirm_token", "response confirmation method")

            audit_events = _request_json(
                backend_port,
                "GET",
                "/api/native-audit/events?operation=weknora_chunk_toggle&limit=5",
            )
            audit_items = audit_events.get("items")
            _assert(isinstance(audit_items, list) and bool(audit_items), "audit API returned events")
            _assert(
                any(item.get("id") == audit.get("id") for item in audit_items if isinstance(item, dict)),
                "audit API includes mutation event",
            )
            _assert(
                not _contains_raw_confirmation_token(audit_items),
                "audit API does not return raw confirm token",
            )

            enabled = _request_json(
                backend_port,
                "PATCH",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/enabled",
                {
                    "confirm_token": NATIVE_CHUNK_CONFIRM_PHRASE,
                    "is_enabled": True,
                    "reason": "wnfc_0_03_token_toggle_on",
                },
            )
            enabled_audit = _audit_from_action(enabled)
            _assert(enabled_audit.get("status") == "succeeded", "enable audit succeeded")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_library_chunk_dom(
                    frontend_port,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    user_data_dir=temp_path / "chrome-profile",
                )
                for marker in ("资料库", "分块", "生成问题", "已启用", "定位"):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WNFC-0-03 native safety foundation")
            print("- decision: PASS")
            print("- evidence_type: live_api/browser_plus_audit" if browser_mode else "- evidence_type: live_api_plus_audit")
            print("- confirmation: confirm_token")
            print(f"- audit: operation=weknora_chunk_toggle status=succeeded id={audit.get('id')}")
            print(f"- audit_api: total={audit_events.get('total')}")
            print("- masked_summary: raw_confirm_token_absent")
            if browser_mode:
                print("- browser: Library DOM rendered native chunk workflow")
            return 0
        finally:
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _audit_from_action(response: dict[str, Any]) -> dict[str, Any]:
    audit = response.get("audit")
    _assert(isinstance(audit, dict), "action response includes audit object")
    return audit


def _contains_raw_confirmation_token(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_raw_confirmation_token(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_raw_confirmation_token(item) for item in value)
    return str(value) == NATIVE_CHUNK_CONFIRM_PHRASE


if __name__ == "__main__":
    raise SystemExit(main())
