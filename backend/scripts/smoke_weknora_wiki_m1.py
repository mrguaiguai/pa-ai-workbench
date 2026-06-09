"""Live M1 smoke for PA -> WeKnora Wiki publish/retrieve.

This smoke intentionally requires a real WeKnora service. It creates a
sanitized Wiki draft through PA's WeKnora adapter, publishes it by updating the
page status, then waits until WeKnora RAG retrieval returns traceable
source_type=wiki_page evidence.

Required environment:
    KNOWLEDGE_BACKEND=weknora_api
    MOCK_MODE=false
    WEKNORA_BASE_URL=...
    WEKNORA_SERVICE_TOKEN=...
    WEKNORA_DEFAULT_KB_ID=...

Optional environment:
    WEKNORA_WIKI_SMOKE_WAIT_SECONDS=180
    WEKNORA_WIKI_SMOKE_POLL_SECONDS=5

The script does not print service tokens or real pilot content.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import time
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
from knowledge_engine.schemas import WikiPage  # noqa: E402


SMOKE_QUERY_PREFIX = "pa-m1-wiki-smoke-anchor"
SMOKE_TITLE = "PA M1 Wiki Smoke Sanitized Fixture"


class SmokeError(RuntimeError):
    """Raised when the live Wiki smoke fails."""


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
            wait_seconds=_int_env("WEKNORA_WIKI_SMOKE_WAIT_SECONDS", 180),
            poll_seconds=_int_env("WEKNORA_WIKI_SMOKE_POLL_SECONDS", 5),
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
        )


def main() -> int:
    config = SmokeConfig.from_settings()
    try:
        _validate_config(config)
        result = _run_live_smoke(config)
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki E2E smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora Wiki E2E smoke passed (live)")
    print(f"- base URL: {config.base_url}")
    print(f"- knowledge base: {config.default_kb_id}")
    print(f"- slug: {result['slug']}")
    print(f"- published status: {result['status']}")
    print(f"- evidence id: {result['evidence_id']}")
    print(f"- wiki page id: {result['wiki_page_id']}")
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
        missing.append("WEKNORA_WIKI_SMOKE_WAIT_SECONDS")
    if config.poll_seconds <= 0:
        missing.append("WEKNORA_WIKI_SMOKE_POLL_SECONDS")
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if missing:
        raise SmokeError("missing or invalid required env: " + ", ".join(missing))


def _run_live_smoke(config: SmokeConfig) -> dict[str, str]:
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        default_kb_id=config.default_kb_id,
        timeout=config.timeout_seconds,
    )
    smoke_id = uuid4().hex[:12]
    slug = f"pa-smoke/m1-wiki-{smoke_id}"
    query = f"{SMOKE_QUERY_PREFIX}-{smoke_id}"

    draft = _create_draft(backend=backend, slug=slug, query=query)
    _assert_wiki_page(page=draft, slug=slug, expected_status="draft")
    published = _publish_page(backend=backend, slug=slug, draft=draft, query=query)
    _assert_wiki_page(page=published, slug=slug, expected_status="published")

    evidence = _wait_for_wiki_evidence(
        backend=backend,
        slug=slug,
        query=query,
        config=config,
    )
    _assert_traceable_wiki_evidence(evidence=evidence, slug=slug)
    return {
        "slug": slug,
        "status": str(published.metadata.get("status") or "published"),
        "evidence_id": evidence.evidence_id or "",
        "wiki_page_id": evidence.wiki_page_id or "",
        "source": evidence.source,
        "source_type": evidence.source_type,
    }


def _create_draft(backend: WeKnoraApiBackend, slug: str, query: str) -> WikiPage:
    try:
        return backend.create_wiki_page(
            {
                "slug": slug,
                "title": SMOKE_TITLE,
                "summary": "Synthetic M1 Wiki E2E smoke draft.",
                "content": _wiki_content(query=query, status="draft"),
                "page_type": "smoke",
                "status": "draft",
                "source_refs": ["pa-m1-f2-smoke-output|PA M1 Wiki Smoke"],
                "chunk_refs": ["pa-m1-f2-smoke-chunk"],
                "page_metadata": {
                    "source": "pa_ai_workbench",
                    "smoke_task": "P3-M1-F2",
                    "smoke_fixture": "sanitized",
                    "pa_source_output_id": "pa-m1-f2-smoke-output",
                    "weknora_evidence_refs": ["document_chunk:pa-m1-f2-smoke-chunk"],
                },
            },
        )
    except KnowledgeBackendUnavailableError as exc:
        raise SmokeError(f"create draft failed: {exc}") from exc


def _publish_page(
    backend: WeKnoraApiBackend,
    slug: str,
    draft: WikiPage,
    query: str,
) -> WikiPage:
    try:
        return backend.update_wiki_page(
            slug=slug,
            page={
                "slug": slug,
                "title": draft.title or SMOKE_TITLE,
                "summary": draft.summary or "Synthetic M1 Wiki E2E smoke.",
                "content": _wiki_content(query=query, status="published"),
                "page_type": draft.page_type or "smoke",
                "status": "published",
                "source_refs": draft.metadata.get("source_refs")
                or ["pa-m1-f2-smoke-output|PA M1 Wiki Smoke"],
                "chunk_refs": draft.metadata.get("chunk_refs")
                or ["pa-m1-f2-smoke-chunk"],
                "page_metadata": {
                    **draft.metadata,
                    "source": "pa_ai_workbench",
                    "smoke_task": "P3-M1-F2",
                    "smoke_fixture": "sanitized",
                    "publish_operation": "smoke",
                },
            },
        )
    except KnowledgeBackendUnavailableError as exc:
        raise SmokeError(f"publish failed: {exc}") from exc


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
                top_k=5,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise SmokeError(f"retrieve failed: {exc}") from exc
        last_count = len(evidence_items)
        matching = [_matching_wiki_evidence(item, slug) for item in evidence_items]
        matching = [item for item in matching if item is not None]
        if matching:
            return matching[0]
        time.sleep(config.poll_seconds)
    raise SmokeError(
        f"published Wiki page did not appear as wiki_page evidence within "
        f"{config.wait_seconds}s (last wiki evidence count: {last_count})"
    )


def _matching_wiki_evidence(evidence: Evidence, slug: str) -> Evidence | None:
    if evidence.source_type != "wiki_page":
        return None
    metadata = evidence.metadata or {}
    candidates = {
        evidence.wiki_page_id,
        metadata.get("weknora_wiki_page_slug"),
        metadata.get("weknora_slug"),
        metadata.get("weknora_page_id"),
        metadata.get("weknora_wiki_page_id"),
    }
    if slug in {str(item) for item in candidates if item}:
        return evidence
    if slug in evidence.text or slug in evidence.title:
        return evidence
    return None


def _assert_wiki_page(page: WikiPage, slug: str, expected_status: str) -> None:
    if page.source != "weknora_api":
        raise SmokeError(f"Wiki page source is not weknora_api: {page.source}")
    if page.slug != slug:
        raise SmokeError(f"Wiki slug mismatch: {page.slug}")
    status = str(page.metadata.get("status") or expected_status).lower()
    if status != expected_status:
        raise SmokeError(f"Wiki status mismatch: {status}")


def _assert_traceable_wiki_evidence(evidence: Evidence, slug: str) -> None:
    if evidence.source != "weknora_api":
        raise SmokeError(f"evidence source is not weknora_api: {evidence.source}")
    if evidence.source_type != "wiki_page":
        raise SmokeError(f"evidence source_type is not wiki_page: {evidence.source_type}")
    if not evidence.wiki_page_id:
        raise SmokeError("wiki evidence is missing wiki_page_id")
    if not evidence.evidence_id:
        raise SmokeError("wiki evidence is missing evidence_id")
    if not evidence.text:
        raise SmokeError("wiki evidence is missing text")
    if evidence.metadata.get("citation_source_type") != "wiki_page":
        raise SmokeError("wiki evidence metadata is missing citation_source_type=wiki_page")
    trace_fields = (
        "weknora_wiki_page_id",
        "weknora_wiki_id",
        "weknora_wiki_page_slug",
        "weknora_slug",
        "weknora_page_id",
    )
    if not any(evidence.metadata.get(key) for key in trace_fields) and slug not in str(
        evidence.wiki_page_id
    ):
        raise SmokeError("wiki evidence metadata is missing WeKnora trace fields")


def _wiki_content(query: str, status: str) -> str:
    return "\n".join(
        [
            "# PA M1 Wiki Smoke Sanitized Fixture",
            "",
            "This Wiki page is synthetic and contains no real pilot data.",
            f"The retrieval anchor is {query}.",
            f"The page status for this smoke step is {status}.",
            "",
        ]
    )


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
