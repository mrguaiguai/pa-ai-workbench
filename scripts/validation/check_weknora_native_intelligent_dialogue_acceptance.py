"""Acceptance checker for WeKnora Native Intelligent Dialogue claims.

This checker guards WNID final-readiness claims. Default mode is safe for an
in-progress stage: it verifies the governance contract and reports
``final_ready=false`` while later WNID tasks remain open. Use ``--final`` to
fail unless every in-scope Intelligent Conversation capability is complete with
current-run evidence, Web Search in scope, MCP execution in scope, a browser
matrix hook, a final report, and no unsafe evidence wording.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs" / "archive" / "wnid"

SPEC_PATH = DOCS_ROOT / "WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md"
PARITY_MAP_PATH = DOCS_ROOT / "WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md"
HARNESS_REPORT_PATH = DOCS_ROOT / "WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md"
BROWSER_MATRIX_PATH = DOCS_ROOT / "WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_BROWSER_MATRIX_WNID_P8_01.md"
FINAL_REPORT_PATH = DOCS_ROOT / "WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md"

EXPECTED_TASK_IDS = (
    "WNID-0-01",
    "WNID-0-02",
    "WNID-0-03",
    "WNID-P1-01",
    "WNID-P1-02",
    "WNID-P2-01",
    "WNID-P2-02",
    "WNID-P3-01",
    "WNID-P3-02",
    "WNID-P3-03",
    "WNID-P4-01",
    "WNID-P4-02",
    "WNID-P5-01",
    "WNID-P6-01",
    "WNID-P7-01",
    "WNID-P8-01",
    "WNID-P8-02",
)

EXPECTED_CAPABILITY_GROUPS = (
    "Intelligent dialogue shell",
    "Quick Q&A",
    "ReACT/custom Agent reasoning",
    "Wiki Mode",
    "Built-in tool calling",
    "MCP tool calling",
    "Web Search",
    "Conversation strategy",
    "Suggested questions",
    "History/citation/audit",
)

README_INTELLIGENT_CONVERSATION_ROWS = (
    "Intelligent Reasoning",
    "Quick Q&A",
    "Wiki Mode",
    "Tool Calling",
    "Conversation Strategy",
    "Suggested Questions",
)

HARD_GATE_TASK_IDS = {
    "mcp_execution": "WNID-P3-02",
    "web_search_provider": "WNID-P4-01",
    "web_search_agent_run": "WNID-P4-02",
    "browser_matrix": "WNID-P8-01",
    "final_report": "WNID-P8-02",
}

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
        r"(?i)(?:fixture-only|fixture only)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_mock_pass": re.compile(r"(?i)mock\s+PASS\s+(?:allowed|counts|accepted|complete|green)"),
    "unsafe_demo_pass": re.compile(r"(?i)(?:demo|mvp)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"),
    "unsafe_cached_pass": re.compile(
        r"(?i)(?:cached|old report|stale)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_static_ui_pass": re.compile(
        r"(?i)static\s+UI\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
    "unsafe_status_only_pass": re.compile(
        r"(?i)(?:status|catalog|visibility-only|visibility only)\s+PASS\s+(?:allowed|counts|accepted|complete|green)"
    ),
}

NEGATION_MARKERS = (
    "do not",
    "does not",
    "must not",
    "cannot",
    "can not",
    "not ",
    "no ",
    "without",
    "blocked",
    "fails",
    "rejected",
    "not final",
)


@dataclass(frozen=True)
class Issue:
    path: Path | None
    code: str
    message: str
    line_number: int = 0


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    phase: str
    title: str
    status: str
    acceptance: str
    line_number: int


@dataclass(frozen=True)
class CapabilityRow:
    name: str
    baseline_signal: str
    target: str
    hard_evidence: str
    line_number: int


@dataclass(frozen=True)
class CheckSummary:
    task_rows: int
    completed_tasks: int
    open_tasks: int
    progress_log_entries: int
    web_search: str
    mcp_execution: str
    current_run_evidence: str
    browser_matrix: str
    final_report: str
    final_ready: bool
    mode: str


class AcceptanceError(RuntimeError):
    """Raised when WNID acceptance inputs cannot be parsed safely."""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()

    try:
        summary, issues = _run_static_checks(final_mode=args.final)
    except Exception as exc:  # noqa: BLE001
        print(f"WNID acceptance check failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    if issues:
        print("WNID native intelligent dialogue acceptance check failed")
        for issue in issues:
            path = str(issue.path.relative_to(PROJECT_ROOT)) if issue.path else "-"
            line = f":{issue.line_number}" if issue.line_number else ""
            print(f"- {path}{line}: {issue.code}: {issue.message}")
        return 1

    print("WNID native intelligent dialogue acceptance check passed")
    print("- evidence_type: checker_execution")
    print(f"- mode: {summary.mode}")
    print(f"- task_rows: {summary.task_rows}")
    print(f"- completed_tasks: {summary.completed_tasks}")
    print(f"- open_tasks: {summary.open_tasks}")
    print(f"- progress_log_entries: {summary.progress_log_entries}")
    print(f"- web_search: {summary.web_search}")
    print(f"- mcp_execution: {summary.mcp_execution}")
    print(f"- current_run_evidence: {summary.current_run_evidence}")
    print(f"- browser_matrix: {summary.browser_matrix}")
    print(f"- final_report: {summary.final_report}")
    print(f"- final_ready: {str(summary.final_ready).lower()}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check WNID Intelligent Conversation guardrails and final-readiness claims.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run positive and negative fixtures for the WNID checker itself",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="fail unless WNID is truly final-ready with all in-scope hard gates complete",
    )
    return parser.parse_args(argv)


def _run_static_checks(final_mode: bool) -> tuple[CheckSummary, list[Issue]]:
    issues: list[Issue] = []
    spec = _read_text(SPEC_PATH, issues)
    parity_map = _read_text(PARITY_MAP_PATH, issues)
    harness_report = _read_optional_text(HARNESS_REPORT_PATH)
    final_report = _read_optional_text(FINAL_REPORT_PATH)
    browser_report = _read_optional_text(BROWSER_MATRIX_PATH)
    if not spec or not parity_map:
        return _empty_summary("final" if final_mode else "in-progress"), issues

    for path, text in (
        (SPEC_PATH, spec),
        (PARITY_MAP_PATH, parity_map),
        (HARNESS_REPORT_PATH, harness_report),
        (FINAL_REPORT_PATH, final_report),
        (BROWSER_MATRIX_PATH, browser_report),
    ):
        if text:
            issues.extend(_check_text_safety(path, text))

    task_rows = _parse_task_rows(spec)
    capability_rows = _parse_capability_rows(spec)
    progress_tasks = _parse_progress_tasks(spec)
    task_by_id = {row.task_id: row for row in task_rows}
    open_tasks = _open_tasks(task_rows)

    issues.extend(_check_task_board(task_rows, task_by_id))
    issues.extend(_check_progress_log(task_rows, progress_tasks))
    issues.extend(_check_intelligent_conversation_rows(spec, parity_map))
    issues.extend(_check_capability_contract(capability_rows))
    web_search_state, web_search_issues = _check_web_search_in_scope(spec, task_by_id, capability_rows)
    issues.extend(web_search_issues)
    mcp_state, mcp_issues = _check_mcp_execution_in_scope(spec, task_by_id, capability_rows)
    issues.extend(mcp_issues)
    current_run_state, current_run_issues = _check_current_run_evidence(spec, task_by_id, final_report)
    issues.extend(current_run_issues)
    browser_state, browser_issues = _check_browser_matrix_hook(task_by_id, browser_report, final_mode=final_mode)
    issues.extend(browser_issues)
    final_report_state, final_issues = _check_final_report(task_by_id, final_report, final_mode=final_mode)
    issues.extend(final_issues)

    final_ready = (
        not open_tasks
        and final_report_state == "present"
        and browser_state == "present"
        and web_search_state == "in_scope"
        and mcp_state == "in_scope"
        and current_run_state in {"contract_present", "present"}
    )
    if final_mode and not final_ready:
        issues.extend(_check_final_mode(open_tasks, task_by_id, final_report, browser_report))

    summary = CheckSummary(
        task_rows=len(task_rows),
        completed_tasks=sum(1 for row in task_rows if row.status == "[x]"),
        open_tasks=len(open_tasks),
        progress_log_entries=len(progress_tasks),
        web_search=web_search_state,
        mcp_execution=mcp_state,
        current_run_evidence=current_run_state,
        browser_matrix=browser_state,
        final_report=final_report_state,
        final_ready=final_ready,
        mode="final" if final_mode else "in-progress",
    )
    return summary, issues


def _read_text(path: Path, issues: list[Issue]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(Issue(path, "missing_file", "required WNID stage file is missing"))
        return ""


def _read_optional_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _check_text_safety(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for code, pattern in SENSITIVE_TEXT_PATTERNS.items():
            if pattern.search(line):
                issues.append(Issue(path, code, "secret-shaped value is present", line_number))
        lower = line.lower()
        for code, pattern in UNSAFE_PASS_PATTERNS.items():
            if pattern.search(line) and not any(marker in lower for marker in NEGATION_MARKERS):
                issues.append(Issue(path, code, "unsafe evidence appears to count as PASS", line_number))
    return issues


def _parse_task_rows(spec: str) -> list[TaskRow]:
    rows: list[TaskRow] = []
    pattern = re.compile(
        r"^\|\s*(WNID-[0-9A-Z-]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\[[x~! b]\])\s*\|\s*([^|]+?)\s*\|$"
    )
    for line_number, line in enumerate(spec.splitlines(), start=1):
        match = pattern.match(line)
        if not match:
            continue
        rows.append(
            TaskRow(
                task_id=match.group(1).strip(),
                phase=match.group(2).strip(),
                title=match.group(3).strip(),
                status=match.group(4).strip(),
                acceptance=match.group(5).strip(),
                line_number=line_number,
            )
        )
    return rows


def _parse_progress_tasks(spec: str) -> set[str]:
    tasks: set[str] = set()
    for line in spec.splitlines():
        match = re.match(r"\|\s*20\d\d-\d\d-\d\d\s*\|\s*(WNID-[0-9A-Z-]+)\s*\|", line)
        if match:
            tasks.add(match.group(1))
    return tasks


def _parse_capability_rows(spec: str) -> list[CapabilityRow]:
    rows: list[CapabilityRow] = []
    in_table = False
    for line_number, line in enumerate(spec.splitlines(), start=1):
        if line.startswith("| Capability group | Baseline signal | WNID target |"):
            in_table = True
            continue
        if in_table and line.startswith("## 5."):
            break
        if not in_table or line.startswith("| ---") or not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append(
                CapabilityRow(
                    name=cells[0],
                    baseline_signal=cells[1],
                    target=cells[2].strip("`"),
                    hard_evidence=cells[3],
                    line_number=line_number,
                )
            )
    return rows


def _check_task_board(task_rows: list[TaskRow], task_by_id: dict[str, TaskRow]) -> list[Issue]:
    issues: list[Issue] = []
    if not task_rows:
        issues.append(Issue(SPEC_PATH, "missing_task_board", "WNID task board could not be parsed"))
        return issues
    for task_id in EXPECTED_TASK_IDS:
        if task_id not in task_by_id:
            issues.append(Issue(SPEC_PATH, "missing_task_row", f"{task_id} is missing from the task board"))
    for task_id, row in task_by_id.items():
        if row.status == "[b]" and task_id in HARD_GATE_TASK_IDS.values():
            issues.append(Issue(SPEC_PATH, "hard_gate_removed", f"{task_id} cannot be blocked/removed for final WNID PASS", row.line_number))
    return issues


def _check_progress_log(task_rows: list[TaskRow], progress_tasks: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    for row in task_rows:
        if row.status in {"[x]", "[!]", "[b]"} and row.task_id not in progress_tasks:
            issues.append(
                Issue(SPEC_PATH, "missing_progress_log", f"{row.task_id} is {row.status} without progress log", row.line_number)
            )
    return issues


def _check_intelligent_conversation_rows(spec: str, parity_map: str) -> list[Issue]:
    issues: list[Issue] = []
    combined = f"{spec}\n{parity_map}"
    for row in README_INTELLIGENT_CONVERSATION_ROWS:
        if row not in combined:
            issues.append(Issue(SPEC_PATH, "missing_readme_capability", f"README Intelligent Conversation row is not tracked: {row}"))
    return issues


def _check_capability_contract(capability_rows: list[CapabilityRow]) -> list[Issue]:
    issues: list[Issue] = []
    by_name = {row.name: row for row in capability_rows}
    for name in EXPECTED_CAPABILITY_GROUPS:
        row = by_name.get(name)
        if row is None:
            issues.append(Issue(SPEC_PATH, "missing_capability_group", f"{name} is missing from WNID target table"))
            continue
        if row.target != "complete":
            issues.append(Issue(SPEC_PATH, "capability_not_complete_target", f"{name} target must remain complete", row.line_number))
    return issues


def _check_web_search_in_scope(
    spec: str,
    task_by_id: dict[str, TaskRow],
    capability_rows: list[CapabilityRow],
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    required_phrases = (
        "Make Web Search a final PASS requirement",
        "Web Search and MCP execution must not be removed",
        "Web Search PASS needs provider identity plus URL/title/snippet/rank",
    )
    for phrase in required_phrases:
        if phrase not in spec:
            issues.append(Issue(SPEC_PATH, "web_search_contract_missing", f"missing Web Search contract phrase: {phrase}"))
    for task_id in ("WNID-P4-01", "WNID-P4-02"):
        row = task_by_id.get(task_id)
        if row is None:
            issues.append(Issue(SPEC_PATH, "web_search_task_missing", f"{task_id} is required for WNID Web Search"))
        elif row.status == "[b]":
            issues.append(Issue(SPEC_PATH, "web_search_removed", f"{task_id} cannot be removed for final WNID PASS", row.line_number))
    web_rows = [row for row in capability_rows if row.name == "Web Search"]
    if len(web_rows) != 1 or web_rows[0].target != "complete":
        issues.append(Issue(SPEC_PATH, "web_search_not_complete_target", "Web Search capability target must be complete"))
    return ("in_scope" if not issues else "contract_error"), issues


def _check_mcp_execution_in_scope(
    spec: str,
    task_by_id: dict[str, TaskRow],
    capability_rows: list[CapabilityRow],
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    required_phrases = (
        "Make MCP tool execution a final PASS requirement",
        "MCP PASS needs service id/name, tool name",
        "executes at least one tool",
    )
    for phrase in required_phrases:
        if phrase not in spec:
            issues.append(Issue(SPEC_PATH, "mcp_execution_contract_missing", f"missing MCP execution contract phrase: {phrase}"))
    row = task_by_id.get("WNID-P3-02")
    if row is None:
        issues.append(Issue(SPEC_PATH, "mcp_execution_task_missing", "WNID-P3-02 is required for MCP execution"))
    elif row.status == "[b]":
        issues.append(Issue(SPEC_PATH, "mcp_execution_removed", "WNID-P3-02 cannot be removed for final WNID PASS", row.line_number))
    mcp_rows = [capability for capability in capability_rows if capability.name == "MCP tool calling"]
    if len(mcp_rows) != 1 or mcp_rows[0].target != "complete":
        issues.append(Issue(SPEC_PATH, "mcp_not_complete_target", "MCP tool calling capability target must be complete"))
    return ("in_scope" if not issues else "contract_error"), issues


def _check_current_run_evidence(
    spec: str,
    task_by_id: dict[str, TaskRow],
    final_report: str,
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    final_row = task_by_id.get("WNID-P8-02")
    if "current-run evidence" not in spec:
        issues.append(Issue(SPEC_PATH, "current_run_contract_missing", "WNID spec must require current-run evidence"))
    if final_row and "current-run evidence" not in final_row.acceptance:
        issues.append(Issue(SPEC_PATH, "final_task_missing_current_run", "WNID-P8-02 acceptance must require current-run evidence", final_row.line_number))
    if final_report:
        lower = final_report.lower()
        required = ("current-run", "web search", "mcp", "browser matrix")
        missing = [marker for marker in required if marker not in lower]
        if missing:
            issues.append(Issue(FINAL_REPORT_PATH, "final_report_missing_current_run_marker", f"final report missing markers: {', '.join(missing)}"))
        return ("present" if not missing else "contract_error"), issues
    return ("contract_present" if not issues else "contract_error"), issues


def _check_browser_matrix_hook(
    task_by_id: dict[str, TaskRow],
    browser_report: str,
    *,
    final_mode: bool,
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    row = task_by_id.get("WNID-P8-01")
    if row is None:
        issues.append(Issue(SPEC_PATH, "browser_matrix_task_missing", "WNID-P8-01 browser matrix task is missing"))
    else:
        acceptance = row.acceptance.lower()
        for marker in ("desktop/mobile", "browser matrix", "citations", "suggested questions"):
            if marker not in acceptance:
                issues.append(Issue(SPEC_PATH, "browser_matrix_contract_missing", f"WNID-P8-01 missing {marker}", row.line_number))
    if browser_report:
        return ("present" if not issues else "contract_error"), issues
    _ = final_mode
    return ("pending" if not issues else "contract_error"), issues


def _check_final_report(
    task_by_id: dict[str, TaskRow],
    final_report: str,
    *,
    final_mode: bool,
) -> tuple[str, list[Issue]]:
    issues: list[Issue] = []
    row = task_by_id.get("WNID-P8-02")
    if row is None:
        issues.append(Issue(SPEC_PATH, "final_report_task_missing", "WNID-P8-02 final report task is missing"))
    elif "current-run evidence" not in row.acceptance:
        issues.append(Issue(SPEC_PATH, "final_report_contract_missing", "WNID-P8-02 must require current-run evidence", row.line_number))
    if final_report:
        return ("present" if not issues else "contract_error"), issues
    _ = final_mode
    return ("pending" if not issues else "contract_error"), issues


def _open_tasks(task_rows: list[TaskRow]) -> list[TaskRow]:
    return [row for row in task_rows if row.status in {"[ ]", "[~]", "[!]"}]


def _check_final_mode(
    open_tasks: list[TaskRow],
    task_by_id: dict[str, TaskRow],
    final_report: str,
    browser_report: str,
) -> list[Issue]:
    issues: list[Issue] = []
    for row in open_tasks:
        issues.append(
            Issue(
                SPEC_PATH,
                "unfinished_task_blocks_final",
                f"{row.task_id} remains {row.status}; final WNID cannot pass while in-scope tasks are incomplete",
                row.line_number,
            )
        )
    for gate_name, task_id in HARD_GATE_TASK_IDS.items():
        row = task_by_id.get(task_id)
        if row is None or row.status != "[x]":
            issues.append(Issue(SPEC_PATH, f"{gate_name}_not_complete", f"{task_id} must be [x] in final mode"))
    if not final_report:
        issues.append(Issue(FINAL_REPORT_PATH, "final_report_missing", "final mode requires final WNID report"))
    if not browser_report:
        issues.append(Issue(BROWSER_MATRIX_PATH, "browser_matrix_report_missing", "final mode requires browser matrix report"))
    return issues


def _run_self_test() -> int:
    try:
        _self_test_safety_patterns()
        _self_test_contracts()
        _self_test_final_mode()
    except Exception as exc:  # noqa: BLE001
        print(f"WNID acceptance checker self-test failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1
    print("WNID acceptance checker self-test passed")
    print("- positive in-progress fixture reports final_ready=false")
    print("- negative fixtures reject Web Search/MCP removal and unsafe PASS wording")
    print("- final mode rejects incomplete WNID task board")
    return 0


def _self_test_safety_patterns() -> None:
    with TemporaryDirectory(prefix="wnid-acceptance-check-") as temp_dir:
        root = Path(temp_dir)
        good = root / "good.md"
        bad = root / "bad.md"
        bad_key = "sk-" + "fixturefixturefixture"
        sensitive_field = "api" + "_key"
        private_marker = "BEGIN " + "PRIVATE KEY"
        good.write_text(
            "Task: `WNID-0-03`\n"
            "Evidence type: checker execution.\n"
            "mock evidence is not PASS.\n"
            "fixture-only evidence is not PASS.\n",
            encoding="utf-8",
        )
        bad.write_text(
            "Task: `WNID-0-03`\n"
            "mock PASS accepted\n"
            f"{sensitive_field}: {bad_key}\n"
            f"{private_marker}\n",
            encoding="utf-8",
        )
        if _check_text_safety(good, good.read_text(encoding="utf-8")):
            raise AcceptanceError("positive safety fixture produced issues")
        bad_codes = {issue.code for issue in _check_text_safety(bad, bad.read_text(encoding="utf-8"))}
        expected = {"unsafe_mock_pass", "secret_openai_key", "secret_assignment", "private_key_block"}
        if not expected <= bad_codes:
            raise AcceptanceError(f"negative safety fixture missed issues: {sorted(bad_codes)}")


def _self_test_contracts() -> None:
    spec = _fixture_spec(all_done=False)
    parity_map = "\n".join(README_INTELLIGENT_CONVERSATION_ROWS)
    task_rows = _parse_task_rows(spec)
    task_by_id = {row.task_id: row for row in task_rows}
    capability_rows = _parse_capability_rows(spec)
    if _check_intelligent_conversation_rows(spec, parity_map):
        raise AcceptanceError("positive README row fixture produced issues")
    web_state, web_issues = _check_web_search_in_scope(spec, task_by_id, capability_rows)
    mcp_state, mcp_issues = _check_mcp_execution_in_scope(spec, task_by_id, capability_rows)
    if web_state != "in_scope" or web_issues:
        raise AcceptanceError("positive Web Search fixture produced issues")
    if mcp_state != "in_scope" or mcp_issues:
        raise AcceptanceError("positive MCP fixture produced issues")

    bad_spec = spec.replace(
        "| WNID-P4-01 | P4 | Web Search provider setup and test | [ ] | PA supports masked provider create/update/credential/test or records exact credential/provider blocker. |",
        "| WNID-P4-01 | P4 | Web Search provider setup and test | [b] | Removed from scope. |",
    )
    bad_rows = _parse_task_rows(bad_spec)
    bad_by_id = {row.task_id: row for row in bad_rows}
    bad_web_state, bad_web_issues = _check_web_search_in_scope(bad_spec, bad_by_id, capability_rows)
    if bad_web_state != "contract_error" or "web_search_removed" not in {issue.code for issue in bad_web_issues}:
        raise AcceptanceError("Web Search removal was not rejected")

    bad_mcp_spec = spec.replace(
        "| WNID-P3-02 | P3 | MCP approval-gated tool execution | [ ] | At least one safe MCP tool executes or is denied through native approval flow, with PA audit/history and no raw secret leakage. |",
        "| WNID-P3-02 | P3 | MCP approval-gated tool execution | [b] | Removed from scope. |",
    )
    bad_mcp_rows = _parse_task_rows(bad_mcp_spec)
    bad_mcp_by_id = {row.task_id: row for row in bad_mcp_rows}
    bad_mcp_state, bad_mcp_issues = _check_mcp_execution_in_scope(bad_mcp_spec, bad_mcp_by_id, capability_rows)
    if bad_mcp_state != "contract_error" or "mcp_execution_removed" not in {issue.code for issue in bad_mcp_issues}:
        raise AcceptanceError("MCP execution removal was not rejected")


def _self_test_final_mode() -> None:
    spec = _fixture_spec(all_done=False)
    rows = _parse_task_rows(spec)
    task_by_id = {row.task_id: row for row in rows}
    issues = _check_final_mode(_open_tasks(rows), task_by_id, final_report="", browser_report="")
    codes = {issue.code for issue in issues}
    expected = {
        "unfinished_task_blocks_final",
        "web_search_provider_not_complete",
        "mcp_execution_not_complete",
        "final_report_missing",
        "browser_matrix_report_missing",
    }
    if not expected <= codes:
        raise AcceptanceError(f"final-mode negative fixture missed issues: {sorted(codes)}")


def _fixture_spec(*, all_done: bool) -> str:
    status = "[x]" if all_done else "[ ]"
    return f"""# Fixture

Make Web Search a final PASS requirement for WNID.
Make MCP tool execution a final PASS requirement for WNID.
Web Search and MCP execution must not be removed unless the user explicitly changes WNID's goal.
Web Search PASS needs provider identity plus URL/title/snippet/rank.
MCP PASS needs service id/name, tool name, approval requirement, execution summary, audit id, and history visibility.
current-run evidence is required.

| Capability group | Baseline signal | WNID target | Hard evidence |
| --- | --- | --- | --- |
| Intelligent dialogue shell | Baseline | `complete` | Browser. |
| Quick Q&A | Baseline | `complete` | Live answer. |
| ReACT/custom Agent reasoning | Baseline | `complete` | AgentQA. |
| Wiki Mode | Baseline | `complete` | Wiki citations. |
| Built-in tool calling | Baseline | `complete` | Tool events. |
| MCP tool calling | Baseline | `complete` | Live safe MCP service lists tools/resources/prompts, executes at least one tool with approval/audit/history. |
| Web Search | Baseline | `complete` | Provider and references. |
| Conversation strategy | Baseline | `complete` | Strategy audit. |
| Suggested questions | Baseline | `complete` | Suggested questions. |
| History/citation/audit | Baseline | `complete` | Unified history. |

## 5. Execution Protocol

| Task id | Phase | Title | Status | Acceptance |
| --- | --- | --- | --- | --- |
| WNID-0-01 | Governance | Intelligent dialogue spec and skill | [x] | Spec exists. |
| WNID-0-02 | Governance | Native intelligent dialogue parity map | [x] | Audit/map. |
| WNID-0-03 | Governance | WNID acceptance harness | [x] | Checker enforces current-run evidence. |
| WNID-P1-01 | P1 | First-class intelligent dialogue shell | {status} | Browser shell. |
| WNID-P1-02 | P1 | Quick Q&A live path | {status} | RAG answer. |
| WNID-P2-01 | P2 | ReACT/custom Agent strategy editor | {status} | Strategy editor. |
| WNID-P2-02 | P2 | ReACT reasoning trace and run contract | {status} | Trace. |
| WNID-P3-01 | P3 | MCP tools/resources/prompts read path | {status} | MCP read. |
| WNID-P3-02 | P3 | MCP approval-gated tool execution | {status} | At least one safe MCP tool executes or is denied through native approval flow, with PA audit/history and no raw secret leakage. |
| WNID-P4-01 | P4 | Web Search provider setup and test | {status} | PA supports masked provider create/update/credential/test or records exact credential/provider blocker. |
| WNID-P4-02 | P4 | AgentQA Web Search run | {status} | Native AgentQA with `web_search_enabled=true` calls Web Search and returns traceable web references or exact native reference blocker. |
| WNID-P5-01 | P5 | Wiki Mode Agent workflow | {status} | Wiki citations. |
| WNID-P6-01 | P6 | Suggested questions workflow | {status} | Suggested questions. |
| WNID-P7-01 | P7 | Dialogue history, citation, and audit unification | {status} | History/audit. |
| WNID-P8-01 | P8 | Intelligent dialogue browser matrix | {status} | Desktop/mobile browser matrix proves dialogue shell, strategy editor, tool trace, MCP/Web Search status, citations, and suggested questions. |
| WNID-P8-02 | P8 | Final WNID PASS report | {status} | Final report and acceptance harness prove every in-scope README Intelligent Conversation row is complete with current-run evidence. |

| Date | Task | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 2026-06-25 | WNID-0-01 | [x] | Governance artifact. | Done. |
| 2026-06-25 | WNID-0-02 | [x] | Audit/map. | Done. |
| 2026-06-25 | WNID-0-03 | [x] | Checker execution evidence. | Done. |
"""


def _empty_summary(mode: str) -> CheckSummary:
    return CheckSummary(
        task_rows=0,
        completed_tasks=0,
        open_tasks=0,
        progress_log_entries=0,
        web_search="missing",
        mcp_execution="missing",
        current_run_evidence="missing",
        browser_matrix="missing",
        final_report="missing",
        final_ready=False,
        mode=mode,
    )


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        text = text.replace(marker, "[redacted]")
    return text[:260]


if __name__ == "__main__":
    raise SystemExit(main())
