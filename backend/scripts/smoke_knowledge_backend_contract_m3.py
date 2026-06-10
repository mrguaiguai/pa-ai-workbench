"""Static KnowledgeBackend contract smoke for P3-M3-A1.

The suite keeps live WeKnora side effects out of the contract path. It exercises:
- mock backend dev-only successes and unsupported methods;
- weknora_api via a sanitized fixture adapter;
- extracted backend local partial behavior and explicit pending methods.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.backends import MockKnowledgeBackend  # noqa: E402
from knowledge_engine.backends import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendComponents  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendConfig  # noqa: E402
from knowledge_engine.capabilities import BACKEND_CAPABILITY_MATRIX  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402
from knowledge_engine.wiki import InMemoryWikiStore  # noqa: E402


ENV_KEYS = (
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL_NAME",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_API_KEY",
)
SUPPORTED_OR_PARTIAL = {"supported", "partial", "dev-only"}


class ContractError(RuntimeError):
    """Raised when a backend contract expectation fails."""


@dataclass(frozen=True)
class BackendFixture:
    name: str
    backend: object
    document_path: Path
    expected_source: str


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            "fixture://weknora",
            "fixture-auth-value",
            workspace_id="workspace-contract",
            default_kb_id="kb-contract",
        )
        self.uploaded_paths: list[str] = []
        self.wiki_payloads: list[dict[str, Any]] = []

    def _request_multipart_json(
        self,
        path: str,
        *,
        file_path: Path,
        fields: dict[str, str],
    ) -> dict | list:
        _assert("/knowledge/file" in path, f"unexpected upload path: {path}")
        self.uploaded_paths.append(str(file_path.name))
        return {
            "data": {
                "id": "wk-doc-contract-001",
                "file_name": fields.get("fileName") or file_path.name,
                "parse_status": "indexed",
                "metadata": {"fixture": "contract"},
            }
        }

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        if method == "GET" and path == "/health":
            return {"status": "ok"}
        if method == "GET" and path.startswith("/api/v1/knowledge/"):
            return {
                "data": {
                    "id": path.rsplit("/", 1)[-1],
                    "status": "indexed",
                    "metadata": {"fixture": "contract"},
                }
            }
        if method == "GET" and path.startswith("/api/v1/chunks/"):
            return {
                "data": {
                    "items": [
                        {
                            "id": "wk-chunk-contract-001",
                            "knowledge_id": "wk-doc-contract-001",
                            "chunk_index": 0,
                            "content": "Contract fixture chunk summary.",
                            "token_count": 7,
                            "is_enabled": True,
                        }
                    ]
                }
            }
        if method == "POST" and path == "/api/v1/knowledge-search":
            return {
                "data": [
                    {
                        "id": "wk-chunk-contract-001",
                        "knowledge_id": "wk-doc-contract-001",
                        "knowledge_base_id": "kb-contract",
                        "title": "Contract Fixture Evidence",
                        "content": "Contract fixture evidence summary.",
                        "score": 0.91,
                        "metadata": {"fixture": "contract"},
                    }
                ]
            }
        if method == "GET" and "/wiki/" in path and path.endswith("/search?q=contract&limit=5"):
            return {
                "data": {
                    "pages": [
                        {
                            "id": "wk-wiki-contract-001",
                            "slug": "contract-fixture",
                            "title": "Contract Fixture Wiki",
                            "page_type": "policy",
                            "summary": "Contract wiki summary.",
                            "content": "Contract wiki body.",
                        }
                    ]
                }
            }
        if method == "GET" and "/wiki/" in path and "/pages/contract-fixture" in path:
            return {
                "data": {
                    "id": "wk-wiki-contract-001",
                    "slug": "contract-fixture",
                    "title": "Contract Fixture Wiki",
                    "page_type": "policy",
                    "summary": "Contract wiki summary.",
                    "content": "Contract wiki body.",
                }
            }
        if method in {"POST", "PUT"} and "/wiki/" in path and "/pages" in path:
            self.wiki_payloads.append(dict(payload or {}))
            page = dict(payload or {})
            page.setdefault("id", "wk-wiki-contract-created")
            page.setdefault("summary", "Created by contract fixture.")
            page.setdefault("content", "Created contract fixture body.")
            return {"data": page}
        raise ContractError(f"unexpected fixture WeKnora request: {method} {path}")


def main() -> int:
    try:
        result = _run_contracts()
    except Exception as exc:  # noqa: BLE001
        print(f"KnowledgeBackend contract smoke failed: {exc}", file=sys.stderr)
        return 1

    print("KnowledgeBackend contract smoke passed")
    print(f"- backends checked: {', '.join(result['backends'])}")
    print(f"- success checks: {result['success_checks']}")
    print(f"- unsupported checks: {result['unsupported_checks']}")
    print(f"- error checks: {result['error_checks']}")
    return 0


def _run_contracts() -> dict[str, Any]:
    with TemporaryDirectory() as temp_dir:
        document_path = _write_contract_document(Path(temp_dir))
        fixtures = [
            BackendFixture(
                name="mock",
                backend=MockKnowledgeBackend(),
                document_path=document_path,
                expected_source="mock",
            ),
            BackendFixture(
                name="weknora_api",
                backend=FixtureWeKnoraBackend(),
                document_path=document_path,
                expected_source="weknora_api",
            ),
            BackendFixture(
                name="extracted",
                backend=_extracted_backend(),
                document_path=document_path,
                expected_source="extracted",
            ),
        ]
        success_checks = 0
        unsupported_checks = 0
        for fixture in fixtures:
            success_checks += _assert_base_contract(fixture)
            unsupported_checks += _assert_unsupported_contract(fixture)
        error_checks = _assert_error_contracts(document_path)

    return {
        "backends": [fixture.name for fixture in fixtures],
        "success_checks": success_checks,
        "unsupported_checks": unsupported_checks,
        "error_checks": error_checks,
    }


def _assert_base_contract(fixture: BackendFixture) -> int:
    capabilities = BACKEND_CAPABILITY_MATRIX[fixture.name]
    backend = fixture.backend
    checks = 0

    health = backend.health()
    _assert_dict(health, f"{fixture.name}.health")
    _assert(str(health.get("source") or health.get("backend") or ""), f"{fixture.name}.health source")
    checks += 1

    document = backend.upload_document(
        str(fixture.document_path),
        {
            "document_id": f"pa-doc-{fixture.name}",
            "title": f"{fixture.name} contract document",
            "file_name": fixture.document_path.name,
        },
    )
    _assert_document(document, fixture.expected_source)
    checks += 1

    status = backend.get_document_status(str(document.external_doc_id))
    _assert_status(status, fixture.expected_source)
    checks += 1

    if capabilities["document_chunks"] in SUPPORTED_OR_PARTIAL:
        chunks = backend.list_document_chunks(str(document.external_doc_id))
        _assert_chunks(chunks, fixture.expected_source)
        checks += 1

    if fixture.name == "extracted":
        indexed = backend.index_document(str(document.external_doc_id))
        _assert(indexed.get("status") == "indexed", "extracted index status mismatch")

    if capabilities["rag_retrieve"] in SUPPORTED_OR_PARTIAL:
        evidence = backend.retrieve("contract", filters={}, top_k=5)
        _assert_evidence_list(evidence, fixture.expected_source, real=fixture.name == "weknora_api")
        checks += 1

    if capabilities["wiki_search"] in SUPPORTED_OR_PARTIAL:
        summaries = backend.search_wiki(_wiki_query(fixture.name), kb_id=_wiki_kb_id(fixture.name), limit=5)
        _assert_wiki_summaries(summaries, fixture.expected_source)
        checks += 1

    if capabilities["wiki_read"] in SUPPORTED_OR_PARTIAL:
        page = backend.read_wiki_page(_first_wiki_slug(fixture.name), kb_id=_wiki_kb_id(fixture.name))
        _assert_wiki_page(page, fixture.expected_source)
        checks += 1

    if capabilities["wiki_create_update_publish"] == "supported":
        created = backend.create_wiki_page(_wiki_payload("contract-created"), kb_id="kb-contract")
        updated = backend.update_wiki_page(
            "contract-created",
            _wiki_payload("contract-created"),
            kb_id="kb-contract",
        )
        _assert_wiki_page(created, fixture.expected_source)
        _assert_wiki_page(updated, fixture.expected_source)
        checks += 2
    elif capabilities["wiki_create_update_publish"] == "partial":
        created = backend.create_wiki_page(_wiki_payload("contract-created"), kb_id="kb-contract")
        published = backend.publish_wiki_page("contract-created")
        indexed = backend.index_wiki_page("contract-created")
        _assert_wiki_page(created, fixture.expected_source)
        _assert_wiki_page(published, fixture.expected_source)
        _assert(indexed.get("source") == fixture.expected_source, "partial wiki index source mismatch")
        _assert(indexed.get("wiki_retrievable") is False, "partial wiki must not be retrievable")
        checks += 3

    return checks


def _assert_unsupported_contract(fixture: BackendFixture) -> int:
    checks = 0
    capabilities = BACKEND_CAPABILITY_MATRIX[fixture.name]
    backend = fixture.backend
    if capabilities["document_chunks"] == "unsupported":
        _assert_unsupported(backend, "list_document_chunks", "missing-doc")
        checks += 1
    if capabilities["wiki_create_update_publish"] == "unsupported":
        _assert_unsupported(backend, "create_wiki_page", _wiki_payload("unsupported"))
        checks += 1
        _assert_unsupported(backend, "update_wiki_page", "unsupported", _wiki_payload("unsupported"))
        checks += 1
        _assert_unsupported(backend, "publish_wiki_page", "unsupported")
        checks += 1
        _assert_unsupported(backend, "index_wiki_page", "unsupported")
        checks += 1
    elif fixture.name == "weknora_api":
        _assert_unsupported(backend, "publish_wiki_page", "contract-created")
        _assert_unsupported(backend, "index_wiki_page", "contract-created")
        checks += 2
    return checks


def _assert_error_contracts(document_path: Path) -> int:
    checks = 0
    unconfigured = WeKnoraApiBackend("", "", workspace_id="", default_kb_id="")
    for method_name, args in (
        ("upload_document", (str(document_path), {"title": "missing config"})),
        ("get_document_status", ("missing-doc",)),
        ("retrieve", ("contract", {}, 1)),
        ("search_wiki", ("contract",)),
        ("read_wiki_page", ("contract-fixture",)),
        ("create_wiki_page", (_wiki_payload("missing-config"),)),
        ("update_wiki_page", ("missing-config", _wiki_payload("missing-config"))),
    ):
        try:
            getattr(unconfigured, method_name)(*args)
        except KnowledgeBackendUnavailableError:
            checks += 1
            continue
        raise ContractError(f"unconfigured weknora_api did not fail: {method_name}")

    extracted = _extracted_backend()
    try:
        extracted.get_document_status("missing-doc")
    except Exception as exc:  # noqa: BLE001
        raise ContractError(f"extracted missing status should be safe: {exc}") from exc
    checks += 1
    return checks


def _assert_document(document: KnowledgeDocument, source: str) -> None:
    _assert(isinstance(document, KnowledgeDocument), "upload did not return KnowledgeDocument")
    _assert(document.external_doc_id, "document missing external_doc_id")
    _assert(document.title, "document missing title")
    _assert(document.status, "document missing status")
    _assert(document.source == source, f"document source mismatch: {document.source}")


def _assert_status(status: dict, source: str) -> None:
    _assert_dict(status, "document status")
    _assert(status.get("external_doc_id"), "status missing external_doc_id")
    _assert(status.get("status"), "status missing status")
    _assert(status.get("source") == source, f"status source mismatch: {status.get('source')}")


def _assert_chunks(chunks: list[dict], source: str) -> None:
    _assert(isinstance(chunks, list) and chunks, "chunks must be a non-empty list")
    first = chunks[0]
    _assert_dict(first, "chunk")
    _assert(first.get("id"), "chunk missing id")
    _assert(first.get("external_doc_id"), "chunk missing external_doc_id")
    _assert(first.get("content") or first.get("content_hash"), "chunk missing content/hash")
    _assert(first.get("source") == source, f"chunk source mismatch: {first.get('source')}")


def _assert_evidence_list(items: list[Evidence], source: str, *, real: bool) -> None:
    _assert(isinstance(items, list), "retrieve did not return a list")
    if not items:
        _assert(source != "weknora_api", "weknora_api fixture retrieve returned no evidence")
        return
    for evidence in items:
        _assert(isinstance(evidence, Evidence), "retrieve item is not Evidence")
        _assert(evidence.source == source, f"evidence source mismatch: {evidence.source}")
        _assert(evidence.title, "evidence missing title")
        _assert(evidence.text, "evidence missing text")
        if real:
            _assert(evidence.evidence_id, "real evidence missing evidence_id")
            _assert(evidence.source_type in {"document_chunk", "wiki_page"}, "bad source_type")
            if evidence.source_type == "document_chunk":
                _assert(evidence.chunk_id, "document evidence missing chunk_id")
                _assert(evidence.external_doc_id or evidence.document_id, "document evidence missing doc id")
            if evidence.source_type == "wiki_page":
                _assert(evidence.wiki_page_id, "wiki evidence missing wiki_page_id")
        else:
            _assert(evidence.source != "weknora_api", "fallback evidence mislabeled as WeKnora")


def _assert_wiki_summaries(summaries: list[WikiPageSummary], source: str) -> None:
    _assert(isinstance(summaries, list) and summaries, "wiki search returned no summaries")
    first = summaries[0]
    _assert(isinstance(first, WikiPageSummary), "wiki search item is not WikiPageSummary")
    _assert(first.slug, "wiki summary missing slug")
    _assert(first.title, "wiki summary missing title")
    _assert(first.source == source, f"wiki summary source mismatch: {first.source}")


def _assert_wiki_page(page: WikiPage | None, source: str) -> None:
    _assert(isinstance(page, WikiPage), "wiki read/create/update did not return WikiPage")
    _assert(page.slug, "wiki page missing slug")
    _assert(page.title, "wiki page missing title")
    _assert(page.source == source, f"wiki page source mismatch: {page.source}")


def _assert_unsupported(backend: object, method_name: str, *args: object) -> None:
    method = getattr(backend, method_name, None)
    if method is None:
        return
    try:
        method(*args)
    except (AttributeError, NotImplementedError, KnowledgeBackendUnavailableError):
        return
    raise ContractError(f"{type(backend).__name__}.{method_name} unexpectedly succeeded")


def _first_wiki_slug(backend_name: str) -> str:
    if backend_name == "mock":
        return "mock-policy-watch"
    return "contract-fixture"


def _wiki_query(backend_name: str) -> str:
    if backend_name == "mock":
        return "mock"
    return "contract"


def _wiki_kb_id(backend_name: str) -> str | None:
    if backend_name == "mock":
        return None
    return "kb-contract"


def _wiki_payload(slug: str) -> dict[str, Any]:
    return {
        "slug": slug,
        "title": "Contract Fixture Wiki",
        "page_type": "policy",
        "summary": "Contract wiki summary.",
        "content": "Contract wiki body.",
        "metadata": {"fixture": "contract"},
    }


def _write_contract_document(temp_dir: Path) -> Path:
    path = temp_dir / "contract-fixture.md"
    path.write_text(
        "# Contract Fixture\n\n"
        "This sanitized contract fixture contains policy retrieval text. "
        "It is intentionally short and synthetic. "
        "The repeated contract anchor helps mock embeddings retrieve it.\n",
        encoding="utf-8",
    )
    return path


def _extracted_backend() -> ExtractedKnowledgeBackend:
    wiki_store = InMemoryWikiStore(
        [
            WikiPage(
                slug="contract-fixture",
                title="Contract Fixture Wiki",
                page_type="policy",
                summary="Contract wiki summary.",
                content="Contract wiki body.",
                source="extracted",
                metadata={"kb_id": "kb-contract"},
            )
        ]
    )
    embedding = MockEmbeddingProvider(
        EmbeddingProviderConfig(provider="mock", model_name="contract-mock", dimension=16)
    )
    return ExtractedKnowledgeBackend(
        config=ExtractedBackendConfig(source="extracted", backend_name="extracted"),
        components=ExtractedBackendComponents(
            vector_store=MockVectorStore(name="contract"),
            wiki_store=wiki_store,
        ),
        embedding_provider=embedding,
    )


def _assert_dict(value: object, label: str) -> None:
    _assert(isinstance(value, dict), f"{label} must be a dict")


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise ContractError(message)


@contextmanager
def _without_embedding_env():
    original = {key: os.environ.get(key) for key in ENV_KEYS}
    try:
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in original.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value


if __name__ == "__main__":
    with _without_embedding_env():
        raise SystemExit(main())
