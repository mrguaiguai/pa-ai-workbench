"""P3-M3-B4 backend switch E2E smoke.

The smoke verifies explicit mock / weknora_api / extracted switching without
live network calls, .env reads, persistent DB writes, uploads, or real documents.
Each backend gets a fresh fixture instance and temporary document.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.tools.citation_checker import CitationChecker  # noqa: E402
from agent.tools.real_retriever import RealRetrieverTool  # noqa: E402
from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.backends import MockKnowledgeBackend  # noqa: E402
from knowledge_engine.backends import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendComponents  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendConfig  # noqa: E402
from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.factory import create_knowledge_engine  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402


ENV_KEYS = (
    "APP_ENV",
    "MOCK_MODE",
    "KNOWLEDGE_BACKEND",
    "WEKNORA_BASE_URL",
    "WEKNORA_SERVICE_TOKEN",
    "WEKNORA_API_KEY",
    "WEKNORA_WORKSPACE_ID",
    "WEKNORA_DEFAULT_KB_ID",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL_NAME",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_API_KEY",
    "VECTOR_STORE_PROVIDER",
    "VECTOR_COLLECTION_NAME",
)
EXPECTED_BACKENDS = ("mock", "weknora_api", "extracted")
SANITIZED_DOC = """# Backend Switch Fixture

This sanitized fixture checks backend switch isolation, source labels, and
citation trace behavior. It contains no real public affairs material.
"""


class SmokeError(RuntimeError):
    """Raised when backend switch expectations fail."""


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="fixture://weknora",
            service_token="fixture-token",
            workspace_id="workspace-redacted",
            default_kb_id="kb-redacted",
        )
        self.uploads: list[str] = []
        self.wiki_pages: dict[str, dict[str, Any]] = {
            "switch-fixture": {
                "id": "wk-wiki-switch",
                "slug": "switch-fixture",
                "title": "Switch Fixture Wiki",
                "page_type": "policy",
                "summary": "Sanitized WeKnora fixture Wiki summary.",
                "content": "Sanitized WeKnora fixture Wiki body.",
                "status": "published",
            }
        }

    def _request_multipart_json(
        self,
        path: str,
        *,
        file_path: Path,
        fields: dict[str, str],
    ) -> dict | list:
        self.uploads.append(path)
        return {
            "data": {
                "id": "wk-doc-switch-fixture",
                "file_name": file_path.name,
                "status": "indexed",
                "knowledge_base_id": "kb-redacted",
                "metadata": {"fixture": "backend-switch"},
            }
        }

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        if method == "GET" and path.startswith("/api/v1/knowledge/"):
            return {
                "data": {
                    "id": path.rsplit("/", 1)[-1],
                    "status": "indexed",
                    "knowledge_base_id": "kb-redacted",
                }
            }
        if method == "POST" and path == "/api/v1/knowledge-search":
            return {
                "data": [
                    {
                        "id": "wk-chunk-switch-fixture",
                        "knowledge_id": "wk-doc-switch-fixture",
                        "knowledge_base_id": "kb-redacted",
                        "title": "Switch Fixture Evidence",
                        "content": "Sanitized WeKnora switch evidence.",
                        "score": 0.91,
                        "metadata": {"fixture": "backend-switch", "source_type": "document"},
                    }
                ]
            }
        if method == "GET" and "/wiki/search?" in path:
            return {"data": {"pages": list(self.wiki_pages.values())}}
        if method == "GET" and "/wiki/pages/" in path:
            slug = path.rsplit("/", 1)[-1]
            return {"data": self.wiki_pages.get(slug, {})}
        if method == "POST" and "/wiki/" in path and path.endswith("/pages"):
            page = dict(payload or {})
            page.setdefault("id", "wk-wiki-created-switch")
            page.setdefault("status", "draft")
            self.wiki_pages[str(page.get("slug") or "created-switch")] = page
            return {"data": page}
        if method == "PUT" and "/wiki/pages/" in path:
            slug = path.rsplit("/", 1)[-1]
            page = {**self.wiki_pages.get(slug, {}), **dict(payload or {}), "slug": slug}
            page.setdefault("id", "wk-wiki-updated-switch")
            self.wiki_pages[slug] = page
            return {"data": page}
        raise SmokeError(f"unexpected fixture WeKnora request: {method} {path}")


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"M3 backend switch smoke failed: {exc}", file=sys.stderr)
        return 1

    print("M3 backend switch smoke passed")
    print(f"- backends switched: {', '.join(result['backends'])}")
    print(f"- source isolation checks: {result['source_checks']}")
    print(f"- agent citation checks: {result['agent_checks']}")
    print(f"- release fail-closed checks: {result['fail_closed_checks']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    seen_sources: dict[str, set[str]] = {}
    source_checks = 0
    agent_checks = 0
    with TemporaryDirectory(prefix="pa-m3-backend-switch-") as temp_dir:
        path = Path(temp_dir) / "backend-switch-fixture.md"
        path.write_text(SANITIZED_DOC, encoding="utf-8")
        for backend_name in EXPECTED_BACKENDS:
            with _backend_env(backend_name):
                engine = _engine_for_backend(backend_name)
                sources = _exercise_backend(engine, backend_name, path)
                _assert(sources == {backend_name}, f"{backend_name} leaked sources: {sources}")
                seen_sources[backend_name] = sources
                source_checks += 1
                agent_checks += _assert_agent_retrieval(engine, backend_name)
                _assert_capability_switch(backend_name)
        _assert_no_source_cross_contamination(seen_sources)
    fail_closed_checks = _assert_release_fail_closed()
    return {
        "backends": list(EXPECTED_BACKENDS),
        "source_checks": source_checks,
        "agent_checks": agent_checks,
        "fail_closed_checks": fail_closed_checks,
    }


def _engine_for_backend(backend_name: str):
    if backend_name == "mock":
        engine = create_knowledge_engine()
        _assert(isinstance(engine, MockKnowledgeBackend), "factory did not return mock")
        return engine
    if backend_name == "extracted":
        engine = create_knowledge_engine()
        _assert(
            isinstance(engine, ExtractedKnowledgeBackend),
            "factory did not return extracted",
        )
        return _fresh_extracted_engine()
    if backend_name == "weknora_api":
        configured = create_knowledge_engine()
        _assert(
            isinstance(configured, WeKnoraApiBackend),
            "factory did not return configured WeKnora adapter",
        )
        return FixtureWeKnoraBackend()
    raise SmokeError(f"unsupported test backend: {backend_name}")


def _fresh_extracted_engine() -> ExtractedKnowledgeBackend:
    return ExtractedKnowledgeBackend(
        config=ExtractedBackendConfig(source="extracted", backend_name="extracted"),
        components=ExtractedBackendComponents(
            vector_store=MockVectorStore(name="m3-backend-switch-extracted")
        ),
        embedding_provider=MockEmbeddingProvider(
            EmbeddingProviderConfig(
                provider="mock",
                model_name="m3-backend-switch",
                dimension=16,
            )
        ),
    )


def _exercise_backend(engine: Any, backend_name: str, path: Path) -> set[str]:
    sources: set[str] = set()
    document = engine.upload_document(
        str(path),
        {"document_id": f"pa-doc-switch-{backend_name}", "title": f"{backend_name} switch"},
    )
    sources.add(document.source)
    status = engine.get_document_status(str(document.external_doc_id))
    sources.add(str(status.get("source")))
    if backend_name == "extracted":
        engine.index_document(str(document.external_doc_id))

    evidence = engine.retrieve("switch fixture citation trace", top_k=2)
    _assert(evidence, f"{backend_name} retrieve returned no evidence")
    for item in evidence:
        sources.add(item.source)
        _assert_trace(item, backend_name)

    wiki_slug = _exercise_wiki(engine, backend_name)
    page = engine.read_wiki_page(wiki_slug, kb_id=None if backend_name == "mock" else "kb-redacted")
    _assert(page is not None, f"{backend_name} wiki read returned no page")
    sources.add(page.source)
    if backend_name == "extracted":
        _assert(page.metadata.get("weknora_retrievable") is False, "extracted page claimed WeKnora retrievable")
    summaries = engine.search_wiki(
        _wiki_query(backend_name),
        kb_id=None if backend_name == "mock" else "kb-redacted",
        limit=5,
    )
    _assert(summaries, f"{backend_name} wiki search returned no summaries")
    sources.update(summary.source for summary in summaries)
    return sources


def _exercise_wiki(engine: Any, backend_name: str) -> str:
    if backend_name == "mock":
        return "mock-policy-watch"
    if backend_name == "weknora_api":
        created = engine.create_wiki_page(
            {
                "slug": "created-switch",
                "title": "Created Switch",
                "content": "Sanitized WeKnora created switch body.",
            },
            kb_id="kb-redacted",
        )
        _assert(created.source == "weknora_api", "WeKnora wiki create source mismatch")
        return "created-switch"
    created = engine.create_wiki_page(
        {
            "slug": "extracted-switch",
            "title": "Extracted Switch",
            "content": "Sanitized extracted switch body.",
        },
        kb_id="kb-redacted",
    )
    published = engine.publish_wiki_page(created.slug)
    indexed = engine.index_wiki_page(created.slug)
    _assert(published.source == "extracted", "extracted wiki publish source mismatch")
    _assert(indexed.get("wiki_retrievable") is False, "extracted wiki index claimed retrievable")
    return created.slug


def _wiki_query(backend_name: str) -> str:
    if backend_name == "mock":
        return "mock"
    return "switch"


def _assert_agent_retrieval(engine: Any, backend_name: str) -> int:
    citations = RealRetrieverTool(knowledge_engine=engine, default_top_k=2).retrieve(
        "switch fixture citation trace",
        top_k=2,
    )
    _assert(citations, f"{backend_name} agent retrieve returned no citations")
    for citation in citations:
        _assert(citation.source == backend_name, f"{backend_name} agent citation source mismatch")
    result = CitationChecker().validate(citations)
    _assert(result.valid, f"{backend_name} agent citations invalid: {result.warnings}")
    return len(citations)


def _assert_trace(item: Evidence, backend_name: str) -> None:
    if backend_name == "mock":
        _assert(item.source == "mock", "mock source mismatch")
        return
    _assert(item.evidence_id, f"{backend_name} missing evidence_id")
    _assert(item.source_type in {"document_chunk", "wiki_page"}, f"{backend_name} bad source_type")
    if item.source_type == "document_chunk":
        _assert(item.chunk_id, f"{backend_name} missing chunk_id")
        _assert(
            item.document_id or item.external_doc_id,
            f"{backend_name} missing document id",
        )


def _assert_capability_switch(backend_name: str) -> None:
    snapshot = backend_capability_snapshot(
        backend_name=backend_name,
        app_env="local",
        mock_mode=(backend_name == "mock"),
        weknora_configured=(backend_name == "weknora_api"),
    )
    _assert(snapshot["active_backend"] == backend_name, f"{backend_name} capability active mismatch")
    if backend_name != "weknora_api":
        _assert(not snapshot["release_eligible"], f"{backend_name} unexpectedly release eligible")
    if backend_name == "weknora_api":
        _assert(snapshot["release_eligible"], "configured WeKnora not release eligible")


def _assert_no_source_cross_contamination(seen_sources: dict[str, set[str]]) -> None:
    for backend_name, sources in seen_sources.items():
        for other in set(EXPECTED_BACKENDS) - {backend_name}:
            _assert(other not in sources, f"{backend_name} leaked {other} source")


def _assert_release_fail_closed() -> int:
    checks = 0
    with _temporary_env(
        {
            "APP_ENV": "pilot",
            "MOCK_MODE": "false",
            "KNOWLEDGE_BACKEND": "weknora_api",
            "WEKNORA_BASE_URL": "",
            "WEKNORA_SERVICE_TOKEN": "",
            "WEKNORA_WORKSPACE_ID": "",
            "WEKNORA_DEFAULT_KB_ID": "",
        }
    ):
        try:
            create_knowledge_engine()
        except KnowledgeBackendUnavailableError:
            checks += 1
        else:
            raise SmokeError("release-like missing WeKnora config did not fail closed")
    snapshot = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="pilot",
        mock_mode=False,
        weknora_configured=False,
    )
    _assert(snapshot["fallback_policy"]["fail_closed"] is True, "snapshot not fail-closed")
    _assert(
        snapshot["fallback_policy"]["silent_mock_fallback_allowed"] is False,
        "release-like snapshot allowed silent mock fallback",
    )
    return checks + 1


@contextmanager
def _backend_env(backend_name: str) -> Iterator[None]:
    updates = {
        "APP_ENV": "local",
        "MOCK_MODE": "true" if backend_name == "mock" else "false",
        "KNOWLEDGE_BACKEND": backend_name,
        "EMBEDDING_PROVIDER": "mock",
        "EMBEDDING_MODEL_NAME": "m3-backend-switch",
        "EMBEDDING_DIMENSION": "16",
        "EMBEDDING_API_KEY": "",
        "VECTOR_STORE_PROVIDER": "mock",
        "VECTOR_COLLECTION_NAME": f"m3_backend_switch_{backend_name}",
        "WEKNORA_BASE_URL": "fixture://weknora" if backend_name == "weknora_api" else "",
        "WEKNORA_SERVICE_TOKEN": "fixture-token" if backend_name == "weknora_api" else "",
        "WEKNORA_WORKSPACE_ID": "workspace-redacted" if backend_name == "weknora_api" else "",
        "WEKNORA_DEFAULT_KB_ID": "kb-redacted" if backend_name == "weknora_api" else "",
    }
    with _temporary_env(updates):
        yield


class _temporary_env:
    def __init__(self, updates: dict[str, str]) -> None:
        self.updates = updates
        self.original: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key in ENV_KEYS:
            self.original[key] = os.environ.get(key)
            os.environ.pop(key, None)
        for key, value in self.updates.items():
            if value:
                os.environ[key] = value

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        for key in ENV_KEYS:
            os.environ.pop(key, None)
            if self.original[key] is not None:
                os.environ[key] = self.original[key] or ""


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
