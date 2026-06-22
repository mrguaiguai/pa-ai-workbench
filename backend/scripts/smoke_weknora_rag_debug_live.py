"""Live smoke for PA RAG debug -> WeKnora native search.

The smoke uploads a sanitized temporary Markdown document into WeKnora, waits
for indexing, then calls PA's RAG debug API handler path. It verifies the
debug response keeps PA traceability while the retrieval itself comes from
native WeKnora `/api/v1/knowledge-search`.

The script does not print service tokens, provider payloads, or document body
text.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.api.rag import retrieve_rag_debug  # noqa: E402
from app.config import Settings  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY  # noqa: E402


TERMINAL_INDEXED_STATUSES = {"indexed"}
TERMINAL_FAILED_STATUSES = {"failed"}
PROGRESS_STATUSES = {"uploaded", "parsing", "chunking", "embedding", "indexing", "unknown"}
SMOKE_QUERY_PREFIX = "wfp003ragdebuganchor"


class SmokeError(RuntimeError):
    """Raised when the live RAG debug validation fails."""


def main() -> int:
    settings = Settings()
    try:
        _validate_settings(settings)
        with TemporaryDirectory(prefix="pa-wf-p0-03-rag-debug-") as temp_dir:
            result = _run_live_smoke(settings, Path(temp_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora RAG debug live smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora RAG debug live smoke passed")
    print(f"- base URL: {settings.weknora_base_url.rstrip('/')}")
    print(f"- knowledge base: {settings.weknora_default_kb_id}")
    print(f"- external doc id: {result['external_doc_id']}")
    print(f"- indexed status: {result['status']}")
    print(f"- trace id: {result['trace_id']}")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- chunk id: {result['chunk_id']}")
    print(f"- source: {result['source']}")
    print(f"- source type: {result['source_type']}")
    print(f"- rank: {result['rank']}")
    print(f"- native rank: {result['native_rank']}")
    print(f"- debug trace stages: {result['trace_stages']}")
    return 0


def _run_live_smoke(settings: Settings, temp_dir: Path) -> dict[str, Any]:
    backend = WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        default_kb_id=settings.weknora_default_kb_id,
        timeout=settings.weknora_timeout_seconds,
    )
    document_path, query = _write_sanitized_fixture(temp_dir)
    document = backend.upload_document(
        str(document_path),
        {
            "title": "WF-P0-03 RAG Debug Smoke",
            "file_name": document_path.name,
            "business_area": "public_affairs",
            "document_type": "smoke",
            "source": "wf_p0_03_rag_debug_smoke",
            "smoke_fixture": "sanitized",
        },
    )
    external_doc_id = str(document.external_doc_id or "")
    if document.source != "weknora_api" or not external_doc_id:
        raise SmokeError("upload did not return a traceable WeKnora external_doc_id")
    status = _wait_until_indexed(backend, external_doc_id)
    debug_payload = _wait_for_debug_evidence(query, external_doc_id)
    item = debug_payload["items"][0]
    metadata = item["metadata"]
    return {
        "external_doc_id": external_doc_id,
        "status": status,
        "trace_id": debug_payload["trace_id"],
        "evidence_id": item["evidence_id"],
        "chunk_id": item["chunk_id"],
        "source": item["source"],
        "source_type": item["source_type"],
        "rank": item["rank"],
        "native_rank": metadata.get("weknora_native_rank"),
        "trace_stages": ",".join(
            str(stage.get("stage"))
            for stage in debug_payload["debug_trace"]
            if isinstance(stage, dict)
        ),
    }


def _wait_until_indexed(backend: WeKnoraApiBackend, external_doc_id: str) -> str:
    deadline = time.monotonic() + _wait_seconds()
    last_status = ""
    while time.monotonic() <= deadline:
        status_payload = backend.get_document_status(external_doc_id)
        status = str(status_payload.get("status") or "unknown")
        last_status = status
        if status in TERMINAL_INDEXED_STATUSES:
            return status
        if status in TERMINAL_FAILED_STATUSES:
            detail = status_payload.get("error_message") or status_payload.get("failed_step")
            raise SmokeError(f"WeKnora indexing failed: {detail}")
        if status not in PROGRESS_STATUSES:
            raise SmokeError(f"unexpected WeKnora document status: {status}")
        time.sleep(_poll_seconds())
    raise SmokeError(
        f"WeKnora document did not reach indexed within {_wait_seconds()}s "
        f"(last status: {last_status or 'unknown'})"
    )


def _wait_for_debug_evidence(query: str, external_doc_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + _wait_seconds()
    last_total = 0
    while time.monotonic() <= deadline:
        response = retrieve_rag_debug(
            RagDebugRequest(
                query=query,
                filters={
                    "external_doc_ids": [external_doc_id],
                    "source_type": "document_chunk",
                    RETRIEVAL_OPTIONS_KEY: {},
                },
                top_k=8,
            )
        )
        payload = response.model_dump()
        if payload["status"] != "ok":
            error = payload.get("error") or {}
            raise SmokeError(f"RAG debug returned error: {error.get('error_code')}")
        last_total = int(payload["total"])
        for item in payload["items"]:
            if item.get("external_doc_id") == external_doc_id:
                _assert_debug_item(payload, item, external_doc_id)
                return {**payload, "items": [item]}
        time.sleep(_poll_seconds())
    raise SmokeError(
        "RAG debug did not return current uploaded WeKnora evidence "
        f"within {_wait_seconds()}s (last total: {last_total})"
    )


def _assert_debug_item(
    payload: dict[str, Any],
    item: dict[str, Any],
    external_doc_id: str,
) -> None:
    metadata = item.get("metadata") or {}
    if item.get("source") != "weknora_api":
        raise SmokeError(f"debug item source is not weknora_api: {item.get('source')}")
    if item.get("source_type") != "document_chunk":
        raise SmokeError(f"debug item source_type is not document_chunk: {item.get('source_type')}")
    if item.get("external_doc_id") != external_doc_id:
        raise SmokeError("debug item external_doc_id does not match uploaded document")
    if not item.get("evidence_id"):
        raise SmokeError("debug item missing evidence_id")
    if not item.get("chunk_id"):
        raise SmokeError("debug item missing chunk_id")
    if not isinstance(item.get("rank"), int) or item["rank"] < 1:
        raise SmokeError("debug item missing rank")
    if metadata.get("weknora_search_endpoint") != "/api/v1/knowledge-search":
        raise SmokeError("debug metadata missing native search endpoint")
    if metadata.get("weknora_search_native") is not True:
        raise SmokeError("debug metadata missing native search flag")
    if not isinstance(metadata.get("weknora_native_rank"), int):
        raise SmokeError("debug metadata missing native rank")
    if not metadata.get("evidence_id"):
        raise SmokeError("debug metadata missing evidence_id")
    if metadata.get("citation_source_type") != "document_chunk":
        raise SmokeError("debug metadata missing citation_source_type=document_chunk")
    trace_stages = {
        stage.get("stage")
        for stage in payload.get("debug_trace", [])
        if isinstance(stage, dict)
    }
    if not {"hybrid", "rerank", "threshold"}.issubset(trace_stages):
        raise SmokeError(f"debug trace stages incomplete: {trace_stages}")


def _write_sanitized_fixture(temp_dir: Path) -> tuple[Path, str]:
    run_id = uuid4().hex[:12]
    query = f"{SMOKE_QUERY_PREFIX}{run_id}"
    path = temp_dir / f"wf-p0-03-rag-debug-{run_id}.md"
    path.write_text(
        "\n".join(
            [
                "# WF-P0-03 RAG Debug Smoke",
                "",
                "This document is synthetic and contains no private data.",
                f"The smoke run id is {run_id}.",
                f"The debug retrieval anchor is {query}.",
                "A passing debug smoke must retrieve this sentence from WeKnora.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path, query


def _validate_settings(settings: Settings) -> None:
    missing = []
    if settings.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if settings.mock_mode:
        missing.append("MOCK_MODE=false")
    if not settings.weknora_base_url.strip():
        missing.append("WEKNORA_BASE_URL")
    if not settings.weknora_service_token.strip():
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not settings.weknora_default_kb_id.strip():
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _wait_seconds() -> int:
    return _int_env("WEKNORA_RAG_DEBUG_SMOKE_WAIT_SECONDS", 180)


def _poll_seconds() -> int:
    return _int_env("WEKNORA_RAG_DEBUG_SMOKE_POLL_SECONDS", 5)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(int(value), 1)
    except ValueError:
        return default


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KnowledgeBackendUnavailableError as exc:
        print(f"WeKnora RAG debug live smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
