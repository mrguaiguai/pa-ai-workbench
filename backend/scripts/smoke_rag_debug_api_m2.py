"""Fixture smoke for P3-M2-B2 RAG retrieve debug API.

The smoke calls the FastAPI handler directly with synthetic WeKnora-shaped
Evidence. It proves the debug endpoint stays read-only, uses the PA Evidence
contract, emits trace fields, and redacts/truncates output without requiring a
live WeKnora service or printing secrets.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.api import rag as rag_api  # noqa: E402
from app.schemas import RagDebugRequest  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


FIXTURE_TOKEN = "-".join(["fixture", "redaction", "value", "123456789"])
LONG_BODY = (
    "Synthetic evidence sentence. "
    f"Authorization: Bearer {FIXTURE_TOKEN}. "
    + "This extra synthetic paragraph should be truncated. " * 12
)


class SmokeError(RuntimeError):
    """Raised when the debug API fixture smoke fails."""


def main() -> int:
    original_retrieve = rag_api.retrieve_evidence
    rag_api.retrieve_evidence = _fixture_retrieve
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"RAG debug API smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        rag_api.retrieve_evidence = original_retrieve

    print("RAG debug API smoke passed (fixture)")
    print(f"- trace id: {result['trace_id']}")
    print(f"- items: {result['total']}")
    print(f"- source type: {result['source_type']}")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- summary chars: {result['summary_chars']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    response = rag_api.retrieve_rag_debug(
        RagDebugRequest(
            query="synthetic policy debug query",
            filters={
                "source_type": "document_chunk",
                "business_area": "public_affairs",
                "kb_id": f"Bearer {FIXTURE_TOKEN}",
            },
            top_k=3,
        )
    )
    payload = response.model_dump()
    _assert(payload["status"] == "ok", "expected ok response")
    _assert(payload["trace_id"], "missing trace_id")
    _assert(payload["query"] == "synthetic policy debug query", "query mismatch")
    _assert(payload["top_k"] == 3, "top_k mismatch")
    _assert(payload["requested_source_type"] == "document_chunk", "source_type mismatch")
    _assert(payload["filters"]["kb_id"] == "Bearer [redacted]", "filter token leaked")
    _assert(payload["total"] == 1, "expected one fixture item")

    item = payload["items"][0]
    _assert(item["source"] == "weknora_api", "expected WeKnora source")
    _assert(item["source_type"] == "document_chunk", "expected document_chunk")
    _assert(item["evidence_id"] == "document_chunk:fixture-chunk-001", "evidence id mismatch")
    _assert(item["chunk_id"] == "fixture-chunk-001", "chunk id mismatch")
    _assert(item["score"] == 1.25, "score mismatch")
    _assert(len(item["summary"]) <= rag_api.DEBUG_SUMMARY_LIMIT, "summary not truncated")
    _assert(FIXTURE_TOKEN not in str(payload), "token leaked")
    _assert("raw_response" not in item["metadata"], "raw response metadata leaked")
    _assert("weknora_knowledge_base_id" in item["metadata"], "safe metadata missing")

    return {
        "trace_id": payload["trace_id"],
        "total": payload["total"],
        "source_type": item["source_type"],
        "evidence_id": item["evidence_id"],
        "summary_chars": len(item["summary"]),
    }


def _fixture_retrieve(query: str, filters: dict | None = None, top_k: int = 8) -> list[Evidence]:
    _assert(query == "synthetic policy debug query", "handler did not pass query")
    _assert((filters or {}).get("source_type") == "document_chunk", "handler did not pass filters")
    _assert(top_k == 3, "handler did not pass top_k")
    return [
        Evidence(
            document_id=None,
            external_doc_id="fixture-doc-001",
            chunk_id="fixture-chunk-001",
            title="Synthetic Fixture Evidence",
            text=LONG_BODY,
            score=1.25,
            source="weknora_api",
            metadata={
                "weknora_knowledge_base_id": "fixture-kb",
                "weknora_knowledge_id": "fixture-doc-001",
                "weknora_chunk_index": 4,
                "raw_response": {"token": FIXTURE_TOKEN, "body": LONG_BODY},
                "service_token": FIXTURE_TOKEN,
            },
            evidence_id="document_chunk:fixture-chunk-001",
            source_type="document_chunk",
        )
    ]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
