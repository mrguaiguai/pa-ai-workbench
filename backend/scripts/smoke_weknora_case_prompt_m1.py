"""Smoke-check case workflow grounding with WeKnora evidence.

This fixture smoke covers P3-M1-D4:
- case prompt requires numbered citations for facts/timeline claims;
- run_analysis persists case output with WeKnora document/wiki citations;
- no-evidence case review returns explicit insufficient-evidence wording and a
  to-collect materials list.

The script uses sanitized fixture responses and an in-memory database. It does
not require live WeKnora, secrets, uploads, backend/data, or real documents.
"""

from __future__ import annotations

import json
from pathlib import Path
import os
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


def _set_smoke_env() -> None:
    os.environ["KNOWLEDGE_BACKEND"] = "weknora_api"
    os.environ["WEKNORA_BASE_URL"] = "fixture://weknora"
    os.environ["WEKNORA_SERVICE_TOKEN"] = "fixture-token"
    os.environ["WEKNORA_DEFAULT_KB_ID"] = "kb-case-fixture"
    os.environ["MOCK_MODE"] = "false"
    os.environ["CHAT_MODEL_PROVIDER"] = "mock"
    os.environ["CHAT_MODEL_NAME"] = "mock-chat"
    os.environ["CHAT_MODEL_API_KEY"] = ""
    os.environ["MOCK_MODEL_MODE"] = "true"


_set_smoke_env()

from agent.agents.case_agent import CaseReviewWorkflow  # noqa: E402
from agent.context import AgentContext  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentTaskType  # noqa: E402
from agent.schemas import Citation as AgentCitation  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.services.analysis_service import run_analysis  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the case prompt fixture contract fails."""


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora case prompt smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora case prompt smoke passed (fixture)")
    print(f"- prompt checks: {result['prompt_checks']}")
    print(f"- evidence citations: {result['evidence_citations']}")
    print(f"- evidence mode: {result['evidence_mode']}")
    print(f"- source types: {', '.join(result['source_types'])}")
    print(f"- no-evidence warnings: {result['no_evidence_warnings']}")
    print(f"- request count: {result['request_count']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    _assert_prompt_contract()
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
        query = str((payload or {}).get("query") or "")
        if "no evidence" in query.lower():
            return {"success": True, "data": []}
        return {
            "success": True,
            "data": [
                {
                    "id": "chunk-case-301",
                    "content": (
                        "Sanitized case evidence records a delayed first reply, "
                        "unclear owner handoff, and missing follow-up log."
                    ),
                    "knowledge_id": "wk-case-doc-301",
                    "knowledge_base_id": "kb-case-fixture",
                    "knowledge_title": "Case Fixture Document",
                    "chunk_index": 5,
                    "score": 0.044,
                    "match_type": 2,
                    "chunk_type": "text",
                    "metadata": {"business_area": "public_affairs"},
                },
                {
                    "source_type": "wiki_page",
                    "wiki_page_id": "wiki-case-402",
                    "wiki_title": "Case Fixture Wiki",
                    "content": (
                        "Sanitized wiki evidence says escalation reviews should "
                        "capture the final stakeholder acknowledgement."
                    ),
                    "knowledge_base_id": "kb-case-fixture",
                    "score": 0.061,
                    "metadata": {
                        "slug": "case-fixture-wiki",
                        "business_area": "public_affairs",
                    },
                },
            ],
        }

    WeKnoraApiBackend._request_json = fixture_request_json
    try:
        smoke_result = _assert_run_analysis_contract()
    finally:
        WeKnoraApiBackend._request_json = original_request_json

    smoke_result["prompt_checks"] = 2
    smoke_result["request_count"] = len(requests)
    if len(requests) != 2:
        raise SmokeError(f"expected two retrieve requests, got {len(requests)}")
    for request in requests:
        payload = request["payload"]
        if not isinstance(payload, dict):
            raise SmokeError("missing WeKnora retrieve payload")
        if payload.get("knowledge_base_ids") != ["kb-case-fixture"]:
            raise SmokeError(f"default KB id was not mapped: {payload}")
    return smoke_result


def _assert_prompt_contract() -> None:
    request = AgentRequest(
        task_id="case-prompt-unit",
        conversation_id="case-prompt-conversation",
        task_type=AgentTaskType.CASE_REVIEW,
        query_or_topic="Review a sanitized escalation case.",
    )
    citation = AgentCitation(
        evidence_id="document_chunk:chunk-case-301",
        source_type="document_chunk",
        external_doc_id="wk-case-doc-301",
        chunk_id="chunk-case-301",
        title="Case Fixture Document",
        text="Sanitized case prompt evidence.",
        score=0.044,
        source="weknora_api",
        metadata={},
    )
    prompt = CaseReviewWorkflow._build_grounded_prompt(
        request,
        AgentContext(request=request),
        [citation],
    )
    required_fragments = [
        "[1]",
        "evidence_id=document_chunk:chunk-case-301",
        "source_type=document_chunk",
        "相关事实或时间线",
        "建议补充核查",
        "证据缺口",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in prompt]
    if missing:
        raise SmokeError("case prompt missing fragments: " + ", ".join(missing))

    no_evidence_prompt = CaseReviewWorkflow._build_grounded_prompt(
        request,
        AgentContext(request=request),
        [],
    )
    if "未检索到可用案例、文档或 Wiki 证据" not in no_evidence_prompt:
        raise SmokeError("case prompt does not state no-evidence condition")


def _assert_run_analysis_contract() -> dict[str, Any]:
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _, _, evidence_task, evidence_output, evidence_citations = run_analysis(
            session=session,
            task_type=AgentTaskType.CASE_REVIEW,
            query_or_topic="Review a sanitized escalation case.",
            title="D4 Case Evidence Smoke",
            business_area="public_affairs",
            extra_requirements="Use numbered citations for every case fact.",
        )
        if evidence_task.status != "completed":
            raise SmokeError(f"evidence task failed: {evidence_task.status}")
        if len(evidence_citations) != 2:
            raise SmokeError(f"expected two saved citations, got {len(evidence_citations)}")
        source_types = set()
        for citation in evidence_citations:
            metadata = _json_object(citation.metadata_json)
            source_type = metadata.get("citation_source_type")
            source_types.add(str(source_type))
            if citation.source != "weknora_api":
                raise SmokeError(f"unexpected citation source: {citation.source}")
            if not metadata.get("evidence_id"):
                raise SmokeError(f"citation missing evidence_id: {metadata}")
        if source_types != {"document_chunk", "wiki_page"}:
            raise SmokeError(f"unexpected source types: {source_types}")
        required_markdown = [
            "## 事实与引用",
            "## 待补材料与不确定性",
            "[1]",
            "[2]",
            "evidence_id=document_chunk:chunk-case-301",
            "evidence_id=wiki_page:wiki-case-402",
        ]
        missing_markdown = [
            fragment
            for fragment in required_markdown
            if fragment not in evidence_output.content_markdown
        ]
        if missing_markdown:
            raise SmokeError("case output missing fragments: " + ", ".join(missing_markdown))
        evidence_content = _json_object(evidence_output.content_json)
        if evidence_content.get("citation_count") != 2:
            raise SmokeError(f"unexpected evidence content: {evidence_content}")
        model_metadata = evidence_content.get("model") or {}
        if model_metadata.get("evidence_mode") != "weknora_api":
            raise SmokeError(f"unexpected model metadata: {model_metadata}")

        _, _, no_evidence_task, no_evidence_output, no_evidence_citations = run_analysis(
            session=session,
            task_type=AgentTaskType.CASE_REVIEW,
            query_or_topic="no evidence case topic",
            title="D4 Case No Evidence Smoke",
            business_area="public_affairs",
            extra_requirements="Do not invent case details.",
        )
        if no_evidence_task.status != "completed":
            raise SmokeError(f"no-evidence task failed: {no_evidence_task.status}")
        if no_evidence_citations:
            raise SmokeError("no-evidence run unexpectedly saved citations")
        no_evidence_markdown = no_evidence_output.content_markdown
        if "## 依据不足" not in no_evidence_markdown:
            raise SmokeError("no-evidence output missing insufficient-evidence heading")
        if "## 待补材料" not in no_evidence_markdown:
            raise SmokeError("no-evidence output missing to-collect materials list")
        warnings = _json_array(no_evidence_output.warnings_json)
        if not any("No case evidence" in warning for warning in warnings):
            raise SmokeError(f"no-evidence warning missing: {warnings}")
        no_evidence_content = _json_object(no_evidence_output.content_json)
        no_evidence_model = no_evidence_content.get("model") or {}
        if no_evidence_model.get("evidence_mode") != "no_evidence":
            raise SmokeError(f"unexpected no-evidence model metadata: {no_evidence_model}")

    return {
        "evidence_citations": len(evidence_citations),
        "evidence_mode": model_metadata["evidence_mode"],
        "source_types": sorted(source_types),
        "no_evidence_warnings": len(warnings),
    }


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    data = json.loads(value)
    if not isinstance(data, dict):
        raise SmokeError(f"expected JSON object, got {type(data).__name__}")
    return data


def _json_array(value: str | None) -> list[Any]:
    if not value:
        return []
    data = json.loads(value)
    if not isinstance(data, list):
        raise SmokeError(f"expected JSON array, got {type(data).__name__}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
