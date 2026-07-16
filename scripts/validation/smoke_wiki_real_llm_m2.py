"""Live P3-M2-A5 smoke for Wiki real LLM draft + WeKnora retrieval.

Side effects:
- uploads one tiny sanitized Markdown document to the configured WeKnora KB;
- runs one scoped QA analysis through the real Agent/ModelGateway path;
- creates and publishes one PA Wiki page drafted by the real chat model;
- polls WeKnora until retrieval returns source_type=wiki_page evidence.

The script never prints API keys, full prompts, document bodies, chunks, or
model response text.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
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
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app import models as _models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.schemas import WikiDraftFromOutputRequest  # noqa: E402
from app.services.analysis_service import run_analysis  # noqa: E402
from app.services.wiki_service import create_wiki_draft_from_output  # noqa: E402
from app.services.wiki_service import page_metadata  # noqa: E402
from app.services.wiki_service import publish_wiki_page_record  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


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
            wait_seconds=_int_env("WEKNORA_WIKI_REAL_LLM_WAIT_SECONDS", 180),
            poll_seconds=_int_env("WEKNORA_WIKI_REAL_LLM_POLL_SECONDS", 5),
        )


class SmokeError(RuntimeError):
    """Raised when the live Wiki real-LLM smoke fails."""


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        get_settings.cache_clear()
        with TemporaryDirectory(prefix="pa-m2-wiki-real-llm-") as temp_dir:
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
                "side_effects": [
                    "uploaded one sanitized Markdown fixture to WeKnora",
                    "created and published one generated PA Wiki page",
                    "polled WeKnora retrieval for wiki_page evidence",
                ],
                "knowledge_base": config.default_kb_id,
                "external_doc_id": result["external_doc_id"],
                "slug": result["slug"],
                "draft_provider": result["draft_provider"],
                "draft_model": result["draft_model"],
                "wiki_evidence_id": result["wiki_evidence_id"],
                "wiki_page_id": result["wiki_page_id"],
                "source": result["source"],
                "source_type": result["source_type"],
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
    anchor = f"pam2realwiki{run_id}"
    slug = f"pa-smoke/m2-real-wiki-{run_id}"
    title = f"PA M2 Real Wiki {anchor}"
    fixture_path = temp_dir / "pa_m2_wiki_real_llm_fixture.md"
    _write_fixture(fixture_path, anchor)
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        timeout=config.timeout_seconds,
        default_kb_id=config.default_kb_id,
    )
    external_doc_id = _upload_fixture(backend, fixture_path, anchor)
    _wait_until_indexed(backend, external_doc_id, config)
    _wait_for_scoped_retrieve(backend, external_doc_id, anchor, config)

    engine = create_engine(f"sqlite:///{temp_dir / 'wiki_real_llm.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _conversation, _messages, task, output, citations = run_analysis(
            session=session,
            task_type="knowledge_qa",
            query_or_topic=f"{anchor} wiki briefing",
            title=f"P3-M2-A5 Wiki real LLM smoke {anchor}",
            business_area="public_affairs",
            document_type="m2_real_llm_smoke",
            document_ids=[external_doc_id],
            extra_requirements="Use only the scoped sanitized fixture evidence.",
        )
        if task.status != "completed" or output.status != "completed":
            raise SmokeError("source QA analysis did not complete")
        if not citations:
            raise SmokeError("source QA analysis persisted no citations")
        _assert_source_output(output.content_json, expected_model=config.chat_model_name)

        draft = create_wiki_draft_from_output(
            session=session,
            output_id=output.id,
            payload=WikiDraftFromOutputRequest(
                slug=slug,
                title=title,
                tags=["smoke", "m2-real-llm"],
                business_area="public_affairs",
                page_type="knowledge_qa",
                created_by="p3_m2_a5_smoke",
                metadata={
                    "kb_id": config.default_kb_id,
                    "smoke_task": "P3-M2-A5",
                    "smoke_fixture": "sanitized",
                    "retrieval_anchor": anchor,
                },
            ),
        )
        metadata = page_metadata(draft)
        _assert_real_draft_metadata(metadata, expected_model=config.chat_model_name)
        published = publish_wiki_page_record(session=session, slug=draft.slug)
        published_metadata = page_metadata(published)
        if str(published_metadata.get("weknora_sync_status") or "") != "synced":
            raise SmokeError("published Wiki page did not sync to WeKnora")
        evidence = _wait_for_wiki_evidence(
            backend=backend,
            slug=published.slug,
            query=title,
            config=config,
        )

    return {
        "external_doc_id": external_doc_id,
        "slug": slug,
        "draft_provider": metadata.get("model_provider"),
        "draft_model": metadata.get("model"),
        "wiki_evidence_id": evidence.evidence_id,
        "wiki_page_id": evidence.wiki_page_id,
        "source": evidence.source,
        "source_type": evidence.source_type,
    }


def _write_fixture(path: Path, anchor: str) -> None:
    path.write_text(
        "\n".join(
            [
                "# PA M2 Real LLM Wiki Fixture",
                "",
                f"Anchor: {anchor}.",
                "The synthetic Wiki briefing has a two-step preparation flow.",
                "The synthetic evidence note says publication requires traceable citations.",
                "The synthetic retrieval check must return a wiki_page evidence item.",
            ]
        ),
        encoding="utf-8",
    )


def _upload_fixture(backend: WeKnoraApiBackend, fixture_path: Path, anchor: str) -> str:
    try:
        document = backend.upload_document(
            str(fixture_path),
            metadata={
                "document_id": f"pa-m2-wiki-real-llm-{anchor}",
                "title": "PA M2 Real LLM Wiki Fixture",
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
    anchor: str,
    config: SmokeConfig,
) -> None:
    deadline = time.monotonic() + config.wait_seconds
    last_count = 0
    while time.monotonic() <= deadline:
        try:
            evidence_items = backend.retrieve(
                query=f"{anchor} PA M2 Real LLM Wiki Fixture traceable citations",
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


def _assert_source_output(content_json: str | None, expected_model: str) -> None:
    content = _json_object(content_json)
    model = content.get("model") if isinstance(content.get("model"), dict) else {}
    if model.get("provider") != "openai_compatible":
        raise SmokeError("source QA did not use openai_compatible provider")
    if "deepseek" not in str(model.get("model") or expected_model).lower():
        raise SmokeError("source QA did not record DeepSeek model")
    warning_codes = set(content.get("warning_codes") or [])
    if warning_codes - {"WEAK_EVIDENCE"}:
        raise SmokeError(f"source QA returned blocking warning codes: {sorted(warning_codes)}")


def _assert_real_draft_metadata(metadata: dict[str, Any], expected_model: str) -> None:
    if metadata.get("draft_generator") != "model_gateway":
        raise SmokeError("Wiki draft did not use model_gateway draft generation")
    if metadata.get("model_provider") != "openai_compatible":
        raise SmokeError("Wiki draft did not record openai_compatible provider")
    if "deepseek" not in str(metadata.get("model") or expected_model).lower():
        raise SmokeError("Wiki draft did not record DeepSeek model")
    if metadata.get("model_error"):
        raise SmokeError("Wiki draft recorded model_error")


def _wait_for_wiki_evidence(
    backend: WeKnoraApiBackend,
    slug: str,
    query: str,
    config: SmokeConfig,
) -> Evidence:
    deadline = time.monotonic() + config.wait_seconds
    last_count = 0
    while time.monotonic() <= deadline:
        try:
            evidence_items = backend.retrieve(
                query=query,
                filters={
                    "knowledge_base_ids": [config.default_kb_id],
                    "source_type": "wiki_page",
                },
                top_k=8,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise SmokeError(f"Wiki retrieval failed: {exc}") from exc
        last_count = len(evidence_items)
        for evidence in evidence_items:
            if _matches_wiki_evidence(evidence=evidence, slug=slug):
                _assert_wiki_evidence(evidence)
                return evidence
        time.sleep(config.poll_seconds)
    raise SmokeError(
        f"published Wiki page did not appear as wiki_page evidence within "
        f"{config.wait_seconds}s (last wiki evidence count: {last_count})"
    )


def _matches_wiki_evidence(evidence: Evidence, slug: str) -> bool:
    if evidence.source_type != "wiki_page":
        return False
    metadata = evidence.metadata or {}
    candidates = {
        evidence.wiki_page_id,
        metadata.get("weknora_wiki_page_slug"),
        metadata.get("weknora_slug"),
        metadata.get("slug"),
        metadata.get("weknora_wiki_page_id"),
        metadata.get("id"),
    }
    if slug in {str(item) for item in candidates if item}:
        return True
    return slug in evidence.title


def _assert_wiki_evidence(evidence: Evidence) -> None:
    if evidence.source != "weknora_api":
        raise SmokeError("Wiki evidence source is not weknora_api")
    if evidence.source_type != "wiki_page":
        raise SmokeError("Wiki evidence source_type is not wiki_page")
    if not evidence.evidence_id:
        raise SmokeError("Wiki evidence is missing evidence_id")
    if not evidence.wiki_page_id:
        raise SmokeError("Wiki evidence is missing wiki_page_id")


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
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        return default


def _safe_reason(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    for marker in ("Authorization", "Bearer", "api_key", "token", "secret", "password"):
        text = text.replace(marker, "[redacted]")
    return " ".join(text.split())[:300]


if __name__ == "__main__":
    raise SystemExit(main())
