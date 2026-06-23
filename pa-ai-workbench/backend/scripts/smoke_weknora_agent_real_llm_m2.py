"""Live P3-M2-A5 smoke for Agent real LLM + WeKnora citations.

Side effects:
- uploads one tiny sanitized Markdown document to the configured WeKnora KB;
- runs QA, policy, and case workflows through PA analysis_service;
- calls the configured real chat model through ModelGateway.

The script never prints API keys, full prompts, document bodies, or chunks.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from typing import Any
from uuid import uuid4

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.schemas import CitationRead  # noqa: E402
from app.services.analysis_service import run_analysis  # noqa: E402
from agent.schemas import Citation as AgentCitation  # noqa: E402
from agent.tools import CitationChecker  # noqa: E402
from agent.tools import RetrieverTool  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402


TERMINAL_INDEXED_STATUSES = {"indexed"}
TERMINAL_FAILED_STATUSES = {"failed"}
PROGRESS_STATUSES = {"uploaded", "parsing", "chunking", "indexing", "unknown"}


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    service_token: str
    default_kb_id: str
    timeout_seconds: int
    knowledge_backend: str
    mock_mode: bool
    chat_provider: str
    mock_model_mode: bool
    chat_base_url: str
    chat_api_key: str
    chat_model_name: str
    wait_seconds: int
    poll_seconds: int

    @classmethod
    def from_settings(cls) -> "SmokeConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
            chat_provider=settings.chat_model_provider,
            mock_model_mode=settings.mock_model_mode,
            chat_base_url=settings.chat_model_base_url,
            chat_api_key=settings.chat_model_api_key,
            chat_model_name=settings.chat_model_name,
            wait_seconds=_int_env("WEKNORA_AGENT_REAL_LLM_WAIT_SECONDS", 180),
            poll_seconds=_int_env("WEKNORA_AGENT_REAL_LLM_POLL_SECONDS", 5),
        )


class SmokeError(RuntimeError):
    """Raised when the live real-LLM Agent smoke fails."""


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        get_settings.cache_clear()
        with TemporaryDirectory(prefix="pa-m2-agent-real-llm-") as temp_dir:
            result = _run_live_smoke(config=config, temp_dir=Path(temp_dir))
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"decision": "FAIL", "reason": _safe_reason(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "decision": "PASS",
                "side_effect": "uploaded one sanitized Markdown fixture to WeKnora",
                "knowledge_base": config.default_kb_id,
                "external_doc_id": result["external_doc_id"],
                "workflows": result["workflows"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _validate_config(config: SmokeConfig) -> None:
    missing: list[str] = []
    if config.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if config.mock_mode:
        missing.append("MOCK_MODE=false")
    if config.chat_provider.strip().lower() != "openai_compatible":
        missing.append("CHAT_MODEL_PROVIDER=openai_compatible")
    if config.mock_model_mode:
        missing.append("MOCK_MODEL_MODE=false")
    if not config.chat_base_url:
        missing.append("CHAT_MODEL_BASE_URL")
    if not config.chat_api_key:
        missing.append("CHAT_MODEL_API_KEY")
    if not config.chat_model_name:
        missing.append("CHAT_MODEL_NAME")
    if "deepseek" not in config.chat_model_name.strip().lower():
        missing.append("CHAT_MODEL_NAME must be a DeepSeek model")
    if not config.base_url:
        missing.append("WEKNORA_BASE_URL")
    if not config.service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not config.default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(config: SmokeConfig, temp_dir: Path) -> dict[str, Any]:
    run_id = uuid4().hex[:12]
    anchor = f"pam2realagent{run_id}"
    fixture_path = temp_dir / "pa_m2_agent_real_llm_fixture.md"
    _write_fixture(fixture_path, anchor)
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        timeout=config.timeout_seconds,
        default_kb_id=config.default_kb_id,
    )
    external_doc_id = _upload_fixture(backend, fixture_path, anchor)
    _wait_until_indexed(backend, external_doc_id, config)
    scoped_query = f"{anchor} PA M2 Real LLM Agent Fixture synthetic policy checklist escalation handoff"
    _wait_for_scoped_retrieve(backend, external_doc_id, scoped_query, config)
    _wait_for_agent_retriever(external_doc_id, scoped_query, config)

    engine = create_engine(f"sqlite:///{temp_dir / 'agent_real_llm.db'}")
    SQLModel.metadata.create_all(engine)
    workflows: list[dict[str, Any]] = []
    with Session(engine) as session:
        for task_type, query in (
            ("knowledge_qa", scoped_query),
            ("policy_analysis", scoped_query),
            ("case_review", scoped_query),
        ):
            workflows.append(
                _run_workflow(
                    session=session,
                    task_type=task_type,
                    query=query,
                    external_doc_id=external_doc_id,
                    expected_model=config.chat_model_name,
                )
            )
    return {"external_doc_id": external_doc_id, "workflows": workflows}


def _write_fixture(path: Path, anchor: str) -> None:
    path.write_text(
        "\n".join(
            [
                "# PA M2 Real LLM Agent Fixture",
                "",
                f"Anchor: {anchor}.",
                "The synthetic response window is two business days.",
                "The synthetic policy checklist requires an owner, evidence list, and review date.",
                "The synthetic case review says the escalation handoff must be logged before closure.",
            ]
        ),
        encoding="utf-8",
    )


def _upload_fixture(backend: WeKnoraApiBackend, fixture_path: Path, anchor: str) -> str:
    try:
        document = backend.upload_document(
            str(fixture_path),
            metadata={
                "document_id": f"pa-m2-agent-real-llm-{anchor}",
                "title": "PA M2 Real LLM Agent Fixture",
                "business_area": "public_affairs",
                "document_type": "m2_real_llm_smoke",
                "source": "p3_m2_a5_smoke",
                "file_name": fixture_path.name,
                "smoke_fixture": "sanitized",
            },
        )
    except KnowledgeBackendUnavailableError as exc:
        raise SmokeError(f"WeKnora fixture upload failed: {exc}") from exc
    if not document.external_doc_id:
        raise SmokeError("WeKnora fixture upload returned no external_doc_id")
    return document.external_doc_id


def _wait_for_scoped_retrieve(
    backend: WeKnoraApiBackend,
    external_doc_id: str,
    query: str,
    config: SmokeConfig,
) -> None:
    deadline = time.monotonic() + config.wait_seconds
    last_count = 0
    while time.monotonic() <= deadline:
        try:
            evidence_items = backend.retrieve(
                query=query,
                filters={
                    "knowledge_base_ids": [config.default_kb_id],
                    "document_ids": [external_doc_id],
                },
                top_k=5,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise SmokeError(f"WeKnora scoped retrieve failed: {exc}") from exc
        last_count = len(evidence_items)
        if any(evidence.external_doc_id == external_doc_id for evidence in evidence_items):
            return
        time.sleep(config.poll_seconds)
    raise SmokeError(
        "WeKnora scoped retrieve did not return the uploaded fixture "
        f"within {config.wait_seconds}s (last evidence count: {last_count})"
    )


def _wait_for_agent_retriever(
    external_doc_id: str,
    query: str,
    config: SmokeConfig,
) -> None:
    retriever = RetrieverTool()
    deadline = time.monotonic() + config.wait_seconds
    last_count = 0
    while time.monotonic() <= deadline:
        citations = retriever.retrieve(
            query=query,
            filters={
                "document_ids": [external_doc_id],
                "business_area": "public_affairs",
                "document_type": "m2_real_llm_smoke",
            },
            top_k=5,
        )
        last_count = len(citations)
        if any(citation.external_doc_id == external_doc_id for citation in citations):
            return
        time.sleep(config.poll_seconds)
    raise SmokeError(
        "Agent RetrieverTool did not return the uploaded fixture "
        f"within {config.wait_seconds}s (last citation count: {last_count})"
    )


def _wait_until_indexed(
    backend: WeKnoraApiBackend,
    external_doc_id: str,
    config: SmokeConfig,
) -> None:
    deadline = time.monotonic() + config.wait_seconds
    last_status = "unknown"
    while time.monotonic() <= deadline:
        status_payload = backend.get_document_status(external_doc_id)
        last_status = str(status_payload.get("status") or "unknown")
        if last_status in TERMINAL_INDEXED_STATUSES:
            return
        if last_status in TERMINAL_FAILED_STATUSES:
            detail = status_payload.get("error_message") or status_payload.get("failed_step")
            raise SmokeError(f"WeKnora fixture indexing failed: {detail}")
        if last_status not in PROGRESS_STATUSES:
            raise SmokeError(f"unexpected fixture indexing status: {last_status}")
        time.sleep(config.poll_seconds)
    raise SmokeError(f"fixture did not index within {config.wait_seconds}s: {last_status}")


def _run_workflow(
    session: Session,
    task_type: str,
    query: str,
    external_doc_id: str,
    expected_model: str,
) -> dict[str, Any]:
    _conversation, _messages, task, output, citations = run_analysis(
        session=session,
        task_type=task_type,
        query_or_topic=query,
        title=f"P3-M2-A5 {task_type} real LLM smoke",
        business_area="public_affairs",
        document_type="m2_real_llm_smoke",
        document_ids=[external_doc_id],
        extra_requirements="Use only the scoped sanitized fixture evidence.",
    )
    if task.status != "completed" or output.status != "completed":
        raise SmokeError(f"{task_type} did not complete")
    content = _json_object(output.content_json)
    model = content.get("model") if isinstance(content.get("model"), dict) else {}
    if model.get("provider") != "openai_compatible":
        raise SmokeError(f"{task_type} did not use openai_compatible provider")
    if "deepseek" not in str(model.get("model") or expected_model).lower():
        raise SmokeError(f"{task_type} did not record DeepSeek model")
    warning_codes = set(content.get("warning_codes") or [])
    if warning_codes - {"WEAK_EVIDENCE"}:
        filters = content.get("filters") if isinstance(content.get("filters"), dict) else {}
        raise SmokeError(
            f"{task_type} returned blocking warning codes: {sorted(warning_codes)} "
            f"(accepted={content.get('citation_count')}, "
            f"retrieved={content.get('retrieved_citation_count')}, "
            f"filter_keys={sorted(filters.keys())})"
        )
    reads = [CitationRead.model_validate(citation) for citation in citations]
    if not reads:
        raise SmokeError(f"{task_type} persisted no citations")
    agent_citations = []
    for citation in reads:
        _assert_weknora_citation(task_type, citation, external_doc_id)
        agent_citations.append(
            AgentCitation(
                title=citation.title,
                text=citation.text,
                source=citation.source,
                document_id=citation.document_id,
                external_doc_id=citation.external_doc_id,
                chunk_id=citation.chunk_id,
                score=citation.score,
                evidence_id=citation.evidence_id,
                source_type=citation.source_type,
                wiki_page_id=citation.wiki_page_id,
                metadata=_json_object(citation.metadata_json),
            )
        )
    check = CitationChecker().validate(agent_citations, evidence_items=agent_citations)
    if not check.valid:
        raise SmokeError(f"{task_type} citations failed CitationChecker: {check.warnings}")
    return {
        "task_type": task_type,
        "provider": model.get("provider"),
        "model": model.get("model"),
        "citation_count": len(reads),
        "warning_codes": sorted(warning_codes),
    }


def _assert_weknora_citation(task_type: str, citation: CitationRead, external_doc_id: str) -> None:
    if citation.source != "weknora_api":
        raise SmokeError(f"{task_type} citation source is not WeKnora")
    if citation.source_type != "document_chunk":
        raise SmokeError(f"{task_type} citation source_type is not document_chunk")
    if citation.external_doc_id != external_doc_id:
        raise SmokeError(f"{task_type} citation was not scoped to fixture document")
    if not citation.evidence_id or not citation.chunk_id:
        raise SmokeError(f"{task_type} citation lacks trace fields")


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _int_env(name: str, default: int) -> int:
    try:
        return max(int(__import__("os").getenv(name, str(default))), 1)
    except ValueError:
        return default


def _safe_reason(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    for marker in ("Authorization", "Bearer", "api_key", "token", "secret", "password"):
        text = text.replace(marker, "[redacted]")
    return " ".join(text.split())[:300]


if __name__ == "__main__":
    raise SystemExit(main())
