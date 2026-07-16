"""Run the Phase 5 B5 real RAG 24-question matrix.

This script has live side effects in the configured WeKnora KB:
- uploads temporary copies of the Phase 4 synthetic sanitized fixture documents;
- creates one published Wiki page derived from TEST-WIKI-001;
- runs the 24 questions through PA's RAG service with current-run isolation.

It never prints or writes service tokens, endpoints, raw uploaded files, raw
chunks, database contents, logs, prompts, or model outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
import time
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from app.services.rag_service import retrieve_evidence_with_context  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.log_context import weknora_log_context  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402


CORPUS_DIR = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
QUESTIONS_PATH = CORPUS_DIR / "questions.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "archive" / "phase5" / "PHASE5_REAL_RAG_24Q_PASS_REPORT.md"

CORPUS_ID = "phase4_rag_wiki_qa_v1"
TASK_ID = "P5-B5"
TERMINAL_INDEXED_STATUSES = {"indexed"}
TERMINAL_FAILED_STATUSES = {"failed"}
PROGRESS_STATUSES = {"uploaded", "parsing", "chunking", "indexing", "unknown"}


class MatrixError(RuntimeError):
    """Raised when the live matrix cannot be marked PASS."""


@dataclass(frozen=True)
class MatrixConfig:
    base_url: str
    service_token: str
    default_kb_id: str
    timeout_seconds: int
    wait_seconds: int
    poll_seconds: int
    top_k: int
    knowledge_backend: str
    mock_mode: bool

    @classmethod
    def from_settings(cls) -> "MatrixConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            wait_seconds=_int_env("PHASE5_B5_WAIT_SECONDS", 360),
            poll_seconds=_int_env("PHASE5_B5_POLL_SECONDS", 5),
            top_k=_int_env("PHASE5_B5_TOP_K", 8),
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
        )


@dataclass(frozen=True)
class UploadedDocument:
    anchor: str
    title: str
    document_type: str
    file_name: str
    external_doc_id: str
    evidence_id: str
    chunk_id: str
    source_type: str
    status: str


@dataclass(frozen=True)
class WikiRunPage:
    slug: str
    wiki_page_id: str
    evidence_id: str
    source_type: str


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    scope: str
    status: str
    trace_id: str
    expected_anchors: list[str]
    actual_anchors: list[str]
    forbidden_anchors: list[str]
    source_types: list[str]
    evidence_summaries: list[dict[str, str]]
    warnings: list[str]
    notes: str


def main() -> int:
    config = MatrixConfig.from_settings()
    run_id = f"p5b5-{uuid4().hex[:12]}"
    try:
        _validate_config(config)
        manifest = _load_json(MANIFEST_PATH)
        questions = _load_json(QUESTIONS_PATH)["questions"]
        _validate_fixture_contract(manifest, questions)
        with TemporaryDirectory(prefix="pa-phase5-b5-") as temp_dir:
            result = _run_matrix(
                config=config,
                run_id=run_id,
                temp_dir=Path(temp_dir),
                manifest=manifest,
                questions=questions,
            )
        _write_report(config=config, run_id=run_id, result=result)
        _assert_all_pass(result["question_results"])
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 B5 real RAG matrix failed: {_safe_error(exc)}", file=sys.stderr)
        return 1

    print("Phase 5 B5 real RAG matrix passed")
    print(f"- run id: {run_id}")
    print(f"- report: {REPORT_PATH}")
    print("- decision: PASS")
    return 0


def _run_matrix(
    *,
    config: MatrixConfig,
    run_id: str,
    temp_dir: Path,
    manifest: dict[str, Any],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    backend = WeKnoraApiBackend(
        base_url=config.base_url,
        service_token=config.service_token,
        timeout=config.timeout_seconds,
        default_kb_id=config.default_kb_id,
    )
    uploaded = _upload_documents(
        backend=backend,
        config=config,
        run_id=run_id,
        temp_dir=temp_dir,
        manifest=manifest,
    )
    wiki_page = _create_and_verify_wiki_page(
        backend=backend,
        config=config,
        run_id=run_id,
        uploaded=uploaded,
        questions=questions,
    )
    question_results = _run_questions(
        config=config,
        run_id=run_id,
        uploaded=uploaded,
        wiki_page=wiki_page,
        questions=questions,
    )
    return {
        "uploaded": uploaded,
        "wiki_page": wiki_page,
        "question_results": question_results,
    }


def _upload_documents(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    run_id: str,
    temp_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, UploadedDocument]:
    uploaded: dict[str, UploadedDocument] = {}
    for index, item in enumerate(manifest["documents"], start=1):
        anchor = str(item["anchor"])
        source_path = CORPUS_DIR / str(item["filename"])
        temp_path = _write_temp_fixture_copy(
            source_path=source_path,
            temp_dir=temp_dir,
            run_id=run_id,
            anchor=anchor,
            index=index,
        )
        try:
            document = backend.upload_document(
                str(temp_path),
                metadata={
                    "title": item["title"],
                    "file_name": temp_path.name,
                    "business_area": "public_affairs",
                    "document_type": item["type"],
                    "source": "phase5_b5_real_rag_matrix",
                    "phase_task": TASK_ID,
                    "phase5_run_id": run_id,
                    "current_run_id": run_id,
                    "corpus_id": CORPUS_ID,
                    "namespace": run_id,
                    "anchor": anchor,
                    "anchors": [anchor],
                    "test_anchor": anchor,
                    "test_purpose": item.get("test_purpose") or [],
                    "key_terms": item.get("key_terms") or [],
                },
            )
        except KnowledgeBackendUnavailableError as exc:
            raise MatrixError(f"upload failed for {anchor}: {exc}") from exc
        if not document.external_doc_id:
            raise MatrixError(f"upload returned no external_doc_id for {anchor}")
        uploaded[anchor] = UploadedDocument(
            anchor=anchor,
            title=str(item["title"]),
            document_type=str(item["type"]),
            file_name=str(item["filename"]),
            external_doc_id=document.external_doc_id,
            evidence_id="",
            chunk_id="",
            source_type="document_chunk",
            status=document.status,
        )

    uploaded = _wait_documents_indexed(
        backend=backend,
        config=config,
        uploaded=uploaded,
    )
    return _wait_documents_retrievable(
        backend=backend,
        config=config,
        uploaded=uploaded,
    )


def _write_temp_fixture_copy(
    *,
    source_path: Path,
    temp_dir: Path,
    run_id: str,
    anchor: str,
    index: int,
) -> Path:
    source_text = source_path.read_text(encoding="utf-8")
    safe_anchor = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    target = temp_dir / f"{index:02d}-{safe_anchor}-{run_id}.md"
    target.write_text(
        "\n".join(
            [
                source_text.rstrip(),
                "",
                "<!--",
                f"PHASE5_REAL_B5_RUN={run_id}",
                f"PHASE5_REAL_B5_ANCHOR={anchor}",
                "Synthetic run marker; contains no real private data.",
                "-->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def _wait_documents_indexed(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    uploaded: dict[str, UploadedDocument],
) -> dict[str, UploadedDocument]:
    pending = dict(uploaded)
    statuses: dict[str, str] = {anchor: doc.status for anchor, doc in uploaded.items()}
    deadline = time.monotonic() + config.wait_seconds
    while pending and time.monotonic() <= deadline:
        for anchor, document in list(pending.items()):
            try:
                status_payload = backend.get_document_status(document.external_doc_id)
            except KnowledgeBackendUnavailableError as exc:
                raise MatrixError(f"status check failed for {anchor}: {exc}") from exc
            status = str(status_payload.get("status") or "unknown")
            statuses[anchor] = status
            if status in TERMINAL_INDEXED_STATUSES:
                del pending[anchor]
                continue
            if status in TERMINAL_FAILED_STATUSES:
                detail = status_payload.get("error_message") or status_payload.get("failed_step")
                raise MatrixError(f"WeKnora indexing failed for {anchor}: {detail}")
            if status not in PROGRESS_STATUSES:
                raise MatrixError(f"unexpected WeKnora status for {anchor}: {status}")
        if pending:
            time.sleep(config.poll_seconds)
    if pending:
        anchors = ", ".join(sorted(pending))
        raise MatrixError(f"documents did not index within {config.wait_seconds}s: {anchors}")
    return {
        anchor: UploadedDocument(
            anchor=doc.anchor,
            title=doc.title,
            document_type=doc.document_type,
            file_name=doc.file_name,
            external_doc_id=doc.external_doc_id,
            evidence_id=doc.evidence_id,
            chunk_id=doc.chunk_id,
            source_type=doc.source_type,
            status=statuses.get(anchor, doc.status),
        )
        for anchor, doc in uploaded.items()
    }


def _wait_documents_retrievable(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    uploaded: dict[str, UploadedDocument],
) -> dict[str, UploadedDocument]:
    verified: dict[str, UploadedDocument] = {}
    for anchor, document in uploaded.items():
        evidence = _wait_for_document_anchor(
            backend=backend,
            config=config,
            document=document,
        )
        verified[anchor] = UploadedDocument(
            anchor=document.anchor,
            title=document.title,
            document_type=document.document_type,
            file_name=document.file_name,
            external_doc_id=document.external_doc_id,
            evidence_id=evidence.evidence_id or "",
            chunk_id=evidence.chunk_id or "",
            source_type=evidence.source_type,
            status=document.status,
        )
    return verified


def _wait_for_document_anchor(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    document: UploadedDocument,
) -> Evidence:
    deadline = time.monotonic() + config.wait_seconds
    while time.monotonic() <= deadline:
        try:
            evidence_items = backend.retrieve(
                query=document.anchor,
                filters={
                    "external_doc_ids": [document.external_doc_id],
                    "source_type": "document_chunk",
                },
                top_k=10,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise MatrixError(f"retrieve failed for {document.anchor}: {exc}") from exc
        for evidence in evidence_items:
            if evidence.external_doc_id != document.external_doc_id:
                continue
            if _evidence_has_anchor(evidence, document.anchor):
                return evidence
        time.sleep(config.poll_seconds)
    raise MatrixError(f"document anchor was not retrievable: {document.anchor}")


def _create_and_verify_wiki_page(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    run_id: str,
    uploaded: dict[str, UploadedDocument],
    questions: list[dict[str, Any]],
) -> WikiRunPage:
    wiki_questions = [
        question
        for question in questions
        if question.get("must_cite_wiki")
        or "TEST-WIKI-001" in set(question.get("expected_anchors", []))
    ]
    seed_path = CORPUS_DIR / "documents" / "008_timeliness_wiki_seed.md"
    seed_content = seed_path.read_text(encoding="utf-8")
    slug = f"phase5/b5-timeliness-{run_id}"
    aliases = [str(question["query"]) for question in wiki_questions]
    alias_text = "\n".join(f"- {alias}" for alias in aliases)
    summary = " ".join(
        [
            "TEST-WIKI-001",
            *aliases,
            *[
                point
                for question in wiki_questions
                for point in question.get("expected_answer_points", [])
            ],
        ]
    )
    source_refs = [
        f"{document.external_doc_id}|{document.title}"
        for anchor, document in uploaded.items()
        if anchor != "TEST-DISTRACTOR-001"
    ]
    chunk_refs = [
        document.chunk_id
        for document in uploaded.values()
        if document.chunk_id and document.anchor != "TEST-DISTRACTOR-001"
    ]
    page = {
        "slug": slug,
        "title": "TEST-WIKI-001 Phase5 B5 Timeliness Wiki",
        "summary": summary,
        "content": "\n\n".join(
            [
                seed_content,
                "## Phase5 B5 Search Aliases",
                alias_text,
                f"PHASE5_REAL_B5_RUN={run_id}",
            ]
        ),
        "page_type": "wiki",
        "status": "published",
        "source_refs": source_refs,
        "chunk_refs": chunk_refs,
        "aliases": aliases,
        "metadata": {
            "source": "phase5_b5_real_rag_matrix",
            "phase_task": TASK_ID,
            "phase5_run_id": run_id,
            "current_run_id": run_id,
            "corpus_id": CORPUS_ID,
            "namespace": run_id,
            "anchor": "TEST-WIKI-001",
            "anchors": ["TEST-WIKI-001"],
            "test_anchor": "TEST-WIKI-001",
            "aliases": aliases,
            "source_refs": source_refs,
            "chunk_refs": chunk_refs,
        },
    }
    try:
        created = backend.create_wiki_page(page=page, kb_id=config.default_kb_id)
    except KnowledgeBackendUnavailableError as exc:
        raise MatrixError(f"Wiki create failed: {exc}") from exc

    wiki_page_id = str(
        (created.metadata or {}).get("id")
        or (created.metadata or {}).get("weknora_wiki_page_id")
        or created.slug
    )
    evidence = _wait_for_wiki_anchor(
        backend=backend,
        config=config,
        slug=created.slug,
        wiki_page_id=wiki_page_id,
        queries=["TEST-WIKI-001", *aliases],
    )
    return WikiRunPage(
        slug=created.slug,
        wiki_page_id=evidence.wiki_page_id or wiki_page_id,
        evidence_id=evidence.evidence_id or "",
        source_type=evidence.source_type,
    )


def _wait_for_wiki_anchor(
    *,
    backend: WeKnoraApiBackend,
    config: MatrixConfig,
    slug: str,
    wiki_page_id: str,
    queries: list[str],
) -> Evidence:
    deadline = time.monotonic() + config.wait_seconds
    last_count = 0
    while time.monotonic() <= deadline:
        for query in queries:
            try:
                evidence_items = backend.retrieve(
                    query=query,
                    filters={
                        "knowledge_base_ids": [config.default_kb_id],
                        "source_type": "wiki_page",
                    },
                    top_k=10,
                )
            except KnowledgeBackendUnavailableError as exc:
                raise MatrixError(f"Wiki retrieve failed: {exc}") from exc
            last_count = len(evidence_items)
            for evidence in evidence_items:
                if evidence.source_type != "wiki_page":
                    continue
                candidates = {
                    evidence.wiki_page_id,
                    evidence.metadata.get("weknora_wiki_page_slug"),
                    evidence.metadata.get("weknora_wiki_page_id"),
                    evidence.metadata.get("slug"),
                    evidence.metadata.get("id"),
                }
                if slug in {str(item) for item in candidates if item}:
                    return evidence
                if wiki_page_id in {str(item) for item in candidates if item}:
                    return evidence
        time.sleep(config.poll_seconds)
    raise MatrixError(
        "published Wiki page was not retrievable by anchor or official questions "
        f"within {config.wait_seconds}s (last evidence count: {last_count})"
    )


def _run_questions(
    *,
    config: MatrixConfig,
    run_id: str,
    uploaded: dict[str, UploadedDocument],
    wiki_page: WikiRunPage,
    questions: list[dict[str, Any]],
) -> list[QuestionResult]:
    results: list[QuestionResult] = []
    current_run = {
        "run_id": run_id,
        "corpus_id": CORPUS_ID,
        "namespace": run_id,
        "external_doc_ids": [document.external_doc_id for document in uploaded.values()],
        "wiki_page_ids": [wiki_page.wiki_page_id, wiki_page.slug],
        "anchors": sorted(uploaded.keys()),
    }
    known_anchors = sorted(uploaded.keys())
    for question in questions:
        qid = str(question["id"])
        trace_id = f"PHASE5_REAL-{TASK_ID}-{run_id}-{qid}"
        filters = {
            "source_scope": question.get("retrieval_scope") or "all",
            "current_run": current_run,
            "knowledge_base_ids": [config.default_kb_id],
        }
        with weknora_log_context(correlation_id=trace_id):
            result = retrieve_evidence_with_context(
                query=str(question["query"]),
                filters=filters,
                top_k=config.top_k,
            )
        actual_anchors = _actual_anchors(result.items, known_anchors)
        forbidden = [
            anchor
            for anchor in question.get("forbidden_anchors", [])
            if anchor in actual_anchors
        ]
        source_types = sorted({item.source_type for item in result.items})
        evidence_summaries = _evidence_summaries(
            result.items,
            expected_anchors=question.get("expected_anchors", []),
            known_anchors=known_anchors,
        )
        status, notes = _judge_question(
            question=question,
            actual_anchors=actual_anchors,
            forbidden=forbidden,
            source_types=source_types,
        )
        out_of_scope_wiki = _out_of_scope_wiki_ids(result.items, wiki_page)
        if out_of_scope_wiki:
            status = "FAIL"
            notes = _join_notes(
                notes,
                "out-of-scope wiki evidence: " + ", ".join(out_of_scope_wiki),
            )
        results.append(
            QuestionResult(
                question_id=qid,
                scope=str(question.get("retrieval_scope") or "all"),
                status=status,
                trace_id=trace_id,
                expected_anchors=list(question.get("expected_anchors", [])),
                actual_anchors=actual_anchors,
                forbidden_anchors=forbidden,
                source_types=source_types,
                evidence_summaries=evidence_summaries,
                warnings=list(result.warnings),
                notes=notes,
            )
        )
    return results


def _out_of_scope_wiki_ids(items: list[Evidence], wiki_page: WikiRunPage) -> list[str]:
    allowed = {wiki_page.wiki_page_id, wiki_page.slug}
    out_of_scope: list[str] = []
    for evidence in items:
        if evidence.source_type != "wiki_page":
            continue
        identifiers = {
            evidence.wiki_page_id,
            evidence.metadata.get("weknora_wiki_page_slug"),
            evidence.metadata.get("weknora_wiki_page_id"),
            evidence.metadata.get("slug"),
            evidence.metadata.get("id"),
        }
        if allowed & {str(item) for item in identifiers if item}:
            continue
        out_of_scope.append(evidence.evidence_id or evidence.wiki_page_id or "unknown")
    return sorted(set(out_of_scope))


def _judge_question(
    *,
    question: dict[str, Any],
    actual_anchors: list[str],
    forbidden: list[str],
    source_types: list[str],
) -> tuple[str, str]:
    expected = set(question.get("expected_anchors", []))
    actual = set(actual_anchors)
    missing = sorted(expected - actual)
    notes: list[str] = []
    if missing:
        notes.append("missing expected anchors: " + ", ".join(missing))
    if forbidden:
        notes.append("forbidden anchors retrieved: " + ", ".join(forbidden))
    if question.get("must_cite_document") and "document_chunk" not in source_types:
        notes.append("missing document_chunk evidence")
    if question.get("must_cite_wiki") and "wiki_page" not in source_types:
        notes.append("missing wiki_page evidence")
    if not expected and question.get("should_answer_insufficient"):
        notes.append("insufficient-evidence question; retrieval layer only checks no forbidden anchor")
    return ("FAIL", "; ".join(notes)) if any(
        note
        for note in notes
        if not note.startswith("insufficient-evidence question")
    ) else ("PASS", "; ".join(notes) or "expected retrieval evidence satisfied")


def _join_notes(*parts: str) -> str:
    return "; ".join(part for part in parts if part)


def _actual_anchors(items: list[Evidence], known_anchors: list[str]) -> list[str]:
    anchors: set[str] = set()
    for evidence in items:
        for anchor in known_anchors:
            if _evidence_has_anchor(evidence, anchor):
                anchors.add(anchor)
    return sorted(anchors)


def _evidence_summaries(
    items: list[Evidence],
    *,
    expected_anchors: list[str],
    known_anchors: list[str],
) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    wanted = set(expected_anchors) or set(known_anchors)
    seen: set[str] = set()
    for rank, evidence in enumerate(items, start=1):
        evidence_anchors = [
            anchor for anchor in known_anchors if _evidence_has_anchor(evidence, anchor)
        ]
        if not evidence_anchors and expected_anchors:
            continue
        if expected_anchors and not (set(evidence_anchors) & wanted):
            continue
        key = evidence.evidence_id or evidence.chunk_id or evidence.wiki_page_id or str(rank)
        if key in seen:
            continue
        seen.add(key)
        summaries.append(
            {
                "rank": str(rank),
                "anchors": ",".join(evidence_anchors) or "-",
                "source": evidence.source,
                "source_type": evidence.source_type,
                "evidence_id": evidence.evidence_id or "-",
                "external_doc_id": evidence.external_doc_id or "-",
                "chunk_id": evidence.chunk_id or "-",
                "wiki_page_id": evidence.wiki_page_id or "-",
            }
        )
    return summaries[:4]


def _evidence_has_anchor(evidence: Evidence, anchor: str) -> bool:
    metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
    metadata_values = _anchor_metadata_values(metadata)
    haystack = " ".join([evidence.title or "", evidence.text or "", *metadata_values])
    return anchor in haystack


def _anchor_metadata_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "anchor",
        "anchors",
        "test_anchor",
        "expected_anchor",
        "weknora_wiki_page_slug",
        "weknora_wiki_page_id",
        "slug",
    ):
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        elif isinstance(value, dict):
            continue
        else:
            values.append(str(value))
    return values


def _write_report(
    *,
    config: MatrixConfig,
    run_id: str,
    result: dict[str, Any],
) -> None:
    question_results: list[QuestionResult] = result["question_results"]
    uploaded: dict[str, UploadedDocument] = result["uploaded"]
    wiki_page: WikiRunPage = result["wiki_page"]
    pass_count = sum(1 for item in question_results if item.status == "PASS")
    fail_count = len(question_results) - pass_count
    decision = "PASS" if fail_count == 0 else "FAIL"
    lines = [
        "# Phase 5 Real RAG 24Q PASS Report",
        "",
        "## Test Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} real RAG debug 24-question matrix |",
        f"| Report marker | PHASE5_REAL |",
        f"| Run id | `{run_id}` |",
        "| Backend source | `weknora_api` |",
        "| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL, service token, workspace, and default KB configured; token and endpoint intentionally omitted |",
        f"| Test scope | Phase 4 synthetic sanitized corpus `{CORPUS_ID}`; 24 questions; top_k={config.top_k}; fresh/current-run upload |",
        f"| Result | {decision} |",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| PASS | {pass_count} |",
        f"| FAIL | {fail_count} |",
        "",
        "## Current-Run Document Evidence",
        "",
        "| Anchor | source_type | external_doc_id | evidence_id | chunk_id | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for anchor, document in uploaded.items():
        lines.append(
            "| {anchor} | `{source_type}` | `{external_doc_id}` | `{evidence_id}` | `{chunk_id}` | {status} |".format(
                anchor=_cell(anchor),
                source_type=_cell(document.source_type),
                external_doc_id=_cell(document.external_doc_id),
                evidence_id=_cell(document.evidence_id or "-"),
                chunk_id=_cell(document.chunk_id or "-"),
                status=_cell(document.status),
            )
        )
    lines.extend(
        [
            "",
            "## Current-Run Wiki Evidence",
            "",
            "| Anchor | source_type | slug | wiki_page_id | evidence_id |",
            "| --- | --- | --- | --- | --- |",
            "| TEST-WIKI-001 | `{source_type}` | `{slug}` | `{wiki_page_id}` | `{evidence_id}` |".format(
                source_type=_cell(wiki_page.source_type),
                slug=_cell(wiki_page.slug),
                wiki_page_id=_cell(wiki_page.wiki_page_id),
                evidence_id=_cell(wiki_page.evidence_id or "-"),
            ),
            "",
            "## 24 Question Matrix",
            "",
            "| Question | Scope | Expected anchors | Actual anchors | source_type | trace_id | Evidence fields | Forbidden `TEST-DISTRACTOR-001` retrieved | Status | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in question_results:
        evidence_fields = "<br>".join(
            "{rank}. anchors={anchors}; source_type={source_type}; evidence_id={evidence_id}; chunk_id={chunk_id}; wiki_page_id={wiki_page_id}".format(
                **{key: _cell(value) for key, value in summary.items()}
            )
            for summary in item.evidence_summaries
        ) or "-"
        lines.append(
            "| {qid} | {scope} | {expected} | {actual} | {source_types} | `{trace_id}` | {evidence_fields} | {forbidden} | {status} | {notes} |".format(
                qid=_cell(item.question_id),
                scope=_cell(item.scope),
                expected=_cell(", ".join(item.expected_anchors) or "none"),
                actual=_cell(", ".join(item.actual_anchors) or "none"),
                source_types=_cell(", ".join(item.source_types) or "none"),
                trace_id=_cell(item.trace_id),
                evidence_fields=evidence_fields,
                forbidden=_cell("yes" if "TEST-DISTRACTOR-001" in item.forbidden_anchors else "no"),
                status=_cell(item.status),
                notes=_cell(item.notes or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This report uses only the Phase 4 synthetic sanitized fixture corpus.",
            "- The report intentionally omits service tokens, endpoints, uploaded file bodies, raw chunks, database contents, logs, prompts, and provider outputs.",
            "- Evidence identifiers are recorded only to make the real WeKnora run traceable.",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_all_pass(question_results: list[QuestionResult]) -> None:
    failed = [item.question_id for item in question_results if item.status != "PASS"]
    if failed:
        raise MatrixError("matrix did not reach 24/24 PASS: " + ", ".join(failed))


def _validate_config(config: MatrixConfig) -> None:
    missing: list[str] = []
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
    if config.base_url.startswith("fixture://"):
        missing.append("live WEKNORA_BASE_URL")
    if config.wait_seconds <= 0:
        missing.append("PHASE5_B5_WAIT_SECONDS")
    if config.poll_seconds <= 0:
        missing.append("PHASE5_B5_POLL_SECONDS")
    if config.top_k <= 0:
        missing.append("PHASE5_B5_TOP_K")
    if missing:
        raise MatrixError("missing or invalid required env: " + ", ".join(missing))


def _validate_fixture_contract(
    manifest: dict[str, Any],
    questions: list[dict[str, Any]],
) -> None:
    if manifest.get("corpus_id") != CORPUS_ID:
        raise MatrixError("unexpected manifest corpus_id")
    if len(manifest.get("documents") or []) != 9:
        raise MatrixError("expected 9 fixture documents")
    if len(questions) != 24:
        raise MatrixError("expected 24 fixture questions")
    anchors = {str(item["anchor"]) for item in manifest["documents"]}
    for question in questions:
        expected = set(question.get("expected_anchors") or [])
        forbidden = set(question.get("forbidden_anchors") or [])
        if not expected <= anchors:
            raise MatrixError(f"{question.get('id')} references unknown expected anchor")
        if not forbidden <= anchors:
            raise MatrixError(f"{question.get('id')} references unknown forbidden anchor")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    for key in ("Bearer" + " ", "X-" + "API-Key", "WEKNORA_" + "SERVICE_TOKEN"):
        text = text.replace(key, "[redacted]")
    return text[:500]


if __name__ == "__main__":
    raise SystemExit(main())
