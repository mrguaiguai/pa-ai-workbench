"""Fixture smoke for P3-M2-A4 Agent evidence quality policy.

The smoke runs Agent workflows directly with a fake retriever and mock chat
provider. It does not read .env, call live WeKnora, or print long evidence text.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.agents.case_agent import CaseReviewWorkflow  # noqa: E402
from agent.agents.policy_agent import PolicyAnalysisWorkflow  # noqa: E402
from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.model_gateway.providers.mock import MockChatProvider  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from agent.tools import CitationChecker  # noqa: E402


class FakeRetriever:
    def __init__(self, citations: list[Citation]) -> None:
        self.citations = citations

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[Citation]:
        return self.citations[: top_k or len(self.citations)]


def main() -> int:
    checker = CitationChecker()
    _assert_no_evidence(checker)
    _assert_weak_evidence(checker)
    _assert_source_type_mismatch()
    _assert_malformed_citation_dropped()
    print(
        "Agent evidence policy M2 smoke passed "
        "(no evidence, weak evidence, source mismatch, malformed citation drop)"
    )
    return 0


def _assert_no_evidence(checker: CitationChecker) -> None:
    request = _request("knowledge_qa", "no evidence scoped query")
    workflow = KnowledgeQaWorkflow(
        retriever=FakeRetriever([]),
        citation_checker=checker,
        model_gateway=MockChatProvider(),
    )
    result = workflow(request, AgentContext(request=request))
    _assert(not result.citations, "no evidence run produced citations")
    _assert(_has_code(result, "NO_EVIDENCE"), "no evidence warning code missing")
    _assert("依据不足" in result.markdown, "no evidence markdown missing")


def _assert_weak_evidence(checker: CitationChecker) -> None:
    weak = _document_citation(score=0.1)
    request = _request("policy_analysis", "weak evidence policy fixture")
    workflow = PolicyAnalysisWorkflow(
        retriever=FakeRetriever([weak]),
        citation_checker=checker,
        model_gateway=MockChatProvider(),
    )
    result = workflow(request, AgentContext(request=request))
    _assert(len(result.citations) == 1, "weak evidence citation was dropped")
    _assert(_has_code(result, "WEAK_EVIDENCE"), "weak evidence warning code missing")
    _assert("低置信 evidence" in result.markdown, "weak evidence markdown missing")
    check = checker.validate(result.citations, evidence_items=result.citations)
    _assert(check.valid, f"weak evidence citation failed CitationChecker: {check.warnings}")


def _assert_source_type_mismatch() -> None:
    document = _document_citation(score=0.8)
    request = _request(
        "case_review",
        "source mismatch case fixture",
        metadata={"expected_source_type": "wiki_page"},
    )
    workflow = CaseReviewWorkflow(
        retriever=FakeRetriever([document]),
        citation_checker=CitationChecker(),
        model_gateway=MockChatProvider(),
    )
    result = workflow(request, AgentContext(request=request))
    _assert(not result.citations, "source mismatch citation was not filtered")
    _assert(_has_code(result, "SOURCE_TYPE_MISMATCH"), "source mismatch code missing")
    _assert(_has_code(result, "NO_EVIDENCE"), "source mismatch no-evidence code missing")
    _assert("依据不足" in result.markdown, "source mismatch markdown not fail-closed")


def _assert_malformed_citation_dropped() -> None:
    malformed = Citation(
        title="Malformed WeKnora citation",
        text="Malformed fixture excerpt.",
        source="weknora_api",
        document_id="doc-fixture",
        external_doc_id="wk-doc-fixture",
        chunk_id=None,
        score=0.9,
        evidence_id="document_chunk:wk-chunk-fixture",
        source_type="document_chunk",
        metadata={"citation_source_type": "document_chunk"},
    )
    request = _request("knowledge_qa", "malformed citation fixture")
    workflow = KnowledgeQaWorkflow(
        retriever=FakeRetriever([malformed]),
        citation_checker=CitationChecker(),
        model_gateway=MockChatProvider(),
    )
    result = workflow(request, AgentContext(request=request))
    _assert(not result.citations, "malformed citation was not dropped")
    _assert(_has_code(result, "CITATION_DROPPED"), "dropped citation code missing")
    _assert(_has_code(result, "NO_EVIDENCE"), "dropped citation no-evidence code missing")


def _document_citation(score: float) -> Citation:
    return Citation(
        title="Synthetic policy fixture",
        text="Synthetic public affairs evidence for a fixture-only workflow.",
        source="weknora_api",
        document_id=None,
        external_doc_id="wk-doc-fixture",
        chunk_id="wk-chunk-fixture",
        score=score,
        evidence_id="document_chunk:wk-chunk-fixture",
        source_type="document_chunk",
        metadata={
            "evidence_id": "document_chunk:wk-chunk-fixture",
            "citation_source_type": "document_chunk",
        },
    )


def _request(
    task_type: str,
    query: str,
    metadata: dict[str, Any] | None = None,
) -> AgentRequest:
    return AgentRequest(
        task_id=f"task-{task_type}",
        conversation_id=f"conv-{task_type}",
        task_type=task_type,
        query_or_topic=query,
        metadata=metadata or {},
    )


def _has_code(result, code: str) -> bool:
    content_codes = result.content.get("warning_codes")
    if isinstance(content_codes, list) and code in content_codes:
        return True
    return any(str(warning).startswith(f"{code}:") for warning in result.warnings)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
