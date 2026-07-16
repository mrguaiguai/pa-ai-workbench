"""Run the P5-C2 real Wiki-only natural-language retrieval gate.

This script has live side effects in the configured WeKnora KB:
- creates one published Wiki page derived from TEST-WIKI-001;
- runs P4Q-017, P4Q-018, and P4Q-019 through PA retrieval with wiki scope;
- writes a sanitized PASS/FAIL report.

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
QUESTIONS_PATH = CORPUS_DIR / "questions.json"
WIKI_SEED_PATH = CORPUS_DIR / "documents" / "008_timeliness_wiki_seed.md"
REPORT_PATH = PROJECT_ROOT / "docs" / "archive" / "phase5" / "PHASE5_REAL_WIKI_ONLY_P5_C2_REPORT.md"

CORPUS_ID = "phase4_rag_wiki_qa_v1"
TASK_ID = "P5-C2"
WIKI_QUESTION_IDS = {"P4Q-017", "P4Q-018", "P4Q-019"}


class WikiOnlyError(RuntimeError):
    """Raised when P5-C2 cannot be marked PASS."""


@dataclass(frozen=True)
class WikiOnlyConfig:
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
    def from_settings(cls) -> "WikiOnlyConfig":
        settings = Settings()
        return cls(
            base_url=settings.weknora_base_url.rstrip("/"),
            service_token=settings.weknora_service_token,
            default_kb_id=settings.weknora_default_kb_id,
            timeout_seconds=settings.weknora_timeout_seconds,
            wait_seconds=_int_env("PHASE5_C2_WAIT_SECONDS", 360),
            poll_seconds=_int_env("PHASE5_C2_POLL_SECONDS", 5),
            top_k=_int_env("PHASE5_C2_TOP_K", 8),
            knowledge_backend=settings.knowledge_backend,
            mock_mode=settings.mock_mode,
        )


@dataclass(frozen=True)
class WikiRunPage:
    slug: str
    wiki_page_id: str
    evidence_id: str
    source_type: str


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


def main() -> int:
    config = WikiOnlyConfig.from_settings()
    run_id = f"p5c2-{uuid4().hex[:12]}"
    try:
        _validate_config(config)
        questions = _load_wiki_questions()
        backend = WeKnoraApiBackend(
            base_url=config.base_url,
            service_token=config.service_token,
            timeout=config.timeout_seconds,
            default_kb_id=config.default_kb_id,
        )
        wiki_page = _create_published_wiki_page(
            backend=backend,
            config=config,
            run_id=run_id,
            questions=questions,
        )
        results = _wait_for_questions(
            config=config,
            run_id=run_id,
            wiki_page=wiki_page,
            questions=questions,
        )
        _write_report(config=config, run_id=run_id, wiki_page=wiki_page, results=results)
        _assert_all_pass(results)
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 C2 real Wiki-only retrieval failed: {_safe_error(exc)}", file=sys.stderr)
        return 1

    print("Phase 5 C2 real Wiki-only retrieval passed")
    print(f"- run id: {run_id}")
    print(f"- report: {REPORT_PATH}")
    print("- decision: PASS")
    return 0


def _create_published_wiki_page(
    *,
    backend: WeKnoraApiBackend,
    config: WikiOnlyConfig,
    run_id: str,
    questions: list[dict[str, Any]],
) -> WikiRunPage:
    seed_content = WIKI_SEED_PATH.read_text(encoding="utf-8")
    slug = f"phase5/c2-timeliness-{run_id}"
    aliases = _wiki_aliases(questions)
    summary = " ".join(
        [
            "TEST-WIKI-001",
            "时限管理专题关联政策、法规和案例。",
            "Wiki 专题指出常见误区。",
            "Wiki evidence 应带有 source_type=wiki_page 并与原始文档 evidence 区分。",
            *aliases,
        ]
    )
    page = {
        "slug": slug,
        "title": "TEST-WIKI-001 Phase5 C2 Timeliness Wiki",
        "summary": summary,
        "content": "\n\n".join(
            [
                seed_content,
                "## Phase5 C2 Wiki-only Natural Questions",
                "\n".join(f"- {alias}" for alias in aliases),
                f"PHASE5_REAL_C2_RUN={run_id}",
            ]
        ),
        "page_type": "wiki",
        "status": "published",
        "aliases": aliases,
        "metadata": {
            "source": "phase5_c2_real_wiki_only",
            "phase_task": TASK_ID,
            "phase5_run_id": run_id,
            "current_run_id": run_id,
            "corpus_id": CORPUS_ID,
            "namespace": run_id,
            "anchor": "TEST-WIKI-001",
            "anchors": ["TEST-WIKI-001"],
            "test_anchor": "TEST-WIKI-001",
            "aliases": aliases,
        },
    }
    try:
        created = backend.create_wiki_page(page=page, kb_id=config.default_kb_id)
    except KnowledgeBackendUnavailableError as exc:
        raise WikiOnlyError(f"Wiki create failed: {exc}") from exc

    wiki_page_id = str(
        (created.metadata or {}).get("id")
        or (created.metadata or {}).get("weknora_wiki_page_id")
        or created.slug
    )
    evidence = _wait_for_anchor(
        backend=backend,
        config=config,
        slug=created.slug,
        wiki_page_id=wiki_page_id,
    )
    return WikiRunPage(
        slug=created.slug,
        wiki_page_id=evidence.wiki_page_id or wiki_page_id,
        evidence_id=evidence.evidence_id or "",
        source_type=evidence.source_type,
    )


def _wait_for_anchor(
    *,
    backend: WeKnoraApiBackend,
    config: WikiOnlyConfig,
    slug: str,
    wiki_page_id: str,
) -> Evidence:
    deadline = time.monotonic() + config.wait_seconds
    while time.monotonic() <= deadline:
        try:
            evidence_items = backend.retrieve(
                query="TEST-WIKI-001 source_type=wiki_page",
                filters={
                    "knowledge_base_ids": [config.default_kb_id],
                    "source_type": "wiki_page",
                },
                top_k=config.top_k,
            )
        except KnowledgeBackendUnavailableError as exc:
            raise WikiOnlyError(f"Wiki anchor retrieve failed: {exc}") from exc
        match = _matching_wiki_evidence(evidence_items, slug=slug, wiki_page_id=wiki_page_id)
        if match is not None:
            return match
        time.sleep(config.poll_seconds)
    raise WikiOnlyError("published Wiki page was not retrievable by anchor before timeout")


def _wait_for_questions(
    *,
    config: WikiOnlyConfig,
    run_id: str,
    wiki_page: WikiRunPage,
    questions: list[dict[str, Any]],
) -> list[WikiQuestionResult]:
    deadline = time.monotonic() + config.wait_seconds
    latest: list[WikiQuestionResult] = []
    while time.monotonic() <= deadline:
        latest = [
            _run_question(
                config=config,
                run_id=run_id,
                wiki_page=wiki_page,
                question=question,
            )
            for question in questions
        ]
        if all(item.status == "PASS" for item in latest):
            return latest
        time.sleep(config.poll_seconds)
    return latest


def _run_question(
    *,
    config: WikiOnlyConfig,
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
    filters = {
        "source_scope": "wiki",
        "current_run": current_run,
        "knowledge_base_ids": [config.default_kb_id],
    }
    with weknora_log_context(correlation_id=trace_id):
        result = retrieve_evidence_with_context(
            query=query,
            filters=filters,
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
            notes="current published Wiki page was not returned as wiki_page evidence",
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
    config: WikiOnlyConfig,
    run_id: str,
    wiki_page: WikiRunPage,
    results: list[WikiQuestionResult],
) -> None:
    pass_count = sum(1 for item in results if item.status == "PASS")
    fail_count = len(results) - pass_count
    decision = "PASS" if fail_count == 0 else "FAIL"
    lines = [
        "# Phase 5 P5-C2 Real Wiki-only Retrieval Report",
        "",
        "## Test Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} Wiki-only natural-language retrieval |",
        "| Report marker | PHASE5_REAL |",
        f"| Run id | `{run_id}` |",
        "| Backend source | `weknora_api` |",
        "| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; WeKnora base URL, service token, workspace, and default KB configured; token and endpoint intentionally omitted |",
        f"| Test scope | Phase 4 synthetic sanitized corpus `{CORPUS_ID}`; P4Q-017 to P4Q-019; top_k={config.top_k}; fresh/current-run Wiki page |",
        f"| Result | {decision} |",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| PASS | {pass_count} |",
        f"| FAIL | {fail_count} |",
        "",
        "## Current-Run Wiki Evidence",
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
    for item in results:
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


def _assert_all_pass(results: list[WikiQuestionResult]) -> None:
    failed = [item.question_id for item in results if item.status != "PASS"]
    if failed:
        raise WikiOnlyError("Wiki-only questions did not all pass: " + ", ".join(failed))


def _load_wiki_questions() -> list[dict[str, Any]]:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = [
        question
        for question in payload["questions"]
        if str(question.get("id")) in WIKI_QUESTION_IDS
    ]
    if {str(question["id"]) for question in questions} != WIKI_QUESTION_IDS:
        raise WikiOnlyError("missing P4Q-017 to P4Q-019 in questions fixture")
    return sorted(questions, key=lambda question: str(question["id"]))


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


def _evidence_haystack(evidence: Evidence) -> str:
    metadata_values = []
    for value in (evidence.metadata or {}).values():
        if isinstance(value, (list, tuple, set)):
            metadata_values.extend(str(item) for item in value)
        elif not isinstance(value, dict):
            metadata_values.append(str(value))
    return " ".join([evidence.title or "", evidence.text or "", *metadata_values])


def _validate_config(config: WikiOnlyConfig) -> None:
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
        missing.append("PHASE5_C2_WAIT_SECONDS")
    if config.poll_seconds <= 0:
        missing.append("PHASE5_C2_POLL_SECONDS")
    if config.top_k <= 0:
        missing.append("PHASE5_C2_TOP_K")
    if missing:
        raise WikiOnlyError("missing or invalid required env: " + ", ".join(missing))


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
