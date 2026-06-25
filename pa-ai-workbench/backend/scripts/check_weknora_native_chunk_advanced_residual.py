"""Live WNFC-P5-02 native chunk advanced residual smoke.

The script verifies the current product truth: basic native chunk list/read/
toggle/delete, content rewrite/re-index, generated-question data/delete, and
search-by-chunk are live. It creates a temporary real WeKnora-backed document
under a question-generation-enabled KB, waits for native generated-question
metadata, deletes one generated question through PA, and checks PA event/audit
surfaces. Output is sanitized and contains only statuses and counts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from check_weknora_native_chunk_management import _dump_library_chunk_dom
from check_weknora_native_chunk_management import _json_object
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_chunk_management import _upload_chunk_document
from check_weknora_native_document_lifecycle import _active_or_first_kb_id
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_faq_workflow import _dump_capability_dom
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from app.config import get_settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    run_id = uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-chunk-advanced-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'chunk-p5-02.db'}"
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        document_id = ""
        temp_kb_id = ""
        direct_backend = _weknora_backend_from_env()
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            kb_overview = _request_json(backend_port, "GET", "/api/knowledge-bases/native/overview?limit=10")
            _assert(_no_secret_payload(kb_overview), "KB overview is sanitized")
            _assert(kb_overview.get("status") in {"live", "partial"}, "WeKnora KB API is reachable")
            selected_kb_id = _question_generation_kb_id(kb_overview)
            if not selected_kb_id:
                temp_kb = direct_backend.create_temporary_question_generation_knowledge_base(
                    name=f"WNFC-P5-02 generated-question {run_id}",
                    question_count=1,
                )
                selected_kb_id = str(temp_kb.get("_native_kb_id") or temp_kb.get("id") or "")
                temp_kb_id = selected_kb_id
            if not selected_kb_id:
                selected_kb_id = _active_or_first_kb_id(kb_overview)
            _assert(bool(selected_kb_id), "active KB id is available internally")

            document = _upload_chunk_document(backend_port, selected_kb_id, run_id)
            document_id = str(document.get("id") or "")
            _assert(bool(document_id), "PA document id returned")
            _assert(document.get("knowledge_backend") == "weknora_api", "document uses WeKnora")

            indexed = _wait_until_indexed(backend_port, document_id)
            _assert(indexed.get("status") == "indexed", "document reached indexed status")

            first_chunk, question_id = _wait_for_generated_question_chunk(backend_port, document_id)
            chunk_id = str(first_chunk.get("id") or "")
            _assert(bool(chunk_id), "native chunk id is present")

            deleted = _request_json_checked(
                backend_port,
                "DELETE",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/questions/{quote(question_id, safe='')}",
                {
                    "confirm": True,
                    "reason": "wnfc_p5_02_generated_question_delete",
                },
            )
            _assert(deleted.get("action") == "delete_generated_question", "generated-question delete action returned")
            deleted_chunk = deleted.get("chunk") if isinstance(deleted.get("chunk"), dict) else {}
            deleted_ids = _generated_question_ids(deleted_chunk)
            _assert(question_id not in deleted_ids, "generated question id was removed from metadata")

            similar = _request_json_checked(
                backend_port,
                "GET",
                f"/api/documents/{document_id}/chunks/{quote(chunk_id, safe='')}/similar?top_k=3",
            )
            _assert(similar.get("source") == "weknora_api", "search-by-chunk PA source is native")

            events = _request_json(backend_port, "GET", f"/api/documents/{document_id}/events")
            event_steps = [
                str(item.get("step") or "")
                for item in events.get("items", [])
                if isinstance(item, dict)
            ]
            _assert("weknora_chunk_question_delete" in event_steps, "question delete event recorded")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=10")
            _assert(_no_secret_payload(native_status), "native status is sanitized")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            chunk_group = groups.get("chunk_management") if isinstance(groups.get("chunk_management"), dict) else {}
            summary = chunk_group.get("summary") if isinstance(chunk_group.get("summary"), dict) else {}

            _assert(chunk_group.get("status") == "live", "chunk advanced group is live")
            _assert(summary.get("basic_mutations_status") == "live", "basic chunk mutations remain live")
            _assert(summary.get("content_rewrite_status") == "live", "content rewrite is live")
            _assert(summary.get("generated_question_seed_status") == "live", "generated-question seed data is live")
            _assert(summary.get("generated_question_delete_status") == "live", "generated-question delete is live")
            _assert(summary.get("search_by_chunk_status") == "live", "search-by-chunk is live")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, temp_path / "chrome-profile-capability")
                for marker in (
                    "Chunk management",
                    "basic_mutations_status: live",
                    "content_rewrite_status: live",
                    "generated_question_seed_status: live",
                    "generated_question_delete_status: live",
                    "search_by_chunk_status: live",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")
                library_dom = _dump_library_chunk_dom(
                    frontend_port,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    user_data_dir=temp_path / "chrome-profile-library",
                )
                for marker in ("资料库", "分块", "生成问题", "定位"):
                    _assert(marker in library_dom, f"Library DOM contains {marker}")

            print("WeKnora native chunk advanced residual")
            print("- decision: PASS")
            print(
                "- evidence_type: live api/browser plus audit evidence"
                if browser_mode
                else "- evidence_type: live api plus audit evidence"
            )
            print("- basic_chunks: list/read/toggle/delete already live")
            print("- content_rewrite_reembedding: live native route plus PA BFF/UI")
            print("- generated_question_seed: live temporary KB question_generation_config metadata")
            print("- generated_question_delete: live native route plus PA audit")
            print("- search_by_chunk: live native route plus PA BFF/UI")
            if browser_mode:
                print("- browser: Capability Center and Library rendered chunk advanced workflow")
            print("- output: sanitized")
            return 0
        finally:
            if document_id:
                try:
                    _request_json(backend_port, "DELETE", f"/api/documents/{document_id}")
                except Exception:
                    pass
            if temp_kb_id:
                try:
                    direct_backend.delete_knowledge_base(temp_kb_id)
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


def _generated_question_ids(chunk: dict[str, Any]) -> set[str]:
    metadata = _json_object(chunk.get("metadata_json"))
    questions = metadata.get("generated_questions")
    if not isinstance(questions, list):
        return set()
    return {
        str(question.get("id") or "")
        for question in questions
        if isinstance(question, dict) and question.get("id")
    }


def _question_generation_kb_id(kb_overview: dict[str, Any]) -> str:
    items = kb_overview.get("items") if isinstance(kb_overview.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        config = item.get("question_generation")
        if isinstance(config, dict) and config.get("enabled"):
            return str(item.get("id") or "")
    return ""


def _wait_for_generated_question_chunk(
    backend_port: int,
    document_id: str,
    timeout_seconds: float = 240.0,
) -> tuple[dict[str, Any], str]:
    deadline = time.time() + timeout_seconds
    last_chunk_count = 0
    while time.time() < deadline:
        chunks = _request_json(backend_port, "GET", f"/api/documents/{document_id}/chunks")
        items = chunks.get("items") if isinstance(chunks.get("items"), list) else []
        last_chunk_count = len(items)
        for item in items:
            if not isinstance(item, dict):
                continue
            question_ids = sorted(_generated_question_ids(item))
            if question_ids:
                return item, question_ids[0]
        time.sleep(3)
    raise AssertionError(
        "timed out waiting for generated-question metadata "
        f"on live temporary document chunks; chunks_seen={last_chunk_count}"
    )


def _weknora_backend_from_env() -> WeKnoraApiBackend:
    settings = get_settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _request_json_checked(
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return _request_json(port, method, path, payload)
    except HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        detail = _safe_error_detail(body_text)
        raise AssertionError(f"{method} {path} failed with HTTP {exc.code}: {detail}") from exc


def _safe_error_detail(body_text: str) -> str:
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError:
        return body_text[:240]
    if not isinstance(parsed, dict):
        return str(parsed)[:240]
    safe = {
        key: str(parsed.get(key) or "")[:240]
        for key in ("detail", "error", "message")
        if parsed.get(key)
    }
    return json.dumps(safe, ensure_ascii=False) if safe else "{}"


if __name__ == "__main__":
    raise SystemExit(main())
