"""Fixture smoke for P3-M3-C1 retrieval parameter schema.

The smoke uses sanitized fixtures only. It validates conservative PA
retrieval_options parsing, WeKnora adapter forwarding gates, and debug trace
visibility for rerank/hybrid stages.
"""

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
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402
from knowledge_engine.retrieval import RETRIEVAL_OPTIONS_KEY  # noqa: E402
from knowledge_engine.retrieval import normalize_retrieval_options  # noqa: E402
from knowledge_engine.retrieval import retrieval_debug_trace  # noqa: E402
from knowledge_engine.retrieval import retrieval_options_payload  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_RETRIEVAL_PARAMETER_SCHEMA.md"


class SmokeError(RuntimeError):
    """Raised when retrieval parameter expectations fail."""


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="fixture://weknora",
            service_token="fixture-token",
            workspace_id="workspace-redacted",
            default_kb_id="kb-redacted",
        )
        self.payloads: list[dict[str, Any]] = []

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        if method == "POST" and path == "/api/v1/knowledge-search":
            self.payloads.append(dict(payload or {}))
            return {
                "data": [
                    {
                        "id": "wk-chunk-retrieval-params",
                        "knowledge_id": "wk-doc-retrieval-params",
                        "knowledge_base_id": "kb-redacted",
                        "title": "Retrieval Parameter Fixture",
                        "content": "Sanitized retrieval parameter evidence.",
                        "score": 0.88,
                        "metadata": {"fixture": "p3-m3-c1", "source_type": "document"},
                    }
                ]
            }
        raise SmokeError(f"unexpected fixture request: {method} {path}")


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Retrieval parameter smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Retrieval parameter smoke passed")
    print(f"- default forwarded: {result['default_forwarded']}")
    print(f"- enabled forwarded: {result['enabled_forwarded']}")
    print(f"- debug rerank stage: {result['debug_rerank_stage']}")
    print(f"- validation checks: {result['validation_checks']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    _assert_doc()
    _assert_options_schema()
    default_forwarded, enabled_forwarded = _assert_weknora_forwarding()
    debug_rerank_stage = _assert_debug_trace()
    validation_checks = _assert_validation()
    _assert_capability_summary()
    return {
        "default_forwarded": default_forwarded,
        "enabled_forwarded": enabled_forwarded,
        "debug_rerank_stage": debug_rerank_stage,
        "validation_checks": validation_checks,
    }


def _assert_options_schema() -> None:
    options = normalize_retrieval_options(
        {
            "hybrid": {"enabled": True, "keyword_weight": 0.4, "vector_weight": 0.6},
            "rerank": {"enabled": True, "model": "configured-rerank", "top_n": 8},
            "threshold": {"score": 0.2},
        }
    )
    payload = retrieval_options_payload(options)
    _assert(payload["hybrid"]["enabled"] is True, "hybrid enabled missing")
    _assert(payload["rerank"]["enabled"] is True, "rerank enabled missing")
    trace = retrieval_debug_trace(options)
    _assert(any(item["stage"] == "rerank" and item["status"] == "requested" for item in trace), "rerank trace missing")


def _assert_weknora_forwarding() -> tuple[bool, bool]:
    backend = FixtureWeKnoraBackend()
    default_items = backend.retrieve("retrieval params default", filters={}, top_k=2)
    _assert(default_items, "default retrieve returned no evidence")
    default_payload = backend.payloads[-1]
    default_forwarded = RETRIEVAL_OPTIONS_KEY in default_payload
    _assert(not default_forwarded, "default request forwarded retrieval_options")
    _assert(default_items[0].metadata.get("weknora_retrieval_options_forwarded") is False, "default metadata forwarded flag mismatch")

    enabled_filters = {
        RETRIEVAL_OPTIONS_KEY: {
            "hybrid": {"enabled": True, "keyword_weight": 0.4, "vector_weight": 0.6},
            "rerank": {"enabled": True, "model": "configured-rerank", "top_n": 4},
        }
    }
    enabled_items = backend.retrieve("retrieval params enabled", filters=enabled_filters, top_k=2)
    _assert(enabled_items, "enabled retrieve returned no evidence")
    enabled_payload = backend.payloads[-1]
    enabled_forwarded = RETRIEVAL_OPTIONS_KEY in enabled_payload
    _assert(enabled_forwarded, "enabled request did not forward retrieval_options")
    _assert(enabled_payload[RETRIEVAL_OPTIONS_KEY]["rerank"]["enabled"] is True, "rerank payload missing")
    _assert(enabled_items[0].metadata.get("weknora_retrieval_options_forwarded") is True, "enabled metadata forwarded flag mismatch")
    return default_forwarded, enabled_forwarded


def _assert_debug_trace() -> str:
    original_retrieve = rag_api.retrieve_evidence
    rag_api.retrieve_evidence = _fixture_retrieve
    try:
        request = RagDebugRequest(
            query="retrieval params debug",
            top_k=3,
            filters={
                "source_type": "document",
                RETRIEVAL_OPTIONS_KEY: {
                    "rerank": {"enabled": True, "model": "configured-rerank", "top_n": 3}
                },
            },
        )
        response = rag_api.retrieve_rag_debug(request)
    finally:
        rag_api.retrieve_evidence = original_retrieve
    payload = response.model_dump()
    rerank = next(
        item for item in payload["debug_trace"] if item.get("stage") == "rerank"
    )
    _assert(rerank["status"] == "requested", "debug trace did not show rerank requested")
    _assert(payload["retrieval_options"]["rerank"]["enabled"] is True, "debug options missing rerank")
    return str(rerank["status"])


def _assert_validation() -> int:
    checks = 0
    invalid_payloads = (
        {"query": "x", "filters": {RETRIEVAL_OPTIONS_KEY: {"rerank": {"enabled": True, "secret": "blocked"}}}},
        {"query": "x", "filters": {RETRIEVAL_OPTIONS_KEY: {"hybrid": {"keyword_weight": 1.5}}}},
        {"query": "x", "filters": {RETRIEVAL_OPTIONS_KEY: {"threshold": {"score": -0.1}}}},
    )
    for payload in invalid_payloads:
        try:
            RagDebugRequest(**payload)
        except ValidationError:
            checks += 1
        else:
            raise SmokeError(f"invalid retrieval options unexpectedly passed: {payload}")
    return checks


def _assert_capability_summary() -> None:
    snapshot = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="local",
        mock_mode=False,
        weknora_configured=True,
    )
    params = snapshot.get("retrieval_parameters")
    _assert(isinstance(params, dict), "capability snapshot missing retrieval_parameters")
    _assert(params.get("schema_version") == "p3-m3-c1", "retrieval parameter schema version mismatch")
    _assert(params.get("requires_explicit_enable") is True, "retrieval parameters not gated")
    _assert(params.get("default_forwarding") is False, "retrieval parameters should not forward by default")


def _fixture_retrieve(
    query: str,
    filters: dict | None = None,
    top_k: int = 8,
) -> list[Evidence]:
    return [
        Evidence(
            document_id="pa-doc-retrieval-params",
            external_doc_id="wk-doc-retrieval-params",
            chunk_id="wk-chunk-retrieval-params",
            title="Retrieval Parameter Fixture",
            text="Sanitized retrieval parameter evidence.",
            score=0.88,
            source="weknora_api",
            metadata={
                "score_semantics": "weknora_rrf_or_backend_score",
                "citation_source_type": "document_chunk",
                "retrieval_debug_trace": retrieval_debug_trace(
                    normalize_retrieval_options((filters or {}).get(RETRIEVAL_OPTIONS_KEY))
                ),
            },
            evidence_id="document_chunk:wk-chunk-retrieval-params",
            source_type="document_chunk",
        )
    ][:top_k]


def _assert_doc() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for phrase in (
        "p3-m3-c1",
        "retrieval_options",
        "hybrid",
        "rerank",
        "debug trace",
        "default request",
    ):
        _assert(phrase in text, f"retrieval parameter doc missing phrase: {phrase}")


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
