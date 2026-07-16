"""Run the Phase 5 F1 RAG 24-question matrix through the PA backend API.

Dry mode is fixture-safe and validates the 24-question execution contract
without touching a live backend. Real mode posts each question to
`/api/rag/retrieve`, so retrieval goes through PA's RAG service, source-scope
normalization, current-run isolation, ranking, and guards. It intentionally does
not upload fixtures or call raw WeKnora.

Real mode requires current-run identifiers from the fresh acceptance corpus,
for example:

    python scripts/validation/run_phase5_f1_real_rag_matrix.py --mode real \
      --api-base-url http://127.0.0.1:8000 \
      --run-id p5g2-... \
      --external-doc-id wk-doc-... \
      --wiki-page-id wiki-page-... \
      --wiki-page-id phase5/wiki-current \
      --kb-id kb-...

Alternatively pass `--current-run-json /path/to/current_run.json` with
`current_run` and optional `knowledge_base_ids` fields.
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
CORPUS_DIR = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
QUESTIONS_PATH = CORPUS_DIR / "questions.json"
CORPUS_ID = "phase4_rag_wiki_qa_v1"
TASK_ID = "P5-F1"
DEFAULT_TOP_K = 8
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
VALID_SCOPES = {"all", "document", "wiki"}
VALID_SOURCE_TYPES = {"document_chunk", "wiki_page"}


class MatrixError(RuntimeError):
    """Raised when the matrix cannot be marked PASS."""


@dataclass(frozen=True)
class MatrixConfig:
    mode: str
    api_base_url: str
    top_k: int
    timeout_seconds: int
    output_path: Path | None
    current_run: dict[str, Any]
    knowledge_base_ids: list[str]


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    scope: str
    status: str
    expected_anchors: list[str]
    actual_anchors: list[str]
    forbidden_anchors: list[str]
    expected_source_types: list[str]
    actual_source_types: list[str]
    evidence_summaries: list[dict[str, str]]
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
        print(f"Phase 5 F1 RAG matrix failed: {_safe_error(exc)}", file=sys.stderr)
        return 1

    print(f"Phase 5 F1 RAG matrix passed ({config.mode})")
    if config.output_path:
        print(f"- output: {config.output_path}")
    print("- decision: PASS")
    if config.mode == "dry":
        print("- real mode: rerun with --mode real and fresh current-run identifiers")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 5 RAG 24-question matrix through PA /api/rag/retrieve. "
            "Dry mode validates the fixture contract; real mode requires fresh "
            "current-run identifiers and never calls raw WeKnora."
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
        "--top-k",
        type=int,
        default=int(os.getenv("PHASE5_F1_TOP_K", str(DEFAULT_TOP_K))),
        help="RAG top_k sent to PA backend in real mode",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("PHASE5_F1_TIMEOUT_SECONDS", "60")),
        help="HTTP timeout for each PA backend request in real mode",
    )
    parser.add_argument(
        "--current-run-json",
        type=Path,
        help=(
            "JSON file containing current_run and optional knowledge_base_ids. "
            "Use this for G2/G3 handoff instead of relying on old cached data."
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
        "--kb-id",
        action="append",
        default=[],
        help="knowledge_base_ids filter sent to PA backend; repeat if needed",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional Markdown output path; stdout is used when omitted",
    )
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace, known_anchors: list[str]) -> MatrixConfig:
    current_run: dict[str, Any] = {}
    knowledge_base_ids: list[str] = []
    if args.current_run_json:
        payload = _load_json(args.current_run_json)
        current_run = dict(payload.get("current_run") or payload)
        knowledge_base_ids = _unique_strings(
            payload.get("knowledge_base_ids")
            or payload.get("kb_ids")
            or current_run.pop("knowledge_base_ids", [])
        )

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
    knowledge_base_ids = _unique_strings([*knowledge_base_ids, *args.kb_id])
    return MatrixConfig(
        mode=args.mode,
        api_base_url=str(args.api_base_url).rstrip("/"),
        top_k=args.top_k,
        timeout_seconds=args.timeout_seconds,
        output_path=args.output,
        current_run=current_run,
        knowledge_base_ids=knowledge_base_ids,
    )


def _validate_real_config(config: MatrixConfig) -> None:
    if not config.api_base_url or config.api_base_url.startswith("fixture://"):
        raise MatrixError("real mode requires a live PA backend --api-base-url")
    if config.top_k <= 0:
        raise MatrixError("--top-k must be positive")
    if config.timeout_seconds <= 0:
        raise MatrixError("--timeout-seconds must be positive")
    if not (
        config.current_run.get("external_doc_ids")
        or config.current_run.get("knowledge_ids")
        or config.current_run.get("wiki_page_ids")
    ):
        raise MatrixError(
            "real mode requires fresh current-run external_doc_ids, knowledge_ids, "
            "or wiki_page_ids; refusing to use historical cache"
        )


def _dry_run(questions: list[dict[str, Any]]) -> list[QuestionResult]:
    results: list[QuestionResult] = []
    for question in questions:
        results.append(
            QuestionResult(
                question_id=str(question["id"]),
                scope=str(question["retrieval_scope"]),
                status="PASS",
                expected_anchors=list(question.get("expected_anchors") or []),
                actual_anchors=[],
                forbidden_anchors=[],
                expected_source_types=list(question.get("expected_source_types") or []),
                actual_source_types=[],
                evidence_summaries=[],
                notes="dry mode validated fixture contract; no backend call executed",
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
            url=f"{config.api_base_url}/api/rag/retrieve",
            payload=payload,
            timeout_seconds=config.timeout_seconds,
        )
        items = list(response.get("items") or [])
        actual_anchors = _actual_anchors(items, known_anchors)
        forbidden = sorted(set(question.get("forbidden_anchors") or []) & set(actual_anchors))
        actual_source_types = sorted(
            {str(item.get("source_type") or "unknown") for item in items}
        )
        status, notes = _judge_question(
            question=question,
            actual_anchors=actual_anchors,
            forbidden=forbidden,
            actual_source_types=actual_source_types,
        )
        results.append(
            QuestionResult(
                question_id=str(question["id"]),
                scope=str(question.get("retrieval_scope") or "all"),
                status=status,
                expected_anchors=list(question.get("expected_anchors") or []),
                actual_anchors=actual_anchors,
                forbidden_anchors=forbidden,
                expected_source_types=list(question.get("expected_source_types") or []),
                actual_source_types=actual_source_types,
                evidence_summaries=_evidence_summaries(
                    items,
                    expected_anchors=list(question.get("expected_anchors") or []),
                    known_anchors=known_anchors,
                ),
                notes=notes,
            )
        )
    return results


def _request_payload(config: MatrixConfig, question: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "source_scope": question.get("retrieval_scope") or "all",
        "current_run": config.current_run,
    }
    if config.knowledge_base_ids:
        filters["knowledge_base_ids"] = config.knowledge_base_ids
    return {
        "query": str(question["query"]),
        "filters": filters,
        "top_k": config.top_k,
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
    actual_anchors: list[str],
    forbidden: list[str],
    actual_source_types: list[str],
) -> tuple[str, str]:
    expected_anchors = set(question.get("expected_anchors") or [])
    missing = sorted(expected_anchors - set(actual_anchors))
    expected_source_types = set(question.get("expected_source_types") or [])
    missing_source_types = sorted(expected_source_types - set(actual_source_types))
    notes: list[str] = []
    if missing:
        notes.append("missing expected anchors: " + ", ".join(missing))
    if forbidden:
        notes.append("forbidden anchors retrieved: " + ", ".join(forbidden))
    if missing_source_types:
        notes.append("missing expected source_type: " + ", ".join(missing_source_types))
    scope = str(question.get("retrieval_scope") or "all")
    if scope == "document" and any(item != "document_chunk" for item in actual_source_types):
        notes.append("document scope returned non-document evidence")
    if scope == "wiki" and any(item != "wiki_page" for item in actual_source_types):
        notes.append("wiki scope returned non-wiki evidence")
    if not expected_anchors and question.get("should_answer_insufficient"):
        notes.append("insufficient-evidence question; retrieval layer checks no forbidden anchor")
    blocking = [
        note
        for note in notes
        if not note.startswith("insufficient-evidence question")
    ]
    return ("FAIL", "; ".join(notes)) if blocking else (
        "PASS",
        "; ".join(notes) or "expected retrieval evidence satisfied",
    )


def _actual_anchors(items: list[dict[str, Any]], known_anchors: list[str]) -> list[str]:
    anchors: set[str] = set()
    for item in items:
        for anchor in known_anchors:
            if _item_has_anchor(item, anchor):
                anchors.add(anchor)
    return sorted(anchors)


def _item_has_anchor(item: dict[str, Any], anchor: str) -> bool:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    haystack = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("text") or ""),
            *_anchor_metadata_values(metadata),
        ]
    )
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
        elif not isinstance(value, dict):
            values.append(str(value))
    return values


def _evidence_summaries(
    items: list[dict[str, Any]],
    *,
    expected_anchors: list[str],
    known_anchors: list[str],
) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    wanted = set(expected_anchors) or set(known_anchors)
    seen: set[str] = set()
    for rank, item in enumerate(items, start=1):
        item_anchors = [
            anchor for anchor in known_anchors if _item_has_anchor(item, anchor)
        ]
        if expected_anchors and not (set(item_anchors) & wanted):
            continue
        key = (
            item.get("evidence_id")
            or item.get("chunk_id")
            or item.get("wiki_page_id")
            or str(rank)
        )
        if str(key) in seen:
            continue
        seen.add(str(key))
        summaries.append(
            {
                "rank": str(rank),
                "anchors": ",".join(item_anchors) or "-",
                "source_type": str(item.get("source_type") or "-"),
                "evidence_id": str(item.get("evidence_id") or "-"),
                "chunk_id": str(item.get("chunk_id") or "-"),
                "wiki_page_id": str(item.get("wiki_page_id") or "-"),
            }
        )
    return summaries[:4]


def _render_output(config: MatrixConfig, results: list[QuestionResult]) -> str:
    pass_count = sum(1 for item in results if item.status == "PASS")
    fail_count = len(results) - pass_count
    lines = [
        "# Phase 5 F1 RAG 24Q Matrix",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} |",
        f"| Mode | `{config.mode}` |",
        f"| Corpus | `{CORPUS_ID}` |",
        f"| API path | `/api/rag/retrieve` |",
        f"| top_k | {config.top_k} |",
        f"| Result | {'PASS' if fail_count == 0 else 'FAIL'} |",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| PASS | {pass_count} |",
        f"| FAIL | {fail_count} |",
        "",
        "## Question Matrix",
        "",
        "| Question | Scope | Expected anchors | Actual anchors | Expected source_type | Actual source_type | Evidence fields | Forbidden retrieved | Status | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        evidence_fields = "<br>".join(
            "{rank}. anchors={anchors}; source_type={source_type}; evidence_id={evidence_id}; chunk_id={chunk_id}; wiki_page_id={wiki_page_id}".format(
                **{key: _cell(value) for key, value in summary.items()}
            )
            for summary in item.evidence_summaries
        ) or "-"
        lines.append(
            "| {qid} | {scope} | {expected} | {actual} | {expected_types} | {actual_types} | {evidence_fields} | {forbidden} | {status} | {notes} |".format(
                qid=_cell(item.question_id),
                scope=_cell(item.scope),
                expected=_cell(", ".join(item.expected_anchors) or "none"),
                actual=_cell(", ".join(item.actual_anchors) or "none"),
                expected_types=_cell(", ".join(item.expected_source_types) or "none"),
                actual_types=_cell(", ".join(item.actual_source_types) or "none"),
                evidence_fields=evidence_fields,
                forbidden=_cell("yes" if item.forbidden_anchors else "no"),
                status=_cell(item.status),
                notes=_cell(item.notes),
            )
        )
    return "\n".join(lines) + "\n"


def _assert_all_pass(results: list[QuestionResult]) -> None:
    failed = [item.question_id for item in results if item.status != "PASS"]
    if failed:
        raise MatrixError("matrix did not reach 24/24 PASS: " + ", ".join(failed))


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
        raw_values = [values]
    seen: set[str] = set()
    result: list[str] = []
    for value in raw_values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    for marker in ("Bearer ", "Authorization", "SERVICE_TOKEN", "api_key"):
        text = text.replace(marker, "[redacted]")
    return text[:700]


if __name__ == "__main__":
    raise SystemExit(main())
