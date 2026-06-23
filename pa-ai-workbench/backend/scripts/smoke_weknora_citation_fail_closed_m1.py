"""Smoke-check fail-closed citation validation for WeKnora evidence.

This fixture smoke covers P3-M1-D6:
- CitationChecker marks malformed non-mock citations invalid.
- generation_service refuses to persist malformed real citations.
- mock citations remain usable for local smoke/demo paths.

The script uses sanitized fixture records and an in-memory database. It does
not require live WeKnora, secrets, uploads, backend/data, or real documents.
"""

from __future__ import annotations

import json
from pathlib import Path
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


from agent.schemas import Citation as AgentCitation  # noqa: E402
from agent.tools.citation_checker import CitationChecker  # noqa: E402
from app import models as _models  # noqa: E402,F401
from app.services.generation_service import create_citation  # noqa: E402
from app.services.generation_service import create_output_with_citations  # noqa: E402
from app.services.generation_service import create_task  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the citation fail-closed contract fails."""


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora citation fail-closed smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora citation fail-closed smoke passed (fixture)")
    print(f"- checker invalid cases: {result['checker_invalid_cases']}")
    print(f"- persistence rejects: {result['persistence_rejects']}")
    print(f"- saved valid citations: {result['saved_valid_citations']}")
    print(f"- mock saved: {result['mock_saved']}")
    return 0


def _run_fixture_smoke() -> dict[str, Any]:
    checker_invalid_cases = _assert_citation_checker_fail_closed()
    persistence = _assert_generation_service_fail_closed()
    return {
        "checker_invalid_cases": checker_invalid_cases,
        **persistence,
    }


def _assert_citation_checker_fail_closed() -> int:
    checker = CitationChecker()
    invalid_cases = [
        (
            _citation(metadata={"citation_source_type": "document_chunk"}, chunk_id="chunk-1"),
            "missing an evidence id",
        ),
        (
            _citation(
                evidence_id="document_chunk:chunk-1",
                metadata={},
                chunk_id="chunk-1",
                external_doc_id="wk-doc-1",
            ),
            "missing a source type",
        ),
        (
            _citation(
                evidence_id="document_chunk:chunk-1",
                metadata={"citation_source_type": "document_chunk"},
                chunk_id=None,
                external_doc_id="wk-doc-1",
            ),
            "missing a chunk id",
        ),
        (
            _citation(
                evidence_id="document_chunk:chunk-1",
                metadata={"citation_source_type": "document_chunk"},
                chunk_id="chunk-1",
                external_doc_id=None,
            ),
            "missing a document id",
        ),
        (
            _citation(
                evidence_id="wiki_page:wiki-1",
                metadata={"citation_source_type": "wiki_page"},
                source_type="wiki_page",
                chunk_id=None,
                external_doc_id=None,
                wiki_page_id=None,
            ),
            "missing a wiki page id",
        ),
    ]
    for citation, expected_warning in invalid_cases:
        result = checker.validate([citation], evidence_items=[citation])
        if result.valid:
            raise SmokeError(f"invalid citation unexpectedly passed: {citation}")
        if not any(expected_warning in warning for warning in result.warnings):
            raise SmokeError(
                f"expected warning '{expected_warning}', got {result.warnings}"
            )

    valid_document = _citation(
        evidence_id="document_chunk:chunk-valid",
        metadata={"citation_source_type": "document_chunk"},
        chunk_id="chunk-valid",
        external_doc_id="wk-doc-valid",
        text="Sanitized valid document evidence.",
    )
    valid_wiki = _citation(
        evidence_id="wiki_page:wiki-valid",
        metadata={"citation_source_type": "wiki_page", "wiki_page_id": "wiki-valid"},
        source_type="wiki_page",
        chunk_id=None,
        external_doc_id=None,
        wiki_page_id="wiki-valid",
        text="Sanitized valid wiki evidence.",
    )
    result = checker.validate(
        [valid_document, valid_wiki],
        evidence_items=[valid_document, valid_wiki],
    )
    if not result.valid:
        raise SmokeError("valid citations failed: " + "; ".join(result.warnings))
    return len(invalid_cases)


def _assert_generation_service_fail_closed() -> dict[str, Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        task = create_task(session=session, task_type="knowledge_qa", title="D6 fixture")
        invalid_payloads = [
            (
                _generation_citation(
                    metadata={"citation_source_type": "document_chunk"},
                    chunk_id="chunk-1",
                    external_doc_id="wk-doc-1",
                ),
                "evidence id",
            ),
            (
                _generation_citation(
                    metadata={"evidence_id": "document_chunk:chunk-1"},
                    chunk_id="chunk-1",
                    external_doc_id="wk-doc-1",
                ),
                "source type",
            ),
            (
                _generation_citation(
                    metadata={
                        "evidence_id": "document_chunk:chunk-1",
                        "citation_source_type": "document_chunk",
                    },
                    chunk_id=None,
                    external_doc_id="wk-doc-1",
                ),
                "chunk_id",
            ),
            (
                _generation_citation(
                    metadata={
                        "evidence_id": "document_chunk:chunk-1",
                        "citation_source_type": "document_chunk",
                    },
                    chunk_id="chunk-1",
                    external_doc_id=None,
                ),
                "document id",
            ),
            (
                _generation_citation(
                    metadata={
                        "evidence_id": "wiki_page:wiki-1",
                        "citation_source_type": "wiki_page",
                    },
                    chunk_id=None,
                    external_doc_id=None,
                ),
                "wiki_page_id",
            ),
        ]
        rejects = 0
        for payload, expected_message in invalid_payloads:
            try:
                create_output_with_citations(
                    session=session,
                    task=task,
                    title="invalid citation output",
                    citations=[payload],
                    content_markdown="invalid citation output",
                )
            except ValueError as exc:
                if expected_message not in str(exc):
                    raise SmokeError(
                        f"unexpected validation error '{exc}', expected {expected_message}"
                    ) from exc
                rejects += 1
            else:
                raise SmokeError("malformed citation was unexpectedly persisted")

        _, saved = create_output_with_citations(
            session=session,
            task=task,
            title="valid citation output",
            citations=[
                _generation_citation(
                    metadata={
                        "evidence_id": "document_chunk:chunk-valid",
                        "citation_source_type": "document_chunk",
                    },
                    chunk_id="chunk-valid",
                    external_doc_id="wk-doc-valid",
                    text="Sanitized valid document evidence.",
                ),
                _generation_citation(
                    metadata={
                        "evidence_id": "wiki_page:wiki-valid",
                        "citation_source_type": "wiki_page",
                        "wiki_page_id": "wiki-valid",
                    },
                    chunk_id=None,
                    external_doc_id=None,
                    text="Sanitized valid wiki evidence.",
                ),
            ],
            content_markdown="valid citation output",
        )
        if len(saved) != 2:
            raise SmokeError(f"expected 2 valid citations saved, got {len(saved)}")

        mock = create_citation(
            session=session,
            task_id=task.id,
            title="Mock Citation",
            text="Mock citation remains available for local smoke.",
            source="mock",
        )
        return {
            "persistence_rejects": rejects,
            "saved_valid_citations": len(saved),
            "mock_saved": bool(mock.id),
        }


def _citation(
    metadata: dict[str, Any],
    evidence_id: str | None = None,
    source_type: str | None = None,
    chunk_id: str | None = "chunk-1",
    external_doc_id: str | None = "wk-doc-1",
    wiki_page_id: str | None = None,
    text: str = "Sanitized citation evidence.",
) -> AgentCitation:
    return AgentCitation(
        title="D6 Fixture Citation",
        text=text,
        source="weknora_api",
        external_doc_id=external_doc_id,
        chunk_id=chunk_id,
        score=0.5,
        metadata=metadata,
        evidence_id=evidence_id,
        source_type=source_type,
        wiki_page_id=wiki_page_id,
    )


def _generation_citation(
    metadata: dict[str, Any],
    chunk_id: str | None,
    external_doc_id: str | None,
    text: str = "Sanitized citation evidence.",
) -> dict[str, Any]:
    return {
        "title": "D6 Fixture Citation",
        "text": text,
        "source": "weknora_api",
        "external_doc_id": external_doc_id,
        "chunk_id": chunk_id,
        "score": 0.5,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
    }


if __name__ == "__main__":
    raise SystemExit(main())
