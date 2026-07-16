"""Offline retrieval quality golden-set smoke for P3-M3-C2.

The smoke evaluates only sanitized fixture cases. It validates the golden set
shape, checks the expected citation conditions, and runs PA citation
traceability checks against fixture Evidence items.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.schemas import Citation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from knowledge_engine.evidence import normalize_evidence_results  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


GOLDEN_SET_PATH = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "retrieval_quality_golden_m3.json"
DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_RETRIEVAL_QUALITY_GOLDEN_SET.md"
EXPECTED_SCHEMA_VERSION = "p3-m3-c2"
MIN_CASES = 4
ALLOWED_TASK_TYPES = {"knowledge_qa", "policy_analysis", "case_review", "wiki_draft"}
ALLOWED_SOURCE_TYPES = {"document_chunk", "wiki_page"}
DISALLOWED_EVIDENCE_SOURCES = {"weknora_api", "mock"}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class SmokeError(RuntimeError):
    """Raised when golden-set expectations fail."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Retrieval quality golden-set smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Retrieval quality golden-set smoke passed")
    print(f"- fixture: {GOLDEN_SET_PATH.relative_to(PROJECT_ROOT)}")
    print(f"- cases evaluated: {result['case_count']}")
    print(f"- evidence checked: {result['evidence_count']}")
    print(f"- citation checks: {result['citation_checks']}")
    print(f"- fixture checksum: {result['fixture_checksum']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    fixture_text = GOLDEN_SET_PATH.read_text(encoding="utf-8")
    _assert_no_sensitive_fixture_text(fixture_text)
    payload = json.loads(fixture_text)
    _assert_golden_set_schema(payload)
    _assert_doc_report()

    citation_checks = 0
    evidence_count = 0
    for case in payload["cases"]:
        evidence = _case_evidence(case)
        normalized = normalize_evidence_results(evidence, top_k=int(case["top_k"]))
        _assert_case_conditions(case, normalized)
        _assert_traceable_citations(case, normalized)
        citation_checks += len(normalized)
        evidence_count += len(normalized)

    return {
        "case_count": len(payload["cases"]),
        "evidence_count": evidence_count,
        "citation_checks": citation_checks,
        "fixture_checksum": hashlib.sha256(fixture_text.encode("utf-8")).hexdigest()[:16],
    }


def _assert_golden_set_schema(payload: dict[str, Any]) -> None:
    _assert(payload.get("schema_version") == EXPECTED_SCHEMA_VERSION, "schema version mismatch")
    _assert(payload.get("fixture_kind") == "sanitized_retrieval_quality_golden_set", "bad fixture kind")
    _assert(payload.get("source") == "golden_fixture", "fixture source must be explicit")
    cases = payload.get("cases")
    _assert(isinstance(cases, list), "cases must be a list")
    _assert(len(cases) >= MIN_CASES, f"golden set must contain at least {MIN_CASES} cases")
    seen_ids: set[str] = set()
    for case in cases:
        _assert_case_schema(case, seen_ids)


def _assert_case_schema(case: dict[str, Any], seen_ids: set[str]) -> None:
    case_id = _required_str(case, "id")
    _assert(case_id not in seen_ids, f"duplicate case id: {case_id}")
    seen_ids.add(case_id)
    query = _required_str(case, "query")
    _assert(12 <= len(query) <= 180, f"{case_id} query length is out of range")
    _assert(_required_str(case, "task_type") in ALLOWED_TASK_TYPES, f"{case_id} task_type is unsupported")
    _assert(1 <= int(case.get("top_k") or 0) <= 10, f"{case_id} top_k is out of range")
    _assert(_required_str(case, "human_note"), f"{case_id} missing human note")
    conditions = case.get("expected_citation_conditions")
    _assert(isinstance(conditions, dict), f"{case_id} missing expected citation conditions")
    _assert(int(conditions.get("min_evidence") or 0) >= 1, f"{case_id} min_evidence is invalid")
    _assert(conditions.get("requires_traceable_citations") is True, f"{case_id} must require traceable citations")
    source_types = conditions.get("source_types")
    _assert(isinstance(source_types, list) and source_types, f"{case_id} missing expected source types")
    _assert(set(source_types).issubset(ALLOWED_SOURCE_TYPES), f"{case_id} has unsupported source types")
    required_terms = conditions.get("required_terms")
    _assert(isinstance(required_terms, list) and required_terms, f"{case_id} missing required terms")
    for term in required_terms:
        _assert(isinstance(term, str) and term.strip(), f"{case_id} has blank required term")
    fixture_evidence = case.get("fixture_evidence")
    _assert(isinstance(fixture_evidence, list) and fixture_evidence, f"{case_id} missing fixture evidence")
    for item in fixture_evidence:
        _assert_evidence_schema(case_id, item)


def _assert_evidence_schema(case_id: str, item: dict[str, Any]) -> None:
    _assert(_required_str(item, "evidence_id"), f"{case_id} evidence missing evidence_id")
    source = _required_str(item, "source")
    _assert(source not in DISALLOWED_EVIDENCE_SOURCES, f"{case_id} fixture evidence source is not explicit: {source}")
    source_type = _required_str(item, "source_type")
    _assert(source_type in ALLOWED_SOURCE_TYPES, f"{case_id} bad evidence source_type")
    _assert(_required_str(item, "title"), f"{case_id} evidence missing title")
    text = _required_str(item, "text")
    _assert(24 <= len(text) <= 360, f"{case_id} evidence text length is out of range")
    if source_type == "document_chunk":
        _assert(_required_str(item, "chunk_id"), f"{case_id} document evidence missing chunk_id")
        _assert(item.get("document_id") or item.get("external_doc_id"), f"{case_id} document evidence missing document id")
    if source_type == "wiki_page":
        _assert(_required_str(item, "wiki_page_id"), f"{case_id} wiki evidence missing wiki_page_id")


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
                    "golden_case_id": case["id"],
                    "quality_fixture": "p3-m3-c2",
                    "evidence_id": item["evidence_id"],
                    "source_type": item["source_type"],
                },
                evidence_id=str(item["evidence_id"]),
                source_type=str(item["source_type"]),
                wiki_page_id=_optional_str(item.get("wiki_page_id")),
            )
        )
    return evidence


def _assert_case_conditions(case: dict[str, Any], evidence: list[Evidence]) -> None:
    case_id = str(case["id"])
    conditions = case["expected_citation_conditions"]
    _assert(len(evidence) >= int(conditions["min_evidence"]), f"{case_id} returned too little evidence")
    expected_types = set(conditions["source_types"])
    actual_types = {item.source_type for item in evidence}
    _assert(expected_types.issubset(actual_types), f"{case_id} missing expected source types: {expected_types - actual_types}")
    title_count = len({item.title for item in evidence})
    _assert(title_count >= int(conditions.get("min_distinct_titles") or 1), f"{case_id} lacks source title diversity")
    combined_text = " ".join(f"{item.title} {item.text}" for item in evidence).lower()
    missing_terms = [
        term
        for term in conditions["required_terms"]
        if str(term).strip().lower() not in combined_text
    ]
    _assert(not missing_terms, f"{case_id} missing required terms: {missing_terms}")


def _assert_traceable_citations(case: dict[str, Any], evidence: list[Evidence]) -> None:
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
    _assert(result.valid, f"{case['id']} citation checker warnings: {result.warnings}")


def _assert_doc_report() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for phrase in (
        "retrieval_quality_golden_m3.json",
        "smoke_retrieval_quality_golden_m3.py",
        "expected_citation_conditions",
        "synthetic",
    ):
        _assert(phrase in text, f"golden-set doc missing phrase: {phrase}")


def _assert_no_sensitive_fixture_text(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        _assert(not pattern.search(text), f"fixture matched sensitive pattern: {pattern.pattern}")
    forbidden_literals = (".env", "uploads/", "node_modules/", "dist/", "BEGIN PRIVATE KEY")
    for literal in forbidden_literals:
        _assert(literal not in text, f"fixture contains forbidden literal: {literal}")


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    _assert(isinstance(value, str) and value.strip(), f"missing string field: {key}")
    return value.strip()


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
