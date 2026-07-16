"""Fixture smoke for P3-M3-B1 extracted schema parity.

The smoke keeps WeKnora out of the path and proves that explicit extracted
fallback output uses the same PA-facing schema fields as the WeKnora adapter.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
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


from agent.schemas import Citation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from app.schemas import CitationRead  # noqa: E402
from app.schemas import EvidenceRead  # noqa: E402
from app.schemas import WikiPageRead  # noqa: E402
from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendComponents  # noqa: E402
from knowledge_engine.backends.extracted_backend import ExtractedBackendConfig  # noqa: E402
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig  # noqa: E402
from knowledge_engine.embeddings.providers.mock import MockEmbeddingProvider  # noqa: E402
from knowledge_engine.factory import create_knowledge_engine  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.vectorstores import MockVectorStore  # noqa: E402
from knowledge_engine.wiki import InMemoryWikiStore  # noqa: E402


ENV_KEYS = (
    "KNOWLEDGE_BACKEND",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL_NAME",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_API_KEY",
)
EXTRACTED_SOURCE = "extracted"


class SmokeError(RuntimeError):
    """Raised when extracted schema parity expectations fail."""


def main() -> int:
    try:
        with _temporary_env({"KNOWLEDGE_BACKEND": "extracted"}):
            result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Extracted schema parity smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Extracted schema parity smoke passed")
    print(f"- source: {result['source']}")
    print(f"- document status: {result['document_status']}")
    print(f"- evidence source_type: {result['evidence_source_type']}")
    print(f"- wiki source: {result['wiki_source']}")
    print(f"- frontend schemas checked: {result['frontend_schemas']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    explicit_engine = create_knowledge_engine("extracted")
    _assert(
        isinstance(explicit_engine, ExtractedKnowledgeBackend),
        "factory did not return extracted when explicitly selected",
    )

    backend = _backend()
    with TemporaryDirectory() as temp_dir:
        document_path = Path(temp_dir) / "extracted-schema-parity.md"
        document_path.write_text(
            "# Extracted schema parity\n\n"
            "A sanitized fixture about policy schema parity, citation trace, "
            "and local extracted fallback retrieval.\n",
            encoding="utf-8",
        )
        document = backend.upload_document(
            str(document_path),
            {
                "document_id": "pa-doc-extracted-parity",
                "title": "Extracted Schema Parity",
                "business_area": "policy",
                "document_type": "runbook",
            },
        )
        _assert_document(document)
        uploaded_status = backend.get_document_status(str(document.external_doc_id))
        _assert_status(uploaded_status, "uploaded")
        indexed_status = backend.index_document(str(document.external_doc_id))
        _assert_status(indexed_status, "indexed")
        chunks = backend.list_document_chunks(str(document.external_doc_id))
        _assert_chunks(chunks)
        evidence_items = backend.retrieve("schema parity citation trace", top_k=3)

    _assert_evidence(evidence_items)
    _assert_citation_checker(evidence_items)
    _assert_frontend_citation_schema(evidence_items[0])

    summaries = backend.search_wiki("parity", kb_id="kb-extracted-parity", limit=5)
    _assert(summaries, "extracted wiki search returned no summaries")
    summary = summaries[0]
    _assert(summary.source == EXTRACTED_SOURCE, "wiki summary source is not extracted")
    _assert_schema_metadata(summary.metadata, "wiki summary")

    page = backend.read_wiki_page("extracted-parity", kb_id="kb-extracted-parity")
    _assert(page is not None, "extracted wiki page was not readable")
    _assert(page.source == EXTRACTED_SOURCE, "wiki page source is not extracted")
    _assert_schema_metadata(page.metadata, "wiki page")
    _assert(page.citations, "wiki page citation fixture missing")
    _assert_evidence(page.citations)
    _assert_frontend_wiki_schema(page)

    return {
        "source": document.source,
        "document_status": indexed_status["status"],
        "evidence_source_type": evidence_items[0].source_type,
        "wiki_source": page.source,
        "frontend_schemas": "CitationRead/EvidenceRead/WikiPageRead",
    }


def _backend() -> ExtractedKnowledgeBackend:
    wiki_store = InMemoryWikiStore(
        [
            WikiPage(
                slug="extracted-parity",
                title="Extracted Parity Wiki",
                page_type="policy",
                summary="Sanitized parity wiki summary.",
                content="Sanitized parity wiki body with citation trace.",
                citations=[
                    Evidence(
                        document_id="pa-doc-extracted-parity",
                        external_doc_id="extracted_doc_fixture",
                        chunk_id="extracted_doc_fixture:0",
                        title="Extracted Parity Wiki",
                        text="Sanitized wiki citation excerpt.",
                        score=0.77,
                        source="wiki",
                        metadata={"source_type": "document"},
                    )
                ],
                source="wiki",
                metadata={
                    "id": "wiki-local-extracted-parity",
                    "kb_id": "kb-extracted-parity",
                    "status": "published",
                },
            )
        ]
    )
    return ExtractedKnowledgeBackend(
        config=ExtractedBackendConfig(source=EXTRACTED_SOURCE, backend_name=EXTRACTED_SOURCE),
        components=ExtractedBackendComponents(
            vector_store=MockVectorStore(name="extracted-schema-parity"),
            wiki_store=wiki_store,
        ),
        embedding_provider=MockEmbeddingProvider(
            EmbeddingProviderConfig(
                provider="mock",
                model_name="extracted-schema-parity",
                dimension=16,
            )
        ),
    )


def _assert_document(document: Any) -> None:
    _assert(document.source == EXTRACTED_SOURCE, "document source is not extracted")
    _assert(document.external_doc_id, "document missing external_doc_id")
    _assert_schema_metadata(document.metadata, "document")


def _assert_status(status: dict[str, Any], expected_status: str) -> None:
    _assert(status.get("source") == EXTRACTED_SOURCE, "status source is not extracted")
    _assert(status.get("status") == expected_status, f"status mismatch: {status}")
    _assert("message" in status, "status missing message")
    _assert("failed_step" in status, "status missing failed_step")
    _assert("error_message" in status, "status missing error_message")
    _assert_schema_metadata(status.get("metadata"), "document status")


def _assert_chunks(chunks: list[dict[str, Any]]) -> None:
    _assert(chunks, "list_document_chunks returned no chunks")
    first = chunks[0]
    _assert(first.get("source") == EXTRACTED_SOURCE, "chunk source is not extracted")
    _assert(first.get("id"), "chunk missing id")
    _assert(first.get("external_doc_id"), "chunk missing external_doc_id")
    _assert_schema_metadata(first.get("metadata"), "chunk")


def _assert_evidence(items: list[Evidence]) -> None:
    _assert(items, "evidence list is empty")
    for evidence in items:
        _assert(evidence.source == EXTRACTED_SOURCE, "evidence source is not extracted")
        _assert(evidence.source != "weknora_api", "fallback evidence is mislabeled weknora_api")
        _assert(evidence.evidence_id, "evidence missing evidence_id")
        _assert(
            evidence.source_type in {"document_chunk", "wiki_page"},
            f"bad evidence source_type: {evidence.source_type}",
        )
        if evidence.source_type == "document_chunk":
            _assert(evidence.chunk_id, "document evidence missing chunk_id")
            _assert(
                evidence.document_id or evidence.external_doc_id,
                "document evidence missing document id",
            )
        if evidence.source_type == "wiki_page":
            _assert(evidence.wiki_page_id, "wiki evidence missing wiki_page_id")
        _assert_schema_metadata(evidence.metadata, "evidence")
        binding = evidence.metadata.get("citation_binding")
        _assert(isinstance(binding, dict), "evidence missing citation_binding")
        binding_metadata = binding.get("metadata")
        _assert(
            isinstance(binding_metadata, dict)
            and binding_metadata.get("source") == EXTRACTED_SOURCE,
            "citation_binding metadata source is not extracted",
        )


def _assert_citation_checker(evidence_items: list[Evidence]) -> None:
    citations = [
        Citation(
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
        for evidence in evidence_items
    ]
    result = CitationChecker().validate(citations, evidence_items=evidence_items)
    _assert(result.valid, "CitationChecker rejected extracted evidence: " + "; ".join(result.warnings))


def _assert_frontend_citation_schema(evidence: Evidence) -> None:
    citation = CitationRead(
        id="citation-extracted-parity",
        task_id=None,
        output_id=None,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        title=evidence.title,
        text=evidence.text,
        score=evidence.score,
        source=evidence.source,
        evidence_id=None,
        source_type=None,
        wiki_page_id=None,
        metadata_json=json.dumps(evidence.metadata, default=str),
        created_at=datetime.now(UTC),
    )
    _assert(citation.source_type == evidence.source_type, "CitationRead source_type hydration failed")
    _assert(citation.evidence_id == evidence.evidence_id, "CitationRead evidence_id hydration failed")
    evidence_read = EvidenceRead(
        evidence_id=evidence.evidence_id,
        source_type=evidence.source_type,
        document_id=evidence.document_id,
        external_doc_id=evidence.external_doc_id,
        chunk_id=evidence.chunk_id,
        wiki_page_id=evidence.wiki_page_id,
        title=evidence.title,
        text=evidence.text,
        score=evidence.score,
        source=evidence.source,
        metadata=evidence.metadata,
    )
    _assert(evidence_read.source == EXTRACTED_SOURCE, "EvidenceRead source mismatch")


def _assert_frontend_wiki_schema(page: WikiPage) -> None:
    wiki = WikiPageRead(
        id=page.metadata.get("id"),
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        summary=page.summary,
        content=page.content,
        content_markdown=page.content,
        citations=[
            EvidenceRead(
                evidence_id=evidence.evidence_id,
                source_type=evidence.source_type,
                document_id=evidence.document_id,
                external_doc_id=evidence.external_doc_id,
                chunk_id=evidence.chunk_id,
                wiki_page_id=evidence.wiki_page_id,
                title=evidence.title,
                text=evidence.text,
                score=evidence.score,
                source=evidence.source,
                metadata=evidence.metadata,
            )
            for evidence in page.citations
        ],
        source=page.source,
        metadata=page.metadata,
    )
    _assert(wiki.source == EXTRACTED_SOURCE, "WikiPageRead source mismatch")
    _assert(wiki.citations[0].source == EXTRACTED_SOURCE, "WikiPageRead citation source mismatch")


def _assert_schema_metadata(value: object, label: str) -> None:
    _assert(isinstance(value, dict), f"{label} metadata is not a dict")
    metadata = value
    _assert(metadata.get("source") == EXTRACTED_SOURCE, f"{label} metadata source mismatch")
    _assert(metadata.get("fallback_backend") == EXTRACTED_SOURCE, f"{label} missing fallback backend")
    _assert(metadata.get("fallback_explicit") is True, f"{label} fallback is not explicit")
    _assert(metadata.get("schema_parity") == "weknora_api_pa_schema", f"{label} schema parity missing")
    _assert("weknora_api" not in {metadata.get("source"), metadata.get("fallback_backend")}, f"{label} spoofed WeKnora")


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


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


if __name__ == "__main__":
    raise SystemExit(main())
