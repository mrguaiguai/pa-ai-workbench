"""Fixture smoke for P3-M2-B4 RAG debug parameter validation."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.api import rag as rag_api  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from app.services.rag_service import RetrievalContext  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the debug parameter smoke fails."""


def main() -> int:
    original_retrieve = rag_api.retrieve_evidence_with_context
    calls: list[dict[str, Any]] = []
    rag_api.retrieve_evidence_with_context = lambda query, filters=None, top_k=8: _fixture_retrieve(
        calls,
        query,
        filters,
        top_k,
    )
    try:
        result = _run_smoke(calls)
    except Exception as exc:  # noqa: BLE001
        print(f"RAG debug parameter smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_api.retrieve_evidence_with_context = original_retrieve

    print("RAG debug parameter smoke passed (fixture)")
    print(f"- trace id: {result['trace_id']}")
    print(f"- source type: {result['source_type']}")
    print(f"- top_k: {result['top_k']}")
    print(f"- validation checks: {result['validation_checks']}")
    return 0


def _run_smoke(calls: list[dict[str, Any]]) -> dict[str, Any]:
    request = RagDebugRequest(
        query="policy scope",
        top_k=5,
        filters={
            "source_type": "wiki",
            "document_ids": ["doc-a", "doc-b"],
            "kb_id": "kb-fixture",
            "business_area": "public_affairs",
            "document_type": "policy",
        },
    )
    _assert(request.filters["source_type"] == "wiki_page", "source_type was not normalized")
    response = rag_api.retrieve_rag_debug(request)
    payload = response.model_dump()
    _assert(payload["status"] == "ok", "expected ok debug response")
    _assert(payload["top_k"] == 5, "top_k response mismatch")
    _assert(payload["filters"]["source_type"] == "wiki_page", "filter source_type mismatch")
    _assert(calls and calls[0]["top_k"] == 5, "handler did not pass top_k")
    _assert(calls[0]["filters"]["kb_id"] == "kb-fixture", "handler did not pass kb_id")

    validation_checks = 0
    for invalid_payload in (
        {"query": "x", "top_k": 0, "filters": {}},
        {"query": "x", "top_k": 51, "filters": {}},
        {"query": "x", "top_k": 5, "filters": {"source_type": "raw"}},
        {"query": "x", "top_k": 5, "filters": {"token": "blocked"}},
    ):
        try:
            RagDebugRequest(**invalid_payload)
        except ValidationError:
            validation_checks += 1
        else:
            raise SmokeError(f"invalid payload unexpectedly passed: {invalid_payload}")

    return {
        "trace_id": payload["trace_id"],
        "source_type": payload["filters"]["source_type"],
        "top_k": payload["top_k"],
        "validation_checks": validation_checks,
    }


def _fixture_retrieve(
    calls: list[dict[str, Any]],
    query: str,
    filters: dict | None,
    top_k: int,
) -> RetrievalContext:
    calls.append({"query": query, "filters": filters or {}, "top_k": top_k})
    return RetrievalContext(
        items=[
            Evidence(
                document_id=None,
                external_doc_id=None,
                chunk_id=None,
                wiki_page_id="wiki-fixture-001",
                title="Fixture Wiki",
                text="Synthetic wiki evidence.",
                score=None,
                source="weknora_api",
                evidence_id="wiki_page:wiki-fixture-001",
                source_type="wiki_page",
                metadata={"wiki_page_id": "wiki-fixture-001"},
            )
        ],
        filters=filters or {},
        warnings=[],
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
