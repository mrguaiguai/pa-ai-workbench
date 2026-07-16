"""M1 release readiness checker for PA AI Workbench.

This checker is intentionally conservative. It fails readiness if the runtime
is not configured for WeKnora, if mock mode is enabled, if live smoke gates are
missing or not run, or if sensitive files are tracked/staged.

It never prints service tokens or reads real .env contents directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402


REQUIRED_SMOKES = (
    "scripts/validation/smoke_weknora_connection.py",
    "scripts/validation/smoke_weknora_rag_m1.py",
    "scripts/validation/smoke_weknora_agent_m1.py",
    "scripts/validation/smoke_weknora_wiki_m1.py",
)

SENSITIVE_PATH_PARTS = (
    ".env",
    "backend/data/",
    "backend/uploads/",
    "logs/",
    "node_modules/",
    "dist/",
)

SENSITIVE_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Check M1 release readiness.")
    parser.add_argument(
        "--run-live-smokes",
        action="store_true",
        help="Run live WeKnora smoke scripts after static release checks.",
    )
    args = parser.parse_args()

    checks = _run_checks(run_live_smokes=args.run_live_smokes)
    decision = "READY" if all(check.status == "PASS" for check in checks) else "NOT READY"

    print("M1 release readiness")
    print(f"- decision: {decision}")
    for check in checks:
        print(f"- {check.name}: {check.status} - {check.detail}")
    return 0 if decision == "READY" else 1


def _run_checks(run_live_smokes: bool) -> list[Check]:
    settings = Settings()
    checks = [
        _check_config_mode(settings),
        _check_weknora_config(settings),
        _check_smoke_scripts(),
        _check_git_safety(),
    ]
    checks.extend(_check_live_smokes(run_live_smokes))
    return checks


def _check_config_mode(settings: Settings) -> Check:
    backend_ok = settings.knowledge_backend.strip().lower() == "weknora_api"
    mock_ok = settings.mock_mode is False
    if backend_ok and mock_ok:
        return Check("Config mode", "PASS", "KNOWLEDGE_BACKEND=weknora_api and MOCK_MODE=false")
    missing = []
    if not backend_ok:
        missing.append("KNOWLEDGE_BACKEND=weknora_api")
    if not mock_ok:
        missing.append("MOCK_MODE=false")
    return Check("Config mode", "FAIL", "missing " + ", ".join(missing))


def _check_weknora_config(settings: Settings) -> Check:
    missing = []
    if not settings.weknora_base_url:
        missing.append("WEKNORA_BASE_URL")
    if not settings.weknora_service_token:
        missing.append("WEKNORA_SERVICE_TOKEN")
    if not settings.weknora_workspace_id:
        missing.append("WEKNORA_WORKSPACE_ID")
    if not settings.weknora_default_kb_id:
        missing.append("WEKNORA_DEFAULT_KB_ID")
    if settings.weknora_timeout_seconds <= 0:
        missing.append("WEKNORA_TIMEOUT_SECONDS")
    if not missing:
        return Check("WeKnora config", "PASS", "required variables are present")
    return Check("WeKnora config", "FAIL", "missing " + ", ".join(missing))


def _check_smoke_scripts() -> Check:
    missing = [path for path in REQUIRED_SMOKES if not (PROJECT_ROOT / path).is_file()]
    if not missing:
        return Check("Smoke scripts", "PASS", "connection, RAG, Agent, and Wiki smokes exist")
    return Check("Smoke scripts", "FAIL", "missing " + ", ".join(missing))


def _check_git_safety() -> Check:
    try:
        status = _git(["status", "--short"])
    except RuntimeError as exc:
        return Check("Git safety", "FAIL", str(exc))
    risky = [
        line
        for line in status.splitlines()
        if _is_sensitive_status_path(line[3:].strip())
    ]
    if risky:
        return Check("Git safety", "FAIL", "sensitive tracked/staged paths: " + "; ".join(risky))
    return Check("Git safety", "PASS", "no sensitive tracked or staged paths detected")


def _check_live_smokes(run_live_smokes: bool) -> list[Check]:
    if not run_live_smokes:
        return [
            Check(
                "Live smokes",
                "FAIL",
                "not run; rerun with --run-live-smokes before M1 release",
            )
        ]

    smoke_commands = (
        ("WeKnora connection", [sys.executable, "scripts/validation/smoke_weknora_connection.py"]),
        ("RAG smoke", [sys.executable, "scripts/validation/smoke_weknora_rag_m1.py"]),
        ("Agent smoke", [sys.executable, "scripts/validation/smoke_weknora_agent_m1.py"]),
        ("Wiki smoke", [sys.executable, "scripts/validation/smoke_weknora_wiki_m1.py"]),
    )
    checks: list[Check] = []
    for name, command in smoke_commands:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            checks.append(Check(name, "PASS", _first_output_line(result.stdout, "passed")))
        else:
            checks.append(Check(name, "FAIL", _first_output_line(result.stderr, "failed")))
    return checks


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
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def _first_output_line(value: str, fallback: str) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return fallback


if __name__ == "__main__":
    raise SystemExit(main())
