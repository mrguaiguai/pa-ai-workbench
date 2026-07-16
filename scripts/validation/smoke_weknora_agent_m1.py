"""Live M1 smoke for PA Agent workflows with WeKnora evidence.

This smoke intentionally requires a real WeKnora service. It runs PA's
run_analysis service for QA, policy, and case workflows, then verifies each
workflow persists non-mock WeKnora citations. It also runs a scoped no-evidence
QA case and verifies the Agent emits an evidence warning.

Required environment:
    KNOWLEDGE_BACKEND=weknora_api
    MOCK_MODE=false
    WEKNORA_BASE_URL=...
    WEKNORA_SERVICE_TOKEN=...
    WEKNORA_DEFAULT_KB_ID=...

Optional query overrides:
    WEKNORA_AGENT_SMOKE_QA_QUERY
    WEKNORA_AGENT_SMOKE_POLICY_QUERY
    WEKNORA_AGENT_SMOKE_CASE_QUERY

The chat model defaults to the local mock provider unless the operator has
configured a real provider. This smoke focuses on citation/status behavior, not
model prose.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from app.config import get_settings  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the live Agent smoke fails."""


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    service_token: str
    default_kb_id: str
    timeout_seconds: int
    knowledge_backend: str
    mock_mode: bool
    qa_query: str
    policy_query: str
    case_query: str

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
            qa_query=_str_env(
                "WEKNORA_AGENT_SMOKE_QA_QUERY",
                "PA M1 smoke knowledge QA evidence",
            ),
            policy_query=_str_env(
                "WEKNORA_AGENT_SMOKE_POLICY_QUERY",
                "PA M1 smoke policy analysis evidence",
            ),
            case_query=_str_env(
                "WEKNORA_AGENT_SMOKE_CASE_QUERY",
                "PA M1 smoke case review evidence",
            ),
        )


WORKFLOW_RUNS = (
    ("knowledge_qa", "qa_query", "Knowledge QA"),
    ("policy_analysis", "policy_query", "Policy Analysis"),
    ("case_review", "case_query", "Case Review"),
)


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        _set_model_defaults()
        get_settings.cache_clear()
        with TemporaryDirectory(prefix="pa-weknora-agent-smoke-") as temp_dir:
            result = _run_live_smoke(config=config, temp_dir=Path(temp_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Agent E2E smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora Agent E2E smoke passed (live)")
    print(f"- base URL: {config.base_url}")
    print(f"- knowledge base: {config.default_kb_id}")
    for workflow in result["workflows"]:
        print(
            "- {task_type}: citations={citation_count}, "
            "sources={sources}, source_types={source_types}".format(**workflow)
        )
    print(f"- no evidence warning: {result['no_evidence_warning']}")
    return 0


def _validate_config(config: SmokeConfig) -> None:
    missing = []
    if config.knowledge_backend.strip().lower() != "weknora_api":
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if config.mock_mode:
        missing.append("MOCK_MODE=false")
    if not config.base_url:
        missing.append("WEKNORA_BASE_URL")
    if not config.service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not config.default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if config.timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _set_model_defaults() -> None:
    os.environ.setdefault("CHAT_MODEL_PROVIDER", "mock")
    os.environ.setdefault("CHAT_MODEL_NAME", "mock-chat")
    os.environ.setdefault("MOCK_MODEL_MODE", "true")


def _run_live_smoke(config: SmokeConfig, temp_dir: Path) -> dict[str, Any]:
    import app.models  # noqa: F401
    from sqlmodel import Session
    from sqlmodel import SQLModel
    from sqlmodel import create_engine

    engine = create_engine(f"sqlite:///{temp_dir / 'agent_smoke.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        workflow_results = [
            _run_workflow(session=session, config=config, task_type=task_type, query_attr=query_attr)
            for task_type, query_attr, _label in WORKFLOW_RUNS
        ]
        no_evidence_warning = _run_no_evidence_case(session=session)
    return {
        "workflows": workflow_results,
        "no_evidence_warning": no_evidence_warning,
    }


def _run_workflow(
    session: Any,
    config: SmokeConfig,
    task_type: str,
    query_attr: str,
) -> dict[str, Any]:
    from app.schemas import CitationRead
    from app.services.analysis_service import run_analysis

    query = getattr(config, query_attr)
    _conversation, _messages, task, output, citations = run_analysis(
        session=session,
        task_type=task_type,
        query_or_topic=query,
        title=f"P3-M1-F3 {task_type} live smoke",
        business_area="public_affairs",
        extra_requirements="Use only retrieved WeKnora evidence and cite every factual claim.",
    )
    if task.status != "completed":
        raise SmokeError(f"{task_type} task did not complete: {task.status}")
    if output.status != "completed":
        raise SmokeError(f"{task_type} output did not complete: {output.status}")

    reads = [CitationRead.model_validate(citation) for citation in citations]
    if not reads:
        raise SmokeError(f"{task_type} returned no citations")
    for citation in reads:
        _assert_real_weknora_citation(task_type=task_type, citation=citation)
    warnings = _json_list(output.warnings_json)
    blocking_warnings = [
        warning
        for warning in warnings
        if not str(warning).startswith("WEAK_EVIDENCE:")
    ]
    if blocking_warnings:
        raise SmokeError(
            f"{task_type} returned blocking warnings despite citations: {blocking_warnings}"
        )
    return {
        "task_type": task_type,
        "citation_count": len(reads),
        "sources": ",".join(sorted({citation.source for citation in reads})),
        "source_types": ",".join(
            sorted({str(citation.source_type or "unknown") for citation in reads})
        ),
    }


def _run_no_evidence_case(session: Any) -> str:
    from app.services.analysis_service import run_analysis

    _conversation, _messages, task, output, citations = run_analysis(
        session=session,
        task_type="knowledge_qa",
        query_or_topic="P3-M1-F3 no evidence scoped query",
        title="P3-M1-F3 no evidence live smoke",
        document_ids=["pa-m1-f3-nonexistent-document-id"],
        extra_requirements="This scoped smoke should not use evidence outside document_ids.",
    )
    if task.status != "completed":
        raise SmokeError(f"no-evidence task did not complete: {task.status}")
    if citations:
        raise SmokeError("no-evidence scoped run unexpectedly persisted citations")
    warnings = _json_list(output.warnings_json)
    matching = [
        warning
        for warning in warnings
        if "No evidence" in warning or "No evidence was found" in warning
    ]
    if not matching:
        raise SmokeError(f"no-evidence run did not emit expected warning: {warnings}")
    return matching[0]


def _assert_real_weknora_citation(task_type: str, citation: Any) -> None:
    if citation.source != "weknora_api":
        raise SmokeError(f"{task_type} returned non-WeKnora citation: {citation.source}")
    if not citation.evidence_id:
        raise SmokeError(f"{task_type} citation is missing evidence_id")
    if citation.source_type not in {"document_chunk", "wiki_page"}:
        raise SmokeError(f"{task_type} citation has invalid source_type: {citation.source_type}")
    if not citation.title.strip() or not citation.text.strip():
        raise SmokeError(f"{task_type} citation is missing title/text")
    if citation.source_type == "document_chunk":
        if not citation.chunk_id:
            raise SmokeError(f"{task_type} document citation is missing chunk_id")
        if not citation.document_id and not citation.external_doc_id:
            raise SmokeError(f"{task_type} document citation is missing document id")
    if citation.source_type == "wiki_page" and not citation.wiki_page_id:
        raise SmokeError(f"{task_type} wiki citation is missing wiki_page_id")


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _str_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


if __name__ == "__main__":
    raise SystemExit(main())
