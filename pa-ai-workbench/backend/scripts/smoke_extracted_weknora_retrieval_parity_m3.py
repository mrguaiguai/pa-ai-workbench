"""Offline extracted/WeKnora retrieval parity smoke for P3-M3-B2.

The smoke uses only sanitized fixtures. It compares local extracted chunking and
retrieval with a fixture WeKnora adapter response, records differences, and
asserts that key queries still return traceable PA Evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.schemas import Citation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendComponents  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendConfig  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.chunking import ChunkingConfig  # noqa: E402
from knowledge_engine.chunking import ParagraphChunker  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.evidence import normalize_evidence_results  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "PHASE3_M3_EXTRACTED_WEKNORA_RETRIEVAL_PARITY.md"
ENV_KEYS = (
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL_NAME",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_API_KEY",
)
FIXTURE_TEXT = """# Sanitized Policy Runbook

Retention controls require quarterly review, owner approval, and evidence of
exception handling. Local fallback retrieval should expose a traceable chunk for
the retention controls query.

Incident review notes require a timeline, impacted service summary, policy
exception marker, and follow-up owner. WeKnora may choose a different chunk
boundary than the local paragraph chunker.

Knowledge base refresh checks must document source type, score semantics, and
citation trace fields so downstream Agent checks can reject untraceable output.
"""
KEY_QUERIES = (
    "retention controls evidence",
    "incident review policy exception",
)


class SmokeError(RuntimeError):
    """Raised when retrieval parity expectations fail."""


@dataclass(frozen=True)
class RetrievalComparison:
    query: str
    top_k: int
    extracted_count: int
    weknora_count: int
    extracted_source_types: list[str]
    weknora_source_types: list[str]
    extracted_score_semantics: list[str]
    weknora_score_semantics: list[str]
    extracted_evidence_ids: list[str]
    weknora_evidence_ids: list[str]
    first_rank_same_title: bool


def main() -> int:
    try:
        with _without_embedding_env():
            result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Extracted/WeKnora retrieval parity smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Extracted/WeKnora retrieval parity smoke passed")
    print(f"- fixture document chunks: extracted={result['chunk_delta']['extracted_count']} weknora={result['chunk_delta']['weknora_count']}")
    print(f"- chunk boundary delta recorded: {result['chunk_delta']['boundary_delta_count']}")
    print(f"- key queries compared: {result['query_count']}")
    print(f"- traceable evidence checks: {result['traceable_checks']}")
    print(f"- live comparison: {result['live_comparison']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    _assert_doc_report()
    extracted = _extracted_backend()
    weknora = FixtureWeKnoraBackend()

    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "sanitized-policy-runbook.md"
        path.write_text(FIXTURE_TEXT, encoding="utf-8")
        document = extracted.upload_document(
            str(path),
            {
                "document_id": "pa-doc-parity-fixture",
                "title": "Sanitized Policy Runbook",
                "document_type": "runbook",
                "business_area": "policy",
            },
        )
        extracted.index_document(str(document.external_doc_id))
        extracted_chunks = extracted.list_document_chunks(str(document.external_doc_id))

    weknora_chunks = weknora.list_document_chunks("wk-doc-parity-fixture")
    chunk_delta = _chunk_boundary_delta(extracted_chunks, weknora_chunks)
    _assert(chunk_delta["extracted_count"] > 0, "extracted produced no chunks")
    _assert(chunk_delta["weknora_count"] > 0, "weknora fixture produced no chunks")
    _assert(
        chunk_delta["boundary_delta_count"] >= 0,
        "chunk boundary delta was not recorded",
    )

    comparisons: list[RetrievalComparison] = []
    traceable_checks = 0
    for query in KEY_QUERIES:
        extracted_items = normalize_evidence_results(
            extracted.retrieve(query, top_k=4),
            top_k=2,
        )
        weknora_items = normalize_evidence_results(
            weknora.retrieve(query, top_k=4),
            top_k=2,
        )
        _assert_traceable_evidence(extracted_items, expected_source="extracted")
        _assert_traceable_evidence(weknora_items, expected_source="weknora_api")
        _assert_citation_checker(extracted_items)
        _assert_citation_checker(weknora_items)
        traceable_checks += len(extracted_items) + len(weknora_items)
        comparisons.append(
            _compare_retrieval(query, top_k=2, extracted=extracted_items, weknora=weknora_items)
        )

    report = _parity_report(chunk_delta, comparisons)
    _assert_report(report)
    return {
        "chunk_delta": chunk_delta,
        "query_count": len(comparisons),
        "traceable_checks": traceable_checks,
        "live_comparison": "not_run_offline_fixture",
    }


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="fixture://weknora",
            service_token="fixture-token",
            workspace_id="workspace-redacted",
            default_kb_id="kb-redacted",
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        if method == "GET" and path.startswith("/api/v1/chunks/"):
            return {"data": {"items": _weknora_chunk_items()}}
        if method == "POST" and path == "/api/v1/knowledge-search":
            return {"data": _weknora_retrieval_items(str((payload or {}).get("query") or ""))}
        raise SmokeError(f"unexpected fixture request: {method} {path}")


def _extracted_backend() -> ExtractedKnowledgeBackend:
    return ExtractedKnowledgeBackend(
        config=ExtractedBackendConfig(source="extracted", backend_name="extracted"),
        components=ExtractedBackendComponents(
            chunker=ParagraphChunker(
                ChunkingConfig(max_chars=260, overlap_chars=40, min_chars=80)
            ),
            vector_store=MockVectorStore(name="m3-b2-extracted-parity"),
        ),
        embedding_provider=MockEmbeddingProvider(
            EmbeddingProviderConfig(
                provider="mock",
                model_name="m3-b2-parity",
                dimension=16,
            )
        ),
    )


def _weknora_chunk_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "wk-chunk-retention",
            "knowledge_id": "wk-doc-parity-fixture",
            "knowledge_base_id": "kb-redacted",
            "chunk_index": 0,
            "title": "Sanitized Policy Runbook",
            "content": "Retention controls require quarterly review and owner approval.",
            "token_count": 16,
            "start_at": 29,
            "end_at": 154,
            "is_enabled": True,
        },
        {
            "id": "wk-chunk-incident",
            "knowledge_id": "wk-doc-parity-fixture",
            "knowledge_base_id": "kb-redacted",
            "chunk_index": 1,
            "title": "Sanitized Policy Runbook",
            "content": "Incident review notes require a timeline and policy exception marker.",
            "token_count": 18,
            "start_at": 155,
            "end_at": 323,
            "is_enabled": True,
        },
        {
            "id": "wk-chunk-trace",
            "knowledge_id": "wk-doc-parity-fixture",
            "knowledge_base_id": "kb-redacted",
            "chunk_index": 2,
            "title": "Sanitized Policy Runbook",
            "content": "Citation trace fields let downstream Agent checks reject untraceable output.",
            "token_count": 17,
            "start_at": 324,
            "end_at": 534,
            "is_enabled": True,
        },
    ]


def _weknora_retrieval_items(query: str) -> list[dict[str, Any]]:
    normalized = query.lower()
    if "incident" in normalized:
        ordered = (
            ("wk-chunk-incident", "Incident review notes require a timeline and policy exception marker.", 0.93),
            ("wk-chunk-trace", "Citation trace fields let downstream Agent checks reject untraceable output.", 0.76),
        )
    else:
        ordered = (
            ("wk-chunk-retention", "Retention controls require quarterly review and owner approval.", 0.95),
            ("wk-chunk-trace", "Citation trace fields let downstream Agent checks reject untraceable output.", 0.72),
        )
    return [
        {
            "id": chunk_id,
            "knowledge_id": "wk-doc-parity-fixture",
            "knowledge_base_id": "kb-redacted",
            "title": "Sanitized Policy Runbook",
            "content": content,
            "score": score,
            "metadata": {"fixture": "m3-b2", "source_type": "document"},
        }
        for chunk_id, content, score in ordered
    ]


def _chunk_boundary_delta(
    extracted_chunks: list[dict[str, Any]],
    weknora_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    extracted_boundaries = [
        (chunk.get("start_char"), chunk.get("end_char")) for chunk in extracted_chunks
    ]
    weknora_boundaries = [
        (chunk.get("start_char"), chunk.get("end_char")) for chunk in weknora_chunks
    ]
    common_prefix = min(len(extracted_boundaries), len(weknora_boundaries))
    boundary_delta_count = sum(
        1
        for index in range(common_prefix)
        if extracted_boundaries[index] != weknora_boundaries[index]
    )
    boundary_delta_count += abs(len(extracted_boundaries) - len(weknora_boundaries))
    return {
        "extracted_count": len(extracted_chunks),
        "weknora_count": len(weknora_chunks),
        "count_delta": len(extracted_chunks) - len(weknora_chunks),
        "boundary_delta_count": boundary_delta_count,
        "extracted_boundaries": extracted_boundaries,
        "weknora_boundaries": weknora_boundaries,
    }


def _compare_retrieval(
    query: str,
    *,
    top_k: int,
    extracted: list[Evidence],
    weknora: list[Evidence],
) -> RetrievalComparison:
    return RetrievalComparison(
        query=query,
        top_k=top_k,
        extracted_count=len(extracted),
        weknora_count=len(weknora),
        extracted_source_types=sorted({item.source_type for item in extracted}),
        weknora_source_types=sorted({item.source_type for item in weknora}),
        extracted_score_semantics=sorted(
            {str(item.metadata.get("score_semantics") or "") for item in extracted}
        ),
        weknora_score_semantics=sorted(
            {str(item.metadata.get("score_semantics") or "") for item in weknora}
        ),
        extracted_evidence_ids=[str(item.evidence_id) for item in extracted],
        weknora_evidence_ids=[str(item.evidence_id) for item in weknora],
        first_rank_same_title=bool(
            extracted
            and weknora
            and extracted[0].title == weknora[0].title
            and extracted[0].chunk_id == weknora[0].chunk_id
        ),
    )


def _parity_report(
    chunk_delta: dict[str, Any],
    comparisons: list[RetrievalComparison],
) -> dict[str, Any]:
    return {
        "task_id": "P3-M3-B2",
        "fixture": "sanitized_offline",
        "live_comparison": "not_run_offline_fixture",
        "chunk_delta": chunk_delta,
        "retrieval_comparisons": [comparison.__dict__ for comparison in comparisons],
        "ranking_assertion": "record_difference_only",
        "acceptance": "key_queries_return_traceable_evidence",
    }


def _assert_report(report: dict[str, Any]) -> None:
    _assert(report["task_id"] == "P3-M3-B2", "report task mismatch")
    _assert(report["ranking_assertion"] == "record_difference_only", "ranking policy drifted")
    comparisons = report.get("retrieval_comparisons")
    _assert(isinstance(comparisons, list) and len(comparisons) == len(KEY_QUERIES), "missing comparisons")
    for comparison in comparisons:
        _assert(comparison["extracted_count"] > 0, "report recorded empty extracted result")
        _assert(comparison["weknora_count"] > 0, "report recorded empty WeKnora result")
        _assert(comparison["extracted_count"] <= comparison["top_k"], "extracted exceeded top_k")
        _assert(comparison["weknora_count"] <= comparison["top_k"], "WeKnora exceeded top_k")
        _assert(
            comparison["extracted_score_semantics"] != comparison["weknora_score_semantics"],
            "score semantics should remain distinct",
        )


def _assert_traceable_evidence(items: list[Evidence], *, expected_source: str) -> None:
    _assert(items, f"{expected_source} returned no evidence")
    for item in items:
        _assert(item.source == expected_source, f"{expected_source} source mismatch: {item.source}")
        if expected_source == "extracted":
            _assert(item.source != "weknora_api", "extracted evidence spoofed WeKnora")
        _assert(item.evidence_id, f"{expected_source} evidence missing evidence_id")
        _assert(item.source_type == "document_chunk", f"{expected_source} source_type mismatch")
        _assert(item.chunk_id, f"{expected_source} evidence missing chunk_id")
        _assert(
            item.document_id or item.external_doc_id,
            f"{expected_source} evidence missing document id",
        )
        _assert(
            item.metadata.get("citation_source_type") == item.source_type,
            f"{expected_source} citation source type metadata mismatch",
        )
        binding = item.metadata.get("citation_binding")
        if expected_source == "extracted":
            _assert(isinstance(binding, dict), f"{expected_source} missing citation binding")
        _assert(
            item.metadata.get("score_semantics"),
            f"{expected_source} missing score semantics",
        )


def _assert_citation_checker(items: list[Evidence]) -> None:
    citations = [
        Citation(
            title=item.title,
            text=item.text,
            source=item.source,
            document_id=item.document_id,
            external_doc_id=item.external_doc_id,
            chunk_id=item.chunk_id,
            score=item.score,
            metadata=item.metadata,
            evidence_id=item.evidence_id,
            source_type=item.source_type,
            wiki_page_id=item.wiki_page_id,
        )
        for item in items
    ]
    result = CitationChecker().validate(citations, evidence_items=items)
    _assert(result.valid, "CitationChecker rejected evidence: " + "; ".join(result.warnings))


def _assert_doc_report() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    for phrase in (
        "p3-m3-b2",
        "chunk boundaries",
        "top_k",
        "source_type",
        "score semantics",
        "citation trace",
        "difference recorded",
        "live comparison",
    ):
        _assert(phrase in lower, f"parity report missing phrase: {phrase}")


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


class _without_embedding_env:
    def __init__(self) -> None:
        self.original: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key in ENV_KEYS:
            self.original[key] = os.environ.get(key)
            os.environ.pop(key, None)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        for key in ENV_KEYS:
            os.environ.pop(key, None)
            if self.original[key] is not None:
                os.environ[key] = self.original[key] or ""


if __name__ == "__main__":
    raise SystemExit(main())
