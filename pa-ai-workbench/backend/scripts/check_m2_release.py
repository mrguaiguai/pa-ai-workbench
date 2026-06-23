"""M2 release readiness checker for PA AI Workbench.

Default behavior is conservative: static/fixture gates run, but live gates are
reported as blocking skipped checks unless --run-live-smokes is explicit.

The checker never prints secrets, full prompts, full documents, private
endpoints, or raw WeKnora responses. It relies on task-scoped smoke scripts that
already use sanitized fixtures or explicitly documented live side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

STATIC_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    ("compileall", [sys.executable, "-m", "compileall", "knowledge_engine", "backend/app", "agent"]),
    ("adapter error mapping", [sys.executable, "backend/scripts/smoke_weknora_adapter_errors_m2.py"]),
    ("RAG debug API", [sys.executable, "backend/scripts/smoke_rag_debug_api_m2.py"]),
    ("RAG debug params", [sys.executable, "backend/scripts/smoke_rag_debug_params_m2.py"]),
    ("citation contract", [sys.executable, "backend/scripts/smoke_weknora_citation_contract_m1.py"]),
    ("citation fail closed", [sys.executable, "backend/scripts/smoke_weknora_citation_fail_closed_m1.py"]),
    ("evidence dedup score", [sys.executable, "backend/scripts/smoke_evidence_dedup_score_m2.py"]),
    ("document recovery", [sys.executable, "backend/scripts/smoke_document_processing_recovery_m2.py"]),
    ("wiki status recovery", [sys.executable, "backend/scripts/smoke_wiki_status_recovery_m2.py"]),
    ("retrieve logging redaction", [sys.executable, "backend/scripts/smoke_weknora_logging_m2.py"]),
    ("request id propagation", [sys.executable, "backend/scripts/smoke_weknora_correlation_m2.py"]),
    ("history filters", [sys.executable, "backend/scripts/smoke_history_filters_m2.py"]),
    ("pilot feedback docs", [sys.executable, "backend/scripts/smoke_pilot_feedback_docs_m2.py"]),
    ("intranet runbook docs", [sys.executable, "backend/scripts/smoke_intranet_runbook_m2.py"]),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], str], ...] = (
    (
        "M2 preflight: DeepSeek/DashScope/KB/vector/Redis/DocReader",
        [sys.executable, "backend/scripts/check_m2_preflight.py"],
        "live probes validate DashScope Embedding, KB embedding_model_id, vector dimension, Redis, DocReader",
    ),
    (
        "DeepSeek chat smoke",
        [sys.executable, "backend/scripts/smoke_real_chat_model_m2.py"],
        "calls configured real chat model through ModelGateway",
    ),
    (
        "WeKnora RAG live gate",
        [sys.executable, "backend/scripts/smoke_weknora_rag_m1.py"],
        "requires live WeKnora retrieval with non-mock evidence",
    ),
    (
        "WeKnora Wiki live gate",
        [sys.executable, "backend/scripts/smoke_weknora_wiki_m1.py"],
        "requires live WeKnora Wiki search/read/create path",
    ),
    (
        "Agent real LLM + non-mock citation",
        [sys.executable, "backend/scripts/smoke_weknora_agent_real_llm_m2.py"],
        "uploads one sanitized Markdown fixture and runs QA/policy/case through real LLM",
    ),
    (
        "Wiki real LLM draft + publish + retrieve",
        [sys.executable, "backend/scripts/smoke_wiki_real_llm_m2.py"],
        "uploads one sanitized fixture and publishes one generated PA Wiki page",
    ),
)

REQUIRED_FILES = (
    "backend/scripts/check_m2_preflight.py",
    "backend/scripts/smoke_real_chat_model_m2.py",
    "backend/scripts/smoke_weknora_rag_m1.py",
    "backend/scripts/smoke_weknora_wiki_m1.py",
    "backend/scripts/smoke_weknora_agent_real_llm_m2.py",
    "backend/scripts/smoke_wiki_real_llm_m2.py",
    "backend/scripts/smoke_weknora_logging_m2.py",
    "backend/scripts/smoke_weknora_correlation_m2.py",
    "docs/PHASE3_M2_INTRANET_RUNBOOK.md",
    "docs/PHASE3_M2_REQUEST_ID_PROPAGATION.md",
    "docs/PHASE3_M2_PILOT_FEEDBACK_TEMPLATE.md",
    "docs/PHASE3_M2_RELEASE_CHECKLIST.md",
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
    parser = argparse.ArgumentParser(description="Check M2 release readiness.")
    parser.add_argument(
        "--run-live-smokes",
        action="store_true",
        help="Run live side-effecting WeKnora/LLM smoke gates.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Run only static and sanitized fixture gates; live gates are informational.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Per-command timeout for smoke gates.",
    )
    args = parser.parse_args()

    if args.static_only and args.run_live_smokes:
        print("M2 release readiness")
        print("- decision: NOT READY")
        print("- argument validation: FAIL - use either --static-only or --run-live-smokes, not both")
        return 1

    gates = run_gates(
        run_live_smokes=args.run_live_smokes,
        static_only=args.static_only,
        timeout_seconds=max(args.timeout_seconds, 1),
    )
    blocking_failures = [gate for gate in gates if gate.blocking and gate.status == FAIL]
    if blocking_failures:
        decision = "NOT READY"
    elif args.static_only:
        decision = "STATIC READY"
    else:
        decision = "READY"

    print("M2 release readiness")
    print(f"- decision: {decision}")
    print(f"- mode: {_mode(args.run_live_smokes, args.static_only)}")
    for gate in gates:
        blocking = "blocking" if gate.blocking else "info"
        print(f"- {gate.name}: {gate.status} ({blocking}) - {gate.detail}")
    return 0 if not blocking_failures else 1


def run_gates(
    *,
    run_live_smokes: bool = False,
    static_only: bool = False,
    timeout_seconds: int = 300,
) -> list[Gate]:
    gates: list[Gate] = [
        _check_required_files(),
        _check_git_safety(),
        _check_release_docs(),
    ]
    gates.extend(_run_static_commands(timeout_seconds))
    gates.extend(_live_gates(run_live_smokes, static_only, timeout_seconds))
    gates.append(_check_no_mock_release_pass(gates, run_live_smokes, static_only))
    return gates


def _check_required_files() -> Gate:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    if missing:
        return Gate("required M2 release artifacts", FAIL, "missing " + ", ".join(missing))
    return Gate("required M2 release artifacts", PASS, f"{len(REQUIRED_FILES)} artifacts present")


def _check_git_safety() -> Gate:
    try:
        status = _git(["status", "--short"])
    except RuntimeError as exc:
        return Gate("git safety", FAIL, str(exc))
    risky = [
        line
        for line in status.splitlines()
        if _is_sensitive_status_path(line[3:].strip())
    ]
    if risky:
        return Gate("git safety", FAIL, "sensitive tracked/staged paths: " + "; ".join(risky))
    return Gate("git safety", PASS, "no sensitive tracked or staged paths detected")


def _check_release_docs() -> Gate:
    checklist = PROJECT_ROOT / "docs" / "PHASE3_M2_RELEASE_CHECKLIST.md"
    if not checklist.is_file():
        return Gate("release checklist", FAIL, "docs/PHASE3_M2_RELEASE_CHECKLIST.md is missing")
    text = checklist.read_text(encoding="utf-8")
    required_terms = [
        "DeepSeek Chat",
        "DashScope Embedding",
        "embedding_model_id",
        "WeKnora RAG",
        "WeKnora Wiki",
        "Agent real LLM",
        "Wiki real LLM draft",
        "mock/fallback",
        "git safety",
    ]
    missing = [term for term in required_terms if term not in text]
    if missing:
        return Gate("release checklist", FAIL, "missing terms: " + ", ".join(missing))
    if _contains_secret_shape(text):
        return Gate("release checklist", FAIL, "checklist contains secret or endpoint shape")
    return Gate("release checklist", PASS, "required M2 release terms present")


def _run_static_commands(timeout_seconds: int) -> list[Gate]:
    return [
        _run_command(name, command, timeout_seconds=timeout_seconds, blocking=True)
        for name, command in STATIC_COMMANDS
    ]


def _live_gates(
    run_live_smokes: bool,
    static_only: bool,
    timeout_seconds: int,
) -> list[Gate]:
    if static_only:
        return [
            Gate(name, INFO, "not run in --static-only mode; " + detail, blocking=False)
            for name, _command, detail in LIVE_COMMANDS
        ]
    if not run_live_smokes:
        return [
            Gate(
                name,
                FAIL,
                "not run; rerun with --run-live-smokes in an approved intranet environment. " + detail,
                blocking=True,
            )
            for name, _command, detail in LIVE_COMMANDS
        ]
    return [
        _run_command(name, command, timeout_seconds=timeout_seconds, blocking=True)
        for name, command, _detail in LIVE_COMMANDS
    ]


def _check_no_mock_release_pass(
    gates: list[Gate],
    run_live_smokes: bool,
    static_only: bool,
) -> Gate:
    if static_only:
        return Gate(
            "mock/fallback release pass guard",
            INFO,
            "static-only mode does not prove non-mock live evidence",
            blocking=False,
        )
    if not run_live_smokes:
        return Gate(
            "mock/fallback release pass guard",
            FAIL,
            "live non-mock gates were not run; release cannot count mock/fallback evidence",
        )
    failed_live = [gate for gate in gates if gate.name in {name for name, _cmd, _detail in LIVE_COMMANDS} and gate.status != PASS]
    if failed_live:
        return Gate(
            "mock/fallback release pass guard",
            FAIL,
            "live non-mock gates are not all PASS; release cannot count mock/fallback evidence",
        )
    return Gate(
        "mock/fallback release pass guard",
        PASS,
        "all live gates required for non-mock release evidence are PASS",
    )


def _run_command(
    name: str,
    command: list[str],
    *,
    timeout_seconds: int,
    blocking: bool,
) -> Gate:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=_safe_child_env(),
        )
    except subprocess.TimeoutExpired:
        return Gate(name, FAIL, f"timed out after {timeout_seconds}s", blocking=blocking)
    except OSError as exc:
        return Gate(name, FAIL, _safe_text(str(exc)), blocking=blocking)

    detail = _first_output_line(result.stdout, result.stderr, "completed")
    if result.returncode == 0:
        return Gate(name, PASS, detail, blocking=blocking)
    return Gate(name, FAIL, detail, blocking=blocking)


def _safe_child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _is_sensitive_status_path(path: str) -> bool:
    if path == ".env.example" or path.endswith("/.env.example"):
        return False
    normalized = path.replace("\\", "/")
    if any(part in normalized for part in SENSITIVE_PATH_PARTS):
        return True
    return normalized.endswith(SENSITIVE_SUFFIXES)


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
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+",
        r"sk-[A-Za-z0-9_-]{12,}",
        r"https?://",
    )
    return any(re.search(pattern, value) for pattern in patterns)


def _mode(run_live_smokes: bool, static_only: bool) -> str:
    if run_live_smokes:
        return "live"
    if static_only:
        return "static-only"
    return "default-no-live"


if __name__ == "__main__":
    raise SystemExit(main())
