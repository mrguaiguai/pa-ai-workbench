"""Fixture smoke for P5-D2 knowledge_qa current-run and source_type strategy.

This smoke covers the four Phase 4 questions named by P5-D2:
- P4Q-001 document-only
- P4Q-013 all-source document + Wiki
- P4Q-017 wiki-only
- P4Q-019 wiki-only source_type traceability

It uses synthetic citations only. The result is an offline contract check, not
real WeKnora PASS.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel import Session
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.model_gateway import ChatResponse  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentResult  # noqa: E402
from agent.schemas import AgentStatus  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from app import models as _models  # noqa: E402,F401
import app.services.analysis_service as analysis_service  # noqa: E402


QUESTIONS_PATH = (
    PROJECT_ROOT / "backend" / "fixtures" / "phase4_rag_wiki_qa" / "questions.json"
)
TARGET_IDS = ("P4Q-001", "P4Q-013", "P4Q-017", "P4Q-019")
CURRENT_RUN = {
    "run_id": "p5d2-current-run",
    "corpus_id": "phase4_rag_wiki_qa_v1",
    "namespace": "p5d2-current-run",
    "external_doc_ids": ["wk-doc-rag-001", "wk-doc-rag-003", "wk-doc-rag-004"],
    "wiki_page_ids": ["wiki-page-001", "phase5/wiki-current"],
    "anchors": ["TEST-RAG-001", "TEST-RAG-003", "TEST-RAG-004", "TEST-WIKI-001"],
}


class SmokeError(RuntimeError):
    """Raised when knowledge_qa scope strategy expectations fail."""


class FixtureRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[Citation]:
        filters = filters or {}
        self.calls.append({"query": query, "filters": filters, "top_k": top_k})
        if filters.get("source_scope") == "wiki":
            return [
                _current_wiki("TEST-WIKI-001"),
                _historical_wiki(),
                _current_document("TEST-RAG-001", "wk-doc-rag-001"),
            ]
        if filters.get("source_scope") == "document":
            return [
                _current_document("TEST-RAG-001", "wk-doc-rag-001"),
                _historical_document("TEST-RAG-001"),
                _current_wiki("TEST-WIKI-001"),
            ]
        return [
            _current_wiki("TEST-WIKI-001"),
            _current_document("TEST-RAG-003", "wk-doc-rag-003"),
            _current_document("TEST-RAG-004", "wk-doc-rag-004"),
            _historical_wiki(),
            _historical_document("TEST-RAG-003"),
        ]


class FixtureModelGateway:
    def __init__(self) -> None:
        self.metadata: list[dict[str, Any]] = []

    def generate(self, request):
        self.metadata.append(request.metadata)
        return ChatResponse(
            content="基于当前验收语料回答，并使用 [1] 引用。",
            model="fixture-model",
            provider="fixture",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
        )


class ServiceRecordingOrchestrator:
    requests: list[AgentRequest] = []

    def run(self, request: AgentRequest, recent_messages: list[dict[str, Any]] | None = None):
        del recent_messages
        self.requests.append(request)
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.SUCCEEDED,
            title="P5-D2 service fixture",
            content={"answer": "Fixture answer."},
            markdown="Fixture answer.",
            warnings=[],
            memory_updates=[],
        )


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 knowledge_qa scope strategy smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 knowledge_qa scope strategy smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    for qid in TARGET_IDS:
        details = result[qid]
        print(
            f"- {qid}: scope={details['scope']}; "
            f"source_types={','.join(details['source_types'])}; "
            f"citations={details['citation_count']}"
        )
    return 0


def _run_smoke() -> dict[str, dict[str, Any]]:
    _assert_analysis_service_contract()
    questions = _target_questions()
    retriever = FixtureRetriever()
    model_gateway = FixtureModelGateway()
    workflow = KnowledgeQaWorkflow(
        retriever=retriever,  # type: ignore[arg-type]
        model_gateway=model_gateway,  # type: ignore[arg-type]
        top_k=5,
    )

    results: dict[str, dict[str, Any]] = {}
    for question in questions:
        request = _request_from_question(question)
        result = workflow(request, AgentContext(request=request))
        citations = result.citations
        source_types = sorted({citation.source_type for citation in citations})
        expected_source_types = sorted(question["expected_source_types"])
        _assert(
            source_types == expected_source_types,
            f"{question['id']} source types mismatch: {source_types} != {expected_source_types}",
        )
        _assert(
            all(_is_current_run_citation(citation) for citation in citations),
            f"{question['id']} kept out-of-scope citation",
        )
        if question["retrieval_scope"] == "document":
            _assert(
                all(citation.source_type == "document_chunk" for citation in citations),
                f"{question['id']} document scope kept non-document citation",
            )
        if question["retrieval_scope"] == "wiki":
            _assert(
                all(citation.source_type == "wiki_page" for citation in citations),
                f"{question['id']} wiki scope kept non-wiki citation",
            )
        if question["id"] == "P4Q-013":
            _assert(
                {"document_chunk", "wiki_page"} == set(source_types),
                "P4Q-013 did not keep mixed document/wiki citations",
            )
        _assert(
            result.content["filters"].get("current_run") == CURRENT_RUN,
            f"{question['id']} current_run missing from workflow filters",
        )
        _assert(
            result.content["filters"].get("source_scope") == question["retrieval_scope"],
            f"{question['id']} source_scope missing from workflow filters",
        )
        results[question["id"]] = {
            "scope": question["retrieval_scope"],
            "source_types": source_types,
            "citation_count": len(citations),
            "warnings": result.warnings,
        }

    _assert(len(retriever.calls) == len(TARGET_IDS), "unexpected retry or missing retrieve call")
    for call in retriever.calls:
        _assert(call["filters"].get("current_run") == CURRENT_RUN, "current_run not forwarded")
    _assert(
        all("expected_source_types" in metadata for metadata in model_gateway.metadata),
        "model metadata did not include expected_source_types",
    )
    return results


def _assert_analysis_service_contract() -> None:
    original_orchestrator = analysis_service.AgentOrchestrator
    analysis_service.AgentOrchestrator = ServiceRecordingOrchestrator  # type: ignore[assignment]
    ServiceRecordingOrchestrator.requests = []
    try:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            _, _, task, _, _ = analysis_service.run_analysis(
                session=session,
                task_type="knowledge_qa",
                query_or_topic="P5-D2 service scope question",
                title="P5-D2 service scope",
                retrieval_scope="wiki",
                current_run=CURRENT_RUN,
                expected_source_types=["wiki_page"],
            )
            task_input = json.loads(task.input_json or "{}")
    finally:
        analysis_service.AgentOrchestrator = original_orchestrator  # type: ignore[assignment]

    _assert(ServiceRecordingOrchestrator.requests, "service did not build AgentRequest")
    request = ServiceRecordingOrchestrator.requests[0]
    _assert(request.current_run == CURRENT_RUN, "current_run did not enter AgentRequest")
    _assert(
        request.expected_source_types == ["wiki_page"],
        "expected_source_types did not enter AgentRequest",
    )
    _assert(task_input.get("current_run") == CURRENT_RUN, "current_run missing from task input")
    _assert(
        task_input.get("expected_source_types") == ["wiki_page"],
        "expected_source_types missing from task input",
    )


def _target_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    by_id = {question["id"]: question for question in payload["questions"]}
    return [by_id[qid] for qid in TARGET_IDS]


def _request_from_question(question: dict[str, Any]) -> AgentRequest:
    return AgentRequest(
        task_id=f"task-{question['id']}",
        conversation_id="conv-p5d2",
        task_type="knowledge_qa",
        query_or_topic=str(question["query"]),
        retrieval_scope=str(question["retrieval_scope"]),
        current_run=CURRENT_RUN,
        expected_source_types=list(question["expected_source_types"]),
        metadata={
            "question_id": question["id"],
            "expected_source_types": list(question["expected_source_types"]),
        },
    )


def _current_document(anchor: str, external_doc_id: str) -> Citation:
    chunk_id = f"chunk-{external_doc_id}"
    return Citation(
        title=f"Current document {anchor}",
        text=f"{anchor} current-run document evidence.",
        source="weknora_api",
        document_id=f"pa-{external_doc_id}",
        external_doc_id=external_doc_id,
        chunk_id=chunk_id,
        score=0.91,
        evidence_id=f"document_chunk:{chunk_id}",
        source_type="document_chunk",
        metadata={
            "anchor": anchor,
            "corpus_id": "phase4_rag_wiki_qa_v1",
            "current_run_id": "p5d2-current-run",
            "evidence_id": f"document_chunk:{chunk_id}",
        },
    )


def _historical_document(anchor: str) -> Citation:
    return Citation(
        title=f"Historical document {anchor}",
        text=f"{anchor} historical document evidence from an old run.",
        source="weknora_api",
        document_id="pa-old-doc",
        external_doc_id="wk-old-doc",
        chunk_id="chunk-old-doc",
        score=0.89,
        evidence_id="document_chunk:chunk-old-doc",
        source_type="document_chunk",
        metadata={"anchor": anchor, "evidence_id": "document_chunk:chunk-old-doc"},
    )


def _current_wiki(anchor: str) -> Citation:
    return Citation(
        title=f"Current wiki {anchor}",
        text=f"{anchor} current-run wiki evidence.",
        source="weknora_api",
        wiki_page_id="wiki-page-001",
        score=0.93,
        evidence_id="wiki_page:wiki-page-001",
        source_type="wiki_page",
        metadata={
            "anchor": anchor,
            "slug": "phase5/wiki-current",
            "wiki_page_id": "wiki-page-001",
            "corpus_id": "phase4_rag_wiki_qa_v1",
            "current_run_id": "p5d2-current-run",
            "evidence_id": "wiki_page:wiki-page-001",
        },
    )


def _historical_wiki() -> Citation:
    return Citation(
        title="Historical wiki TEST-WIKI-001",
        text="TEST-WIKI-001 historical wiki evidence from an old run.",
        source="weknora_api",
        wiki_page_id="wiki-old-001",
        score=0.9,
        evidence_id="wiki_page:wiki-old-001",
        source_type="wiki_page",
        metadata={
            "anchor": "TEST-WIKI-001",
            "slug": "phase5/wiki-old",
            "wiki_page_id": "wiki-old-001",
            "evidence_id": "wiki_page:wiki-old-001",
        },
    )


def _is_current_run_citation(citation: Citation) -> bool:
    return (
        citation.external_doc_id in set(CURRENT_RUN["external_doc_ids"])
        or citation.wiki_page_id in set(CURRENT_RUN["wiki_page_ids"])
        or citation.metadata.get("slug") in set(CURRENT_RUN["wiki_page_ids"])
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
