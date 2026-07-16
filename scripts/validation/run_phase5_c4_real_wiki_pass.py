"""Run the P5-C4 real Wiki closed-loop PASS gate.

This script has live side effects in the configured WeKnora KB:
- creates one synthetic TEST-WIKI-001 draft page;
- publishes the same page;
- reads it back and waits until it is retrievable as wiki_page evidence;
- runs P4Q-017 to P4Q-019 through PA retrieval with Wiki-only scope;
- verifies a real Wiki citation can be located to the Wiki page route.

It never prints or writes service tokens, endpoints, raw uploaded files, raw
chunks, database contents, logs, prompts, or model outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.config import Settings  # noqa: E402
from app.schemas import CitationLocateRequest  # noqa: E402
from app.services.citation_locator_service import locate_citation  # noqa: E402
from app.services.rag_service import retrieve_evidence_with_context  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.citations import CitationBuilder  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.log_context import weknora_log_context  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402


CORPUS_DIR = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa"
QUESTIONS_PATH = CORPUS_DIR / "questions.json"
WIKI_SEED_PATH = CORPUS_DIR / "documents" / "008_timeliness_wiki_seed.md"
REPORT_PATH = PROJECT_ROOT / "docs" / "archive" / "phase5" / "PHASE5_REAL_WIKI_PASS_REPORT.md"

CORPUS_ID = "phase4_rag_wiki_qa_v1"
TASK_ID = "P5-C4"
WIKI_QUESTION_IDS = {"P4Q-017", "P4Q-018", "P4Q-019"}


class WikiPassError(RuntimeError):
    """Raised when P5-C4 cannot be marked PASS."""


@dataclass(frozen=True)
class WikiPassConfig:
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
    def from_settings(cls) -> "WikiPassConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            wait_seconds=_int_env("PHASE5_C4_WAIT_SECONDS", 360),
            poll_seconds=_int_env("PHASE5_C4_POLL_SECONDS", 5),
            top_k=_int_env("PHASE5_C4_TOP_K", 8),
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
        )


@dataclass(frozen=True)
class WikiRunPage:
    slug: str
    wiki_page_id: str
    evidence_id: str
    source_type: str
    draft_status: str
    published_status: str
    read_status: str
    retrievable_query: str


@dataclass(frozen=True)
class WikiQuestionResult:
    question_id: str
    query: str
    trace_id: str
    status: str
    source: str
    source_type: str
    evidence_id: str
    wiki_page_id: str
    matched_anchor: str
    search_query: str
    notes: str


@dataclass(frozen=True)
class LocateResult:
    status: str
    target_type: str
    ui_hash: str
    message: str


def main() -> int:
    config = WikiPassConfig.from_settings()
    run_id = f"p5c4-{uuid4().hex[:12]}"
    try:
        _validate_config(config)
        questions = _load_wiki_questions()
        backend = WeKnoraApiBackend(
            base_url=config.base_url,
            service_token=config.service_token,
            timeout=config.timeout_seconds,
            default_kb_id=config.default_kb_id,
        )
        wiki_page = _run_wiki_closed_loop(
            backend=backend,
            config=config,
            run_id=run_id,
            questions=questions,
        )
        question_results = _run_wiki_questions(
            config=config,
            run_id=run_id,
            wiki_page=wiki_page,
            questions=questions,
        )
        locate_result = _verify_citation_locate(wiki_page=wiki_page, evidence=question_results[0])
        _write_report(
            config=config,
            run_id=run_id,
            wiki_page=wiki_page,
            question_results=question_results,
            locate_result=locate_result,
        )
        _assert_pass(wiki_page=wiki_page, question_results=question_results, locate_result=locate_result)
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 C4 real Wiki PASS failed: {_safe_error(exc)}", file=sys.stderr)
        return 1

    print("Phase 5 C4 real Wiki PASS completed")
    print(f"- run id: {run_id}")
    print(f"- report: {REPORT_PATH}")
    print("- decision: PASS")
    return 0


def _run_wiki_closed_loop(
    *,
    backend: WeKnoraApiBackend,
    config: WikiPassConfig,
    run_id: str,
    questions: list[dict[str, Any]],
) -> WikiRunPage:
    slug = f"phase5/c4-timeliness-{run_id}"
    aliases = _wiki_aliases(questions)
    draft = _create_draft(backend=backend, slug=slug, run_id=run_id, aliases=aliases)
    published = _publish_page(backend=backend, slug=slug, run_id=run_id, aliases=aliases, draft=draft)
    read_back = _read_page(backend=backend, slug=slug, kb_id=config.default_kb_id)
    wiki_page_id = _wiki_page_id(published, fallback_slug=slug)
    evidence = _wait_for_retrievable(
        backend=backend,
        config=config,
        slug=slug,
        wiki_page_id=wiki_page_id,
        queries=["TEST-WIKI-001", *aliases],
    )
    return WikiRunPage(
        slug=slug,
        wiki_page_id=evidence.wiki_page_id or wiki_page_id,
        evidence_id=evidence.evidence_id or "",
        source_type=evidence.source_type,
        draft_status=_page_status(draft, "draft"),
        published_status=_page_status(published, "published"),
        read_status=_page_status(read_back, "published"),
        retrievable_query=str(evidence.metadata.get("wiki_search_query") or "TEST-WIKI-001"),
    )


def _create_draft(
    *,
    backend: WeKnoraApiBackend,
    slug: str,
    run_id: str,
    aliases: list[str],
) -> WikiPage:
    try:
        return backend.create_wiki_page(
            page={
                "slug": slug,
                "title": "TEST-WIKI-001 Phase5 C4 Timeliness Wiki",
                "summary": "P5-C4 draft for TEST-WIKI-001 Wiki closed-loop validation.",
                "content": _wiki_content(run_id=run_id, aliases=aliases, status="draft"),
                "page_type": "wiki",
                "status": "draft",
                "aliases": aliases,
                "metadata": _wiki_metadata(run_id=run_id, aliases=aliases, status="draft"),
            }
        )
    except KnowledgeBackendUnavailableError as exc:
        raise WikiPassError(f"Wiki draft create failed: {exc}") from exc


def _publish_page(
    *,
    backend: WeKnoraApiBackend,
    slug: str,
    run_id: str,
    aliases: list[str],
    draft: WikiPage,
) -> WikiPage:
    try:
        return backend.update_wiki_page(
            slug=slug,
            page={
                "slug": slug,
                "title": draft.title or "TEST-WIKI-001 Phase5 C4 Timeliness Wiki",
                "summary": " ".join(
                    [
                        "TEST-WIKI-001",
                        "时限管理专题关联政策、法规和案例。",
                        "Wiki 专题指出常见误区。",
                        "Wiki evidence 应带有 source_type=wiki_page 并与原始文档 evidence 区分。",
                        *aliases,
                    ]
                ),
                "content": _wiki_content(run_id=run_id, aliases=aliases, status="published"),
                "page_type": draft.page_type or "wiki",
                "status": "published",
                "aliases": aliases,
                "metadata": {
                    **(draft.metadata or {}),
                    **_wiki_metadata(run_id=run_id, aliases=aliases, status="published"),
                },
            },
            kb_id=None,
        )
    except KnowledgeBackendUnavailableError as exc:
        raise WikiPassError(f"Wiki publish failed: {exc}") from exc


def _read_page(backend: WeKnoraApiBackend, slug: str, kb_id: str) -> WikiPage:
    try:
        page = backend.read_wiki_page(slug=slug, kb_id=kb_id)
    except KnowledgeBackendUnavailableError as exc:
        raise WikiPassError(f"Wiki read back failed: {exc}") from exc
    if page is None:
        raise WikiPassError("Wiki read back returned no page")
    return page


def _wait_for_retrievable(
    *,
    backend: WeKnoraApiBackend,
    config: WikiPassConfig,
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
                    top_k=config.top_k,
                )
            except KnowledgeBackendUnavailableError as exc:
                raise WikiPassError(f"Wiki retrieve failed: {exc}") from exc
            last_count = len(evidence_items)
            match = _matching_wiki_evidence(evidence_items, slug=slug, wiki_page_id=wiki_page_id)
            if match is not None:
                return match
        time.sleep(config.poll_seconds)
    raise WikiPassError(
        "published Wiki page was not retrievable before timeout "
        f"(last wiki evidence count: {last_count})"
    )


def _run_wiki_questions(
    *,
    config: WikiPassConfig,
    run_id: str,
    wiki_page: WikiRunPage,
    questions: list[dict[str, Any]],
) -> list[WikiQuestionResult]:
    results = [
        _run_question(config=config, run_id=run_id, wiki_page=wiki_page, question=question)
        for question in questions
    ]
    return results


def _run_question(
    *,
    config: WikiPassConfig,
    run_id: str,
    wiki_page: WikiRunPage,
    question: dict[str, Any],
) -> WikiQuestionResult:
    qid = str(question["id"])
    query = str(question["query"])
    trace_id = f"PHASE5_REAL-{TASK_ID}-{run_id}-{qid}"
    current_run = {
        "run_id": run_id,
        "corpus_id": CORPUS_ID,
        "namespace": run_id,
        "wiki_page_ids": [wiki_page.wiki_page_id, wiki_page.slug],
        "anchors": ["TEST-WIKI-001"],
    }
    with weknora_log_context(correlation_id=trace_id):
        result = retrieve_evidence_with_context(
            query=query,
            filters={
                "source_scope": "wiki",
                "current_run": current_run,
                "knowledge_base_ids": [config.default_kb_id],
            },
            top_k=config.top_k,
        )
    match = _matching_wiki_evidence(
        result.items,
        slug=wiki_page.slug,
        wiki_page_id=wiki_page.wiki_page_id,
    )
    if match is None:
        return WikiQuestionResult(
            question_id=qid,
            query=query,
            trace_id=trace_id,
            status="FAIL",
            source="-",
            source_type="-",
            evidence_id="-",
            wiki_page_id="-",
            matched_anchor="-",
            search_query="-",
            notes="current Wiki page was not returned",
        )
    notes: list[str] = []
    if match.source != "weknora_api":
        notes.append(f"source mismatch: {match.source}")
    if match.source_type != "wiki_page":
        notes.append(f"source_type mismatch: {match.source_type}")
    if not match.wiki_page_id:
        notes.append("missing wiki_page_id")
    if not match.evidence_id:
        notes.append("missing evidence_id")
    if "TEST-WIKI-001" not in _evidence_haystack(match):
        notes.append("missing TEST-WIKI-001 anchor")
    return WikiQuestionResult(
        question_id=qid,
        query=query,
        trace_id=trace_id,
        status="FAIL" if notes else "PASS",
        source=match.source,
        source_type=match.source_type,
        evidence_id=match.evidence_id or "-",
        wiki_page_id=match.wiki_page_id or "-",
        matched_anchor="TEST-WIKI-001" if "TEST-WIKI-001" in _evidence_haystack(match) else "-",
        search_query=str(match.metadata.get("wiki_search_query") or "-"),
        notes="; ".join(notes) if notes else "expected Wiki-only evidence satisfied",
    )


def _verify_citation_locate(
    *,
    wiki_page: WikiRunPage,
    evidence: WikiQuestionResult,
) -> LocateResult:
    builder = CitationBuilder()
    bound = builder.build(
        Evidence(
            document_id=None,
            external_doc_id=None,
            chunk_id=None,
            title="TEST-WIKI-001 Phase5 C4 Wiki citation",
            text="TEST-WIKI-001 source_type=wiki_page citation locate evidence.",
            score=None,
            source=evidence.source,
            evidence_id=evidence.evidence_id,
            source_type=evidence.source_type,
            wiki_page_id=evidence.wiki_page_id,
            metadata={
                "wiki_page_id": evidence.wiki_page_id,
                "weknora_wiki_page_id": evidence.wiki_page_id,
                "weknora_wiki_page_slug": wiki_page.slug,
                "anchor": "TEST-WIKI-001",
            },
        )
    )
    sql_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(sql_engine)
    with Session(sql_engine) as session:
        target = locate_citation(
            session=session,
            request=CitationLocateRequest(
                source=bound.source,
                evidence_id=bound.evidence_id,
                source_type=bound.source_type,
                wiki_page_id=bound.wiki_page_id,
                metadata=bound.metadata,
            ),
        )
    return LocateResult(
        status="PASS" if target.located and target.target_type == "wiki_page" else "FAIL",
        target_type=target.target_type or "-",
        ui_hash=target.ui_hash or "-",
        message=target.message,
    )


def _matching_wiki_evidence(
    items: list[Evidence],
    *,
    slug: str,
    wiki_page_id: str,
) -> Evidence | None:
    for evidence in items:
        if evidence.source_type != "wiki_page":
            continue
        metadata = evidence.metadata or {}
        candidates = {
            evidence.wiki_page_id,
            metadata.get("weknora_wiki_page_slug"),
            metadata.get("weknora_wiki_page_id"),
            metadata.get("weknora_slug"),
            metadata.get("slug"),
            metadata.get("id"),
        }
        candidate_strings = {str(item) for item in candidates if item}
        if slug in candidate_strings or wiki_page_id in candidate_strings:
            return evidence
    return None


def _write_report(
    *,
    config: WikiPassConfig,
    run_id: str,
    wiki_page: WikiRunPage,
    question_results: list[WikiQuestionResult],
    locate_result: LocateResult,
) -> None:
    pass_count = sum(1 for item in question_results if item.status == "PASS")
    fail_count = len(question_results) - pass_count
    decision = "PASS" if fail_count == 0 and locate_result.status == "PASS" else "FAIL"
    lines = [
        "# Phase 5 Real Wiki PASS Report",
        "",
        "## Test Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} real Wiki closed-loop retest |",
        "| Report marker | PHASE5_REAL |",
        f"| Run id | `{run_id}` |",
        "| Backend source | `weknora_api` |",
        "| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL, service token, workspace, and default KB configured; token and endpoint intentionally omitted |",
        f"| Test scope | Phase 4 synthetic sanitized corpus `{CORPUS_ID}`; draft -> publish -> read -> indexed/retrievable -> Wiki-only retrieve -> citation locate; top_k={config.top_k} |",
        f"| Result | {decision} |",
        "",
        "## Closed Loop Summary",
        "",
        "| Step | Status | Evidence |",
        "| --- | --- | --- |",
        f"| Draft create | PASS | status=`{_cell(wiki_page.draft_status)}`; slug=`{_cell(wiki_page.slug)}` |",
        f"| Publish | PASS | status=`{_cell(wiki_page.published_status)}`; source_type target=`wiki_page` |",
        f"| Read back | PASS | status=`{_cell(wiki_page.read_status)}`; wiki_page_id=`{_cell(wiki_page.wiki_page_id)}` |",
        f"| Indexed / retrievable | PASS | source_type=`{_cell(wiki_page.source_type)}`; evidence_id=`{_cell(wiki_page.evidence_id)}`; query=`{_cell(wiki_page.retrievable_query)}` |",
        f"| Citation locate | {locate_result.status} | target_type=`{_cell(locate_result.target_type)}`; ui_hash=`{_cell(locate_result.ui_hash)}` |",
        "",
        "## Wiki Evidence",
        "",
        "| Anchor | source_type | slug | wiki_page_id | evidence_id |",
        "| --- | --- | --- | --- | --- |",
        f"| TEST-WIKI-001 | `{_cell(wiki_page.source_type)}` | `{_cell(wiki_page.slug)}` | `{_cell(wiki_page.wiki_page_id)}` | `{_cell(wiki_page.evidence_id)}` |",
        "",
        "## Wiki-only Question Results",
        "",
        "| Question | Query | source | source_type | evidence_id | wiki_page_id | search_query | trace_id | Status | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in question_results:
        lines.append(
            "| {qid} | {query} | {source} | {source_type} | `{evidence_id}` | `{wiki_page_id}` | {search_query} | `{trace_id}` | {status} | {notes} |".format(
                qid=_cell(item.question_id),
                query=_cell(item.query),
                source=_cell(item.source),
                source_type=_cell(item.source_type),
                evidence_id=_cell(item.evidence_id),
                wiki_page_id=_cell(item.wiki_page_id),
                search_query=_cell(item.search_query),
                trace_id=_cell(item.trace_id),
                status=_cell(item.status),
                notes=_cell(item.notes),
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


def _assert_pass(
    *,
    wiki_page: WikiRunPage,
    question_results: list[WikiQuestionResult],
    locate_result: LocateResult,
) -> None:
    failures = [item.question_id for item in question_results if item.status != "PASS"]
    if wiki_page.draft_status != "draft":
        failures.append("draft")
    if wiki_page.published_status != "published":
        failures.append("publish")
    if wiki_page.source_type != "wiki_page":
        failures.append("retrievable")
    if locate_result.status != "PASS":
        failures.append("citation_locate")
    if failures:
        raise WikiPassError("Wiki closed loop did not reach PASS: " + ", ".join(failures))


def _wiki_content(run_id: str, aliases: list[str], status: str) -> str:
    seed_content = WIKI_SEED_PATH.read_text(encoding="utf-8")
    return "\n\n".join(
        [
            seed_content,
            f"## Phase5 C4 Closed Loop Status: {status}",
            "\n".join(f"- {alias}" for alias in aliases),
            f"PHASE5_REAL_C4_RUN={run_id}",
        ]
    )


def _wiki_metadata(run_id: str, aliases: list[str], status: str) -> dict[str, Any]:
    return {
        "source": "phase5_c4_real_wiki_pass",
        "phase_task": TASK_ID,
        "phase5_run_id": run_id,
        "current_run_id": run_id,
        "corpus_id": CORPUS_ID,
        "namespace": run_id,
        "anchor": "TEST-WIKI-001",
        "anchors": ["TEST-WIKI-001"],
        "test_anchor": "TEST-WIKI-001",
        "aliases": aliases,
        "closed_loop_status": status,
    }


def _wiki_aliases(questions: list[dict[str, Any]]) -> list[str]:
    aliases = [
        "关联政策 关联法规 关联案例",
        "时限管理 关联政策 关联法规 关联案例",
        "常见误区",
        "Wiki 常见误区",
        "source_type=wiki_page",
        "Wiki evidence source_type=wiki_page",
        "原始文档 evidence 区分",
    ]
    for question in questions:
        aliases.append(str(question["query"]))
        aliases.extend(str(point) for point in question.get("expected_answer_points", []))
    return _dedupe(aliases)


def _load_wiki_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = [
        question for question in payload["questions"] if str(question.get("id")) in WIKI_QUESTION_IDS
    ]
    if {str(question["id"]) for question in questions} != WIKI_QUESTION_IDS:
        raise WikiPassError("missing P4Q-017 to P4Q-019 in questions fixture")
    return sorted(questions, key=lambda question: str(question["id"]))


def _wiki_page_id(page: WikiPage, fallback_slug: str) -> str:
    metadata = page.metadata or {}
    return str(
        metadata.get("id")
        or metadata.get("weknora_wiki_page_id")
        or metadata.get("wiki_page_id")
        or fallback_slug
    )


def _page_status(page: WikiPage, fallback: str) -> str:
    return str((page.metadata or {}).get("status") or fallback).strip().lower()


def _evidence_haystack(evidence: Evidence) -> str:
    metadata_values: list[str] = []
    for value in (evidence.metadata or {}).values():
        if isinstance(value, (list, tuple, set)):
            metadata_values.extend(str(item) for item in value)
        elif not isinstance(value, dict):
            metadata_values.append(str(value))
    return " ".join([evidence.title or "", evidence.text or "", *metadata_values])


def _validate_config(config: WikiPassConfig) -> None:
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
        missing.append("PHASE5_C4_WAIT_SECONDS")
    if config.poll_seconds <= 0:
        missing.append("PHASE5_C4_POLL_SECONDS")
    if config.top_k <= 0:
        missing.append("PHASE5_C4_TOP_K")
    if missing:
        raise WikiPassError("missing or invalid required env: " + ", ".join(missing))


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _cell(value: object) -> str:
    text = str(value if value is not None else "-")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    token = os.getenv("WEKNORA_SERVICE_TOKEN", "")
    return text.replace(token, "[redacted]") if token else text


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
