"""Offline Agent-output faithfulness regression smoke for P3-M3-C4.

The smoke runs QA / policy / case Agent workflows with sanitized golden-set
evidence. It validates citation coverage, PA CitationChecker traceability,
no-evidence warnings, and unsupported-claim detection without live WeKnora,
.env reads, or real source material.
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


from agent.agents.case_agent import CaseReviewWorkflow  # noqa: E402
from agent.agents.policy_agent import PolicyAnalysisWorkflow  # noqa: E402
from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.model_gateway.base import ModelGateway  # noqa: E402
from agent.model_gateway.schemas import ChatRequest  # noqa: E402
from agent.model_gateway.schemas import ChatResponse  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from agent.tools.faithfulness_checker import FaithfulnessChecker  # noqa: E402
from knowledge_engine.evidence import normalize_evidence_results  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


GOLDEN_SET_PATH = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "retrieval_quality_golden_m3.json"
FAITHFULNESS_FIXTURE_PATH = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "agent_faithfulness_m3.json"
DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_AGENT_FAITHFULNESS_REGRESSION.md"
EXPECTED_SCHEMA_VERSION = "p3-m3-c4"
REQUIRED_WORKFLOWS = {"knowledge_qa", "policy_analysis", "case_review"}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class SmokeError(RuntimeError):
    """Raised when Agent faithfulness expectations fail."""


class FixtureRetriever:
    def __init__(self, citations: list[Citation]) -> None:
        self.citations = citations

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[Citation]:
        return self.citations[: top_k or len(self.citations)]


class FixedAnswerProvider(ModelGateway):
    def __init__(self, content: str) -> None:
        self.content = content

    def generate(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            content=self.content,
            model="fixture-faithfulness",
            provider="fixture",
            usage={
                "prompt_tokens": _estimate_tokens(" ".join(message.content for message in request.messages)),
                "completion_tokens": _estimate_tokens(self.content),
            },
            raw_metadata={"fixture": "p3-m3-c4"},
        )


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Agent faithfulness smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Agent faithfulness smoke passed")
    print(f"- workflows checked: {', '.join(result['workflows'])}")
    print(f"- grounded cases: {result['grounded_cases']}")
    print(f"- citation coverage checks: {result['citation_coverage_checks']}")
    print(f"- traceability checks: {result['traceability_checks']}")
    print(f"- no evidence warning: {result['no_evidence_warning']}")
    print(f"- unsupported claim warning: {result['unsupported_claim_warning']}")
    print(f"- fixture checksum: {result['fixture_checksum']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    golden_text = GOLDEN_SET_PATH.read_text(encoding="utf-8")
    fixture_text = FAITHFULNESS_FIXTURE_PATH.read_text(encoding="utf-8")
    _assert_no_sensitive_text(golden_text, "golden set")
    _assert_no_sensitive_text(fixture_text, "faithfulness fixture")
    golden = json.loads(golden_text)
    fixture = json.loads(fixture_text)
    _assert_fixture_schema(fixture, golden)
    _assert_doc()

    golden_cases = {case["id"]: case for case in golden["cases"]}
    checker = FaithfulnessChecker()
    citation_checker = CitationChecker()
    workflows_seen: set[str] = set()
    citation_coverage_checks = 0
    traceability_checks = 0

    for case in fixture["cases"]:
        golden_case = golden_cases[str(case["golden_case_id"])]
        result = _run_grounded_workflow(case, golden_case)
        workflows_seen.add(str(case["workflow"]))
        faith = checker.validate(
            result.markdown,
            result.citations,
            required_terms=[str(term) for term in case["required_terms"]],
            unsupported_terms=[str(term) for term in case.get("unsupported_terms", [])],
        )
        _assert(faith.valid, f"{case['id']} faithfulness warnings: {faith.warnings}")
        _assert(
            faith.citation_coverage >= float(case["expected_min_citation_coverage"]),
            f"{case['id']} citation coverage too low: {faith.citation_coverage}",
        )
        citation_coverage_checks += 1
        trace = citation_checker.validate(result.citations, evidence_items=result.citations)
        _assert(trace.valid, f"{case['id']} citation trace failed: {trace.warnings}")
        traceability_checks += len(result.citations)

    _assert(workflows_seen == REQUIRED_WORKFLOWS, f"workflow coverage mismatch: {workflows_seen}")
    no_evidence_warning = _assert_no_evidence_negative_case(fixture, checker)
    unsupported_claim_warning = _assert_unsupported_negative_case(fixture, golden_cases, checker)
    return {
        "workflows": sorted(workflows_seen),
        "grounded_cases": len(fixture["cases"]),
        "citation_coverage_checks": citation_coverage_checks,
        "traceability_checks": traceability_checks,
        "no_evidence_warning": no_evidence_warning,
        "unsupported_claim_warning": unsupported_claim_warning,
        "fixture_checksum": hashlib.sha256(fixture_text.encode("utf-8")).hexdigest()[:16],
    }


def _assert_fixture_schema(fixture: dict[str, Any], golden: dict[str, Any]) -> None:
    _assert(fixture.get("schema_version") == EXPECTED_SCHEMA_VERSION, "schema version mismatch")
    _assert(fixture.get("fixture_kind") == "agent_faithfulness_regression", "bad fixture kind")
    _assert(fixture.get("source") == "golden_fixture", "fixture source must be explicit")
    _assert(fixture.get("golden_set") == GOLDEN_SET_PATH.name, "fixture must reference C2 golden set")
    cases = fixture.get("cases")
    _assert(isinstance(cases, list) and cases, "faithfulness cases missing")
    golden_ids = {str(case["id"]) for case in golden.get("cases", [])}
    seen_ids: set[str] = set()
    for case in cases:
        case_id = _required_str(case, "id")
        _assert(case_id not in seen_ids, f"duplicate case id: {case_id}")
        seen_ids.add(case_id)
        workflow = _required_str(case, "workflow")
        _assert(workflow in REQUIRED_WORKFLOWS, f"{case_id} unsupported workflow")
        _assert(str(case.get("golden_case_id")) in golden_ids, f"{case_id} missing golden case")
        required_terms = case.get("required_terms")
        _assert(isinstance(required_terms, list) and required_terms, f"{case_id} missing required terms")
        _assert(float(case.get("expected_min_citation_coverage") or 0) >= 1.0, f"{case_id} coverage threshold too low")
    negative_cases = fixture.get("negative_cases")
    _assert(isinstance(negative_cases, list) and len(negative_cases) >= 2, "negative cases missing")
    codes = {str(case.get("expected_warning_code")) for case in negative_cases}
    _assert({"NO_EVIDENCE", "UNSUPPORTED_CLAIM"}.issubset(codes), "negative warning coverage missing")


def _run_grounded_workflow(case: dict[str, Any], golden_case: dict[str, Any]):
    citations = _case_citations(golden_case)
    answer = _grounded_answer(str(case["workflow"]), case["required_terms"], citations)
    workflow = _workflow(
        str(case["workflow"]),
        retriever=FixtureRetriever(citations),
        model_gateway=FixedAnswerProvider(answer),
    )
    request = _request(
        str(case["workflow"]),
        str(golden_case["query"]),
        task_id=str(case["id"]),
    )
    return workflow(request, AgentContext(request=request))


def _assert_no_evidence_negative_case(
    fixture: dict[str, Any],
    checker: FaithfulnessChecker,
) -> bool:
    negative = _negative_case(fixture, "NO_EVIDENCE")
    workflow = _workflow(
        str(negative["workflow"]),
        retriever=FixtureRetriever([]),
        model_gateway=FixedAnswerProvider("This should be replaced by no-evidence markdown."),
    )
    request = _request(
        str(negative["workflow"]),
        str(negative["query"]),
        task_id=str(negative["id"]),
    )
    result = workflow(request, AgentContext(request=request))
    _assert(not result.citations, "no-evidence workflow returned citations")
    _assert(_has_warning_code(result, "NO_EVIDENCE"), "Agent result missing NO_EVIDENCE warning code")
    faith = checker.validate(
        result.markdown,
        result.citations,
        require_no_evidence_warning=True,
    )
    _assert(faith.valid, f"no-evidence faithfulness warning failed: {faith.warnings}")
    return True


def _assert_unsupported_negative_case(
    fixture: dict[str, Any],
    golden_cases: dict[str, dict[str, Any]],
    checker: FaithfulnessChecker,
) -> bool:
    negative = _negative_case(fixture, "UNSUPPORTED_CLAIM")
    golden_case = golden_cases[str(negative["golden_case_id"])]
    citations = _case_citations(golden_case)
    answer = (
        "## Fixture Answer\n\n"
        "Retention review needs quarterly review [1]. "
        "It also grants same-day approval [1]."
    )
    workflow = _workflow(
        str(negative["workflow"]),
        retriever=FixtureRetriever(citations),
        model_gateway=FixedAnswerProvider(answer),
    )
    request = _request(
        str(negative["workflow"]),
        str(golden_case["query"]),
        task_id=str(negative["id"]),
    )
    result = workflow(request, AgentContext(request=request))
    faith = checker.validate(
        result.markdown,
        result.citations,
        required_terms=["quarterly review"],
        unsupported_terms=[str(term) for term in negative["unsupported_terms"]],
    )
    _assert(not faith.valid, "unsupported claim unexpectedly passed")
    _assert(
        str(negative["expected_warning_code"]) in faith.warning_codes,
        f"unsupported claim did not produce {negative['expected_warning_code']}",
    )
    _assert(faith.unsupported_claims == ["same-day approval"], "unsupported claim term mismatch")
    return True


def _workflow(
    workflow: str,
    *,
    retriever: FixtureRetriever,
    model_gateway: ModelGateway,
):
    kwargs = {
        "retriever": retriever,
        "citation_checker": CitationChecker(),
        "model_gateway": model_gateway,
    }
    if workflow == "knowledge_qa":
        return KnowledgeQaWorkflow(**kwargs)
    if workflow == "policy_analysis":
        return PolicyAnalysisWorkflow(**kwargs)
    if workflow == "case_review":
        return CaseReviewWorkflow(**kwargs)
    raise SmokeError(f"unsupported workflow: {workflow}")


def _case_citations(case: dict[str, Any]) -> list[Citation]:
    evidence = normalize_evidence_results(_case_evidence(case), top_k=int(case["top_k"]))
    return [
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
                    "quality_fixture": "p3-m3-c4",
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


def _grounded_answer(
    workflow: str,
    required_terms: list[str],
    citations: list[Citation],
) -> str:
    heading = {
        "knowledge_qa": "## Direct Answer",
        "policy_analysis": "## Policy Analysis",
        "case_review": "## Case Review",
    }[workflow]
    lines = [heading, ""]
    for index, term in enumerate(required_terms, start=1):
        citation_index = min(index, len(citations))
        lines.append(f"- {term} is supported by evidence [{citation_index}].")
    return "\n".join(lines)


def _request(workflow: str, query: str, *, task_id: str) -> AgentRequest:
    return AgentRequest(
        task_id=task_id,
        conversation_id=f"conv-{task_id}",
        task_type=workflow,
        query_or_topic=query,
    )


def _negative_case(fixture: dict[str, Any], warning_code: str) -> dict[str, Any]:
    for case in fixture["negative_cases"]:
        if case.get("expected_warning_code") == warning_code:
            return case
    raise SmokeError(f"missing negative case for {warning_code}")


def _has_warning_code(result: Any, code: str) -> bool:
    content_codes = result.content.get("warning_codes")
    if isinstance(content_codes, list) and code in content_codes:
        return True
    return any(str(warning).startswith(f"{code}:") for warning in result.warnings)


def _assert_doc() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    for phrase in (
        "P3-M3-C4",
        "FaithfulnessChecker",
        "citation coverage",
        "unsupported claim",
        "NO_EVIDENCE",
        "knowledge_qa",
        "policy_analysis",
        "case_review",
    ):
        _assert(phrase in text, f"faithfulness doc missing phrase: {phrase}")


def _assert_no_sensitive_text(text: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        _assert(not pattern.search(text), f"{label} matched sensitive pattern: {pattern.pattern}")


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    _assert(isinstance(value, str) and value.strip(), f"missing string field: {key}")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
