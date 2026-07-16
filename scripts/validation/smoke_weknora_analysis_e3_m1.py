"""Smoke-check M1 AnalysisPage citation contract for Real WeKnora RAG.

This fixture smoke covers P3-M1-E3:
- run_analysis returns non-mock WeKnora document/wiki citations;
- CitationRead hydrates evidence_id/source_type/wiki_page_id for frontend display;
- warnings remain available for AnalysisPage WarningList.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

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


from agent.schemas import AgentResult  # noqa: E402
from agent.schemas import AgentStatus  # noqa: E402
from agent.schemas import Citation as AgentCitation  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.schemas import AnalysisRunResponse  # noqa: E402
from app.schemas import CitationRead  # noqa: E402
from app.schemas import ConversationMessageRead  # noqa: E402
from app.schemas import ConversationRead  # noqa: E402
from app.schemas import GeneratedOutputRead  # noqa: E402
from app.schemas import TaskRead  # noqa: E402
import app.services.analysis_service as analysis_service  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the WeKnora analysis display contract fails."""


class FixtureOrchestrator:
    def run(self, request, recent_messages):
        del recent_messages
        return AgentResult(
            task_id=request.task_id,
            conversation_id=request.conversation_id,
            task_type=request.task_type,
            status=AgentStatus.SUCCEEDED,
            title="E3 Real WeKnora RAG fixture",
            content={
                "answer": "Fixture answer grounded in WeKnora document and wiki evidence.",
                "evidence_mode": "weknora_api",
            },
            markdown=(
                "Fixture answer grounded in Real WeKnora RAG.\n\n"
                "- Uses document_chunk evidence.\n"
                "- Uses wiki_page evidence."
            ),
            citations=[
                AgentCitation(
                    title="Fixture Document Chunk",
                    text="Document chunk evidence from WeKnora.",
                    source="weknora_api",
                    document_id="doc-e3-fixture",
                    external_doc_id="wk-doc-e3",
                    chunk_id="wk-chunk-e3",
                    score=0.91,
                    evidence_id="document_chunk:wk-chunk-e3",
                    source_type="document_chunk",
                    metadata={
                        "evidence_id": "document_chunk:wk-chunk-e3",
                        "citation_source_type": "document_chunk",
                        "source": "weknora_api",
                    },
                ),
                AgentCitation(
                    title="Fixture Wiki Page",
                    text="Wiki page evidence from WeKnora.",
                    source="weknora_api",
                    wiki_page_id="wiki-e3-fixture",
                    score=0.87,
                    evidence_id="wiki_page:wiki-e3-fixture",
                    source_type="wiki_page",
                    metadata={
                        "evidence_id": "wiki_page:wiki-e3-fixture",
                        "citation_source_type": "wiki_page",
                        "wiki_page_id": "wiki-e3-fixture",
                        "source": "weknora_api",
                    },
                ),
            ],
            warnings=["Fixture warning for WarningList visibility."],
            memory_updates=[
                {
                    "role": "assistant",
                    "content": "Fixture answer grounded in Real WeKnora RAG.",
                    "metadata": {"source": "fixture"},
                }
            ],
        )


def main() -> int:
    original_orchestrator = analysis_service.AgentOrchestrator
    analysis_service.AgentOrchestrator = FixtureOrchestrator  # type: ignore[assignment]
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora analysis E3 smoke failed: {exc}", file=sys.stderr)
        return 1
    finally:
        analysis_service.AgentOrchestrator = original_orchestrator  # type: ignore[assignment]

    print("WeKnora analysis E3 smoke passed (fixture)")
    print(f"- rag mode: {result['rag_mode']}")
    print(f"- document citations: {result['document_count']}")
    print(f"- wiki citations: {result['wiki_count']}")
    print(f"- warnings: {result['warning_count']}")
    return 0


def _run_fixture_smoke() -> dict[str, int | str]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        conversation, messages, task, output, citations = analysis_service.run_analysis(
            session=session,
            task_type="knowledge_qa",
            query_or_topic="E3 fixture question",
            title="E3 fixture analysis",
        )
        response = AnalysisRunResponse(
            conversation=ConversationRead.model_validate(conversation),
            messages=[ConversationMessageRead.model_validate(message) for message in messages],
            task=TaskRead.model_validate(task),
            output=GeneratedOutputRead.model_validate(output),
            citations=[CitationRead.model_validate(citation) for citation in citations],
        )

    if response.task.status != "completed":
        raise SmokeError(f"analysis task did not complete: {response.task.status}")
    if len(response.citations) != 2:
        raise SmokeError(f"expected 2 citations, got {len(response.citations)}")
    if not all(citation.source == "weknora_api" for citation in response.citations):
        raise SmokeError("non-mock citations were not marked as WeKnora")

    source_types = {citation.source_type for citation in response.citations}
    if source_types != {"document_chunk", "wiki_page"}:
        raise SmokeError(f"unexpected source types: {source_types}")
    evidence_ids = {citation.evidence_id for citation in response.citations}
    if evidence_ids != {"document_chunk:wk-chunk-e3", "wiki_page:wiki-e3-fixture"}:
        raise SmokeError(f"unexpected evidence ids: {evidence_ids}")
    if not any(citation.wiki_page_id == "wiki-e3-fixture" for citation in response.citations):
        raise SmokeError("wiki citation did not expose wiki_page_id")

    warning_count = len(json.loads(response.output.warnings_json or "[]"))
    if "Fixture warning" not in (response.output.warnings_json or ""):
        raise SmokeError("warning JSON missing fixture warning")

    return {
        "rag_mode": "Real WeKnora RAG",
        "document_count": sum(
            1 for citation in response.citations if citation.source_type == "document_chunk"
        ),
        "wiki_count": sum(1 for citation in response.citations if citation.source_type == "wiki_page"),
        "warning_count": warning_count,
    }


if __name__ == "__main__":
    raise SystemExit(main())
