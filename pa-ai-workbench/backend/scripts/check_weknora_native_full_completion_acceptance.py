"""Acceptance checker for WeKnora Native Full Completion claims.

This checker guards WNFC 100% claims. It verifies the WNFC spec, task
reports, score math, Web Search exclusion, unsafe evidence wording, sensitive
patterns, progress rows, and browser-matrix hook inventory. The default mode is
safe for an in-progress stage: it can pass while reporting ``final_ready=false``.
Use ``--final`` to fail unless the stage is truly at ``14.00/14 = 100.0%`` with
no unfinished in-scope non-Web-Search tasks. Task rows marked ``[b]`` are
explicit user scope removals, not unfinished work.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"

SPEC_PATH = DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md"
REPORTS_BY_TASK = {
    "WNFC-0-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_PARITY_AUDIT_WNFC_0_02.md",
    "WNFC-0-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_FOUNDATION_WNFC_0_03.md",
    "WNFC-0-04": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_ACCEPTANCE_HARNESS_REPORT.md",
    "WNFC-P1-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_CREDENTIAL_BLOCKER_WNFC_P1_01.md",
    "WNFC-P1-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_WORKFLOW_WNFC_P1_02.md",
    "WNFC-P1-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_DATA_SOURCE_RAG_LOOP_WNFC_P1_03.md",
    "WNFC-P2-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_MCP_CRUD_CREDENTIALS_WNFC_P2_01.md",
    "WNFC-P2-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOLS_RESOURCES_PROMPTS_BLOCKER_WNFC_P2_02.md",
    "WNFC-P2-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_MCP_TOOL_EXECUTION_BLOCKER_WNFC_P2_03.md",
    "WNFC-P3-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_MODEL_CONFIG_SOURCE_WNFC_P3_01.md",
    "WNFC-P3-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_MODEL_ACTIVE_TESTS_WNFC_P3_02.md",
    "WNFC-P3-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_PARSER_STORAGE_DIAGNOSTICS_WNFC_P3_03.md",
    "WNFC-P3-04": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_VECTOR_STORE_FULL_MANAGEMENT_WNFC_P3_04.md",
    "WNFC-P4-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_FAQ_WORKFLOW_WNFC_P4_01.md",
    "WNFC-P4-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_TAGS_FAVORITES_WORKFLOW_WNFC_P4_02.md",
    "WNFC-P4-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_SKILL_MANAGEMENT_BLOCKER_WNFC_P4_03.md",
    "WNFC-P5-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_KB_ADMIN_RESIDUAL_WNFC_P5_01.md",
    "WNFC-P5-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_CHUNK_ADVANCED_RESIDUAL_BLOCKER_WNFC_P5_02.md",
    "WNFC-P5-03": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_CUSTOM_AGENT_ADMIN_WNFC_P5_03.md",
    "WNFC-P5-04": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_WIKI_GLOBAL_MAINTENANCE_BLOCKER_WNFC_P5_04.md",
    "WNFC-P6-01": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_BROWSER_MATRIX_WNFC_P6_01.md",
    "WNFC-P6-02": DOCS_ROOT / "WEKNORA_NATIVE_FULL_COMPLETION_FINAL_BLOCKER_REPORT_WNFC_P6_02.md",
}

EXPECTED_SCORED_GROUPS = 14
TARGET_SCORE = 14.0
TARGET_PERCENT = 100.0
EXCLUDED_CAPABILITY = "Web Search"
HARNESS_TASK_ID = "WNFC-0-04"
FINAL_TASK_ID = "WNFC-P6-02"

EVIDENCE_LABELS = (
    "audit/map",
    "governance artifact",
    "checker execution evidence",
    "live api/browser plus audit proof",
    "live api/browser",
    "live api",
    "live browser",
    "native go test",
    "docker runtime",
    "blocked evidence",
    "backlog evidence",
    "excluded evidence",
)

SENSITIVE_TEXT_PATTERNS = {
    "secret_bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    "secret_openai_key": re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{14,}\b"),
    "secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|service[_-]?token|password|secret|private[_-]?key|authorization)"
        r"\s*[:=]\s*(?!\[?redacted\]?|omitted|configured\b|true\b|false\b|masked\b)"
        r"[^\s`|,;]{8,}"
    ),
    "private_key_block": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
}

UNSAFE_PASS_PATTERNS = {
    "unsafe_fixture_only_pass": re.compile(
        r"(?i)(?<!not )(?:fixture-only|fixture only)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_mock_pass": re.compile(r"(?i)(?<!not )mock\s+PASS\s+(?:allowed|counts|accepted|complete|green)"),
    "unsafe_cached_pass": re.compile(
        r"(?i)(?<!not )(?:cached|old report|stale)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_static_ui_pass": re.compile(
        r"(?i)(?<!not )static\s+UI\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_demo_pass": re.compile(r"(?i)(?<!not )(?:demo|MVP)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"),
}


@dataclass(frozen=True)
class Issue:
    path: Path | None
    code: str
    message: str
    line_number: int = 0


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    priority: str
    capability_slice: str
    status: str
    evidence: str
    line_number: int


@dataclass(frozen=True)
class CapabilityRow:
    name: str
    wnx_state: str
    wnfc_target: str
    line_number: int


@dataclass(frozen=True)
class ScoreInfo:
    group_count: int
    current_score: float
    current_percent: float
    target_score: float
    target_percent: float
    excluded_group: str


@dataclass(frozen=True)
class CheckSummary:
    reports_checked: int
    task_rows: int
    completed_tasks: int
    unfinished_tasks: int
    current_score: float
    current_percent: float
    target_score: float
    target_percent: float
    final_ready: bool
    browser_hooks: str
    mode: str


class AcceptanceError(RuntimeError):
    """Raised when static stage inputs cannot be parsed safely."""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()

    try:
        summary, issues = _run_static_checks(final_mode=args.final)
    except Exception as exc:  # noqa: BLE001
        print(f"WNFC acceptance check failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    if issues:
        print("WNFC native full completion acceptance check failed")
        for issue in issues:
            path = str(issue.path.relative_to(PROJECT_ROOT)) if issue.path else "-"
            line = f":{issue.line_number}" if issue.line_number else ""
            print(f"- {path}{line}: {issue.code}: {issue.message}")
        return 1

    print("WNFC native full completion acceptance check passed")
    print("- evidence_type: checker_execution")
    print(f"- mode: {summary.mode}")
    print(f"- reports checked: {summary.reports_checked}")
    print(f"- task rows: {summary.task_rows}")
    print(f"- completed tasks: {summary.completed_tasks}")
    print(f"- unfinished tasks: {summary.unfinished_tasks}")
    print(f"- current score: {summary.current_score:.2f}/14 = {summary.current_percent:.1f}%")
    print(f"- target score: {summary.target_score:.2f}/14 = {summary.target_percent:.1f}%")
    print("- web_search: excluded")
    print(f"- final_ready: {str(summary.final_ready).lower()}")
    print(f"- browser_hooks: {summary.browser_hooks}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check WNFC 100% acceptance guardrails and final-readiness claims.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run positive and negative fixtures for the WNFC checker itself",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="fail unless WNFC is truly final-ready at 14.00/14 with no unfinished tasks",
    )
    return parser.parse_args(argv)


def _run_static_checks(final_mode: bool) -> tuple[CheckSummary, list[Issue]]:
    issues: list[Issue] = []
    spec = _read_text(SPEC_PATH, issues)
    if not spec:
        return _empty_summary("final" if final_mode else "in-progress"), issues

    issues.extend(_check_text_safety(SPEC_PATH, spec))

    task_rows = _parse_task_rows(spec)
    if not task_rows:
        issues.append(Issue(SPEC_PATH, "missing_task_board", "WNFC task board could not be parsed"))
    task_by_id = {row.task_id: row for row in task_rows}
    progress_tasks = _parse_progress_tasks(spec)
    score_info = _parse_score_info(spec)
    capabilities = _parse_capability_rows(spec)

    issues.extend(_check_score_contract(score_info, capabilities))
    issues.extend(_check_task_progress(task_rows, progress_tasks))
    issues.extend(_check_web_search_boundary(task_rows, capabilities))
    browser_hooks = _check_browser_hook_inventory(task_by_id, issues)

    reports_checked = 0
    for task_id, report_path in REPORTS_BY_TASK.items():
        row = task_by_id.get(task_id)
        required_now = row is not None and row.status in {"[x]", "[!]"}
        if task_id != HARNESS_TASK_ID:
            required_now = True
        text = _read_optional_report(report_path, issues if required_now else None)
        if not text:
            continue
        reports_checked += 1
        issues.extend(_check_text_safety(report_path, text))
        issues.extend(_check_report_evidence(task_id, report_path, text, required_now=required_now))

    unfinished = _unfinished_tasks(task_rows)
    final_ready = _is_final_ready(score_info, unfinished)
    if final_mode:
        issues.extend(_check_final_mode(score_info, unfinished, task_by_id))

    summary = CheckSummary(
        reports_checked=reports_checked,
        task_rows=len(task_rows),
        completed_tasks=sum(1 for row in task_rows if row.status == "[x]"),
        unfinished_tasks=len(unfinished),
        current_score=score_info.current_score,
        current_percent=score_info.current_percent,
        target_score=score_info.target_score,
        target_percent=score_info.target_percent,
        final_ready=final_ready,
        browser_hooks=browser_hooks,
        mode="final" if final_mode else "in-progress",
    )
    return summary, issues


def _read_text(path: Path, issues: list[Issue]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(Issue(path, "missing_file", "required stage file is missing"))
        return ""


def _read_optional_report(path: Path, issues: list[Issue] | None) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if issues is not None:
            issues.append(Issue(path, "missing_report", "required WNFC evidence report is missing"))
        return ""


def _check_text_safety(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for code, pattern in SENSITIVE_TEXT_PATTERNS.items():
            if pattern.search(line):
                issues.append(Issue(path, code, "secret-shaped value is present", line_number))
        for code, pattern in UNSAFE_PASS_PATTERNS.items():
            if pattern.search(line):
                issues.append(Issue(path, code, "unsafe evidence appears to count as PASS", line_number))
    return issues


def _parse_task_rows(spec: str) -> list[TaskRow]:
    rows: list[TaskRow] = []
    pattern = re.compile(
        r"^\|\s*(WNFC-[0-9A-Z-]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\[[x~! b]\])\s*\|\s*([^|]+?)\s*\|$"
    )
    for line_number, line in enumerate(spec.splitlines(), start=1):
        match = pattern.match(line)
        if not match:
            continue
        rows.append(
            TaskRow(
                task_id=match.group(1).strip(),
                priority=match.group(2).strip(),
                capability_slice=match.group(3).strip(),
                status=match.group(4).strip(),
                evidence=match.group(5).strip(),
                line_number=line_number,
            )
        )
    return rows


def _parse_progress_tasks(spec: str) -> set[str]:
    tasks: set[str] = set()
    for line in spec.splitlines():
        match = re.match(r"\|\s*20\d\d-\d\d-\d\d\s*\|\s*(WNFC-[0-9A-Z-]+)\s*\|", line)
        if match:
            tasks.add(match.group(1))
    return tasks


def _parse_score_info(spec: str) -> ScoreInfo:
    group_match = re.search(r"WNFC scored groups\s*=\s*(\d+)", spec)
    current_match = re.search(
        r"current WNFC score\s*=\s*([0-9.]+)\s*/\s*14\s*=\s*([0-9.]+)%",
        spec,
    )
    target_match = re.search(
        r"target WNFC score\s*=\s*([0-9.]+)\s*/\s*14\s*=\s*([0-9.]+)%",
        spec,
    )
    if not group_match or not current_match or not target_match:
        raise AcceptanceError("WNFC score block could not be parsed")
    excluded = EXCLUDED_CAPABILITY if "Web Search | `live-partial` | `excluded`" in spec else ""
    return ScoreInfo(
        group_count=int(group_match.group(1)),
        current_score=float(current_match.group(1)),
        current_percent=float(current_match.group(2)),
        target_score=float(target_match.group(1)),
        target_percent=float(target_match.group(2)),
        excluded_group=excluded,
    )


def _parse_capability_rows(spec: str) -> list[CapabilityRow]:
    rows: list[CapabilityRow] = []
    in_table = False
    for line_number, line in enumerate(spec.splitlines(), start=1):
        if line.startswith("| Capability group | WNX state | WNFC target |"):
            in_table = True
            continue
        if in_table and line.startswith("## 8."):
            break
        if not in_table or line.startswith("| ---") or not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3:
            rows.append(
                CapabilityRow(
                    name=cells[0],
                    wnx_state=cells[1].strip("`"),
                    wnfc_target=cells[2].strip("`"),
                    line_number=line_number,
                )
            )
    return rows


def _check_score_contract(score_info: ScoreInfo, capabilities: list[CapabilityRow]) -> list[Issue]:
    issues: list[Issue] = []
    if score_info.group_count != EXPECTED_SCORED_GROUPS:
        issues.append(Issue(SPEC_PATH, "wrong_scored_group_count", "WNFC scored groups must equal 14"))
    if score_info.target_score != TARGET_SCORE or score_info.target_percent != TARGET_PERCENT:
        issues.append(Issue(SPEC_PATH, "wrong_target_score", "target WNFC score must be 14.00/14 = 100.0%"))
    if score_info.excluded_group != EXCLUDED_CAPABILITY:
        issues.append(Issue(SPEC_PATH, "web_search_not_excluded", "Web Search must be the excluded WNFC capability"))
    excluded = [row for row in capabilities if row.wnfc_target == "excluded"]
    if len(excluded) != 1 or excluded[0].name != EXCLUDED_CAPABILITY:
        issues.append(Issue(SPEC_PATH, "wrong_excluded_capability", "only Web Search may be excluded"))
    non_web = [row for row in capabilities if row.name != EXCLUDED_CAPABILITY]
    if len(non_web) != EXPECTED_SCORED_GROUPS:
        issues.append(Issue(SPEC_PATH, "wrong_non_web_capability_count", "exactly 14 non-Web-Search groups are required"))
    for row in non_web:
        if row.wnfc_target != "full-complete":
            issues.append(
                Issue(
                    SPEC_PATH,
                    "non_web_target_not_full_complete",
                    f"{row.name} target is {row.wnfc_target}, expected full-complete",
                    row.line_number,
                )
            )
    return issues


def _check_task_progress(task_rows: list[TaskRow], progress_tasks: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    for row in task_rows:
        if row.status in {"[x]", "[!]", "[b]"} and row.task_id not in progress_tasks:
            issues.append(
                Issue(SPEC_PATH, "missing_progress_log", f"{row.task_id} is {row.status} without progress log", row.line_number)
            )
    return issues


def _check_web_search_boundary(task_rows: list[TaskRow], capabilities: list[CapabilityRow]) -> list[Issue]:
    issues: list[Issue] = []
    for row in task_rows:
        text = f"{row.capability_slice} {row.evidence}".lower()
        normalized = text.replace("-", " ")
        if "web search" not in normalized:
            continue
        if not any(marker in normalized for marker in ("excluding", "excludes", "excluded", "non web search")):
            issues.append(
                Issue(
                    SPEC_PATH,
                    "web_search_task_in_scope",
                    f"{row.task_id} appears to put Web Search in WNFC scope",
                    row.line_number,
                )
            )
    for row in capabilities:
        if row.name == EXCLUDED_CAPABILITY and row.wnfc_target != "excluded":
            issues.append(Issue(SPEC_PATH, "web_search_target_not_excluded", "Web Search target must be excluded", row.line_number))
    return issues


def _check_browser_hook_inventory(task_by_id: dict[str, TaskRow], issues: list[Issue]) -> str:
    matrix = task_by_id.get("WNFC-P6-01")
    final = task_by_id.get(FINAL_TASK_ID)
    if matrix is None:
        issues.append(Issue(SPEC_PATH, "missing_browser_matrix_task", "WNFC-P6-01 browser matrix task is missing"))
        return "missing"
    if final is None:
        issues.append(Issue(SPEC_PATH, "missing_final_report_task", "WNFC-P6-02 final report task is missing"))
        return "incomplete"
    matrix_text = f"{matrix.capability_slice} {matrix.evidence}".lower()
    final_text = f"{final.capability_slice} {final.evidence}".lower()
    if "browser matrix" not in matrix_text or "desktop/mobile" not in matrix_text:
        issues.append(Issue(SPEC_PATH, "missing_browser_matrix_hook", "WNFC-P6-01 must require desktop/mobile browser matrix", matrix.line_number))
        return "incomplete"
    if "14.00/14" not in final_text and "14.00 / 14" not in final_text:
        issues.append(Issue(SPEC_PATH, "missing_final_score_hook", "WNFC-P6-02 must require final 14.00/14 proof", final.line_number))
        return "incomplete"
    return "WNFC-P6-01 desktop/mobile matrix and WNFC-P6-02 final report hooks present"


def _check_report_evidence(task_id: str, path: Path, text: str, *, required_now: bool) -> list[Issue]:
    issues: list[Issue] = []
    lower = text.lower()
    if task_id not in text:
        issues.append(Issue(path, "missing_task_id", f"report does not mention {task_id}"))
    if "pass" in lower and not any(label in lower for label in EVIDENCE_LABELS):
        issues.append(Issue(path, "missing_evidence_class", "PASS report lacks evidence classification"))
    if task_id == "WNFC-0-02":
        for required in ("Native routes", "PA-first work possible", "Native exception", "Required external input"):
            if required not in text:
                issues.append(Issue(path, "missing_parity_marker", f"missing parity marker {required}"))
    if task_id == "WNFC-0-03":
        for required in ("confirm_token", "native mutation audit", "live_api/browser_plus_audit", "raw_confirm_token_absent"):
            if required not in text:
                issues.append(Issue(path, "missing_foundation_marker", f"missing foundation marker {required}"))
    if task_id == HARNESS_TASK_ID and required_now:
        for required in (
            "checker execution evidence",
            "final_ready=false",
            "Web Search exclusion",
            "Browser Hook Inventory",
            "Final Mode Negative Proof",
        ):
            if required.lower() not in lower:
                issues.append(Issue(path, "missing_harness_marker", f"missing harness marker {required}"))
    return issues


def _unfinished_tasks(task_rows: list[TaskRow]) -> list[TaskRow]:
    return [row for row in task_rows if row.status in {"[ ]", "[~]", "[!]"}]


def _is_final_ready(score_info: ScoreInfo, unfinished: list[TaskRow]) -> bool:
    return (
        score_info.current_score == TARGET_SCORE
        and score_info.current_percent == TARGET_PERCENT
        and not unfinished
    )


def _check_final_mode(
    score_info: ScoreInfo,
    unfinished: list[TaskRow],
    task_by_id: dict[str, TaskRow],
) -> list[Issue]:
    issues: list[Issue] = []
    if score_info.current_score != TARGET_SCORE or score_info.current_percent != TARGET_PERCENT:
        issues.append(
            Issue(SPEC_PATH, "final_score_below_target", "final mode requires current WNFC score 14.00/14 = 100.0%")
        )
    for row in unfinished:
        issues.append(
            Issue(
                SPEC_PATH,
                "unfinished_task_blocks_final",
                f"{row.task_id} remains {row.status}; final WNFC cannot pass while in-scope non-Web-Search tasks are incomplete",
                row.line_number,
            )
        )
    final = task_by_id.get(FINAL_TASK_ID)
    if final is None or final.status != "[x]":
        issues.append(Issue(SPEC_PATH, "final_report_not_complete", "WNFC-P6-02 final report must be [x] in final mode"))
    return issues


def _run_self_test() -> int:
    try:
        _self_test_safety_patterns()
        _self_test_score_and_web_search()
        _self_test_final_mode()
    except Exception as exc:  # noqa: BLE001
        print(f"WNFC acceptance checker self-test failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1
    print("WNFC acceptance checker self-test passed")
    print("- positive 14/14 fixture accepted")
    print("- negative fixture rejected unsafe PASS evidence and secret-shaped values")
    print("- final-mode fixture rejects incomplete non-Web-Search tasks")
    print("- Web Search implementation task is rejected")
    return 0


def _self_test_safety_patterns() -> None:
    with TemporaryDirectory(prefix="wnfc-acceptance-check-") as temp_dir:
        root = Path(temp_dir)
        good = root / "good.md"
        bad = root / "bad.md"
        fake_key = "sk-" + "fixturefixturefixture"
        good.write_text(
            "Task: `WNFC-0-04`\n"
            "Evidence type: checker execution evidence.\n"
            "fixture-only evidence is not PASS.\n"
            "mock evidence is not PASS.\n",
            encoding="utf-8",
        )
        bad.write_text(
            "Task: `WNFC-0-04`\n"
            "Evidence type: fixture-only\n"
            "fixture-only PASS allowed\n"
            f"api_key: {fake_key}\n",
            encoding="utf-8",
        )
        if _check_text_safety(good, good.read_text(encoding="utf-8")):
            raise AcceptanceError("positive safety fixture produced issues")
        bad_codes = {issue.code for issue in _check_text_safety(bad, bad.read_text(encoding="utf-8"))}
        expected = {"unsafe_fixture_only_pass", "secret_openai_key", "secret_assignment"}
        if not expected <= bad_codes:
            raise AcceptanceError(f"negative safety fixture missed issues: {sorted(bad_codes)}")


def _self_test_score_and_web_search() -> None:
    good_spec = _fixture_spec(current="14.00 / 14 = 100.0%", all_done=True)
    score_info = _parse_score_info(good_spec)
    capabilities = _parse_capability_rows(good_spec)
    score_issues = _check_score_contract(score_info, capabilities)
    if score_issues:
        raise AcceptanceError("positive score fixture produced issues")

    bad_spec = good_spec.replace(
        "| WNFC-0-02 | Governance | Native parity audit excluding Web Search | [x] | Source audit. |",
        "| WNFC-P0-99 | P0 | Web Search provider setup | [ ] | Real provider test. |",
    )
    rows = _parse_task_rows(bad_spec)
    codes = {issue.code for issue in _check_web_search_boundary(rows, capabilities)}
    if "web_search_task_in_scope" not in codes:
        raise AcceptanceError("Web Search implementation task was not rejected")

    bad_score_spec = good_spec.replace("target WNFC score = 14.00 / 14 = 100.0%", "target WNFC score = 13.00 / 14 = 92.9%")
    bad_codes = {issue.code for issue in _check_score_contract(_parse_score_info(bad_score_spec), capabilities)}
    if "wrong_target_score" not in bad_codes:
        raise AcceptanceError("wrong target score was not rejected")


def _self_test_final_mode() -> None:
    in_progress_spec = _fixture_spec(current="11.50 / 14 = 82.1%", all_done=False)
    score_info = _parse_score_info(in_progress_spec)
    rows = _parse_task_rows(in_progress_spec)
    issues = _check_final_mode(score_info, _unfinished_tasks(rows), {row.task_id: row for row in rows})
    codes = {issue.code for issue in issues}
    expected = {"final_score_below_target", "unfinished_task_blocks_final", "final_report_not_complete"}
    if not expected <= codes:
        raise AcceptanceError(f"final-mode negative fixture missed issues: {sorted(codes)}")


def _fixture_spec(*, current: str, all_done: bool) -> str:
    status = "[x]" if all_done else "[ ]"
    return f"""# Fixture

WNFC scored groups = 14
current WNFC score = {current}
target WNFC score = 14.00 / 14 = 100.0%

| Capability group | WNX state | WNFC target | Required move |
| --- | --- | --- | --- |
| System health/status/deployment | `live-full` | `full-complete` | Preserve. |
| Workspace/knowledge-base management | `live-full` | `full-complete` | Preserve. |
| Document lifecycle | `live-full` | `full-complete` | Preserve. |
| Chunk management | `live-full` | `full-complete` | Preserve. |
| Knowledge-search/RAG | `live-full` | `full-complete` | Preserve. |
| Knowledge-chat/session chat | `live-full` | `full-complete` | Preserve. |
| AgentQA/custom Agent | `live-full` | `full-complete` | Preserve. |
| Native Wiki | `live-full` | `full-complete` | Preserve. |
| MCP | `live-full` | `full-complete` | Preserve. |
| Web Search | `live-partial` | `excluded` | Freeze. |
| Vector store | `live-full` | `full-complete` | Preserve. |
| Model/embedding/rerank/parser | `live-full` | `full-complete` | Preserve. |
| Data sources/connectors | `live-full` | `full-complete` | Preserve. |
| FAQ/tags/favorites/skills | `live-full` | `full-complete` | Preserve. |
| History/citation/product shell | `live-full` | `full-complete` | Preserve. |

## 8. Execution Protocol

| ID | Priority | Capability slice | Status | Required evidence |
| --- | --- | --- | --- | --- |
| WNFC-0-02 | Governance | Native parity audit excluding Web Search | [x] | Source audit. |
| WNFC-0-04 | Governance | 100% acceptance harness | [x] | Checker excludes Web Search. |
| WNFC-P6-01 | P0 | Full local productivity browser matrix | {status} | Desktop/mobile browser matrix. |
| WNFC-P6-02 | P0 | Final 100% completion report | {status} | Final report proves `14.00/14 = 100%`. |
"""


def _empty_summary(mode: str) -> CheckSummary:
    return CheckSummary(
        reports_checked=0,
        task_rows=0,
        completed_tasks=0,
        unfinished_tasks=0,
        current_score=0,
        current_percent=0,
        target_score=0,
        target_percent=0,
        final_ready=False,
        browser_hooks="missing",
        mode=mode,
    )


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        text = text.replace(marker, "[redacted]")
    return text[:260]


if __name__ == "__main__":
    raise SystemExit(main())
