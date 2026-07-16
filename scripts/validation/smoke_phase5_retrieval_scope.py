"""Fixture smoke for P5-D1 knowledge_qa retrieval_scope plumbing.

This smoke proves the official knowledge QA request accepts the simple
retrieval_scope values all/document/wiki, rejects invalid values, persists the
scope in task input, passes it into AgentRequest, and maps it to source_scope
inside KnowledgeQaWorkflow.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from pydantic import ValidationError
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
from agent.schemas import Citation as AgentCitation  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.schemas import AnalysisRunRequest  # noqa: E402
import app.services.analysis_service as analysis_service  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when retrieval_scope plumbing expectations fail."""


class RecordingOrchestrator:
    requests: list[AgentRequest] = []

    def run(self, request: AgentRequest, recent_messages: list[dict[str, Any]] | None = None):
        del recent_messages
        self.requests.append(request)
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.SUCCEEDED,
            title="P5-D1 retrieval_scope fixture",
            content={
                "answer": "Fixture answer.",
                "retrieval_scope": request.retrieval_scope,
            },
            markdown="Fixture answer.",
            warnings=[],
            memory_updates=[
                {
                    "role": "assistant",
                    "content": "Fixture answer.",
                    "metadata": {"retrieval_scope": request.retrieval_scope},
                }
            ],
        )


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> list[AgentCitation]:
        self.calls.append({"query": query, "filters": filters or {}, "top_k": top_k})
        return [
            AgentCitation(
                title="Fixture Document",
                text="Fixture document evidence for retrieval_scope.",
                source="weknora_api",
                document_id="doc-p5d1",
                external_doc_id="wk-doc-p5d1",
                chunk_id="chunk-p5d1",
                score=0.91,
                evidence_id="document_chunk:chunk-p5d1",
                source_type="document_chunk",
                metadata={"evidence_id": "document_chunk:chunk-p5d1"},
            )
        ]


class FixtureModelGateway:
    def generate(self, request):
        return ChatResponse(
            content="基于 [1] 回答。",
            model="fixture-model",
            provider="fixture",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            raw_metadata={"request_metadata": request.metadata},
        )


def main() -> int:
    original_orchestrator = analysis_service.AgentOrchestrator
    analysis_service.AgentOrchestrator = RecordingOrchestrator  # type: ignore[assignment]
    RecordingOrchestrator.requests = []
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 retrieval_scope smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        analysis_service.AgentOrchestrator = original_orchestrator  # type: ignore[assignment]

    print("Phase 5 retrieval_scope smoke passed (fixture)")
    print("- scope: fixture smoke only; this is not real WeKnora PASS")
    print(f"- default scope: {result['default_scope']}")
    print(f"- legal scopes: {', '.join(result['legal_scopes'])}")
    print(f"- rejected invalid scope: {result['invalid_rejected']}")
    print(f"- workflow source_scope: {result['workflow_source_scope']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    default_request = AnalysisRunRequest(query_or_topic="default scope question")
    _assert(default_request.retrieval_scope == "all", "default retrieval_scope is not all")

    legal_scopes = []
    for scope in ("all", "document", "wiki"):
        request = AnalysisRunRequest(query_or_topic=f"{scope} scope question", retrieval_scope=scope)
        _assert(request.retrieval_scope == scope, f"{scope} did not round-trip in schema")
        legal_scopes.append(request.retrieval_scope)

    try:
        AnalysisRunRequest(query_or_topic="bad scope", retrieval_scope="raw")
    except ValidationError:
        invalid_rejected = True
    else:
        raise SmokeError("invalid retrieval_scope unexpectedly passed schema validation")

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _, messages, default_task, _, _ = analysis_service.run_analysis(
            session=session,
            task_type="knowledge_qa",
            query_or_topic="default scope service question",
            title="P5-D1 default scope",
        )
        _, _, wiki_task, _, _ = analysis_service.run_analysis(
            session=session,
            task_type="knowledge_qa",
            query_or_topic="wiki scope service question",
            title="P5-D1 wiki scope",
            retrieval_scope="wiki",
        )
        default_input = json.loads(default_task.input_json or "{}")
        wiki_input = json.loads(wiki_task.input_json or "{}")
        user_metadata = json.loads(messages[0].metadata_json or "{}")

    _assert(len(RecordingOrchestrator.requests) == 2, "AgentRequest was not captured")
    _assert(
        RecordingOrchestrator.requests[0].retrieval_scope == "all",
        "default scope did not enter AgentRequest",
    )
    _assert(
        RecordingOrchestrator.requests[1].retrieval_scope == "wiki",
        "wiki scope did not enter AgentRequest",
    )

    _assert(default_input.get("retrieval_scope") == "all", "default task input missing all scope")
    _assert(wiki_input.get("retrieval_scope") == "wiki", "wiki task input missing wiki scope")

    _assert(
        user_metadata.get("retrieval_scope") == "all",
        "user message metadata missing retrieval_scope",
    )

    retriever = RecordingRetriever()
    workflow = KnowledgeQaWorkflow(
        retriever=retriever,  # type: ignore[arg-type]
        model_gateway=FixtureModelGateway(),  # type: ignore[arg-type]
        top_k=3,
    )
    workflow_request = AgentRequest(
        task_id="task-p5d1",
        conversation_id="conv-p5d1",
        task_type="knowledge_qa",
        query_or_topic="workflow wiki question",
        retrieval_scope="wiki",
    )
    result = workflow(workflow_request, AgentContext(request=workflow_request))
    _assert(result.content.get("retrieval_scope") == "wiki", "workflow result missing scope evidence")
    _assert(retriever.calls, "workflow did not call retriever")
    _assert(
        retriever.calls[0]["filters"].get("source_scope") == "wiki",
        "workflow did not map retrieval_scope to source_scope",
    )
    _assert(
        result.content["filters"].get("source_scope") == "wiki",
        "workflow result filters missing source_scope",
    )

    return {
        "default_scope": default_request.retrieval_scope,
        "legal_scopes": legal_scopes,
        "invalid_rejected": invalid_rejected,
        "workflow_source_scope": retriever.calls[0]["filters"]["source_scope"],
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
