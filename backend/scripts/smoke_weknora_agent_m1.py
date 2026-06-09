"""Smoke-check Agent RetrieverTool with WeKnora evidence.

This fixture smoke covers P3-M1-D1. It verifies that a normal Agent workflow
can use ``RetrieverTool`` with ``KNOWLEDGE_BACKEND=weknora_api`` and receive
traceable, non-mock citations without changing workflow business logic.

The script uses sanitized fixture responses and does not require a live
WeKnora service, secrets, uploads, databases, or real pilot documents.
"""

from __future__ import annotations

from pathlib import Path
import os
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "weknora_api"
    os.environ["WEKNORA_BASE_URL"] = "fixture://weknora"
    os.environ["WEKNORA_SERVICE_TOKEN"] = "fixture-token"
    os.environ["WEKNORA_DEFAULT_KB_ID"] = "kb-agent-fixture"
    os.environ["MOCK_MODE"] = "false"
    os.environ["CHAT_MODEL_PROVIDER"] = "mock"
    os.environ["CHAT_MODEL_NAME"] = "mock-chat"
    os.environ["CHAT_MODEL_API_KEY"] = ""
    os.environ["MOCK_MODEL_MODE"] = "true"


_set_smoke_env()

from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentTaskType  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the WeKnora Agent fixture contract fails."""


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Agent smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora Agent smoke passed (fixture)")
    print(f"- request path: {result['path']}")
    print(f"- backend: {result['backend']}")
    print(f"- citations: {result['citation_count']}")
    print(f"- sources: {', '.join(result['sources'])}")
    print(f"- source types: {', '.join(result['source_types'])}")
    print(f"- evidence ids: {', '.join(result['evidence_ids'])}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    original_request_json = WeKnoraApiBackend._request_json

    def fixture_request_json(
        self: WeKnoraApiBackend,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict:
        requests.append(
            {
                "backend": self.__class__.__name__,
                "method": method,
                "path": path,
                "payload": payload,
            }
        )
        if method != "POST" or path != "/api/v1/knowledge-search":
            raise SmokeError(f"unexpected WeKnora request: {method} {path}")
        return {
            "success": True,
            "data": [
                {
                    "id": "chunk-agent-001",
                    "content": (
                        "Sanitized WeKnora document evidence for the Agent "
                        "retriever smoke."
                    ),
                    "knowledge_id": "wk-agent-doc-001",
                    "knowledge_base_id": "kb-agent-fixture",
                    "knowledge_title": "Agent Fixture Document",
                    "chunk_index": 1,
                    "score": 0.041,
                    "match_type": 2,
                    "chunk_type": "text",
                    "metadata": {"business_area": "public_affairs"},
                },
                {
                    "source_type": "wiki_page",
                    "wiki_page_id": "wiki-agent-page-001",
                    "wiki_title": "Agent Fixture Wiki",
                    "content": (
                        "Sanitized WeKnora wiki evidence for the Agent "
                        "retriever smoke."
                    ),
                    "knowledge_base_id": "kb-agent-fixture",
                    "score": 0.063,
                    "metadata": {
                        "slug": "agent-fixture-wiki",
                        "business_area": "public_affairs",
                    },
                },
            ],
        }

    WeKnoraApiBackend._request_json = fixture_request_json
    try:
        workflow = KnowledgeQaWorkflow()
        request = AgentRequest(
            task_id="smoke-weknora-agent-m1",
            conversation_id="smoke-conversation",
            task_type=AgentTaskType.KNOWLEDGE_QA,
            query_or_topic="What does the sanitized WeKnora fixture say?",
            business_area="public_affairs",
            extra_requirements="Use only retrieved WeKnora evidence.",
        )
        result = workflow(request, AgentContext(request=request))
    finally:
        WeKnoraApiBackend._request_json = original_request_json

    if len(requests) != 1:
        raise SmokeError(f"expected one retrieve request, got {len(requests)}")
    retrieve_request = requests[0]
    payload = retrieve_request["payload"]
    if not isinstance(payload, dict):
        raise SmokeError("missing WeKnora retrieve payload")
    if payload.get("query") != "What does the sanitized WeKnora fixture say?":
        raise SmokeError(f"query was not mapped to WeKnora payload: {payload}")
    if payload.get("knowledge_base_ids") != ["kb-agent-fixture"]:
        raise SmokeError(f"default KB id was not mapped: {payload}")
    if result.content.get("citation_count") != 2:
        raise SmokeError(f"unexpected citation_count: {result.content}")
    if result.warnings:
        raise SmokeError("expected no citation warnings: " + "; ".join(result.warnings))

    citations = result.citations
    if len(citations) != 2:
        raise SmokeError(f"expected 2 citations, got {len(citations)}")
    if {citation.source for citation in citations} != {"weknora_api"}:
        raise SmokeError("Agent returned non-WeKnora citations")

    source_types = {citation.source_type for citation in citations}
    if source_types != {"document_chunk", "wiki_page"}:
        raise SmokeError(f"unexpected source types: {source_types}")
    for citation in citations:
        if not citation.evidence_id:
            raise SmokeError("citation is missing evidence_id")
        if not citation.title.strip() or not citation.text.strip():
            raise SmokeError("citation is missing title/text")
        if citation.source_type == "document_chunk":
            if citation.chunk_id != "chunk-agent-001":
                raise SmokeError(f"unexpected chunk_id: {citation.chunk_id}")
            if citation.external_doc_id != "wk-agent-doc-001":
                raise SmokeError(f"unexpected external_doc_id: {citation.external_doc_id}")
        if citation.source_type == "wiki_page" and (
            citation.wiki_page_id != "wiki-agent-page-001"
        ):
            raise SmokeError(f"unexpected wiki_page_id: {citation.wiki_page_id}")

    return {
        "path": retrieve_request["path"],
        "backend": retrieve_request["backend"],
        "citation_count": len(citations),
        "sources": sorted({citation.source for citation in citations}),
        "source_types": sorted(str(citation.source_type) for citation in citations),
        "evidence_ids": sorted(str(citation.evidence_id) for citation in citations),
    }


if __name__ == "__main__":
    raise SystemExit(main())
