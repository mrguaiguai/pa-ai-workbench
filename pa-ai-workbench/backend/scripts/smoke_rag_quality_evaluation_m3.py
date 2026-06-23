"""Offline RAG quality evaluation contract smoke for P3-M3-C3.

The smoke reads the P3-M3-C2 golden set and the P3-M3-C3 rubric fixture,
computes deterministic sample metrics, checks diagnostic bucket rules, and
verifies that the documentation/report stay aligned with those contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.schemas import Citation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from knowledge_engine.evidence import normalize_evidence_results  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


GOLDEN_SET_PATH = PROJECT_ROOT / "backend" / "fixtures" / "retrieval_quality_golden_m3.json"
RUBRIC_PATH = PROJECT_ROOT / "backend" / "fixtures" / "rag_quality_evaluation_m3.json"
RUBRIC_DOC_PATH = PROJECT_ROOT / "docs" / "PHASE3_M3_RAG_QUALITY_EVALUATION_RUBRIC.md"
SAMPLE_REPORT_PATH = PROJECT_ROOT / "docs" / "PHASE3_M3_RAG_QUALITY_SAMPLE_REPORT.md"
EXPECTED_SCHEMA_VERSION = "p3-m3-c3"
REQUIRED_METRICS = {
    "recall_proxy",
    "citation_traceability",
    "source_diversity",
    "latency",
    "manual_rating",
}
EXPECTED_BUCKETS = {
    "configuration_problem",
    "retrieval_problem",
    "generation_problem",
    "material_quality_problem",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class SmokeError(RuntimeError):
    """Raised when RAG quality evaluation expectations fail."""


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    recall_proxy: float
    citation_traceability: float
    source_diversity: float
    latency_ms: int
    manual_rating: float
    bucket: str

    @property
    def passed(self) -> bool:
        return self.bucket == "healthy"


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"RAG quality evaluation smoke failed: {exc}", file=sys.stderr)
        return 1

    print("RAG quality evaluation smoke passed")
    print(f"- cases evaluated: {result['case_count']}")
    print(f"- mean recall proxy: {result['mean_recall_proxy']:.2f}")
    print(f"- citation traceability pass rate: {result['citation_traceability_pass_rate']:.2f}")
    print(f"- source diversity pass rate: {result['source_diversity_pass_rate']:.2f}")
    print(f"- average latency ms: {result['average_latency_ms']}")
    print(f"- average manual rating: {result['average_manual_rating']:.2f}")
    print(f"- diagnostic buckets: {', '.join(result['diagnostic_buckets'])}")
    print(f"- rubric checksum: {result['rubric_checksum']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    golden_text = GOLDEN_SET_PATH.read_text(encoding="utf-8")
    rubric_text = RUBRIC_PATH.read_text(encoding="utf-8")
    _assert_no_sensitive_text(golden_text, "golden set")
    _assert_no_sensitive_text(rubric_text, "rubric fixture")
    golden = json.loads(golden_text)
    rubric = json.loads(rubric_text)
    _assert_rubric_schema(rubric, golden)
    case_scores = [_score_case(case, rubric) for case in golden["cases"]]
    diagnostics = _assert_diagnostic_scenarios(rubric)
    summary = _summarize(case_scores, diagnostics, rubric_text)
    _assert_docs(summary)
    return summary


def _assert_rubric_schema(rubric: dict[str, Any], golden: dict[str, Any]) -> None:
    _assert(rubric.get("schema_version") == EXPECTED_SCHEMA_VERSION, "schema version mismatch")
    _assert(rubric.get("fixture_kind") == "rag_quality_evaluation_rubric", "bad fixture kind")
    _assert(rubric.get("source") == "golden_fixture", "rubric source must be explicit")
    _assert(rubric.get("golden_set") == GOLDEN_SET_PATH.name, "rubric must reference C2 golden set")
    metric_ids = {str(item.get("id")) for item in rubric.get("metrics", []) if isinstance(item, dict)}
    _assert(REQUIRED_METRICS.issubset(metric_ids), f"missing metrics: {REQUIRED_METRICS - metric_ids}")

    manual = rubric.get("manual_rating")
    _assert(isinstance(manual, dict), "manual_rating block missing")
    dimensions = manual.get("dimensions")
    _assert(isinstance(dimensions, list) and len(dimensions) >= 5, "manual dimensions missing")
    _assert(float(manual.get("pass_threshold") or 0) >= 4.0, "manual pass threshold too low")

    latency = rubric.get("latency")
    _assert(isinstance(latency, dict), "latency block missing")
    _assert(int(latency.get("target_ms") or 0) > 0, "latency target missing")

    observations = rubric.get("sample_observations")
    _assert(isinstance(observations, list), "sample observations missing")
    case_ids = {str(case["id"]) for case in golden.get("cases", [])}
    observation_ids = {str(item.get("case_id")) for item in observations if isinstance(item, dict)}
    _assert(case_ids == observation_ids, f"sample observations do not match golden set: {case_ids ^ observation_ids}")


def _score_case(case: dict[str, Any], rubric: dict[str, Any]) -> CaseScore:
    evidence = normalize_evidence_results(_case_evidence(case), top_k=int(case["top_k"]))
    observation = _observation_for_case(rubric, str(case["id"]))
    conditions = case["expected_citation_conditions"]
    recall_proxy = _recall_proxy(conditions["required_terms"], evidence)
    citation_traceability = _citation_traceability(evidence)
    source_diversity = _source_diversity(conditions, evidence)
    latency_ms = int(observation["latency_ms"])
    manual_rating = _manual_rating_average(observation["manual_rating"])
    retrieval_pass = (
        recall_proxy >= _metric_threshold(rubric, "recall_proxy")
        and citation_traceability >= _metric_threshold(rubric, "citation_traceability")
        and source_diversity >= _metric_threshold(rubric, "source_diversity")
    )
    signals = {
        "config_ready": True,
        "backend_error": None,
        "retrieval_pass": retrieval_pass,
        "citation_traceability": citation_traceability,
        "unsupported_claims": int(observation["generated_answer_observations"]["unsupported_claims"]),
        "material_sufficiency": int(observation["material_quality"]["sufficiency"]),
    }
    bucket = _diagnose(signals)
    return CaseScore(
        case_id=str(case["id"]),
        recall_proxy=recall_proxy,
        citation_traceability=citation_traceability,
        source_diversity=source_diversity,
        latency_ms=latency_ms,
        manual_rating=manual_rating,
        bucket=bucket,
    )


def _case_evidence(case: dict[str, Any]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for item in case["fixture_evidence"]:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        evidence.append(
            Evidence(
                document_id=_optional_str(item.get("document_id")),
                external_doc_id=_optional_str(item.get("external_doc_id")),
                chunk_id=_optional_str(item.get("chunk_id")),
                title=str(item["title"]),
                text=str(item["text"]),
                score=float(item["score"]) if item.get("score") is not None else None,
                source=str(item["source"]),
                metadata={
                    **metadata,
                    "quality_fixture": "p3-m3-c3",
                    "golden_case_id": case["id"],
                    "evidence_id": item["evidence_id"],
                    "source_type": item["source_type"],
                },
                evidence_id=str(item["evidence_id"]),
                source_type=str(item["source_type"]),
                wiki_page_id=_optional_str(item.get("wiki_page_id")),
            )
        )
    return evidence


def _recall_proxy(required_terms: list[str], evidence: list[Evidence]) -> float:
    combined_text = " ".join(f"{item.title} {item.text}" for item in evidence).lower()
    hits = [term for term in required_terms if str(term).strip().lower() in combined_text]
    return len(hits) / len(required_terms)


def _citation_traceability(evidence: list[Evidence]) -> float:
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
        for item in evidence
    ]
    result = CitationChecker().validate(citations, evidence)
    return 1.0 if result.valid else 0.0


def _source_diversity(conditions: dict[str, Any], evidence: list[Evidence]) -> float:
    expected_types = set(conditions["source_types"])
    actual_types = {item.source_type for item in evidence}
    type_score = len(expected_types & actual_types) / len(expected_types)
    min_titles = max(int(conditions.get("min_distinct_titles") or 1), 1)
    title_score = min(len({item.title for item in evidence}) / min_titles, 1.0)
    return (type_score + title_score) / 2


def _manual_rating_average(ratings: dict[str, Any]) -> float:
    values = [float(value) for value in ratings.values()]
    _assert(values and all(1 <= value <= 5 for value in values), "manual rating values must be 1..5")
    return statistics.fmean(values)


def _assert_diagnostic_scenarios(rubric: dict[str, Any]) -> list[str]:
    scenarios = rubric.get("diagnostic_scenarios")
    _assert(isinstance(scenarios, list), "diagnostic scenarios missing")
    actual_buckets: list[str] = []
    for scenario in scenarios:
        expected = str(scenario.get("expected_bucket"))
        actual = _diagnose(scenario.get("signals") or {})
        _assert(actual == expected, f"diagnostic scenario {scenario.get('id')} expected {expected}, got {actual}")
        actual_buckets.append(actual)
    _assert(EXPECTED_BUCKETS == set(actual_buckets), f"diagnostic buckets mismatch: {set(actual_buckets)}")
    return actual_buckets


def _diagnose(signals: dict[str, Any]) -> str:
    if signals.get("config_ready") is not True or signals.get("backend_error"):
        return "configuration_problem"
    if signals.get("retrieval_pass") is not True:
        return "retrieval_problem"
    if float(signals.get("citation_traceability") or 0) < 1.0 or int(signals.get("unsupported_claims") or 0) > 0:
        return "generation_problem"
    if int(signals.get("material_sufficiency") or 0) <= 2:
        return "material_quality_problem"
    return "healthy"


def _summarize(
    case_scores: list[CaseScore],
    diagnostic_buckets: list[str],
    rubric_text: str,
) -> dict[str, Any]:
    case_count = len(case_scores)
    _assert(case_count > 0, "no cases scored")
    return {
        "case_count": case_count,
        "mean_recall_proxy": statistics.fmean(score.recall_proxy for score in case_scores),
        "citation_traceability_pass_rate": statistics.fmean(score.citation_traceability for score in case_scores),
        "source_diversity_pass_rate": statistics.fmean(score.source_diversity for score in case_scores),
        "average_latency_ms": round(statistics.fmean(score.latency_ms for score in case_scores)),
        "average_manual_rating": statistics.fmean(score.manual_rating for score in case_scores),
        "overall_pass": all(score.passed for score in case_scores),
        "diagnostic_buckets": sorted(set(diagnostic_buckets)),
        "rubric_checksum": hashlib.sha256(rubric_text.encode("utf-8")).hexdigest()[:16],
    }


def _assert_docs(summary: dict[str, Any]) -> None:
    rubric_doc = RUBRIC_DOC_PATH.read_text(encoding="utf-8")
    report_doc = SAMPLE_REPORT_PATH.read_text(encoding="utf-8")
    for phrase in (
        "P3-M3-C3",
        "recall_proxy",
        "citation_traceability",
        "source_diversity",
        "latency",
        "manual_rating",
        "configuration_problem",
        "retrieval_problem",
        "generation_problem",
        "material_quality_problem",
    ):
        _assert(phrase in rubric_doc, f"rubric doc missing phrase: {phrase}")
    expected_report_lines = (
        f"Cases evaluated: {summary['case_count']}",
        f"Mean recall proxy: {summary['mean_recall_proxy']:.2f}",
        f"Citation traceability pass rate: {summary['citation_traceability_pass_rate']:.2f}",
        f"Source diversity pass rate: {summary['source_diversity_pass_rate']:.2f}",
        f"Average latency: {summary['average_latency_ms']} ms",
        f"Average manual rating: {summary['average_manual_rating']:.2f}",
        f"Overall pass: {'yes' if summary['overall_pass'] else 'no'}",
    )
    for line in expected_report_lines:
        _assert(line in report_doc, f"sample report missing computed line: {line}")


def _observation_for_case(rubric: dict[str, Any], case_id: str) -> dict[str, Any]:
    for observation in rubric["sample_observations"]:
        if observation.get("case_id") == case_id:
            return observation
    raise SmokeError(f"missing sample observation for case: {case_id}")


def _metric_threshold(rubric: dict[str, Any], metric_id: str) -> float:
    for metric in rubric["metrics"]:
        if metric.get("id") == metric_id:
            return float(metric["pass_threshold"])
    raise SmokeError(f"missing metric threshold: {metric_id}")


def _assert_no_sensitive_text(text: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        _assert(not pattern.search(text), f"{label} matched sensitive pattern: {pattern.pattern}")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
