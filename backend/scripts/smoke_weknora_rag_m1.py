"""Smoke-check WeKnora retrieve response mapping for PA Evidence.

This is a sanitized fixture contract test. It does not require a live
WeKnora service and does not use real pilot documents.
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

from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the retrieve fixture contract fails."""


class FixtureRetrieveBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="fixture://weknora",
            service_token="fixture-token",
            default_kb_id="kb-default",
            timeout=5,
        )
        self.requests: list[dict[str, Any]] = []

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        self.requests.append({"method": method, "path": path, "payload": payload})
        if path != "/api/v1/knowledge-search":
            raise SmokeError(f"unexpected path: {path}")
        return {
            "success": True,
            "data": [
                {
                    "id": "chunk-policy-001",
                    "content": "sanitized policy evidence",
                    "knowledge_id": "wk-doc-001",
                    "knowledge_base_id": "kb-default",
                    "knowledge_title": "Fixture Policy",
                    "knowledge_filename": "fixture-policy.md",
                    "chunk_index": 3,
                    "start_at": 10,
                    "end_at": 38,
                    "seq": 4,
                    "score": 0.031,
                    "match_type": 2,
                    "chunk_type": "text",
                    "parent_chunk_id": "parent-001",
                    "knowledge_source": "smoke",
                    "knowledge_channel": "api",
                    "metadata": {"business_area": "public_affairs"},
                    "chunk_metadata": {"section": "scope"},
                },
                {
                    "id": "chunk-case-002",
                    "content": "sanitized case evidence",
                    "knowledge_id": "wk-doc-002",
                    "knowledge_base_id": "kb-default",
                    "knowledge_title": "Fixture Case",
                    "chunk_index": 1,
                    "score": 0.02,
                    "match_type": 1,
                    "chunk_type": "text",
                },
            ],
        }


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora RAG smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora RAG smoke passed (fixture)")
    print(f"- request path: {result['path']}")
    print(f"- knowledge ids: {', '.join(result['knowledge_ids'])}")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- source: {result['source']}")
    print(f"- total returned: {result['total']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    backend = FixtureRetrieveBackend()
    evidence = backend.retrieve(
        query="policy",
        filters={
            "document_ids": ["wk-doc-001"],
            "knowledge_base_ids": ["kb-default"],
            "source_type": "document_chunk",
        },
        top_k=1,
    )
    if len(backend.requests) != 1:
        raise SmokeError(f"expected one request, got {len(backend.requests)}")
    request = backend.requests[0]
    payload = request["payload"]
    if request["method"] != "POST":
        raise SmokeError(f"unexpected method: {request['method']}")
    if not isinstance(payload, dict):
        raise SmokeError("missing retrieve payload")
    if payload.get("query") != "policy":
        raise SmokeError(f"query not mapped: {payload}")
    if payload.get("knowledge_base_ids") != ["kb-default"]:
        raise SmokeError(f"knowledge_base_ids not mapped: {payload}")
    if payload.get("knowledge_ids") != ["wk-doc-001"]:
        raise SmokeError(f"knowledge_ids not mapped: {payload}")
    if len(evidence) != 1:
        raise SmokeError(f"top_k/source_type filtering failed: {len(evidence)}")
    item = evidence[0]
    if item.source != "weknora_api":
        raise SmokeError(f"unexpected evidence source: {item.source}")
    if item.source_type != "document_chunk":
        raise SmokeError(f"unexpected source_type: {item.source_type}")
    if item.evidence_id != "document_chunk:chunk-policy-001":
        raise SmokeError(f"unexpected evidence_id: {item.evidence_id}")
    if item.chunk_id != "chunk-policy-001":
        raise SmokeError(f"unexpected chunk_id: {item.chunk_id}")
    if item.external_doc_id != "wk-doc-001":
        raise SmokeError(f"unexpected external_doc_id: {item.external_doc_id}")
    if item.title != "Fixture Policy" or not item.text:
        raise SmokeError("title/text not mapped")
    required_metadata = [
        "weknora_knowledge_base_id",
        "weknora_chunk_index",
        "weknora_match_type",
        "score_semantics",
    ]
    missing = [key for key in required_metadata if key not in item.metadata]
    if missing:
        raise SmokeError("missing metadata: " + ", ".join(missing))
    return {
        "path": request["path"],
        "knowledge_ids": payload["knowledge_ids"],
        "evidence_id": item.evidence_id,
        "source": item.source,
        "total": len(evidence),
    }


if __name__ == "__main__":
    raise SystemExit(main())
