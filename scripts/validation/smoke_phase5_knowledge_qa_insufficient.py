"""Fixture smoke for P5-D3 knowledge_qa insufficient-evidence refusal.

The smoke covers P4Q-020 and P4Q-021. It simulates retrieval returning related
synthetic context, then verifies knowledge_qa refuses deterministically, keeps
support citations empty, and records that searched context is not supporting
evidence.
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
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentResult  # noqa: E402
from agent.schemas import AgentStatus  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from app import models as _models  # noqa: E402,F401
import app.services.analysis_service as analysis_service  # noqa: E402


QUESTIONS_PATH = (
    PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa" / "questions.json"
)
TARGET_IDS = ("P4Q-020", "P4Q-021")


class SmokeError(RuntimeError):
    """Raised when insufficient-evidence refusal expectations fail."""


class RelatedContextRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[Citation]:
        self.calls.append({"query": query, "filters": filters or {}, "top_k": top_k})
        return [
            Citation(
                title="Synthetic related policy context",
                text=(
                    "TEST-RAG-002 synthetic policy context mentions three working days, "
                    "but it does not mention real regulator hourly reporting or real customers."
                ),
                source="weknora_api",
                document_id="pa-doc-related",
                external_doc_id="wk-doc-related",
                chunk_id="chunk-related",
                score=0.86,
                evidence_id="document_chunk:chunk-related",
                source_type="document_chunk",
                metadata={
                    "anchor": "TEST-RAG-002",
                    "evidence_id": "document_chunk:chunk-related",
                    "citation_source_type": "document_chunk",
                },
            )
        ]


class FailingModelGateway:
    def generate(self, request):
        del request
        raise SmokeError("ModelGateway should not be called for forced no-answer QA")


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
            title="P5-D3 service fixture",
            content={"answer": "Fixture refusal."},
            markdown="Fixture refusal.",
            warnings=[],
            memory_updates=[],
        )


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 knowledge_qa insufficient smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 knowledge_qa insufficient smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    for qid in TARGET_IDS:
        print(
            f"- {qid}: citations={result[qid]['citation_count']}; "
            f"retrieved={result[qid]['retrieved_count']}; "
            f"codes={','.join(result[qid]['warning_codes'])}"
        )
    return 0


def _run_smoke() -> dict[str, dict[str, Any]]:
    _assert_analysis_service_contract()
    questions = _target_questions()
    retriever = RelatedContextRetriever()
    workflow = KnowledgeQaWorkflow(
        retriever=retriever,  # type: ignore[arg-type]
        model_gateway=FailingModelGateway(),  # type: ignore[arg-type]
        top_k=5,
    )

    results: dict[str, dict[str, Any]] = {}
    for question in questions:
        request = _request_from_question(question)
        result = workflow(request, AgentContext(request=request))
        markdown = result.markdown
        _assert(not result.citations, f"{question['id']} produced support citations")
        _assert(
            result.content.get("citation_count") == 0,
            f"{question['id']} citation_count should be zero",
        )
        _assert(
            result.content.get("retrieved_citation_count", 0) > 0,
            f"{question['id']} did not record searched context",
        )
        _assert("依据不足" in markdown, f"{question['id']} missing insufficient cue")
        _assert("不能" in markdown, f"{question['id']} missing refusal wording")
        _assert(
            "未作为事实结论的支持引用" in markdown,
            f"{question['id']} did not distinguish searched context from support",
        )
        _assert(
            "INSUFFICIENT_EVIDENCE_EXPECTED" in result.content.get("warning_codes", []),
            f"{question['id']} missing insufficient warning code",
        )
        _assert(
            result.content["model"].get("provider") == "deterministic",
            f"{question['id']} should use deterministic refusal policy",
        )
        if question["id"] == "P4Q-020":
            _assert(
                "真实监管要求" in markdown,
                "P4Q-020 did not explicitly refuse real regulator claim",
            )
        if question["id"] == "P4Q-021":
            _assert(
                "真实客户名称" in markdown and "合成脱敏文本" in markdown,
                "P4Q-021 did not explicitly refuse real customer claim",
            )
        results[question["id"]] = {
            "citation_count": len(result.citations),
            "retrieved_count": result.content.get("retrieved_citation_count", 0),
            "warning_codes": result.content.get("warning_codes", []),
        }

    _assert(len(retriever.calls) == len(TARGET_IDS), "unexpected retrieve call count")
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
                query_or_topic="P5-D3 service no-answer question",
                title="P5-D3 service no-answer",
                should_answer_insufficient=True,
            )
            task_input = json.loads(task.input_json or "{}")
    finally:
        analysis_service.AgentOrchestrator = original_orchestrator  # type: ignore[assignment]

    _assert(ServiceRecordingOrchestrator.requests, "service did not build AgentRequest")
    request = ServiceRecordingOrchestrator.requests[0]
    _assert(
        request.should_answer_insufficient is True,
        "should_answer_insufficient did not enter AgentRequest",
    )
    _assert(
        task_input.get("should_answer_insufficient") is True,
        "should_answer_insufficient missing from task input",
    )


def _target_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    by_id = {question["id"]: question for question in payload["questions"]}
    return [by_id[qid] for qid in TARGET_IDS]


def _request_from_question(question: dict[str, Any]) -> AgentRequest:
    return AgentRequest(
        task_id=f"task-{question['id']}",
        conversation_id="conv-p5d3",
        task_type="knowledge_qa",
        query_or_topic=str(question["query"]),
        retrieval_scope=str(question["retrieval_scope"]),
        should_answer_insufficient=bool(question["should_answer_insufficient"]),
        metadata={
            "question_id": question["id"],
            "should_answer_insufficient": bool(question["should_answer_insufficient"]),
        },
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
