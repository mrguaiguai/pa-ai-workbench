"""Live WNFC-P1-03 data-source to KB/RAG evidence loop smoke.

The script creates a temporary real RSS data source through the native
WeKnora API, triggers sync through the PA confirmation-gated BFF, waits for a
new RSS-synced native knowledge item to reach the index, then proves PA RAG
debug and PA native knowledge-chat return traceable citations scoped to that
native knowledge id.

It prints only statuses and counts. It does not print feed URLs, raw resource
names, raw answers, raw chunks, connector config, provider payloads, logs, or
local database paths.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_data_source_management import CONFIRM_SYNC_PHRASE
from check_weknora_native_data_source_management import DEFAULT_FEED_URL
from check_weknora_native_data_source_management import _find_source_by_name
from check_weknora_native_data_source_management import _no_secret_shaped_fields
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json
from check_weknora_native_rag_chat import _request_json_timeout
from app.config import Settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


def main() -> int:
    backend_port = _free_port()
    run_id = uuid4().hex[:8]
    temp_source_name = f"WNFC-P1-03 temporary RSS {run_id}"
    temp_source_id: str | None = None
    direct_backend = _weknora_backend_from_env()
    kb_id = str(direct_backend.default_kb_id or "").strip()
    _assert(bool(kb_id), "default native KB id is configured")

    with tempfile.TemporaryDirectory(prefix="pa-wnfc-ds-rag-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'data-source-rag.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, None)
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            before_ids = _rss_knowledge_ids(direct_backend, kb_id)
            created = direct_backend.create_rss_data_source(
                feed_url=DEFAULT_FEED_URL,
                name=temp_source_name,
            )
            temp_source_id = str(created.get("id") or "").strip() or None
            _assert(created.get("type") == "rss", "temporary RSS data source created")

            overview = _request_json(backend_port, "GET", "/api/data-sources/native/overview?limit=10")
            _assert(_no_secret_shaped_fields(overview), "overview excludes secret-shaped fields")
            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            data_sources = surfaces.get("data_sources") if isinstance(surfaces.get("data_sources"), dict) else {}
            items = data_sources.get("items") if isinstance(data_sources.get("items"), list) else []
            selected = _find_source_by_name(items, temp_source_name)
            _assert(bool(selected), "temporary RSS source is visible through PA safe index")
            data_source_index = int((selected or {}).get("safe_index") or 0)

            sync = _request_json(
                backend_port,
                "POST",
                f"/api/data-sources/native/sources/by-index/{data_source_index}/sync",
                {"confirm_token": CONFIRM_SYNC_PHRASE},
            )
            _assert(_no_secret_shaped_fields(sync), "confirmed sync excludes secret-shaped fields")
            sync_surfaces = sync.get("surfaces") if isinstance(sync.get("surfaces"), dict) else {}
            sync_control = (
                sync_surfaces.get("sync_control")
                if isinstance(sync_surfaces.get("sync_control"), dict)
                else {}
            )
            _assert(sync_control.get("status") == "live", "confirmed sync returns live")
            audit = sync.get("audit") if isinstance(sync.get("audit"), dict) else {}
            _assert(audit.get("operation") == "weknora_data_source_sync", "sync audit operation is recorded")
            _assert(audit.get("status") == "succeeded", "sync audit succeeded")

            knowledge = _wait_for_new_indexed_rss_knowledge(
                direct_backend,
                kb_id=kb_id,
                before_ids=before_ids,
            )
            external_doc_id = str(knowledge.get("id") or "").strip()
            _assert(bool(external_doc_id), "synced RSS knowledge id is available")

            query = _query_from_knowledge(knowledge)
            debug = _request_json(
                backend_port,
                "POST",
                "/api/rag/debug",
                {
                    "query": query,
                    "top_k": 5,
                    "filters": {
                        "source_type": "document_chunk",
                        "knowledge_ids": [external_doc_id],
                        "current_run": {"expected_external_doc_ids": [external_doc_id]},
                    },
                },
            )
            _assert(debug.get("status") == "ok", "RAG debug returned ok")
            _assert(int(debug.get("total") or 0) > 0, "RAG debug returned scoped evidence")
            _assert(_debug_has_native_citation(debug, external_doc_id), "RAG evidence is traceable to synced RSS knowledge")

            chat = _request_json_timeout(
                backend_port,
                "POST",
                "/api/rag/knowledge-chat",
                {
                    "query": query,
                    "title": f"WNFC-P1-03 native data-source chat {run_id}",
                    "knowledge_ids": [external_doc_id],
                    "current_run": {"expected_external_doc_ids": [external_doc_id]},
                },
                timeout=180,
            )
            runtime = chat.get("runtime") if isinstance(chat.get("runtime"), dict) else {}
            output = chat.get("output") if isinstance(chat.get("output"), dict) else {}
            citations = chat.get("citations") if isinstance(chat.get("citations"), list) else []
            guard = runtime.get("current_run_guard") if isinstance(runtime.get("current_run_guard"), dict) else {}
            _assert(output.get("status") == "completed", "native knowledge-chat output completed")
            _assert(int(runtime.get("reference_count") or 0) > 0, "native knowledge-chat references returned")
            _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved native citations")
            _assert(bool(guard.get("passed")), "current-run guard passed for data-source knowledge")
            _assert(_citations_match_external_doc(citations, external_doc_id), "saved citations match synced RSS knowledge")

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_knowledge_chat")
            _assert(int(history.get("total") or 0) > 0, "history lists data-source knowledge-chat output")

            print("WeKnora native data source to KB/RAG evidence loop")
            print("- decision: PASS")
            print("- evidence_type: live_api+native_citation_current_run")
            print("- native_sync: rss_source=created sync=audit_succeeded")
            print("- kb_index: rss_knowledge=indexed")
            print(f"- rag_debug: total={int(debug.get('total') or 0)} scoped_native_evidence=passed")
            print(
                "- knowledge_chat: references={refs} saved_citations={citations} guard=passed".format(
                    refs=int(runtime.get("reference_count") or 0),
                    citations=int(runtime.get("saved_citation_count") or 0),
                )
            )
            print("- history: native_knowledge_chat output listed")
            print("- cleanup: temporary data source removed; synced KB evidence was validated before cleanup")
            return 0
        finally:
            if temp_source_id:
                try:
                    direct_backend.delete_data_source(temp_source_id)
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


def _rss_knowledge_ids(backend: WeKnoraApiBackend, kb_id: str) -> set[str]:
    return {
        str(item.get("id") or "")
        for item in _list_rss_knowledge(backend, kb_id)
        if isinstance(item, dict) and item.get("id")
    }


def _wait_for_new_indexed_rss_knowledge(
    backend: WeKnoraApiBackend,
    *,
    kb_id: str,
    before_ids: set[str],
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_count = 0
    while time.time() < deadline:
        items = _list_rss_knowledge(backend, kb_id)
        last_count = len(items)
        candidates = [
            item
            for item in items
            if isinstance(item, dict)
            and str(item.get("id") or "") not in before_ids
            and str(item.get("id") or "").strip()
        ]
        for item in candidates:
            external_doc_id = str(item.get("id") or "").strip()
            status = backend.get_document_status(external_doc_id)
            if status.get("status") == "indexed":
                return item
        time.sleep(2)
    raise AssertionError(f"RSS sync did not produce an indexed new knowledge item, last_count={last_count}")


def _list_rss_knowledge(backend: WeKnoraApiBackend, kb_id: str) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "page": 1,
            "page_size": 50,
            "source": "rss",
        }
    )
    data = backend.client.request_json(
        "GET",
        f"/api/v1/knowledge-bases/{quote(kb_id, safe='')}/knowledge?{query}",
    )
    return _items_from_native_response(data)


def _items_from_native_response(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    payload = data.get("data")
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "list", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    for key in ("items", "list"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _query_from_knowledge(knowledge: dict[str, Any]) -> str:
    title = str(knowledge.get("title") or knowledge.get("file_name") or "").strip()
    if title:
        return f"What does this synced RSS knowledge item say about {title[:120]}?"
    return "What does this synced RSS knowledge item say?"


def _debug_has_native_citation(payload: dict[str, Any], external_doc_id: str) -> bool:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        if (
            item.get("external_doc_id") == external_doc_id
            and item.get("source") == "weknora_api"
            and item.get("source_type") == "document_chunk"
            and item.get("evidence_id")
            and metadata.get("weknora_search_native") is True
        ):
            return True
    return False


def _citations_match_external_doc(citations: list[Any], external_doc_id: str) -> bool:
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        if (
            citation.get("external_doc_id") == external_doc_id
            and citation.get("source") == "weknora_api"
            and citation.get("source_type") == "document_chunk"
            and citation.get("evidence_id")
        ):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
