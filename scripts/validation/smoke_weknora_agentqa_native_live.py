"""Live WF-P1-01 smoke for WeKnora native AgentQA through the PA adapter.

This smoke calls WeKnora native /api/v1/agent-chat/{session_id}, then stores the
answer in PA's task/output history model. If native AgentQA does not emit
traceable references, the smoke records an explicit citation blocker instead of
inventing citations.

The script never prints service tokens, provider payloads, raw prompts, raw
documents, logs, database paths, or full model answers.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.schemas import CitationRead  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402
from agent.schemas import Citation as AgentCitation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.citations import CitationBuilder  # noqa: E402
from knowledge_engine.errors import WeKnoraUnavailableError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the native AgentQA smoke cannot prove the declared contract."""


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    service_token: str
    workspace_id: str
    default_kb_id: str
    timeout_seconds: int
    knowledge_backend: str
    mock_mode: bool
    chat_provider: str
    mock_model_mode: bool
    embedding_provider: str
    agent_id: str
    query: str

    @classmethod
    def from_settings(cls) -> "SmokeConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            workspace_id=settings.weknora_workspace_id,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
            chat_provider=settings.chat_model_provider,
            mock_model_mode=settings.mock_model_mode,
            embedding_provider=settings.embedding_provider,
            agent_id=os.getenv("WEKNORA_AGENTQA_AGENT_ID", "builtin-wiki-researcher"),
            query=os.getenv(
                "WEKNORA_AGENTQA_SMOKE_QUERY",
                "用一句话回答：PA WF-P1-01 native AgentQA smoke 是否可运行？",
            ),
        )


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        result = _run_live_smoke(config)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native AgentQA smoke failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    print("WeKnora native AgentQA smoke passed (live)")
    print(f"- base URL: {config.base_url}")
    print(f"- knowledge base: {config.default_kb_id}")
    print(f"- agent id: {result['agent_id']}")
    print(f"- session created: {result['session_created']}")
    print(f"- answer stored: {result['answer_stored']}")
    print(f"- answer chars: {result['answer_chars']}")
    print(f"- native reference count: {result['native_reference_count']}")
    print(f"- saved citations: {result['saved_citations']}")
    print(f"- citation blocker: {result['citation_blocker']}")
    print(f"- event types: {','.join(result['event_types'])}")
    return 0


def _validate_config(config: SmokeConfig) -> None:
    missing: list[str] = []
    if config.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if config.mock_mode:
        missing.append("MOCK_MODE=false")
    if config.chat_provider.strip().lower() == "mock":
        missing.append("non-mock CHAT_MODEL_PROVIDER")
    if config.mock_model_mode:
        missing.append("MOCK_MODEL_MODE=false")
    if config.embedding_provider.strip().lower() == "mock":
        missing.append("non-mock EMBEDDING_PROVIDER")
    if not config.base_url:
        missing.append("WEKNORA_BASE_URL")
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if not config.service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not config.workspace_id:
        missing.append("WEKNORA_WORKSPACE_ID")
    if not config.default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if not config.agent_id:
        missing.append("WEKNORA_AGENTQA_AGENT_ID")
    if config.timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(config: SmokeConfig) -> dict[str, Any]:
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        timeout=config.timeout_seconds,
        workspace_id=config.workspace_id,
        default_kb_id=config.default_kb_id,
    )
    _assert_agent_available(backend, config.agent_id)
    session_id = backend.create_agent_session(
        title="PA WF-P1-01 native AgentQA smoke",
        description="sanitized live smoke",
    )
    agent_result = backend.run_agent_qa(
        session_id=session_id,
        query=config.query,
        agent_id=config.agent_id,
        knowledge_base_ids=[config.default_kb_id],
        disable_title=True,
    )
    if agent_result["errors"]:
        raise SmokeError("native AgentQA returned error events")
    answer = str(agent_result["answer"] or "").strip()
    if not answer:
        raise SmokeError("native AgentQA returned no answer text")

    bound_evidence = CitationBuilder().build_many(agent_result["evidence_items"])
    citations = [_to_agent_citation(evidence) for evidence in bound_evidence]
    citation_blocker = ""
    if citations:
        check = CitationChecker().validate(citations, evidence_items=bound_evidence)
        if not check.valid:
            raise SmokeError("native AgentQA citations failed traceability check")
    else:
        citation_blocker = (
            "CITATION_BLOCKED: native AgentQA returned a live answer but did not "
            "emit traceable references with source_type/evidence_id/native ids."
        )

    saved_count = _persist_pa_output(
        answer=answer,
        citations=citations,
        warnings=[citation_blocker] if citation_blocker else [],
        agent_result=agent_result,
    )
    return {
        "agent_id": config.agent_id,
        "session_created": bool(session_id),
        "answer_stored": True,
        "answer_chars": len(answer),
        "native_reference_count": agent_result["reference_count"],
        "saved_citations": saved_count,
        "citation_blocker": citation_blocker or "none",
        "event_types": sorted(agent_result["event_counts"].keys()),
    }


def _assert_agent_available(backend: WeKnoraApiBackend, agent_id: str) -> None:
    try:
        agents = backend.list_agents()
    except WeKnoraUnavailableError as exc:
        raise SmokeError(f"native custom Agent list unavailable: {exc.error_code}") from exc
    if not any(str(agent.get("id") or "") == agent_id for agent in agents):
        raise SmokeError(f"native custom Agent id is unavailable: {agent_id}")


def _to_agent_citation(evidence: Evidence) -> AgentCitation:
    return AgentCitation(
        title=evidence.title,
        text=evidence.text,
        source=evidence.source,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        score=evidence.score,
        metadata=evidence.metadata,
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type,
        wiki_page_id=evidence.wiki_page_id,
    )


def _persist_pa_output(
    answer: str,
    citations: list[AgentCitation],
    warnings: list[str],
    agent_result: dict[str, Any],
) -> int:
    with TemporaryDirectory(prefix="pa-weknora-agentqa-native-") as temp_dir:
        engine = create_engine(f"sqlite:///{Path(temp_dir) / 'agentqa_native.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            task = create_task(
                session=session,
                task_type="knowledge_qa",
                title="WF-P1-01 native AgentQA smoke",
                status="running",
                current_step="native_agentqa",
                progress=60,
            )
            output, saved = create_output_with_citations(
                session=session,
                task=task,
                title="WF-P1-01 native AgentQA smoke output",
                content_json=json.dumps(
                    {
                        "workflow": "native_agentqa",
                        "agent_id": agent_result["agent_id"],
                        "event_counts": agent_result["event_counts"],
                        "tool_names": agent_result["tool_names"],
                        "citation_blocker": warnings[0] if warnings else "",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                content_markdown=_short_answer(answer),
                warnings_json=json.dumps(warnings, ensure_ascii=False, sort_keys=True),
                status="completed",
                citations=[_citation_payload(citation) for citation in citations],
            )
            if output.status != "completed":
                raise SmokeError("PA output was not stored as completed")
            reads = [CitationRead.model_validate(citation) for citation in saved]
            for citation in reads:
                if citation.source != "weknora_api":
                    raise SmokeError("saved native AgentQA citation is not WeKnora-sourced")
                if not citation.evidence_id or not citation.source_type:
                    raise SmokeError("saved native AgentQA citation lost traceability fields")
            return len(saved)


def _citation_payload(citation: AgentCitation) -> dict[str, Any]:
    metadata = dict(citation.metadata)
    if citation.evidence_id:
        metadata.setdefault("evidence_id", citation.evidence_id)
    if citation.source_type:
        metadata.setdefault("citation_source_type", citation.source_type)
    if citation.wiki_page_id:
        metadata.setdefault("wiki_page_id", citation.wiki_page_id)
    return {
        "document_id": citation.document_id,
        "external_doc_id": citation.external_doc_id,
        "chunk_id": citation.chunk_id,
        "title": citation.title,
        "text": citation.text,
        "score": citation.score,
        "source": citation.source,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


def _short_answer(value: str, limit: int = 500) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password"):
        text = text.replace(marker, "[redacted]")
    if len(text) <= 240:
        return text
    return text[:237].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
