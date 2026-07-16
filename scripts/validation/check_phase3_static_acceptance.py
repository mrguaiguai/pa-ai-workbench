"""Phase 3 static acceptance checker.

This is a repository-level closure gate. It verifies that PHASE3_SPEC task rows
are complete, the final runbook/checker artifacts exist, and sanitized static
or fixture gates pass. It does not claim live WeKnora/model acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = PROJECT_ROOT / "docs" / "archive" / "legacy-product" / "PHASE3_SPEC.md"
DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_STATIC_ACCEPTANCE.md"

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

STATIC_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    (
        "M2 intranet runbook",
        [sys.executable, "scripts/validation/smoke_intranet_runbook_m2.py"],
    ),
    (
        "M2 pilot feedback docs",
        [sys.executable, "scripts/validation/smoke_pilot_feedback_docs_m2.py"],
    ),
    (
        "M3 local product static gates",
        [sys.executable, "scripts/validation/check_m3_local_product.py"],
    ),
)

REQUIRED_ARTIFACTS = (
    "scripts/validation/check_m1_release.py",
    "scripts/validation/check_m2_release.py",
    "scripts/validation/check_m3_local_product.py",
    "scripts/validation/check_phase3_static_acceptance.py",
    "scripts/validation/smoke_retrieval_quality_golden_m3.py",
    "scripts/validation/smoke_rag_quality_evaluation_m3.py",
    "scripts/validation/smoke_agent_faithfulness_m3.py",
    "docs/archive/phase3/PHASE3_M1_RELEASE_CHECKLIST.md",
    "docs/archive/phase3/PHASE3_M2_RELEASE_CHECKLIST.md",
    "docs/archive/phase3/PHASE3_M3_LOCAL_PRODUCT_RUNBOOK.md",
    "docs/archive/phase3/PHASE3_STATIC_ACCEPTANCE.md",
)

M3_ACCEPTANCE_TERMS = (
    "capability matrix",
    "fail-closed",
    "backend contract tests",
    "extracted fallback",
    "backend switch",
    "retrieval quality golden set",
    "faithfulness",
    "local product runbook",
    "chat / embedding / weknora / capability readiness",
    "check_m3_local_product.py",
    "hybrid/rerank",
)

SENSITIVE_PATH_PARTS = (
    ".env",
    "backend/data/",
    "backend/uploads/",
    "uploads/",
    "data/",
    "logs/",
    "node_modules/",
    "dist/",
)
SENSITIVE_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".log")


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str
    blocking: bool = True


def main() -> int:
    gates = run_gates()
    blocking_failures = [gate for gate in gates if gate.blocking and gate.status == FAIL]
    decision = "STATIC READY" if not blocking_failures else "NOT READY"

    print("Phase 3 static acceptance")
    print(f"- decision: {decision}")
    for gate in gates:
        blocking = "blocking" if gate.blocking else "info"
        print(f"- {gate.name}: {gate.status} ({blocking}) - {gate.detail}")
    return 0 if not blocking_failures else 1


def run_gates() -> list[Gate]:
    gates: list[Gate] = [
        _check_task_rows_complete(),
        _check_required_artifacts(),
        _check_m3_acceptance_coverage(),
        _check_doc(),
        _check_git_safety(),
    ]
    gates.extend(
        _run_command(name, command, timeout_seconds=420)
        for name, command in STATIC_COMMANDS
    )
    gates.append(
        Gate(
            "live acceptance reminder",
            INFO,
            "live WeKnora/model gates still require check_m3_local_product.py --run-live-smokes",
            blocking=False,
        )
    )
    return gates


def _check_task_rows_complete() -> Gate:
    text = SPEC_PATH.read_text(encoding="utf-8")
    rows = re.findall(r"\| (P3-[^|]+) \| ([^|]+) \| \[([ x~])\] \|", text)
    if not rows:
        return Gate("PHASE3 task table", FAIL, "no task rows found")
    incomplete = [f"{task_id} {name.strip()} [{status}]" for task_id, name, status in rows if status != "x"]
    if incomplete:
        return Gate("PHASE3 task table", FAIL, "incomplete rows: " + "; ".join(incomplete))
    return Gate("PHASE3 task table", PASS, f"{len(rows)} task rows complete")


def _check_required_artifacts() -> Gate:
    missing = [path for path in REQUIRED_ARTIFACTS if not (PROJECT_ROOT / path).is_file()]
    if missing:
        return Gate("required acceptance artifacts", FAIL, "missing " + ", ".join(missing))
    return Gate("required acceptance artifacts", PASS, f"{len(REQUIRED_ARTIFACTS)} artifacts present")


def _check_m3_acceptance_coverage() -> Gate:
    text = SPEC_PATH.read_text(encoding="utf-8")
    runbook = (PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_LOCAL_PRODUCT_RUNBOOK.md").read_text(encoding="utf-8")
    combined = f"{text}\n{runbook}".lower()
    missing = [term for term in M3_ACCEPTANCE_TERMS if term not in combined]
    if missing:
        return Gate("M3 minimum acceptance coverage", FAIL, "missing " + ", ".join(missing))
    return Gate("M3 minimum acceptance coverage", PASS, f"{len(M3_ACCEPTANCE_TERMS)} terms covered")


def _check_doc() -> Gate:
    if not DOC_PATH.is_file():
        return Gate("static acceptance doc", FAIL, "doc missing")
    text = DOC_PATH.read_text(encoding="utf-8")
    required = (
        "Phase 3 Static Acceptance",
        "check_phase3_static_acceptance.py",
        "check_m2_release.py --static-only",
        "check_m3_local_product.py",
        "--run-live-smokes",
        "does not claim live WeKnora",
    )
    missing = [term for term in required if term not in text]
    if missing:
        return Gate("static acceptance doc", FAIL, "missing " + ", ".join(missing))
    if _contains_secret_shape(text):
        return Gate("static acceptance doc", FAIL, "doc contains secret-shaped text")
    return Gate("static acceptance doc", PASS, "required terms present")


def _check_git_safety() -> Gate:
    try:
        status = _git(["status", "--short"])
    except RuntimeError as exc:
        return Gate("git safety", FAIL, str(exc))
    risky = [
        line for line in status.splitlines() if _is_sensitive_status_path(line[3:].strip())
    ]
    if risky:
        return Gate("git safety", FAIL, "sensitive tracked/staged paths: " + "; ".join(risky))
    return Gate("git safety", PASS, "no sensitive tracked or staged paths detected")


def _run_command(name: str, command: list[str], *, timeout_seconds: int) -> Gate:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Gate(name, FAIL, f"timed out after {timeout_seconds}s")
    except OSError as exc:
        return Gate(name, FAIL, _safe_text(str(exc)))

    detail = _first_output_line(result.stdout, result.stderr, "completed")
    if result.returncode == 0:
        return Gate(name, PASS, detail)
    return Gate(name, FAIL, detail)


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(_safe_text(result.stderr.strip() or "git command failed"))
    return result.stdout


def _is_sensitive_status_path(path: str) -> bool:
    if path == ".env.example" or path.endswith("/.env.example"):
        return False
    normalized = path.replace("\\", "/")
    if any(part in normalized for part in SENSITIVE_PATH_PARTS):
        return True
    return normalized.endswith(SENSITIVE_SUFFIXES)


def _first_output_line(stdout: str, stderr: str, fallback: str) -> str:
    for value in (stdout, stderr):
        for line in value.splitlines():
            stripped = _safe_text(line)
            if stripped:
                return stripped
    return fallback


def _safe_text(value: str, limit: int = 320) -> str:
    redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(
        r"(?i)(authorization|x-api-key|api[_-]?key|token|secret|password)(\s*[:=]\s*)\S+",
        r"\1\2[redacted]",
        redacted,
    )
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "sk-[redacted]", redacted)
    redacted = re.sub(r"https?://[^\s\"'<>]+", "https://[redacted]", redacted)
    collapsed = " ".join(redacted.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _contains_secret_shape(value: str) -> bool:
    patterns = (
        r"WEKNORA_SERVICE_TOKEN\s*=",
        r"WEKNORA_API_KEY\s*=",
        r"CHAT_MODEL_API_KEY\s*=",
        r"EMBEDDING_API_KEY\s*=",
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+",
        r"sk-[A-Za-z0-9_-]{12,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
    return any(re.search(pattern, value) for pattern in patterns)


if __name__ == "__main__":
    raise SystemExit(main())
