"""Run the Phase 5 D5 real knowledge_qa 24-question matrix.

The script prepares a fresh/current-run copy of the Phase 4 synthetic corpus in
the configured WeKnora KB, then sends all 24 questions through PA's
knowledge_qa runtime. It records only sanitized validation metadata and never
writes tokens, endpoints, raw uploaded files, raw chunks, prompts, or provider
answers.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agent.agents.qa_agent import KnowledgeQaWorkflow  # noqa: E402
from agent.model_gateway.factory import ModelGatewayConfig  # noqa: E402
from agent.runtime import AgentRuntime  # noqa: E402
from agent.schemas import AgentRequest  # noqa: E402
from agent.schemas import AgentStatus  # noqa: E402
from agent.schemas import AgentTaskType  # noqa: E402
from agent.schemas import Citation  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.log_context import weknora_log_context  # noqa: E402


B5_SCRIPT_PATH = PROJECT_ROOT / "backend" / "scripts" / "run_phase5_b5_real_rag_matrix.py"
REPORT_PATH = PROJECT_ROOT / "docs" / "PHASE5_REAL_KNOWLEDGE_QA_24Q_PASS_REPORT.md"
TASK_ID = "P5-D5"


class KnowledgeQaMatrixError(RuntimeError):
    """Raised when the real knowledge_qa matrix cannot be marked PASS."""


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    question_type: str
    scope: str
    status: str
    trace_id: str
    expected_answer_points: list[str]
    expected_anchors: list[str]
    actual_anchors: list[str]
    forbidden_anchors: list[str]
    source_types: list[str]
    citation_count: int
    retrieved_count: int
    refusal_status: str
    distractor_status: str
    version_status: str
    answer_point_summary: str
    evidence_summaries: list[dict[str, str]]
    warning_codes: list[str]
    notes: str


def main() -> int:
    b5 = _load_b5_module()
    b5.TASK_ID = TASK_ID
    config = b5.MatrixConfig.from_settings()
    model_config = ModelGatewayConfig()
    run_id = f"p5d5-{uuid4().hex[:12]}"
    try:
        b5._validate_config(config)
        _validate_model_config(model_config)
        manifest = b5._load_json(b5.MANIFEST_PATH)
        questions = b5._load_json(b5.QUESTIONS_PATH)["questions"]
        b5._validate_fixture_contract(manifest, questions)
        with TemporaryDirectory(prefix="pa-phase5-d5-") as temp_dir:
            result = _run_matrix(
                b5=b5,
                config=config,
                run_id=run_id,
                temp_dir=Path(temp_dir),
                manifest=manifest,
                questions=questions,
            )
        _write_report(
            b5=b5,
            config=config,
            model_config=model_config,
            run_id=run_id,
            result=result,
        )
        _assert_all_pass(result["question_results"])
    except Exception as exc:  # noqa: BLE001
        print(
            f"Phase 5 D5 real knowledge_qa matrix failed: {_safe_error(exc)}",
            file=sys.stderr,
        )
        return 1

    print("Phase 5 D5 real knowledge_qa matrix passed")
    print(f"- run id: {run_id}")
    print(f"- report: {REPORT_PATH}")
    print("- decision: PASS")
    return 0


def _run_matrix(
    *,
    b5: Any,
    config: Any,
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
    uploaded = b5._upload_documents(
        backend=backend,
        config=config,
        run_id=run_id,
        temp_dir=temp_dir,
        manifest=manifest,
    )
    wiki_page = b5._create_and_verify_wiki_page(
        backend=backend,
        config=config,
        run_id=run_id,
        uploaded=uploaded,
        questions=questions,
    )
    question_results = _run_questions(
        b5=b5,
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


def _run_questions(
    *,
    b5: Any,
    config: Any,
    run_id: str,
    uploaded: dict[str, Any],
    wiki_page: Any,
    questions: list[dict[str, Any]],
) -> list[QuestionResult]:
    runtime = AgentRuntime()
    runtime.register_workflow(
        AgentTaskType.KNOWLEDGE_QA,
        KnowledgeQaWorkflow(top_k=config.top_k),
    )
    current_run = {
        "run_id": run_id,
        "corpus_id": b5.CORPUS_ID,
        "namespace": run_id,
        "external_doc_ids": [document.external_doc_id for document in uploaded.values()],
        "wiki_page_ids": [wiki_page.wiki_page_id, wiki_page.slug],
        "anchors": sorted(uploaded.keys()),
    }
    known_anchors = sorted({*uploaded.keys(), "TEST-WIKI-001"})
    results: list[QuestionResult] = []
    for question in questions:
        qid = str(question["id"])
        trace_id = f"PHASE5_REAL-{TASK_ID}-{run_id}-{qid}"
        request = _request_from_question(
            question=question,
            run_id=run_id,
            current_run=current_run,
        )
        with weknora_log_context(correlation_id=trace_id):
            result = runtime.run(request=request, recent_messages=[])
        actual_anchors = _actual_anchors(result.citations, known_anchors)
        source_types = sorted({citation.source_type or "unknown" for citation in result.citations})
        forbidden = sorted(
            set(question.get("forbidden_anchors") or []) & set(actual_anchors)
        )
        evidence_summaries = _evidence_summaries(
            result.citations,
            expected_anchors=question.get("expected_anchors", []),
            known_anchors=known_anchors,
        )
        status, notes, refusal_status, distractor_status, version_status = _judge_question(
            question=question,
            result_status=str(result.status),
            markdown=result.markdown,
            citations=result.citations,
            actual_anchors=actual_anchors,
            forbidden=forbidden,
            source_types=source_types,
            warning_codes=list(result.content.get("warning_codes") or []),
        )
        results.append(
            QuestionResult(
                question_id=qid,
                question_type=str(question.get("type") or "-"),
                scope=str(question.get("retrieval_scope") or "all"),
                status=status,
                trace_id=trace_id,
                expected_answer_points=list(question.get("expected_answer_points") or []),
                expected_anchors=list(question.get("expected_anchors") or []),
                actual_anchors=actual_anchors,
                forbidden_anchors=forbidden,
                source_types=source_types,
                citation_count=len(result.citations),
                retrieved_count=int(result.content.get("retrieved_citation_count") or 0),
                refusal_status=refusal_status,
                distractor_status=distractor_status,
                version_status=version_status,
                answer_point_summary=_answer_point_summary(question, result.markdown),
                evidence_summaries=evidence_summaries,
                warning_codes=list(result.content.get("warning_codes") or []),
                notes=notes,
            )
        )
    return results


def _request_from_question(
    *,
    question: dict[str, Any],
    run_id: str,
    current_run: dict[str, Any],
) -> AgentRequest:
    qid = str(question["id"])
    return AgentRequest(
        task_id=f"{TASK_ID}-{qid}-{run_id}",
        conversation_id=f"phase5-d5-{run_id}",
        task_type=AgentTaskType.KNOWLEDGE_QA,
        query_or_topic=str(question["query"]),
        retrieval_scope=str(question.get("retrieval_scope") or "all"),
        current_run=current_run,
        expected_source_types=list(question.get("expected_source_types") or []),
        should_answer_insufficient=bool(question.get("should_answer_insufficient")),
        forbidden_anchors=list(question.get("forbidden_anchors") or []),
        question_type=str(question.get("type") or ""),
        metadata={
            "question_id": qid,
            "expected_anchors": list(question.get("expected_anchors") or []),
            "expected_answer_points": list(question.get("expected_answer_points") or []),
            "expected_source_types": list(question.get("expected_source_types") or []),
            "forbidden_anchors": list(question.get("forbidden_anchors") or []),
            "should_answer_insufficient": bool(
                question.get("should_answer_insufficient")
            ),
            "question_type": str(question.get("type") or ""),
            "phase_task": TASK_ID,
            "phase5_run_id": run_id,
        },
    )


def _judge_question(
    *,
    question: dict[str, Any],
    result_status: str,
    markdown: str,
    citations: list[Citation],
    actual_anchors: list[str],
    forbidden: list[str],
    source_types: list[str],
    warning_codes: list[str],
) -> tuple[str, str, str, str, str]:
    notes: list[str] = []
    if result_status != AgentStatus.SUCCEEDED:
        notes.append(f"workflow status is {result_status}")

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
    )


def _judge_evidence_contract(
    *,
    question: dict[str, Any],
    citations: list[Citation],
    actual_anchors: list[str],
    forbidden: list[str],
    source_types: list[str],
    notes: list[str],
) -> None:
    expected_anchors = set(question.get("expected_anchors") or [])
    actual = set(actual_anchors)
    missing = sorted(expected_anchors - actual)
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
        if citation.source != "weknora_api":
            notes.append(f"citation {index} is not from weknora_api")
        if not (citation.evidence_id or citation.metadata.get("evidence_id")):
            notes.append(f"citation {index} missing evidence_id")
        if not (citation.source_type or citation.metadata.get("citation_source_type")):
            notes.append(f"citation {index} missing source_type")
        if citation.source_type == "document_chunk" and not citation.chunk_id:
            notes.append(f"citation {index} document_chunk missing chunk_id")
        if citation.source_type == "wiki_page" and not citation.wiki_page_id:
            notes.append(f"citation {index} wiki_page missing wiki_page_id")


def _judge_refusal(
    markdown: str,
    citations: list[Citation],
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


def _answer_point_summary(question: dict[str, Any], markdown: str) -> str:
    points = list(question.get("expected_answer_points") or [])
    if not points:
        return "no expected answer points; refusal/evidence contract checked"
    matched = sum(1 for point in points if _point_has_signal(point, markdown))
    return f"expected_points={len(points)}; answer_signal_matches={matched}"


def _point_has_signal(point: str, markdown: str) -> bool:
    tokens = [
        token.strip(" ，。,.;；:：、")
        for token in str(point).replace("，", " ").replace("、", " ").split()
        if len(token.strip(" ，。,.;；:：、")) >= 2
    ]
    if not tokens:
        return False
    return any(token in markdown for token in tokens)


def _actual_anchors(citations: list[Citation], known_anchors: list[str]) -> list[str]:
    anchors: set[str] = set()
    for citation in citations:
        for anchor in known_anchors:
            if _citation_has_anchor(citation, anchor):
                anchors.add(anchor)
    return sorted(anchors)


def _citation_has_anchor(citation: Citation, anchor: str) -> bool:
    values = [
        citation.title or "",
        citation.text or "",
        *_metadata_anchor_values(citation.metadata),
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


def _evidence_summaries(
    citations: list[Citation],
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
        key = citation.evidence_id or citation.chunk_id or citation.wiki_page_id or str(rank)
        if key in seen:
            continue
        seen.add(key)
        summaries.append(
            {
                "rank": str(rank),
                "anchors": ",".join(anchors) or "-",
                "source": citation.source,
                "source_type": citation.source_type or "-",
                "evidence_id": citation.evidence_id or citation.metadata.get("evidence_id") or "-",
                "external_doc_id": citation.external_doc_id or "-",
                "chunk_id": citation.chunk_id or "-",
                "wiki_page_id": citation.wiki_page_id or "-",
            }
        )
    return summaries[:5]


def _write_report(
    *,
    b5: Any,
    config: Any,
    model_config: ModelGatewayConfig,
    run_id: str,
    result: dict[str, Any],
) -> None:
    question_results: list[QuestionResult] = result["question_results"]
    uploaded: dict[str, Any] = result["uploaded"]
    wiki_page = result["wiki_page"]
    pass_count = sum(1 for item in question_results if item.status == "PASS")
    fail_count = len(question_results) - pass_count
    decision = "PASS" if fail_count == 0 else "FAIL"
    lines = [
        "# Phase 5 Real knowledge_qa 24Q PASS Report",
        "",
        "## Test Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Task | {TASK_ID} real knowledge_qa 24-question matrix |",
        "| Report marker | PHASE5_REAL |",
        f"| Run id | `{run_id}` |",
        "| Backend source | `weknora_api` |",
        "| Config summary | `MOCK_MODE=false`; `KNOWLEDGE_BACKEND=weknora_api`; model provider is non-mock; tokens and endpoints intentionally omitted |",
        f"| Model summary | provider=`{_cell(model_config.provider)}`; model=`{_cell(model_config.model_name)}`; `MOCK_MODEL_MODE=false` |",
        f"| Test scope | Phase 4 synthetic sanitized corpus `{b5.CORPUS_ID}`; 24 questions; top_k={config.top_k}; fresh/current-run upload |",
        f"| Result | {decision} |",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "| --- | ---: |",
        f"| PASS | {pass_count} |",
        f"| FAIL | {fail_count} |",
        "",
        "## Fresh Current-Run Evidence",
        "",
        "| Item | Count / id |",
        "| --- | --- |",
        f"| Uploaded documents | {len(uploaded)} |",
        f"| Published Wiki page | `{_cell(wiki_page.wiki_page_id)}` |",
        f"| Wiki slug | `{_cell(wiki_page.slug)}` |",
        "",
        "## 24 Question Matrix",
        "",
        "| Question | Type | Scope | Expected answer points | Expected anchors | Actual anchors | source_type | Citations | Retrieved | Refusal | Distractor `TEST-DISTRACTOR-001` | Version conflict | Evidence fields | Warnings | trace_id | Status | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in question_results:
        evidence_fields = "<br>".join(
            "{rank}. anchors={anchors}; source={source}; source_type={source_type}; evidence_id={evidence_id}; chunk_id={chunk_id}; wiki_page_id={wiki_page_id}".format(
                **{key: _cell(value) for key, value in summary.items()}
            )
            for summary in item.evidence_summaries
        ) or "-"
        lines.append(
            "| {qid} | {qtype} | {scope} | {points} | {expected} | {actual} | {source_types} | {citation_count} | {retrieved_count} | {refusal} | {distractor} | {version} | {evidence_fields} | {warnings} | `{trace_id}` | {status} | {notes} |".format(
                qid=_cell(item.question_id),
                qtype=_cell(item.question_type),
                scope=_cell(item.scope),
                points=_cell(item.answer_point_summary),
                expected=_cell(", ".join(item.expected_anchors) or "none"),
                actual=_cell(", ".join(item.actual_anchors) or "none"),
                source_types=_cell(", ".join(item.source_types) or "none"),
                citation_count=item.citation_count,
                retrieved_count=item.retrieved_count,
                refusal=_cell(item.refusal_status),
                distractor=_cell(item.distractor_status),
                version=_cell(item.version_status),
                evidence_fields=evidence_fields,
                warnings=_cell(", ".join(item.warning_codes) or "none"),
                trace_id=_cell(item.trace_id),
                status=_cell(item.status),
                notes=_cell(item.notes),
            )
        )
    lines.extend(
        [
            "",
            "## Acceptance Notes",
            "",
            "- All non-refusal knowledge_qa citations must be traceable `source=weknora_api` evidence from the current run.",
            "- Refusal questions P4Q-020 and P4Q-021 must return `依据不足` with zero support citations.",
            "- P4Q-022 must cite `TEST-RAG-002` and suppress `TEST-DISTRACTOR-001`.",
            "- P4Q-024 must cite both old and new policy anchors and state 新版 three-working-day priority over 旧版 five-working-day history.",
            "- This report intentionally omits service tokens, endpoints, uploaded file bodies, raw chunks, database contents, logs, prompts, and provider answers.",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_all_pass(question_results: list[QuestionResult]) -> None:
    failed = [item.question_id for item in question_results if item.status != "PASS"]
    if failed:
        raise KnowledgeQaMatrixError(
            "knowledge_qa matrix did not reach 24/24 PASS: " + ", ".join(failed)
        )


def _validate_model_config(config: ModelGatewayConfig) -> None:
    missing: list[str] = []
    provider = config.provider.strip().lower()
    if provider in {"mock", "mock_chat"}:
        missing.append("CHAT_MODEL_PROVIDER must be non-mock")
    if config.mock_model_mode:
        missing.append("MOCK_MODEL_MODE=false")
    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        if not config.base_url:
            missing.append("CHAT_MODEL_BASE_URL")
        if not config.api_key:
            missing.append("CHAT_MODEL_API_KEY")
        if not config.model_name or config.model_name == "mock-chat":
            missing.append("CHAT_MODEL_NAME")
    elif provider not in {"openai", "openai-compatible", "openai_compatible"}:
        missing.append("supported CHAT_MODEL_PROVIDER=openai_compatible")
    if missing:
        raise KnowledgeQaMatrixError(
            "missing or invalid required model env: " + ", ".join(missing)
        )


def _load_b5_module() -> Any:
    spec = importlib.util.spec_from_file_location("phase5_b5_real_rag_matrix", B5_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise KnowledgeQaMatrixError("cannot load P5-B5 helper script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    for key in (
        "Bearer" + " ",
        "X-" + "API-Key",
        "WEKNORA_" + "SERVICE_TOKEN",
        "CHAT_" + "MODEL_API_KEY",
    ):
        text = text.replace(key, "[redacted]")
    return text[:500]


if __name__ == "__main__":
    raise SystemExit(main())
