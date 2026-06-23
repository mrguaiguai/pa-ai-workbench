"""Stage checker for WeKnora Native Expansion acceptance claims.

This checker guards WNX internal-production reports. It verifies report safety,
evidence labels, coverage math, browser-validation hooks, and spec/progress
sanity. With ``--start-pa-api`` or ``--live-api-url`` it also validates the live
masked native status center without printing raw payloads.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from typing import Any
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"

SPEC_PATH = DOCS_ROOT / "WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md"
LEDGER_PATH = DOCS_ROOT / "WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md"

REQUIRED_REPORTS = {
    "WNX-0-02": DOCS_ROOT / "WEKNORA_NATIVE_EXPANSION_ARCHITECTURE.md",
    "WNX-0-03": LEDGER_PATH,
    "WNX-P0-01": DOCS_ROOT / "WEKNORA_NATIVE_CLIENT_REPORT.md",
    "WNX-P0-02": DOCS_ROOT / "WEKNORA_NATIVE_STATUS_CENTER_REPORT.md",
    "WNX-P0-03": DOCS_ROOT / "WEKNORA_NATIVE_CAPABILITY_CENTER_BROWSER_REPORT.md",
    "WNX-P0-04": DOCS_ROOT / "WEKNORA_NATIVE_EXPANSION_ACCEPTANCE_HARNESS_REPORT.md",
    "WNX-P0-05": DOCS_ROOT / "WEKNORA_NATIVE_DEPLOYMENT_READINESS_REPORT.md",
    "WNX-P1-01": DOCS_ROOT / "WEKNORA_NATIVE_KB_MANAGEMENT_LIVE_REPORT.md",
    "WNX-P1-02": DOCS_ROOT / "WEKNORA_NATIVE_DOCUMENT_LIFECYCLE_LIVE_REPORT.md",
    "WNX-P1-03": DOCS_ROOT / "WEKNORA_NATIVE_CHUNK_MANAGEMENT_LIVE_REPORT.md",
    "WNX-P1-04": DOCS_ROOT / "WEKNORA_NATIVE_RAG_KNOWLEDGE_CHAT_LIVE_REPORT.md",
    "WNX-P1-05": DOCS_ROOT / "WEKNORA_NATIVE_AGENTQA_CUSTOM_AGENT_LIVE_REPORT.md",
    "WNX-P1-06": DOCS_ROOT / "WEKNORA_NATIVE_WIKI_WORKFLOW_LIVE_REPORT.md",
    "WNX-P1-07": DOCS_ROOT / "WEKNORA_NATIVE_HISTORY_CITATION_UNIFICATION_LIVE_REPORT.md",
    "WNX-P2-01": DOCS_ROOT / "WEKNORA_NATIVE_MODEL_CONFIG_LIVE_REPORT.md",
    "WNX-P2-02": DOCS_ROOT / "WEKNORA_NATIVE_MCP_MANAGEMENT_LIVE_REPORT.md",
    "WNX-P2-03": DOCS_ROOT / "WEKNORA_NATIVE_WEB_SEARCH_MANAGEMENT_LIVE_REPORT.md",
}

COMPLETED_PREREQUISITE_TASKS = (
    "WNX-0-01",
    "WNX-0-02",
    "WNX-0-03",
    "WNX-P0-01",
    "WNX-P0-02",
    "WNX-P0-03",
    "WNX-P0-04",
    "WNX-P0-05",
    "WNX-P1-01",
    "WNX-P1-02",
    "WNX-P1-03",
    "WNX-P1-04",
    "WNX-P1-05",
    "WNX-P1-06",
    "WNX-P1-07",
    "WNX-P2-01",
    "WNX-P2-02",
    "WNX-P2-03",
)

EVIDENCE_LABELS = (
    "live evidence",
    "live API evidence",
    "live browser evidence",
    "live API/browser evidence",
    "live service/status evidence",
    "fixture evidence",
    "audit/map",
    "checker execution evidence",
    "blocked evidence",
    "backlog evidence",
    "mock evidence",
    "cached evidence",
    "partial evidence",
)

SECRET_PATTERNS = {
    "secret_bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    "secret_openai_key": re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{14,}\b"),
    "secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|service[_-]?token|password|secret|private[_-]?key|authorization)"
        r"\s*[:=]\s*(?!\[?redacted\]?|omitted|configured\b|true\b|false\b)"
        r"[^\s`|,;]{8,}"
    ),
    "private_key_block": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
}

UNSAFE_PASS_PATTERNS = {
    "unsafe_fixture_only_pass": re.compile(r"(?i)(?<!not )fixture-only\s+PASS\s+(?:allowed|counts|accepted)"),
    "unsafe_mock_pass": re.compile(r"(?i)(?<!not )mock\s+PASS\s+(?:allowed|counts|accepted)"),
    "unsafe_cached_pass": re.compile(r"(?i)(?<!not )(?:cached|old report)\s+PASS\s+(?:allowed|counts|accepted)"),
    "unsafe_static_ui_pass": re.compile(r"(?i)(?<!not )static\s+UI\s+PASS\s+(?:allowed|counts|accepted)"),
}

EXPECTED_STATUS_GROUPS = {
    "system_health_status_deployment",
    "workspace_knowledge_base",
    "document_lifecycle",
    "chunk_management",
    "knowledge_search_rag",
    "knowledge_chat_session_chat",
    "agentqa_custom_agent",
    "native_wiki",
    "mcp",
    "web_search",
    "vector_store",
    "model_embedding_rerank_parser",
    "data_sources_connectors",
    "faq_tags_favorites_skills",
    "history_citation_product_shell",
}


@dataclass(frozen=True)
class Issue:
    path: Path | None
    code: str
    message: str
    line_number: int = 0


@dataclass(frozen=True)
class CheckSummary:
    reports_checked: int
    completed_tasks: int
    current_score: float
    current_percent: float
    target_score: float
    target_percent: float
    in_progress: bool
    browser_hooks: str
    live_status: str


class AcceptanceError(RuntimeError):
    """Raised when the acceptance checker cannot prove the guardrail contract."""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()

    issues: list[Issue] = []
    summary: CheckSummary | None = None
    try:
        summary, issues = _run_static_checks()
        live_status = "not requested"
        if args.start_pa_api:
            live_status = _check_started_pa_api()
        elif args.live_api_url:
            live_status = _check_live_status_center(args.live_api_url.rstrip("/"))
        summary = CheckSummary(
            reports_checked=summary.reports_checked,
            completed_tasks=summary.completed_tasks,
            current_score=summary.current_score,
            current_percent=summary.current_percent,
            target_score=summary.target_score,
            target_percent=summary.target_percent,
            in_progress=summary.in_progress,
            browser_hooks=summary.browser_hooks,
            live_status=live_status,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native expansion acceptance check failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    if issues:
        print("WeKnora native expansion acceptance check failed")
        for issue in issues:
            path = str(issue.path.relative_to(PROJECT_ROOT)) if issue.path else "-"
            line = f":{issue.line_number}" if issue.line_number else ""
            print(f"- {path}{line}: {issue.code}: {issue.message}")
        return 1

    print("WeKnora native expansion acceptance check passed")
    print(f"- reports checked: {summary.reports_checked}")
    print(f"- completed prerequisite tasks: {summary.completed_tasks}")
    print(
        "- coverage current: "
        f"{summary.current_score:.2f}/15 = {summary.current_percent:.1f}%"
    )
    print(
        "- coverage target: "
        f"{summary.target_score:.2f}/15 = {summary.target_percent:.1f}%"
    )
    print(f"- stage in progress: {summary.in_progress}")
    print(f"- browser hooks: {summary.browser_hooks}")
    print(f"- live status center: {summary.live_status}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check WNX stage reports, coverage math, and optional live status center.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run positive and negative fixture checks for the WNX checker itself",
    )
    parser.add_argument(
        "--live-api-url",
        help="existing PA API base URL to validate, for example http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--start-pa-api",
        action="store_true",
        help="start a temporary PA backend and validate /api/native/status",
    )
    return parser.parse_args(argv)


def _run_static_checks() -> tuple[CheckSummary, list[Issue]]:
    issues: list[Issue] = []
    spec = _read_text(SPEC_PATH, issues)
    ledger = _read_text(LEDGER_PATH, issues)
    if not spec or not ledger:
        return _empty_summary(), issues

    reports_checked = 0
    for task_id, path in REQUIRED_REPORTS.items():
        text = _read_text(path, issues)
        if not text:
            continue
        reports_checked += 1
        issues.extend(_check_text_safety(path, text))
        issues.extend(_check_report_evidence(task_id, path, text))

    task_statuses = _parse_task_statuses(spec)
    progress_tasks = _parse_progress_tasks(spec)
    for task_id in COMPLETED_PREREQUISITE_TASKS:
        if task_statuses.get(task_id) != "[x]":
            issues.append(Issue(SPEC_PATH, "task_not_completed", f"{task_id} is not [x]"))
        if task_id not in progress_tasks:
            issues.append(Issue(SPEC_PATH, "missing_progress_log", f"{task_id} has no progress log row"))

    if task_statuses.get("WNX-P0-04") == "[x]" and "WNX-P0-04" not in progress_tasks:
        issues.append(Issue(SPEC_PATH, "missing_progress_log", "WNX-P0-04 is [x] without a progress log row"))

    coverage = _parse_coverage(ledger)
    if coverage["group_count"] != 15:
        issues.append(Issue(LEDGER_PATH, "coverage_group_count", "coverage ledger must list 15 groups"))
    if coverage["target_percent"] < 80:
        issues.append(Issue(LEDGER_PATH, "coverage_target_low", "target coverage is below 80%"))

    unfinished = [task for task, status in task_statuses.items() if status == "[ ]"]
    in_progress = bool(unfinished)
    if coverage["current_percent"] < 80 and not in_progress:
        issues.append(
            Issue(
                LEDGER_PATH,
                "coverage_below_target",
                "coverage is below target and the spec is not explicitly in progress",
            )
        )

    browser_hooks = _check_browser_hooks(DOCS_ROOT / "WEKNORA_NATIVE_CAPABILITY_CENTER_BROWSER_REPORT.md", issues)
    issues.extend(_run_phase5_report_checker_self_test())

    return (
        CheckSummary(
            reports_checked=reports_checked,
            completed_tasks=len(COMPLETED_PREREQUISITE_TASKS),
            current_score=coverage["current_score"],
            current_percent=coverage["current_percent"],
            target_score=coverage["target_score"],
            target_percent=coverage["target_percent"],
            in_progress=in_progress,
            browser_hooks=browser_hooks,
            live_status="not requested",
        ),
        issues,
    )


def _read_text(path: Path, issues: list[Issue]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(Issue(path, "missing_file", "required stage file is missing"))
        return ""


def _check_text_safety(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for code, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                issues.append(Issue(path, code, "secret-shaped value is present", line_number))
        for code, pattern in UNSAFE_PASS_PATTERNS.items():
            if pattern.search(line):
                issues.append(Issue(path, code, "unsafe evidence appears to count as PASS", line_number))
    return issues


def _check_report_evidence(task_id: str, path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    lower = text.lower()
    if task_id not in text:
        issues.append(Issue(path, "missing_task_id", f"report does not mention {task_id}"))
    if "pass" in lower and not any(label.lower() in lower for label in EVIDENCE_LABELS):
        issues.append(Issue(path, "missing_evidence_class", "PASS report lacks evidence classification"))
    if task_id == "WNX-P0-03":
        for required in ("Desktop", "Mobile", "live browser evidence backed by live API response"):
            if required not in text:
                issues.append(Issue(path, "missing_browser_evidence", f"missing browser evidence marker {required}"))
    if task_id == "WNX-P0-04":
        for required in (
            "checker execution evidence",
            "negative fixture",
            "coverage current",
            "live status center",
        ):
            if required not in lower:
                issues.append(Issue(path, "missing_harness_marker", f"missing harness marker {required}"))
    return issues


def _parse_task_statuses(spec: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for line in spec.splitlines():
        match = re.match(r"\|\s*(WNX-[0-9A-Z-]+)\s*\|.*?\|\s*(\[[x~! b]\])\s*\|", line)
        if match:
            statuses[match.group(1)] = match.group(2)
    return statuses


def _parse_progress_tasks(spec: str) -> set[str]:
    tasks: set[str] = set()
    for line in spec.splitlines():
        match = re.match(r"\|\s*20\d\d-\d\d-\d\d\s*\|\s*(WNX-[0-9A-Z-]+)\s*\|", line)
        if match:
            tasks.add(match.group(1))
    return tasks


def _parse_coverage(ledger: str) -> dict[str, float | int]:
    group_count = 0
    in_table = False
    for line in ledger.splitlines():
        if line.startswith("| Capability group |"):
            in_table = True
            continue
        if in_table and line.startswith("## Target Coverage Plan"):
            break
        if in_table and line.startswith("| ") and not line.startswith("| ---"):
            group_count += 1

    current_match = re.search(
        r"Current (?:baseline )?score:\s*```text\s*([0-9.]+)\s*/\s*15\s*=\s*([0-9.]+)%",
        ledger,
        re.S,
    )
    target_match = re.search(
        r"Minimum internal production target:\s*```text\s*([0-9.]+)\s*/\s*15\s*=\s*([0-9.]+)%",
        ledger,
        re.S,
    )
    if not current_match or not target_match:
        raise AcceptanceError("coverage ledger score blocks cannot be parsed")
    return {
        "group_count": group_count,
        "current_score": float(current_match.group(1)),
        "current_percent": float(current_match.group(2)),
        "target_score": float(target_match.group(1)),
        "target_percent": float(target_match.group(2)),
    }


def _check_browser_hooks(path: Path, issues: list[Issue]) -> str:
    text = _read_text(path, issues)
    if not text:
        return "missing"
    required = (
        "Desktop `1440x900`",
        "Mobile `390x844`",
        "Chrome/Playwright DOM validation",
        "no horizontal overflow",
        "No mock data",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        issues.append(Issue(path, "missing_browser_hook", "missing browser hook markers: " + ", ".join(missing)))
        return "incomplete"
    return "desktop/mobile capability center report present"


def _run_phase5_report_checker_self_test() -> list[Issue]:
    result = subprocess.run(
        [
            sys.executable,
            str(BACKEND_ROOT / "scripts" / "check_phase5_report_safety.py"),
            "--self-test",
        ],
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return []
    return [
        Issue(
            BACKEND_ROOT / "scripts" / "check_phase5_report_safety.py",
            "phase5_checker_self_test_failed",
            _safe_reason(RuntimeError(result.stderr or result.stdout)),
        )
    ]


def _check_started_pa_api() -> str:
    port = _free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(BACKEND_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_pa_api(port, server)
        return _check_live_status_center(f"http://127.0.0.1:{port}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


def _check_live_status_center(base_url: str) -> str:
    data = _get_json(f"{base_url}/api/native/status?limit=5")
    if data.get("schema_version") != "wnx-p0-02":
        raise AcceptanceError("live status center schema_version is not wnx-p0-02")
    if data.get("source") != "pa_backend_bff":
        raise AcceptanceError("live status center source is not pa_backend_bff")
    if data.get("evidence_type") != "live_api":
        raise AcceptanceError("live status center evidence_type is not live_api")
    if data.get("masked") is not True:
        raise AcceptanceError("live status center response is not masked")
    groups = data.get("groups")
    if not isinstance(groups, dict):
        raise AcceptanceError("live status center groups is not an object")
    missing = sorted(EXPECTED_STATUS_GROUPS - set(groups))
    if missing:
        raise AcceptanceError("live status center missing groups: " + ",".join(missing))
    if int(data.get("group_count") or 0) != 15:
        raise AcceptanceError("live status center group_count is not 15")
    forbidden = _forbidden_json_paths(data)
    if forbidden:
        raise AcceptanceError("live status center leaked forbidden fields: " + ",".join(forbidden[:5]))
    counts: dict[str, int] = {}
    for group in groups.values():
        if not isinstance(group, dict):
            raise AcceptanceError("live status center contains a non-object group")
        status = str(group.get("status") or "unknown")
        if status not in {"live", "partial", "blocked", "backlog"}:
            raise AcceptanceError(f"live status center contains unsupported status {status}")
        counts[status] = counts.get(status, 0) + 1
    return (
        "live_api "
        f"groups=15 live={counts.get('live', 0)} partial={counts.get('partial', 0)} "
        f"blocked={counts.get('blocked', 0)} backlog={counts.get('backlog', 0)}"
    )


def _get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=45) as response:
        if response.status != 200:
            raise AcceptanceError(f"{url} returned HTTP {response.status}")
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise AcceptanceError(f"{url} returned non-object JSON")
    return parsed


def _forbidden_json_paths(value: object, prefix: str = "$") -> list[str]:
    forbidden_names = {
        "api_key",
        "token",
        "password",
        "secret",
        "headers",
        "auth_config",
        "base_url",
        "url",
        "connection_config",
        "provider_payload",
        "raw",
        "records",
        "vectors",
        "chunks",
        "logs",
        "database_url",
    }
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if key in forbidden_names:
                paths.append(path)
            paths.extend(_forbidden_json_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_json_paths(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        if re.search(r"https?://|sk-[A-Za-z0-9]|Bearer\s+|BEGIN .*PRIVATE KEY", value):
            paths.append(prefix)
    return paths


def _wait_for_pa_api(port: int, server: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 30
    last_error = ""
    while time.monotonic() < deadline:
        if server.poll() is not None:
            stderr = server.stderr.read() if server.stderr else ""
            raise AcceptanceError("temporary PA API exited early: " + _safe_reason(RuntimeError(stderr)))
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = _safe_reason(exc)
        time.sleep(0.25)
    raise AcceptanceError("temporary PA API did not become healthy: " + last_error)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_self_test() -> int:
    try:
        _self_test_safety_patterns()
        _self_test_coverage_parser()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora native expansion acceptance checker self-test failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1
    print("WeKnora native expansion acceptance checker self-test passed")
    print("- positive coverage fixture accepted")
    print("- negative fixture rejected unsafe PASS evidence and secret-shaped values")
    return 0


def _self_test_safety_patterns() -> None:
    with TemporaryDirectory(prefix="wnx-acceptance-check-") as temp_dir:
        root = Path(temp_dir)
        good = root / "good.md"
        bad = root / "bad.md"
        fake_key = "sk-" + "fixturefixturefixture"
        good.write_text(
            "Task: `WNX-P0-04`\n"
            "Evidence type: checker execution evidence.\n"
            "fixture-only evidence is not PASS.\n"
            "mock evidence is not PASS.\n",
            encoding="utf-8",
        )
        bad.write_text(
            "Task: `WNX-P0-04`\n"
            "Evidence type: fixture-only\n"
            "fixture-only PASS allowed\n"
            f"api_key: {fake_key}\n",
            encoding="utf-8",
        )
        if _check_text_safety(good, good.read_text(encoding="utf-8")):
            raise AcceptanceError("positive fixture produced safety issues")
        bad_codes = {
            issue.code
            for issue in _check_text_safety(bad, bad.read_text(encoding="utf-8"))
        }
        expected = {"unsafe_fixture_only_pass", "secret_openai_key", "secret_assignment"}
        if not expected <= bad_codes:
            raise AcceptanceError(f"negative fixture missed issues: {sorted(bad_codes)}")


def _self_test_coverage_parser() -> None:
    ledger = """# Ledger

Current baseline score:

```text
5.50 / 15 = 36.7%
```

Minimum internal production target:

```text
12.00 / 15 = 80.0%
```

## Current Coverage Ledger

| Capability group | Current state | Score |
| --- | --- | ---: |
"""
    rows = "".join(f"| Group {index} | `read-only` | 0.25 |\n" for index in range(15))
    parsed = _parse_coverage(ledger + rows + "\n## Target Coverage Plan\n")
    if parsed["group_count"] != 15:
        raise AcceptanceError("coverage parser did not count 15 groups")
    if parsed["target_percent"] != 80.0:
        raise AcceptanceError("coverage parser did not parse target percent")


def _empty_summary() -> CheckSummary:
    return CheckSummary(
        reports_checked=0,
        completed_tasks=0,
        current_score=0,
        current_percent=0,
        target_score=0,
        target_percent=0,
        in_progress=True,
        browser_hooks="missing",
        live_status="not requested",
    )


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    for marker in ("Authorization", "Bearer", "api_key", "service_token", "password", "token"):
        text = text.replace(marker, "[redacted]")
    return text[:260]


if __name__ == "__main__":
    raise SystemExit(main())
