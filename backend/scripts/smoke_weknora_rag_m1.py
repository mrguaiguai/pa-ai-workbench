"""Live M1 smoke for PA -> WeKnora RAG retrieval.

This smoke intentionally requires a real WeKnora service. It uploads a
sanitized temporary Markdown document through PA's WeKnora adapter, waits for
WeKnora indexing, then verifies PA receives non-mock document_chunk evidence
with traceable citation identifiers.

Required environment:
    KNOWLEDGE_BACKEND=weknora_api
    MOCK_MODE=false
    WEKNORA_BASE_URL=...
    WEKNORA_SERVICE_TOKEN=...
    WEKNORA_DEFAULT_KB_ID=...

Optional environment:
    WEKNORA_RAG_SMOKE_WAIT_SECONDS=180
    WEKNORA_RAG_SMOKE_POLL_SECONDS=5

The script does not print service tokens or real document content.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402


SMOKE_TITLE = "PA M1 RAG Smoke Sanitized Fixture"
SMOKE_QUERY_PREFIX = "pam1ragsmokeanchor"
TERMINAL_INDEXED_STATUSES = {"indexed"}
TERMINAL_FAILED_STATUSES = {"failed"}
PROGRESS_STATUSES = {"uploaded", "parsing", "chunking", "indexing", "unknown"}


class SmokeError(RuntimeError):
    """Raised when the live RAG smoke fails."""


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    service_token: str
    default_kb_id: str
    timeout_seconds: int
    wait_seconds: int
    poll_seconds: int
    knowledge_backend: str
    mock_mode: bool

    @classmethod
    def from_settings(cls) -> "SmokeConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            wait_seconds=_int_env("WEKNORA_RAG_SMOKE_WAIT_SECONDS", 180),
            poll_seconds=_int_env("WEKNORA_RAG_SMOKE_POLL_SECONDS", 5),
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
        )


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        with TemporaryDirectory(prefix="pa-weknora-rag-smoke-") as temp_dir:
            result = _run_live_smoke(config, Path(temp_dir))
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora RAG E2E smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora RAG E2E smoke passed (live)")
    print(f"- base URL: {config.base_url}")
    print(f"- knowledge base: {config.default_kb_id}")
    print(f"- external doc id: {result['external_doc_id']}")
    print(f"- indexed status: {result['status']}")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- chunk id: {result['chunk_id']}")
    print(f"- source: {result['source']}")
    print(f"- source type: {result['source_type']}")
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
    if config.wait_seconds <= 0:
        missing.append("WEKNORA_RAG_SMOKE_WAIT_SECONDS")
    if config.poll_seconds <= 0:
        missing.append("WEKNORA_RAG_SMOKE_POLL_SECONDS")
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(config: SmokeConfig, temp_dir: Path) -> dict[str, str]:
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        default_kb_id=config.default_kb_id,
        timeout=config.timeout_seconds,
    )
    document_path, query = _write_sanitized_fixture(temp_dir)
    document = _upload_fixture(backend, document_path)
    external_doc_id = _require_external_doc_id(document)
    status = _wait_until_indexed(backend, external_doc_id, config)
    evidence = _wait_for_retrievable_evidence(backend, external_doc_id, query, config)
    _assert_traceable_document_evidence(evidence, external_doc_id)
    return {
        "external_doc_id": external_doc_id,
        "status": status,
        "evidence_id": evidence.evidence_id or "",
        "chunk_id": evidence.chunk_id or "",
        "source": evidence.source,
        "source_type": evidence.source_type,
    }


def _write_sanitized_fixture(temp_dir: Path) -> tuple[Path, str]:
    run_id = uuid4().hex[:12]
    query = f"{SMOKE_QUERY_PREFIX}{run_id}"
    path = temp_dir / f"pa-m1-rag-smoke-sanitized-{run_id}.md"
    path.write_text(
        "\n".join(
            [
                "# PA M1 RAG Smoke Sanitized Fixture",
                "",
                "This document is synthetic and contains no real pilot data.",
                f"The smoke run id is {run_id}.",
                f"The citation anchor is {query}.",
                "A passing smoke must retrieve this sentence from WeKnora.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path, query


def _upload_fixture(backend: WeKnoraApiBackend, document_path: Path) -> KnowledgeDocument:
    try:
        return backend.upload_document(
            str(document_path),
            {
                "title": SMOKE_TITLE,
                "file_name": document_path.name,
                "business_area": "public_affairs",
                "document_type": "smoke",
                "source": "pa_m1_rag_smoke",
                "smoke_task": "P3-M1-F1",
                "smoke_fixture": "sanitized",
            },
        )
    except KnowledgeBackendUnavailableError as exc:
        raise SmokeError(f"upload failed: {exc}") from exc


def _require_external_doc_id(document: KnowledgeDocument) -> str:
    if document.source != "weknora_api":
        raise SmokeError(f"upload returned non-WeKnora source: {document.source}")
    if not document.external_doc_id:
        raise SmokeError("upload returned no external_doc_id")
    return document.external_doc_id


def _wait_until_indexed(
    backend: WeKnoraApiBackend,
    external_doc_id: str,
    config: SmokeConfig,
) -> str:
    deadline = time.monotonic() + config.wait_seconds
    last_status = ""
    last_message = ""
    while time.monotonic() <= deadline:
        try:
            status_payload = backend.get_document_status(external_doc_id)
        except KnowledgeBackendUnavailableError as exc:
            raise SmokeError(f"status check failed: {exc}") from exc
        status = str(status_payload.get("status") or "unknown")
        last_status = status
        last_message = str(status_payload.get("message") or "")
        if status in TERMINAL_INDEXED_STATUSES:
            return status
        if status in TERMINAL_FAILED_STATUSES:
            detail = status_payload.get("error_message") or status_payload.get("failed_step")
            raise SmokeError(f"WeKnora indexing failed for {external_doc_id}: {detail}")
        if status not in PROGRESS_STATUSES:
            raise SmokeError(f"unexpected WeKnora document status: {status}")
        time.sleep(config.poll_seconds)

    detail = f"; last message: {last_message}" if last_message else ""
    raise SmokeError(
        f"WeKnora document did not reach indexed within {config.wait_seconds}s "
        f"(last status: {last_status or 'unknown'}{detail})"
    )


def _wait_for_retrievable_evidence(
    backend: WeKnoraApiBackend,
    external_doc_id: str,
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
                    "external_doc_ids": [external_doc_id],
                    "source_type": "document_chunk",
                },
                top_k=20,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise SmokeError(f"retrieve failed: {exc}") from exc
        last_count = len(evidence_items)
        for evidence in evidence_items:
            if evidence.external_doc_id == external_doc_id:
                return evidence
        time.sleep(config.poll_seconds)
    raise SmokeError(
        "retrieve did not return traceable evidence for uploaded document "
        f"{external_doc_id} within {config.wait_seconds}s "
        f"(last evidence count after scope filtering: {last_count})"
    )


def _assert_traceable_document_evidence(evidence: Evidence, external_doc_id: str) -> None:
    if evidence.source != "weknora_api":
        raise SmokeError(f"evidence source is not weknora_api: {evidence.source}")
    if evidence.source_type != "document_chunk":
        raise SmokeError(f"evidence source_type is not document_chunk: {evidence.source_type}")
    if evidence.external_doc_id != external_doc_id:
        raise SmokeError(
            "evidence external_doc_id does not match uploaded document: "
            f"{evidence.external_doc_id}"
        )
    if not evidence.chunk_id:
        raise SmokeError("evidence is missing chunk_id")
    if not evidence.evidence_id:
        raise SmokeError("evidence is missing evidence_id")
    if not evidence.text:
        raise SmokeError("evidence is missing text")
    if evidence.metadata.get("citation_source_type") != "document_chunk":
        raise SmokeError("evidence metadata is missing citation_source_type=document_chunk")
    if not (
        evidence.metadata.get("weknora_knowledge_id")
        or evidence.metadata.get("weknora_knowledge_base_id")
    ):
        raise SmokeError("evidence metadata is missing WeKnora trace fields")


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


if __name__ == "__main__":
    raise SystemExit(main())
