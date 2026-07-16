"""Fixture smoke for P5-D4 knowledge_qa distractor and version-conflict strategy.

The smoke covers:
- P4Q-022: policy answer must not cite TEST-DISTRACTOR-001.
- P4Q-024: version-conflict answer cites old and new policy evidence and
  prioritizes the newer three-working-day rule.

It uses synthetic citations only and is not real WeKnora PASS.
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
from agent.model_gateway import ChatResponse  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentResult  # noqa: E402
from agent.schemas import AgentStatus  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from app import models as _models  # noqa: E402,F401
import app.services.analysis_service as analysis_service  # noqa: E402


QUESTIONS_PATH = (
    PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa" / "questions.json"
)
TARGET_IDS = ("P4Q-022", "P4Q-024")


class SmokeError(RuntimeError):
    """Raised when trust-strategy expectations fail."""


class TrustRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[Citation]:
        self.calls.append({"query": query, "filters": filters or {}, "top_k": top_k})
        if "活动排版日期" in query:
            return [_new_policy(), _distractor(), _old_policy()]
        if "旧版五个工作日" in query and "新版三个工作日" in query:
            return [_old_policy(), _new_policy()]
        return [_new_policy()]


class TrustModelGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate(self, request):
        self.calls.append(request.metadata)
        return ChatResponse(
            content="新版政策要求普通事项三个工作日内完成初稿，不引用活动排期材料。",
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
            title="P5-D4 service fixture",
            content={"answer": "Fixture trust answer."},
            markdown="Fixture trust answer.",
            warnings=[],
            memory_updates=[],
        )


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 knowledge_qa trust strategy smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Phase 5 knowledge_qa trust strategy smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- P4Q-022 citations: {','.join(result['P4Q-022']['anchors'])}")
    print(f"- P4Q-024 citations: {','.join(result['P4Q-024']['anchors'])}")
    print(f"- P4Q-024 deterministic model: {result['P4Q-024']['model']}")
    return 0


def _run_smoke() -> dict[str, dict[str, Any]]:
    _assert_analysis_service_contract()
    questions = _target_questions()
    retriever = TrustRetriever()
    model_gateway = TrustModelGateway()
    workflow = KnowledgeQaWorkflow(
        retriever=retriever,  # type: ignore[arg-type]
        model_gateway=model_gateway,  # type: ignore[arg-type]
        top_k=5,
    )

    results: dict[str, dict[str, Any]] = {}
    for question in questions:
        request = _request_from_question(question)
        result = workflow(request, AgentContext(request=request))
        anchors = sorted(_anchors(result.citations))
        if question["id"] == "P4Q-022":
            _assert("TEST-RAG-002" in anchors, "P4Q-022 lost new-policy citation")
            _assert(
                "TEST-DISTRACTOR-001" not in anchors,
                "P4Q-022 kept forbidden distractor citation",
            )
            _assert("三个工作日" in result.markdown, "P4Q-022 did not answer new rule")
            _assert(
                "FORBIDDEN_ANCHOR_DROPPED" in result.content.get("warning_codes", []),
                "P4Q-022 did not record forbidden-anchor drop",
            )
            _assert(
                result.content["model"].get("model") == "distractor_suppression_policy",
                "P4Q-022 did not use deterministic distractor policy",
            )
        if question["id"] == "P4Q-024":
            _assert(
                {"TEST-RAG-001", "TEST-RAG-002"}.issubset(set(anchors)),
                f"P4Q-024 missing old/new citations: {anchors}",
            )
            _assert("新版三个工作日" in result.markdown, "P4Q-024 did not prioritize new rule")
            _assert("旧版" in result.markdown and "五个工作日" in result.markdown, "P4Q-024 did not explain old rule")
            _assert(
                result.content["model"].get("model") == "version_conflict_policy",
                "P4Q-024 did not use deterministic version-conflict policy",
            )
        results[question["id"]] = {
            "anchors": anchors,
            "model": result.content["model"].get("model"),
        }

    _assert(len(model_gateway.calls) == 0, "trust policy answers should not call model")
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
                query_or_topic="P5-D4 service trust question",
                title="P5-D4 service trust",
                forbidden_anchors=["TEST-DISTRACTOR-001"],
                question_type="distractor_suppression",
            )
            task_input = json.loads(task.input_json or "{}")
    finally:
        analysis_service.AgentOrchestrator = original_orchestrator  # type: ignore[assignment]

    _assert(ServiceRecordingOrchestrator.requests, "service did not build AgentRequest")
    request = ServiceRecordingOrchestrator.requests[0]
    _assert(
        request.forbidden_anchors == ["TEST-DISTRACTOR-001"],
        "forbidden_anchors did not enter AgentRequest",
    )
    _assert(request.question_type == "distractor_suppression", "question_type did not enter AgentRequest")
    _assert(
        task_input.get("forbidden_anchors") == ["TEST-DISTRACTOR-001"],
        "forbidden_anchors missing from task input",
    )
    _assert(
        task_input.get("question_type") == "distractor_suppression",
        "question_type missing from task input",
    )


def _target_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    by_id = {question["id"]: question for question in payload["questions"]}
    return [by_id[qid] for qid in TARGET_IDS]


def _request_from_question(question: dict[str, Any]) -> AgentRequest:
    return AgentRequest(
        task_id=f"task-{question['id']}",
        conversation_id="conv-p5d4",
        task_type="knowledge_qa",
        query_or_topic=str(question["query"]),
        retrieval_scope=str(question["retrieval_scope"]),
        expected_source_types=list(question["expected_source_types"]),
        forbidden_anchors=list(question.get("forbidden_anchors") or []),
        question_type=str(question["type"]),
        metadata={
            "question_id": question["id"],
            "question_type": question["type"],
            "forbidden_anchors": list(question.get("forbidden_anchors") or []),
        },
    )


def _old_policy() -> Citation:
    return Citation(
        title="旧版专项信息报送时限政策",
        text="TEST-RAG-001：旧版 2024-03-18 要求普通专项信息五个工作日内完成初稿。",
        source="weknora_api",
        document_id="pa-doc-old-policy",
        external_doc_id="wk-doc-old-policy",
        chunk_id="chunk-old-policy",
        score=0.84,
        evidence_id="document_chunk:chunk-old-policy",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-001", "evidence_id": "document_chunk:chunk-old-policy"},
    )


def _new_policy() -> Citation:
    return Citation(
        title="新版专项信息报送时限政策",
        text="TEST-RAG-002：新版 2025-02-10 要求普通专项信息三个工作日内完成初稿，第四个工作日前完成复核。",
        source="weknora_api",
        document_id="pa-doc-new-policy",
        external_doc_id="wk-doc-new-policy",
        chunk_id="chunk-new-policy",
        score=0.93,
        evidence_id="document_chunk:chunk-new-policy",
        source_type="document_chunk",
        metadata={"anchor": "TEST-RAG-002", "evidence_id": "document_chunk:chunk-new-policy"},
    )


def _distractor() -> Citation:
    return Citation(
        title="活动排期与材料准备提醒",
        text="TEST-DISTRACTOR-001：培训演示材料在 2025-04-03 完成排版，活动讲师使用该材料。",
        source="weknora_api",
        document_id="pa-doc-distractor",
        external_doc_id="wk-doc-distractor",
        chunk_id="chunk-distractor",
        score=0.91,
        evidence_id="document_chunk:chunk-distractor",
        source_type="document_chunk",
        metadata={
            "anchor": "TEST-DISTRACTOR-001",
            "evidence_id": "document_chunk:chunk-distractor",
        },
    )


def _anchors(citations: list[Citation]) -> set[str]:
    anchors: set[str] = set()
    for citation in citations:
        for value in (citation.title, citation.text, citation.metadata.get("anchor")):
            text = str(value or "")
            for anchor in ("TEST-RAG-001", "TEST-RAG-002", "TEST-DISTRACTOR-001"):
                if anchor in text:
                    anchors.add(anchor)
    return anchors


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
