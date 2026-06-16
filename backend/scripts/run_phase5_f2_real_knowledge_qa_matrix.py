"""Run the Phase 5 F2 knowledge_qa 24-question matrix through PA workflow.

Dry mode is fixture-safe and validates the 24-question QA contract without
touching a live backend. Real mode posts each question to `/api/analysis/run`,
which enters `run_analysis()` and the normal PA `knowledge_qa` workflow. The
script intentionally does not call raw WeKnora or the model gateway directly.

Real mode requires fresh/current-run document and Wiki identifiers, for example:

    python backend/scripts/run_phase5_f2_real_knowledge_qa_matrix.py --mode real \
      --api-base-url http://127.0.0.1:8000 \
      --run-id p5g2-... \
      --external-doc-id wk-doc-... \
      --wiki-page-id wiki-page-... \
      --wiki-page-id phase5/wiki-current

Alternatively pass `--current-run-json /path/to/current_run.json`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "backend" / "fixtures" / "phase4_rag_wiki_qa"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
QUESTIONS_PATH = CORPUS_DIR / "questions.json"
CORPUS_ID = "phase4_rag_wiki_qa_v1"
TASK_ID = "P5-F2"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
VALID_SCOPES = {"all", "document", "wiki"}
VALID_SOURCE_TYPES = {"document_chunk", "wiki_page"}


class MatrixError(RuntimeError):
    """Raised when the knowledge_qa matrix cannot be marked PASS."""


@dataclass(frozen=True)
class MatrixConfig:
    mode: str
    api_base_url: str
    timeout_seconds: int
    output_path: Path | None
    current_run: dict[str, Any]


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    question_type: str
    scope: str
    status: str
    expected_answer_points: list[str]
    answer_point_status: str
    expected_anchors: list[str]
    actual_anchors: list[str]
    forbidden_anchors: list[str]
    expected_source_types: list[str]
    actual_source_types: list[str]
    citation_count: int
    retrieved_count: int
    refusal_status: str
    distractor_status: str
    version_status: str
    evidence_summaries: list[dict[str, str]]
    warning_codes: list[str]
    notes: str


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = _load_json(MANIFEST_PATH)
        questions = _load_json(QUESTIONS_PATH)["questions"]
        known_anchors = _validate_fixture_contract(manifest, questions)
        config = _config_from_args(args, known_anchors)
        if config.mode == "dry":
            results = _dry_run(questions)
        else:
            _validate_real_config(config)
            results = _real_run(
                config=config,
                questions=questions,
                known_anchors=known_anchors,
            )
        output = _render_output(config=config, results=results)
        if config.output_path:
            config.output_path.parent.mkdir(parents=True, exist_ok=True)
            config.output_path.write_text(output, encoding="utf-8")
        else:
            print(output)
        _assert_all_pass(results)
    except Exception as exc:  # noqa: BLE001
        print(f"Phase 5 F2 knowledge_qa matrix failed: {_safe_error(exc)}", file=sys.stderr)
        return 1

    print(f"Phase 5 F2 knowledge_qa matrix passed ({config.mode})")
    if config.output_path:
        print(f"- output: {config.output_path}")
    print("- decision: PASS")
    if config.mode == "dry":
        print("- real mode: rerun with --mode real and fresh current-run identifiers")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 5 knowledge_qa 24-question matrix through PA "
            "/api/analysis/run. Dry mode validates the fixture contract; real "
            "mode requires fresh current-run identifiers and never calls raw "
            "WeKnora or the model gateway directly."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("dry", "real"),
        default="dry",
        help="dry validates questions only; real posts each question to PA backend",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("PA_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="PA backend base URL for real mode, for example http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("PHASE5_F2_TIMEOUT_SECONDS", "180")),
        help="HTTP timeout for each PA backend QA request in real mode",
    )
    parser.add_argument(
        "--current-run-json",
        type=Path,
        help=(
            "JSON file containing current_run. Use this for G2/G5 handoff "
            "instead of relying on old cached data."
        ),
    )
    parser.add_argument("--run-id", help="fresh/current-run id")
    parser.add_argument("--namespace", help="fresh/current-run namespace")
    parser.add_argument(
        "--external-doc-id",
        action="append",
        default=[],
        help="current-run WeKnora document id; repeat for multiple documents",
    )
    parser.add_argument(
        "--knowledge-id",
        action="append",
        default=[],
        help="current-run backend knowledge id; repeat for multiple documents",
    )
    parser.add_argument(
        "--wiki-page-id",
        action="append",
        default=[],
        help="current-run Wiki page id or slug; repeat for id and slug",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional Markdown output path; stdout is used when omitted",
    )
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace, known_anchors: list[str]) -> MatrixConfig:
    current_run: dict[str, Any] = {}
    if args.current_run_json:
        payload = _load_json(args.current_run_json)
        current_run = dict(payload.get("current_run") or payload)

    current_run = {
        **current_run,
        **_drop_empty(
            {
                "run_id": args.run_id,
                "corpus_id": current_run.get("corpus_id") or CORPUS_ID,
                "namespace": args.namespace,
                "external_doc_ids": [
                    *current_run.get("external_doc_ids", []),
                    *args.external_doc_id,
                ],
                "knowledge_ids": [
                    *current_run.get("knowledge_ids", []),
                    *args.knowledge_id,
                ],
                "wiki_page_ids": [
                    *current_run.get("wiki_page_ids", []),
                    *args.wiki_page_id,
                ],
                "anchors": current_run.get("anchors") or known_anchors,
            }
        ),
    }
    for key in ("external_doc_ids", "knowledge_ids", "wiki_page_ids", "anchors"):
        if key in current_run:
            current_run[key] = _unique_strings(current_run[key])
    return MatrixConfig(
        mode=args.mode,
        api_base_url=str(args.api_base_url).rstrip("/"),
        timeout_seconds=args.timeout_seconds,
        output_path=args.output,
        current_run=current_run,
    )


def _validate_real_config(config: MatrixConfig) -> None:
    if not config.api_base_url or config.api_base_url.startswith("fixture://"):
        raise MatrixError("real mode requires a live PA backend --api-base-url")
    if config.timeout_seconds <= 0:
        raise MatrixError("--timeout-seconds must be positive")
    has_document_scope = bool(
        config.current_run.get("external_doc_ids")
        or config.current_run.get("knowledge_ids")
    )
    has_wiki_scope = bool(config.current_run.get("wiki_page_ids"))
    if not has_document_scope or not has_wiki_scope:
        raise MatrixError(
            "real mode requires fresh current-run document ids and wiki_page_ids; "
            "refusing to use historical cache or partial corpus scope"
        )


def _dry_run(questions: list[dict[str, Any]]) -> list[QuestionResult]:
    results: list[QuestionResult] = []
    for question in questions:
        answer_points = list(question.get("expected_answer_points") or [])
        results.append(
            QuestionResult(
                question_id=str(question["id"]),
                question_type=str(question.get("type") or "-"),
                scope=str(question["retrieval_scope"]),
                status="PASS",
                expected_answer_points=answer_points,
                answer_point_status=f"planned:{len(answer_points)}",
                expected_anchors=list(question.get("expected_anchors") or []),
                actual_anchors=[],
                forbidden_anchors=[],
                expected_source_types=list(question.get("expected_source_types") or []),
                actual_source_types=[],
                citation_count=0,
                retrieved_count=0,
                refusal_status=(
                    "planned" if question.get("should_answer_insufficient") else "not_applicable"
                ),
                distractor_status=(
                    "planned"
                    if question.get("type") == "distractor_suppression"
                    else "not_applicable"
                ),
                version_status=(
                    "planned" if question.get("type") == "version_conflict" else "not_applicable"
                ),
                evidence_summaries=[],
                warning_codes=[],
                notes=(
                    "dry mode validated fixture QA contract; no backend, model, "
                    "or WeKnora call executed"
                ),
            )
        )
    return results


def _real_run(
    *,
    config: MatrixConfig,
    questions: list[dict[str, Any]],
    known_anchors: list[str],
) -> list[QuestionResult]:
    results: list[QuestionResult] = []
    for question in questions:
        payload = _request_payload(config=config, question=question)
        response = _post_json(
            url=f"{config.api_base_url}/api/analysis/run",
            payload=payload,
            timeout_seconds=config.timeout_seconds,
        )
        citations = list(response.get("citations") or [])
        output = response.get("output") if isinstance(response.get("output"), dict) else {}
        task = response.get("task") if isinstance(response.get("task"), dict) else {}
        content = _output_content(output)
        markdown = str(output.get("content_markdown") or "")
        warning_codes = _warning_codes(content, output)
        actual_anchors = _actual_anchors(citations, known_anchors)
        actual_source_types = sorted({_citation_source_type(citation) for citation in citations})
        forbidden = sorted(set(question.get("forbidden_anchors") or []) & set(actual_anchors))
        status, notes, refusal_status, distractor_status, version_status, answer_status = (
            _judge_question(
                question=question,
                task_status=str(task.get("status") or ""),
                output_status=str(output.get("status") or ""),
                markdown=markdown,
                citations=citations,
                actual_anchors=actual_anchors,
                forbidden=forbidden,
                source_types=actual_source_types,
                warning_codes=warning_codes,
            )
        )
        results.append(
            QuestionResult(
                question_id=str(question["id"]),
                question_type=str(question.get("type") or "-"),
                scope=str(question.get("retrieval_scope") or "all"),
                status=status,
                expected_answer_points=list(question.get("expected_answer_points") or []),
                answer_point_status=answer_status,
                expected_anchors=list(question.get("expected_anchors") or []),
                actual_anchors=actual_anchors,
                forbidden_anchors=forbidden,
                expected_source_types=list(question.get("expected_source_types") or []),
                actual_source_types=actual_source_types,
                citation_count=len(citations),
                retrieved_count=int(content.get("retrieved_citation_count") or 0),
                refusal_status=refusal_status,
                distractor_status=distractor_status,
                version_status=version_status,
                evidence_summaries=_evidence_summaries(
                    citations,
                    expected_anchors=list(question.get("expected_anchors") or []),
                    known_anchors=known_anchors,
                ),
                warning_codes=warning_codes,
                notes=notes,
            )
        )
    return results


def _request_payload(config: MatrixConfig, question: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_type": "knowledge_qa",
        "title": f"{TASK_ID} {question['id']} knowledge_qa matrix",
        "query_or_topic": str(question["query"]),
        "retrieval_scope": str(question.get("retrieval_scope") or "all"),
        "current_run": config.current_run,
        "expected_source_types": list(question.get("expected_source_types") or []),
        "should_answer_insufficient": bool(question.get("should_answer_insufficient")),
        "forbidden_anchors": list(question.get("forbidden_anchors") or []),
        "question_type": str(question.get("type") or ""),
        "extra_requirements": (
            "Phase 5 QA matrix run. Use only current-run evidence and keep "
            "citations traceable."
        ),
    }


def _post_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise MatrixError(f"PA backend returned HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise MatrixError(f"PA backend request failed: {exc.reason}") from exc


def _judge_question(
    *,
    question: dict[str, Any],
    task_status: str,
    output_status: str,
    markdown: str,
    citations: list[dict[str, Any]],
    actual_anchors: list[str],
    forbidden: list[str],
    source_types: list[str],
    warning_codes: list[str],
) -> tuple[str, str, str, str, str, str]:
    notes: list[str] = []
    if task_status != "completed":
        notes.append(f"task status is {task_status or 'unknown'}")
    if output_status != "completed":
        notes.append(f"output status is {output_status or 'unknown'}")

    answer_status = _judge_answer_points(question, markdown)
    if answer_status.startswith("FAIL"):
        notes.append("answer point signal check failed")

    should_refuse = bool(question.get("should_answer_insufficient"))
    if should_refuse:
        refusal_status = _judge_refusal(markdown, citations, warning_codes)
        if refusal_status != "PASS":
            notes.append("insufficient-evidence refusal contract failed")
    else:
        refusal_status = "not_applicable"
        _judge_evidence_contract(
            question=question,
            citations=citations,
            actual_anchors=actual_anchors,
            forbidden=forbidden,
            source_types=source_types,
            notes=notes,
        )

    distractor_status = _judge_distractor(question, markdown, actual_anchors, forbidden)
    if distractor_status == "FAIL":
        notes.append("distractor suppression contract failed")

    version_status = _judge_version_conflict(question, markdown, actual_anchors)
    if version_status == "FAIL":
        notes.append("version-conflict answer contract failed")

    return (
        ("FAIL" if notes else "PASS"),
        "; ".join(notes) or "knowledge_qa evidence and answer contract satisfied",
        refusal_status,
        distractor_status,
        version_status,
        answer_status,
    )


def _judge_evidence_contract(
    *,
    question: dict[str, Any],
    citations: list[dict[str, Any]],
    actual_anchors: list[str],
    forbidden: list[str],
    source_types: list[str],
    notes: list[str],
) -> None:
    expected_anchors = set(question.get("expected_anchors") or [])
    missing = sorted(expected_anchors - set(actual_anchors))
    if missing:
        notes.append("missing expected anchors: " + ", ".join(missing))
    if forbidden:
        notes.append("forbidden anchors cited: " + ", ".join(forbidden))
    expected_source_types = set(question.get("expected_source_types") or [])
    if expected_source_types:
        missing_types = sorted(expected_source_types - set(source_types))
        unexpected_types = sorted(set(source_types) - expected_source_types)
        if missing_types:
            notes.append("missing source_type: " + ", ".join(missing_types))
        if unexpected_types:
            notes.append("unexpected source_type: " + ", ".join(unexpected_types))
    if question.get("must_cite_document") and "document_chunk" not in source_types:
        notes.append("missing document_chunk citation")
    if question.get("must_cite_wiki") and "wiki_page" not in source_types:
        notes.append("missing wiki_page citation")
    if not citations:
        notes.append("non-refusal question returned no citations")
    for index, citation in enumerate(citations, start=1):
        source_type = _citation_source_type(citation)
        if citation.get("source") != "weknora_api":
            notes.append(f"citation {index} is not from weknora_api")
        if not _citation_evidence_id(citation):
            notes.append(f"citation {index} missing evidence_id")
        if source_type == "unknown":
            notes.append(f"citation {index} missing source_type")
        if source_type == "document_chunk" and not citation.get("chunk_id"):
            notes.append(f"citation {index} document_chunk missing chunk_id")
        if source_type == "wiki_page" and not _citation_wiki_page_id(citation):
            notes.append(f"citation {index} wiki_page missing wiki_page_id")


def _judge_answer_points(question: dict[str, Any], markdown: str) -> str:
    points = list(question.get("expected_answer_points") or [])
    if not points:
        return "not_applicable"
    if question.get("should_answer_insufficient"):
        return "checked_by_refusal"
    signal_points = [point for point in points if not _is_negative_instruction(point)]
    if not signal_points:
        return "checked_by_policy"
    matched = sum(1 for point in signal_points if _point_has_signal(point, markdown))
    if matched < len(signal_points):
        return f"FAIL matched={matched}/{len(signal_points)}"
    return f"PASS matched={matched}/{len(signal_points)}"


def _is_negative_instruction(point: str) -> bool:
    text = str(point).strip()
    return any(marker in text for marker in ("不要", "不得", "不能", "不应"))


def _point_has_signal(point: str, markdown: str) -> bool:
    tokens = [
        token.strip(" ，。,.;；:：、")
        for token in str(point).replace("，", " ").replace("、", " ").split()
        if len(token.strip(" ，。,.;；:：、")) >= 2
    ]
    if not tokens:
        return False
    return any(token in markdown for token in tokens)


def _judge_refusal(
    markdown: str,
    citations: list[dict[str, Any]],
    warning_codes: list[str],
) -> str:
    if citations:
        return "FAIL"
    if "依据不足" not in markdown:
        return "FAIL"
    if "INSUFFICIENT_EVIDENCE_EXPECTED" not in warning_codes:
        return "FAIL"
    return "PASS"


def _judge_distractor(
    question: dict[str, Any],
    markdown: str,
    actual_anchors: list[str],
    forbidden: list[str],
) -> str:
    qid = str(question.get("id") or "")
    if qid == "P4Q-022":
        if forbidden or "TEST-DISTRACTOR-001" in actual_anchors:
            return "FAIL"
        if "TEST-RAG-002" not in actual_anchors:
            return "FAIL"
        if not _contains_working_day_phrase(markdown, 3):
            return "FAIL"
        return "PASS"
    if question.get("type") == "distractor_suppression":
        return "PASS" if not forbidden else "FAIL"
    return "not_applicable"


def _judge_version_conflict(
    question: dict[str, Any],
    markdown: str,
    actual_anchors: list[str],
) -> str:
    if question.get("type") != "version_conflict":
        return "not_applicable"
    required = {"TEST-RAG-001", "TEST-RAG-002"}
    if not required <= set(actual_anchors):
        return "FAIL"
    if "新版" not in markdown or "旧版" not in markdown:
        return "FAIL"
    if not _contains_working_day_phrase(markdown, 3):
        return "FAIL"
    if not _contains_working_day_phrase(markdown, 5):
        return "FAIL"
    return "PASS"


def _contains_working_day_phrase(markdown: str, days: int) -> bool:
    variants = {
        3: ("三个工作日", "3个工作日", "3 个工作日", "三 个工作日"),
        5: ("五个工作日", "5个工作日", "5 个工作日", "五 个工作日"),
    }
    return any(variant in markdown for variant in variants.get(days, ()))


def _actual_anchors(citations: list[dict[str, Any]], known_anchors: list[str]) -> list[str]:
    anchors: set[str] = set()
    for citation in citations:
        for anchor in known_anchors:
            if _citation_has_anchor(citation, anchor):
                anchors.add(anchor)
    return sorted(anchors)


def _citation_has_anchor(citation: dict[str, Any], anchor: str) -> bool:
    values = [
        str(citation.get("title") or ""),
        str(citation.get("text") or ""),
        *_metadata_anchor_values(_citation_metadata(citation)),
    ]
    return any(anchor in value for value in values)


def _metadata_anchor_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "anchor",
        "anchors",
        "test_anchor",
        "expected_anchor",
        "weknora_wiki_page_slug",
        "weknora_wiki_page_id",
        "slug",
        "id",
    ):
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value)
        elif not isinstance(value, dict):
            values.append(str(value))
    binding = metadata.get("citation_binding")
    if isinstance(binding, dict):
        binding_metadata = binding.get("metadata")
        if isinstance(binding_metadata, dict):
            values.extend(_metadata_anchor_values(binding_metadata))
    return values


def _citation_metadata(citation: dict[str, Any]) -> dict[str, Any]:
    raw = citation.get("metadata_json")
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    metadata = citation.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _citation_source_type(citation: dict[str, Any]) -> str:
    metadata = _citation_metadata(citation)
    value = (
        citation.get("source_type")
        or metadata.get("citation_source_type")
        or metadata.get("source_type")
    )
    normalized = str(value or "").strip().lower()
    if normalized in {"document", "documents", "doc", "chunk", "document_chunk"}:
        return "document_chunk"
    if normalized in {"wiki", "wiki-page", "wiki_page"}:
        return "wiki_page"
    return normalized or "unknown"


def _citation_evidence_id(citation: dict[str, Any]) -> str | None:
    metadata = _citation_metadata(citation)
    value = citation.get("evidence_id") or metadata.get("evidence_id")
    return _optional_str(value)


def _citation_wiki_page_id(citation: dict[str, Any]) -> str | None:
    metadata = _citation_metadata(citation)
    value = (
        citation.get("wiki_page_id")
        or metadata.get("wiki_page_id")
        or metadata.get("weknora_wiki_page_id")
        or metadata.get("slug")
        or metadata.get("weknora_wiki_page_slug")
    )
    return _optional_str(value)


def _evidence_summaries(
    citations: list[dict[str, Any]],
    *,
    expected_anchors: list[str],
    known_anchors: list[str],
) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    wanted = set(expected_anchors) or set(known_anchors)
    seen: set[str] = set()
    for rank, citation in enumerate(citations, start=1):
        anchors = [
            anchor for anchor in known_anchors if _citation_has_anchor(citation, anchor)
        ]
        if expected_anchors and not (set(anchors) & wanted):
            continue
        key = (
            _citation_evidence_id(citation)
            or citation.get("chunk_id")
            or _citation_wiki_page_id(citation)
            or str(rank)
        )
        if str(key) in seen:
            continue
        seen.add(str(key))
        summaries.append(
            {
                "rank": str(rank),
                "anchors": ",".join(anchors) or "-",
                "source": str(citation.get("source") or "-"),
                "source_type": _citation_source_type(citation),
                "evidence_id": _citation_evidence_id(citation) or "-",
                "external_doc_id": str(citation.get("external_doc_id") or "-"),
                "chunk_id": str(citation.get("chunk_id") or "-"),
                "wiki_page_id": _citation_wiki_page_id(citation) or "-",
            }
        )
    return summaries[:5]


def _output_content(output: dict[str, Any]) -> dict[str, Any]:
    raw = output.get("content_json")
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _warning_codes(content: dict[str, Any], output: dict[str, Any]) -> list[str]:
    codes = _unique_strings(content.get("warning_codes") or [])
    if codes:
        return codes
    warnings_raw = output.get("warnings_json")
    if isinstance(warnings_raw, str) and warnings_raw:
        try:
            warnings = json.loads(warnings_raw)
        except json.JSONDecodeError:
            warnings = []
        if isinstance(warnings, list):
            return _unique_strings(
                str(item).split(":", 1)[0] for item in warnings if ":" in str(item)
            )
    return []


def _render_output(config: MatrixConfig, results: list[QuestionResult]) -> str:
    pass_count = sum(1 for item in results if item.status == "PASS")
    fail_count = len(results) - pass_count
    lines = [
        "# Phase 5 F2 knowledge_qa 24Q Matrix",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} |",
        f"| Mode | `{config.mode}` |",
        f"| Corpus | `{CORPUS_ID}` |",
        f"| API path | `/api/analysis/run` |",
        f"| Result | {'PASS' if fail_count == 0 else 'FAIL'} |",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| PASS | {pass_count} |",
        f"| FAIL | {fail_count} |",
        "",
        "## Question Matrix",
        "",
        "| Question | Type | Scope | Answer points | Expected anchors | Actual anchors | Expected source_type | Actual source_type | Citations | Retrieved | Refusal | Distractor | Version | Evidence fields | Warnings | Status | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        evidence_fields = "<br>".join(
            "{rank}. anchors={anchors}; source={source}; source_type={source_type}; evidence_id={evidence_id}; chunk_id={chunk_id}; wiki_page_id={wiki_page_id}".format(
                **{key: _cell(value) for key, value in summary.items()}
            )
            for summary in item.evidence_summaries
        ) or "-"
        lines.append(
            "| {qid} | {qtype} | {scope} | {answer_points} | {expected} | {actual} | {expected_types} | {actual_types} | {citation_count} | {retrieved_count} | {refusal} | {distractor} | {version} | {evidence_fields} | {warnings} | {status} | {notes} |".format(
                qid=_cell(item.question_id),
                qtype=_cell(item.question_type),
                scope=_cell(item.scope),
                answer_points=_cell(item.answer_point_status),
                expected=_cell(", ".join(item.expected_anchors) or "none"),
                actual=_cell(", ".join(item.actual_anchors) or "none"),
                expected_types=_cell(", ".join(item.expected_source_types) or "none"),
                actual_types=_cell(", ".join(item.actual_source_types) or "none"),
                citation_count=item.citation_count,
                retrieved_count=item.retrieved_count,
                refusal=_cell(item.refusal_status),
                distractor=_cell(item.distractor_status),
                version=_cell(item.version_status),
                evidence_fields=evidence_fields,
                warnings=_cell(", ".join(item.warning_codes) or "none"),
                status=_cell(item.status),
                notes=_cell(item.notes),
            )
        )
    return "\n".join(lines) + "\n"


def _assert_all_pass(results: list[QuestionResult]) -> None:
    failed = [item.question_id for item in results if item.status != "PASS"]
    if failed:
        raise MatrixError("knowledge_qa matrix did not reach 24/24 PASS: " + ", ".join(failed))


def _validate_fixture_contract(
    manifest: dict[str, Any],
    questions: list[dict[str, Any]],
) -> list[str]:
    if manifest.get("corpus_id") != CORPUS_ID:
        raise MatrixError("unexpected manifest corpus_id")
    documents = manifest.get("documents") or []
    if len(documents) != 9:
        raise MatrixError("expected 9 fixture documents")
    if len(questions) != 24:
        raise MatrixError("expected 24 fixture questions")
    anchors = {str(item["anchor"]) for item in documents}
    for question in questions:
        qid = str(question.get("id") or "unknown")
        scope = str(question.get("retrieval_scope") or "")
        if scope not in VALID_SCOPES:
            raise MatrixError(f"{qid} has invalid retrieval_scope")
        expected_source_types = set(question.get("expected_source_types") or [])
        if not expected_source_types <= VALID_SOURCE_TYPES:
            raise MatrixError(f"{qid} has invalid expected_source_types")
        expected = set(question.get("expected_anchors") or [])
        forbidden = set(question.get("forbidden_anchors") or [])
        if not expected <= anchors:
            raise MatrixError(f"{qid} references unknown expected anchor")
        if not forbidden <= anchors:
            raise MatrixError(f"{qid} references unknown forbidden anchor")
        if not isinstance(question.get("expected_answer_points"), list):
            raise MatrixError(f"{qid} missing expected_answer_points list")
    return sorted(anchors)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _unique_strings(values: Any) -> list[str]:
    if values in (None, ""):
        return []
    if isinstance(values, str):
        raw_values = [values]
    elif isinstance(values, (list, tuple, set)):
        raw_values = list(values)
    else:
        raw_values = list(values) if hasattr(values, "__iter__") else [values]
    seen: set[str] = set()
    result: list[str] = []
    for value in raw_values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    for marker in ("Bearer ", "Authorization", "SERVICE_TOKEN", "api_key", "API_KEY"):
        text = text.replace(marker, "[redacted]")
    return text[:700]


if __name__ == "__main__":
    raise SystemExit(main())
