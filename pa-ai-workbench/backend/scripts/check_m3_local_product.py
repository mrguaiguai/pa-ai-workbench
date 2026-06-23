"""M3 local product readiness checker for PA AI Workbench.

Default mode runs static and sanitized fixture gates and reports STATIC READY
without claiming live WeKnora/model acceptance. Use --run-live-smokes in an
approved local product environment to run side-effecting live gates.
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

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

RUNBOOK_PATH = PROJECT_ROOT / "docs" / "PHASE3_M3_LOCAL_PRODUCT_RUNBOOK.md"
HOME_PAGE_PATH = PROJECT_ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"
CLIENT_PATH = PROJECT_ROOT / "frontend" / "src" / "api" / "client.ts"

STATIC_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    (
        "compileall",
        [sys.executable, "-m", "compileall", "knowledge_engine", "backend/app", "agent"],
    ),
    (
        "M3 capability matrix",
        [sys.executable, "backend/scripts/smoke_backend_capability_matrix_m3.py"],
    ),
    (
        "M3 feature flags",
        [sys.executable, "backend/scripts/smoke_backend_feature_flags_m3.py"],
    ),
    (
        "M3 backend switch",
        [sys.executable, "backend/scripts/check_m3_backend_switch.py"],
    ),
    (
        "M3 backend contract",
        [sys.executable, "backend/scripts/smoke_knowledge_backend_contract_m3.py"],
    ),
    (
        "M3 retrieval parameters",
        [sys.executable, "backend/scripts/smoke_retrieval_parameters_m3.py"],
    ),
    (
        "M3 retrieval golden set",
        [sys.executable, "backend/scripts/smoke_retrieval_quality_golden_m3.py"],
    ),
    (
        "M3 RAG quality rubric",
        [sys.executable, "backend/scripts/smoke_rag_quality_evaluation_m3.py"],
    ),
    (
        "M3 Agent faithfulness",
        [sys.executable, "backend/scripts/smoke_agent_faithfulness_m3.py"],
    ),
    (
        "M3 Wiki fallback sync",
        [sys.executable, "backend/scripts/smoke_wiki_fallback_sync_m3.py"],
    ),
)

LIVE_COMMANDS: tuple[tuple[str, list[str], str], ...] = (
    (
        "M3 preflight: DeepSeek/DashScope/KB/vector/Redis/DocReader",
        [sys.executable, "backend/scripts/check_m2_preflight.py"],
        "validates live WeKnora, DeepSeek KnowledgeQA, DashScope Embedding, KB binding, vector store, Redis, and DocReader",
    ),
    (
        "DeepSeek chat via PA ModelGateway",
        [sys.executable, "backend/scripts/smoke_real_chat_model_m2.py"],
        "calls the configured public chat model API",
    ),
    (
        "WeKnora RAG live E2E",
        [sys.executable, "backend/scripts/smoke_weknora_rag_m1.py"],
        "uploads/retrieves sanitized material through PA KnowledgeBackend Adapter",
    ),
    (
        "WeKnora Wiki live E2E",
        [sys.executable, "backend/scripts/smoke_weknora_wiki_m1.py"],
        "checks live Wiki search/read/create path through PA adapter",
    ),
    (
        "Agent real LLM QA/policy/case",
        [sys.executable, "backend/scripts/smoke_weknora_agent_real_llm_m2.py"],
        "runs QA, policy, and case with real LLM and non-mock citations",
    ),
    (
        "Wiki draft publish retrieve live",
        [sys.executable, "backend/scripts/smoke_wiki_real_llm_m2.py"],
        "generates Wiki draft, publishes, and retrieves wiki_page evidence",
    ),
)

REQUIRED_FILES = (
    "docs/PHASE3_M3_LOCAL_PRODUCT_RUNBOOK.md",
    "backend/scripts/check_m3_local_product.py",
    "backend/scripts/check_m2_preflight.py",
    "backend/scripts/smoke_real_chat_model_m2.py",
    "backend/scripts/smoke_weknora_rag_m1.py",
    "backend/scripts/smoke_weknora_wiki_m1.py",
    "backend/scripts/smoke_weknora_agent_real_llm_m2.py",
    "backend/scripts/smoke_wiki_real_llm_m2.py",
    "backend/scripts/smoke_retrieval_quality_golden_m3.py",
    "backend/scripts/smoke_rag_quality_evaluation_m3.py",
    "backend/scripts/smoke_agent_faithfulness_m3.py",
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
    parser = argparse.ArgumentParser(description="Check M3 local product readiness.")
    parser.add_argument(
        "--run-live-smokes",
        action="store_true",
        help="Run live side-effecting WeKnora/model smoke gates.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Per-command timeout for smoke gates.",
    )
    args = parser.parse_args()

    gates = run_gates(
        run_live_smokes=args.run_live_smokes,
        timeout_seconds=max(args.timeout_seconds, 1),
    )
    blocking_failures = [gate for gate in gates if gate.blocking and gate.status == FAIL]
    if blocking_failures:
        decision = "NOT READY"
    elif args.run_live_smokes:
        decision = "READY"
    else:
        decision = "STATIC READY"

    print("M3 local product readiness")
    print(f"- decision: {decision}")
    print(f"- mode: {'live' if args.run_live_smokes else 'static-fixture'}")
    for gate in gates:
        blocking = "blocking" if gate.blocking else "info"
        print(f"- {gate.name}: {gate.status} ({blocking}) - {gate.detail}")
    return 0 if not blocking_failures else 1


def run_gates(*, run_live_smokes: bool = False, timeout_seconds: int = 300) -> list[Gate]:
    gates: list[Gate] = [
        _check_required_files(),
        _check_git_safety(),
        _check_runbook(),
        _check_status_surfaces(),
    ]
    gates.extend(
        _run_command(name, command, timeout_seconds=timeout_seconds, blocking=True)
        for name, command in STATIC_COMMANDS
    )
    gates.extend(_live_gates(run_live_smokes, timeout_seconds))
    gates.append(_check_live_evidence_guard(gates, run_live_smokes))
    return gates


def _check_required_files() -> Gate:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    if missing:
        return Gate("required M3 artifacts", FAIL, "missing " + ", ".join(missing))
    return Gate("required M3 artifacts", PASS, f"{len(REQUIRED_FILES)} artifacts present")


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


def _check_runbook() -> Gate:
    if not RUNBOOK_PATH.is_file():
        return Gate("M3 local product runbook", FAIL, "runbook missing")
    text = RUNBOOK_PATH.read_text(encoding="utf-8")
    required_sections = (
        "## Product Boundary",
        "## Required Runtime Mode",
        "## Empty Data Startup",
        "## Backend And Frontend Startup",
        "## Readiness Surfaces",
        "## Required Checks",
        "## End-To-End Acceptance",
        "## Fallback Rules",
        "## Troubleshooting",
        "## Rollback",
        "## Git Safety",
    )
    required_terms = (
        "PA Frontend -> PA Backend -> PA KnowledgeBackend Adapter -> WeKnora Backend",
        "DeepSeek",
        "DashScope/Aliyun Embedding",
        "embedding_model_id",
        "DocReader",
        "Redis",
        "vector store",
        "GET /api/status",
        "GET /api/model/status",
        "GET /api/capabilities",
        "source=weknora_api",
        "wiki_page",
        "NO_EVIDENCE",
        "smoke_retrieval_quality_golden_m3.py",
        "smoke_rag_quality_evaluation_m3.py",
        "smoke_agent_faithfulness_m3.py",
        "check_m3_local_product.py --run-live-smokes",
        "release evidence",
        "fail-closed",
    )
    missing_sections = [section for section in required_sections if section not in text]
    missing_terms = [term for term in required_terms if term not in text]
    if missing_sections or missing_terms:
        return Gate(
            "M3 local product runbook",
            FAIL,
            "missing " + ", ".join(missing_sections + missing_terms),
        )
    if _contains_secret_shape(text):
        return Gate("M3 local product runbook", FAIL, "runbook contains secret-shaped text")
    return Gate(
        "M3 local product runbook",
        PASS,
        f"{len(required_sections)} sections and {len(required_terms)} required terms present",
    )


def _check_status_surfaces() -> Gate:
    if not HOME_PAGE_PATH.is_file() or not CLIENT_PATH.is_file():
        return Gate("status/capability surfaces", FAIL, "frontend status files missing")
    home = HOME_PAGE_PATH.read_text(encoding="utf-8")
    client = CLIENT_PATH.read_text(encoding="utf-8")
    required_home_terms = (
        "Chat Model",
        "Embedding",
        "RAG Pipeline",
        "Capability",
        "weknora",
        "fail closed",
        "citation",
        "wiki publish",
        "api key",
    )
    required_client_terms = (
        "getStatus",
        "getModelStatus",
        "getCapabilities",
        "backend_capabilities",
        "feature_flags",
        "service_token_configured",
        "api_key_configured",
    )
    missing = [term for term in required_home_terms if term not in home]
    missing.extend(term for term in required_client_terms if term not in client)
    if missing:
        return Gate("status/capability surfaces", FAIL, "missing " + ", ".join(missing))
    if "CHAT_MODEL_API_KEY" in home + client or "WEKNORA_SERVICE_TOKEN" in home + client:
        return Gate("status/capability surfaces", FAIL, "frontend references sensitive env names")
    return Gate("status/capability surfaces", PASS, "home/status/capability fields present")


def _live_gates(run_live_smokes: bool, timeout_seconds: int) -> list[Gate]:
    if not run_live_smokes:
        return [
            Gate(
                name,
                INFO,
                "not run in default mode; rerun with --run-live-smokes in an approved environment. " + detail,
                blocking=False,
            )
            for name, _command, detail in LIVE_COMMANDS
        ]
    return [
        _run_command(name, command, timeout_seconds=timeout_seconds, blocking=True)
        for name, command, _detail in LIVE_COMMANDS
    ]


def _check_live_evidence_guard(gates: list[Gate], run_live_smokes: bool) -> Gate:
    if not run_live_smokes:
        return Gate(
            "live non-mock evidence guard",
            INFO,
            "static fixture gates passed only; live product acceptance still requires --run-live-smokes",
            blocking=False,
        )
    live_names = {name for name, _cmd, _detail in LIVE_COMMANDS}
    failed = [gate.name for gate in gates if gate.name in live_names and gate.status != PASS]
    if failed:
        return Gate(
            "live non-mock evidence guard",
            FAIL,
            "live gates are not all PASS: " + ", ".join(failed),
        )
    return Gate(
        "live non-mock evidence guard",
        PASS,
        "all live gates passed; mock/fallback evidence was not counted",
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
        r"AKIA[0-9A-Z]{16}",
        r"xox[baprs]-[A-Za-z0-9-]{20,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
    return any(re.search(pattern, value) for pattern in patterns)


if __name__ == "__main__":
    raise SystemExit(main())
