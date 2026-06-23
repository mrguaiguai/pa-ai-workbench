"""Fixture smoke for WeKnora-first status/report gates.

This smoke does not call PA, WeKnora, model providers, databases, or logs. It
checks that the backend capability snapshot exposes truthful status categories
and that the report safety checker includes WeKnora-first PASS safeguards.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when status gate smoke validation fails."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora-first status gates smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora-first status gates smoke passed (fixture)")
    print(f"- live categories: {result['live_count']}")
    print(f"- blocked categories: {result['blocked_count']}")
    print(f"- backlog categories: {result['backlog_count']}")
    print(f"- report checker self-test: {result['checker']}")
    return 0


def _run_smoke() -> dict[str, int | str]:
    live_snapshot = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="local",
        mock_mode=False,
        weknora_configured=True,
    )
    live_gates = live_snapshot.get("weknora_first_status_gates") or {}
    live_categories = live_gates.get("status_categories") or {}
    _assert(live_snapshot["release_eligible"] is True, "WeKnora snapshot should be release eligible")
    _assert(live_categories.get("live"), "live categories missing")
    _assert(live_categories.get("backlog"), "backlog categories missing")
    _assert(
        live_gates.get("unsafe_pass_evidence", {}).get("fixture_only_pass_allowed") is False,
        "fixture-only PASS must be forbidden",
    )

    blocked_snapshot = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="staging",
        mock_mode=False,
        weknora_configured=False,
    )
    blocked_categories = (
        blocked_snapshot.get("weknora_first_status_gates", {}).get("status_categories", {})
    )
    _assert(blocked_snapshot["fallback_policy"]["fail_closed"] is True, "fail-closed missing")
    _assert(blocked_categories.get("blocked"), "blocked categories missing")

    mock_snapshot = backend_capability_snapshot(
        backend_name="mock",
        app_env="local",
        mock_mode=True,
        weknora_configured=False,
    )
    mock_categories = mock_snapshot.get("weknora_first_status_gates", {}).get(
        "status_categories",
        {},
    )
    _assert(mock_categories.get("mock"), "mock categories missing")
    _assert(mock_categories.get("fallback"), "fallback categories missing")

    checker_result = subprocess.run(
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
    if checker_result.returncode != 0:
        raise SmokeError(
            "report checker self-test failed: "
            + (checker_result.stderr or checker_result.stdout).strip()[:300]
        )

    return {
        "live_count": len(live_categories.get("live") or []),
        "blocked_count": len(blocked_categories.get("blocked") or []),
        "backlog_count": len(live_categories.get("backlog") or []),
        "checker": "passed",
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
