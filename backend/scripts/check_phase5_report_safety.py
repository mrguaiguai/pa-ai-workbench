"""Check Phase 5 real reports for safety and evidence-field completeness.

The checker is intentionally static. It does not call PA, WeKnora, model
providers, databases, or logs. By default it scans committed Phase 5 real report
files under `docs/PHASE5_REAL_*.md`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_GLOB = "PHASE5_REAL_*.md"
LOCALHOST_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class Issue:
    path: Path
    line_number: int
    code: str
    message: str
    excerpt: str


@dataclass(frozen=True)
class SensitivePattern:
    code: str
    message: str
    regex: re.Pattern[str]


SENSITIVE_PATTERNS = [
    SensitivePattern(
        code="secret_bearer",
        message="Bearer token-like value is present",
        regex=re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    ),
    SensitivePattern(
        code="secret_openai_key",
        message="OpenAI-style API key is present",
        regex=re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{14,}\b"),
    ),
    SensitivePattern(
        code="secret_assignment",
        message="secret-like assignment is present",
        regex=re.compile(
            r"(?i)\b(?:api[_-]?key|service[_-]?token|secret|password|authorization)"
            r"\s*[:=]\s*(?!\[?redacted\]?|omitted|intentionally omitted|configured\b)"
            r"[^\s`|,;]{8,}"
        ),
    ),
    SensitivePattern(
        code="private_ipv4",
        message="RFC1918 private IPv4 address is present",
        regex=re.compile(
            r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
    SensitivePattern(
        code="runtime_upload_path",
        message="runtime uploads path is present",
        regex=re.compile(r"(?i)(?:^|[\s`|])(?:/[\w .-]+/)?(?:backend/)?uploads(?:/|[\s`|]|$)"),
    ),
    SensitivePattern(
        code="runtime_db_path",
        message="runtime database path or database file is present",
        regex=re.compile(
            r"(?i)(?:^|[\s`|])(?:/[\w .-]+/)?backend/data(?:/|[\s`|]|$)|"
            r"\bpa_workbench\.db\b|\.(?:sqlite|sqlite3|db)\b"
        ),
    ),
    SensitivePattern(
        code="runtime_log_path",
        message="runtime log path or log file is present",
        regex=re.compile(r"(?i)(?:^|[\s`|])(?:/[\w .-]+/)?(?:backend/)?logs(?:/|[\s`|]|$)|\b[\w.-]+\.log\b"),
    ),
    SensitivePattern(
        code="dotenv_path",
        message=".env path or file reference is present",
        regex=re.compile(r"(?i)(?:^|[\s`|])\.env(?:[\s`|]|$)|/\.env\b"),
    ),
    SensitivePattern(
        code="raw_log_block",
        message="raw log or traceback line is present",
        regex=re.compile(r"^(?:Traceback \(most recent call last\)|\d{4}-\d{2}-\d{2} .* (?:ERROR|INFO|WARN)\b)"),
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()
    report_paths = _resolve_report_paths(args.paths)
    if not report_paths:
        print("Phase 5 report safety check failed: no report files found", file=sys.stderr)
        return 1

    issues: list[Issue] = []
    for path in report_paths:
        issues.extend(_check_report(path))

    if issues:
        print("Phase 5 report safety check failed")
        for issue in issues:
            location = f"{issue.path}:{issue.line_number}" if issue.line_number else str(issue.path)
            print(f"- {location}: {issue.code}: {issue.message}: {issue.excerpt}")
        return 1

    print("Phase 5 report safety check passed")
    print(f"- reports checked: {len(report_paths)}")
    for path in report_paths:
        print(f"- {path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan Phase 5 real reports for sensitive data risks and required "
            "evidence fields."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="specific report file(s) to scan; defaults to docs/PHASE5_REAL_*.md",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run fixture-generated positive and negative checker samples",
    )
    return parser.parse_args(argv)


def _resolve_report_paths(paths: list[Path]) -> list[Path]:
    if paths:
        return sorted(path.resolve() for path in paths)
    return sorted((PROJECT_ROOT / "docs").glob(DEFAULT_REPORT_GLOB))


def _check_report(path: Path) -> list[Issue]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [
            Issue(
                path=path,
                line_number=0,
                code="missing_file",
                message="report file does not exist",
                excerpt="-",
            )
        ]
    issues: list[Issue] = []
    issues.extend(_check_sensitive_patterns(path, text))
    issues.extend(_check_evidence_fields(path, text))
    return issues


def _check_sensitive_patterns(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _line_is_allowed_local_test_context(line):
            continue
        for pattern in SENSITIVE_PATTERNS:
            if pattern.regex.search(line):
                issues.append(
                    Issue(
                        path=path,
                        line_number=line_number,
                        code=pattern.code,
                        message=pattern.message,
                        excerpt=_excerpt(line),
                    )
                )
    issues.extend(_check_external_urls(path, text))
    return issues


def _check_external_urls(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    url_pattern = re.compile(r"https?://([A-Za-z0-9.\-:\[\]]+)(/[^\s`|)]*)?")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in url_pattern.finditer(line):
            host_port = match.group(1).strip("[]")
            host = host_port.split(":", 1)[0].lower()
            if host in LOCALHOST_HOSTS:
                continue
            if host.endswith(".example") or host.endswith(".example.com"):
                continue
            issues.append(
                Issue(
                    path=path,
                    line_number=line_number,
                    code="external_url",
                    message="external or private service URL is present",
                    excerpt=_excerpt(line),
                )
            )
    return issues


def _line_is_allowed_local_test_context(line: str) -> bool:
    return (
        "127.0.0.1" in line
        or "localhost" in line
        or "/private/tmp/" in line
        or "local temporary directory" in line
    )


def _check_evidence_fields(path: Path, text: str) -> list[Issue]:
    lower_name = path.name.lower()
    if not _is_pass_report(text):
        return []
    issues: list[Issue] = []
    if "PHASE5_REAL" not in text:
        issues.append(_field_issue(path, "missing_marker", "PHASE5_REAL"))
    if _has_nonzero_fail_count(text):
        issues.append(_field_issue(path, "nonzero_fail_count", "FAIL count must be zero"))

    required = _required_fields_for_report(lower_name, text)
    for field in required:
        if field == "source":
            if "weknora_api" not in text:
                issues.append(_field_issue(path, "missing_source", "weknora_api"))
            continue
        if field not in text:
            issues.append(_field_issue(path, f"missing_{field}", field))
    return issues


def _is_pass_report(text: str) -> bool:
    return bool(re.search(r"\|\s*Result\s*\|\s*PASS\s*\|", text)) or " PASS Report" in text


def _has_nonzero_fail_count(text: str) -> bool:
    for match in re.finditer(r"\|\s*FAIL\s*\|\s*(\d+)\s*\|", text):
        if int(match.group(1)) != 0:
            return True
    return False


def _required_fields_for_report(lower_name: str, text: str) -> list[str]:
    del text
    if "frontend" in lower_name or "env" in lower_name:
        return []
    if "rag_24q" in lower_name or "knowledge_qa" in lower_name:
        return ["source", "source_type", "evidence_id", "chunk_id", "wiki_page_id", "trace_id"]
    if "wiki" in lower_name:
        return ["source", "source_type", "evidence_id", "wiki_page_id", "trace_id"]
    if "upload_index" in lower_name:
        return ["source", "source_type", "evidence_id", "chunk_id"]
    return []


def _field_issue(path: Path, code: str, field: str) -> Issue:
    return Issue(
        path=path,
        line_number=0,
        code=code,
        message=f"PASS report is missing required evidence field `{field}`",
        excerpt="-",
    )


def _run_self_test() -> int:
    with TemporaryDirectory(prefix="phase5-report-check-") as temp_dir:
        root = Path(temp_dir)
        good = root / "PHASE5_REAL_RAG_24Q_PASS_REPORT.md"
        good.write_text(_good_fixture_report(), encoding="utf-8")
        bad = root / "PHASE5_REAL_RAG_24Q_BAD_REPORT.md"
        bad.write_text(_bad_fixture_report(), encoding="utf-8")
        local_frontend = root / "PHASE5_REAL_FRONTEND_PASS_REPORT.md"
        local_frontend.write_text(_local_frontend_fixture_report(), encoding="utf-8")

        good_issues = _check_report(good)
        frontend_issues = _check_report(local_frontend)
        bad_issues = _check_report(bad)
        if good_issues or frontend_issues:
            print("Phase 5 report safety self-test failed: positive fixture rejected")
            for issue in [*good_issues, *frontend_issues]:
                print(f"- {issue.code}: {issue.message}: {issue.excerpt}")
            return 1
        required_codes = {issue.code for issue in bad_issues}
        expected_codes = {"secret_openai_key", "private_ipv4", "missing_source", "missing_source_type"}
        if not expected_codes <= required_codes:
            print("Phase 5 report safety self-test failed: negative fixture missed issues")
            print(f"- expected subset: {sorted(expected_codes)}")
            print(f"- actual: {sorted(required_codes)}")
            return 1
    print("Phase 5 report safety self-test passed")
    return 0


def _good_fixture_report() -> str:
    return """# Phase 5 Real RAG 24Q PASS Report

| Field | Value |
| --- | --- |
| Report marker | PHASE5_REAL |
| Result | PASS |

| Status | Count |
| --- | ---: |
| PASS | 24 |
| FAIL | 0 |

| Question | source | source_type | evidence_id | chunk_id | wiki_page_id | trace_id | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P4Q-001 | weknora_api | document_chunk | document_chunk:fixture | chunk-fixture | - | PHASE5_REAL-P5-F3-fixture-P4Q-001 | PASS |
| P4Q-017 | weknora_api | wiki_page | wiki_page:fixture | - | wiki-fixture | PHASE5_REAL-P5-F3-fixture-P4Q-017 | PASS |
"""


def _bad_fixture_report() -> str:
    return """# Phase 5 Real RAG 24Q PASS Report

| Field | Value |
| --- | --- |
| Report marker | PHASE5_REAL |
| Result | PASS |
| Debug URL | http://192.168.1.20:8080 |
| API key | sk-fixturefixturefixture |

| Status | Count |
| --- | ---: |
| PASS | 1 |
| FAIL | 0 |
"""


def _local_frontend_fixture_report() -> str:
    return """# Phase 5 Real Frontend PASS Report

| Field | Value |
| --- | --- |
| Report id | PHASE5_REAL_FRONTEND_PASS_REPORT |
| Environment | Local PA backend on `127.0.0.1:8000`; Vite frontend on `127.0.0.1:5173` |
| Result | PASS |

Screenshots were captured in `/private/tmp/p5-e4-frontend-screens/home.png`.
"""


def _excerpt(line: str) -> str:
    return line.strip()[:160] or "-"


if __name__ == "__main__":
    raise SystemExit(main())
