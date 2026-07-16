"""Smoke-check M3 backend capability matrix and fallback boundaries.

This fixture smoke covers P3-M3-A0 without using real WeKnora credentials:
- mock/weknora_api/extracted expose supported/partial/unsupported/dev-only status;
- release-like and MOCK_MODE=false paths do not silently fallback to mock;
- extracted fallback is explicit-only;
- missing citation trace cannot be considered real WeKnora release evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from knowledge_engine.backends import MockKnowledgeBackend  # noqa: E402
from knowledge_engine.capabilities import BACKEND_CAPABILITY_MATRIX  # noqa: E402
from knowledge_engine.capabilities import CAPABILITY_ORDER  # noqa: E402
from knowledge_engine.capabilities import CAPABILITY_STATUSES  # noqa: E402
from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402
from knowledge_engine.capabilities import is_strict_fallback_mode  # noqa: E402
from knowledge_engine.capabilities import should_fail_closed_for_unavailable_backend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402
from knowledge_engine.factory import create_knowledge_engine  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_BACKEND_CAPABILITY_MATRIX.md"
ENV_KEYS = (
    "APP_ENV",
    "MOCK_MODE",
    "KNOWLEDGE_BACKEND",
    "WEKNORA_BASE_URL",
    "WEKNORA_SERVICE_TOKEN",
    "WEKNORA_API_KEY",
    "WEKNORA_WORKSPACE_ID",
    "WEKNORA_DEFAULT_KB_ID",
)


class SmokeError(RuntimeError):
    """Raised when the M3 capability boundary contract fails."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"M3 backend capability matrix smoke failed: {exc}", file=sys.stderr)
        return 1

    print("M3 backend capability matrix smoke passed")
    print(f"- backends: {', '.join(result['backends'])}")
    print(f"- capabilities checked: {result['capability_count']}")
    print(f"- release fail-closed cases: {result['fail_closed_cases']}")
    print(f"- docs checked: {result['docs_checked']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    _assert_matrix_shape()
    _assert_policy_snapshots()
    _assert_factory_fail_closed()
    _assert_docs()
    return {
        "backends": sorted(BACKEND_CAPABILITY_MATRIX),
        "capability_count": len(CAPABILITY_ORDER),
        "fail_closed_cases": 3,
        "docs_checked": DOC_PATH.name,
    }


def _assert_matrix_shape() -> None:
    expected_backends = {"mock", "weknora_api", "extracted"}
    if set(BACKEND_CAPABILITY_MATRIX) != expected_backends:
        raise SmokeError(f"unexpected matrix backends: {sorted(BACKEND_CAPABILITY_MATRIX)}")

    for backend, capabilities in BACKEND_CAPABILITY_MATRIX.items():
        missing = set(CAPABILITY_ORDER) - set(capabilities)
        extra = set(capabilities) - set(CAPABILITY_ORDER)
        if missing or extra:
            raise SmokeError(f"{backend} capability keys drifted; missing={missing}, extra={extra}")
        invalid = {
            capability: status
            for capability, status in capabilities.items()
            if status not in CAPABILITY_STATUSES
        }
        if invalid:
            raise SmokeError(f"{backend} has invalid capability statuses: {invalid}")

    if BACKEND_CAPABILITY_MATRIX["weknora_api"]["citation_trace"] != "supported":
        raise SmokeError("weknora_api citation_trace must be supported")
    if BACKEND_CAPABILITY_MATRIX["mock"]["citation_trace"] != "unsupported":
        raise SmokeError("mock citation_trace must be unsupported")
    if BACKEND_CAPABILITY_MATRIX["mock"]["real_data_source"] != "unsupported":
        raise SmokeError("mock must not be a real data source")
    if BACKEND_CAPABILITY_MATRIX["extracted"]["real_data_source"] != "unsupported":
        raise SmokeError("extracted must not be marked as a WeKnora real data source")


def _assert_policy_snapshots() -> None:
    dev_mock = backend_capability_snapshot(
        backend_name="mock",
        app_env="local",
        mock_mode=True,
        weknora_configured=False,
    )
    if dev_mock["release_eligible"]:
        raise SmokeError("mock unexpectedly marked release eligible")
    if dev_mock["fallback_policy"]["extracted_fallback"] != "explicit-only":
        raise SmokeError("extracted fallback policy must be explicit-only")

    pilot_missing = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="pilot",
        mock_mode=True,
        weknora_configured=False,
    )
    if not pilot_missing["strict_fallback_mode"]:
        raise SmokeError("pilot mode must be strict")
    if not pilot_missing["fallback_policy"]["fail_closed"]:
        raise SmokeError("pilot missing WeKnora config must fail closed")
    if pilot_missing["fallback_policy"]["silent_mock_fallback_allowed"]:
        raise SmokeError("pilot mode must not allow silent mock fallback")

    local_real_missing = backend_capability_snapshot(
        backend_name="weknora_api",
        app_env="local",
        mock_mode=False,
        weknora_configured=False,
    )
    if not local_real_missing["fallback_policy"]["fail_closed"]:
        raise SmokeError("MOCK_MODE=false missing WeKnora config must fail closed")

    extracted = backend_capability_snapshot(
        backend_name="extracted",
        app_env="local",
        mock_mode=True,
        weknora_configured=False,
    )
    if extracted["active_backend"] != "extracted":
        raise SmokeError("extracted backend must only appear when explicitly selected")
    if extracted["release_eligible"]:
        raise SmokeError("extracted must not be release eligible")

    if not is_strict_fallback_mode(app_env="intranet", mock_mode=True):
        raise SmokeError("intranet mode must be strict")
    if not should_fail_closed_for_unavailable_backend("weknora_api", app_env="local", mock_mode=False):
        raise SmokeError("weknora_api must fail closed when MOCK_MODE=false")
    if should_fail_closed_for_unavailable_backend("extracted", app_env="pilot", mock_mode=False):
        raise SmokeError("explicit extracted selection must not be treated as silent mock fallback")


def _assert_factory_fail_closed() -> None:
    with _temporary_env(
        {
            "APP_ENV": "local",
            "MOCK_MODE": "true",
            "KNOWLEDGE_BACKEND": "weknora_api",
            "WEKNORA_BASE_URL": "",
            "WEKNORA_SERVICE_TOKEN": "",
            "WEKNORA_API_KEY": "",
            "WEKNORA_WORKSPACE_ID": "",
            "WEKNORA_DEFAULT_KB_ID": "",
        }
    ):
        engine = create_knowledge_engine()
        if not isinstance(engine, MockKnowledgeBackend):
            raise SmokeError("local dev missing WeKnora config should fallback to mock")

    strict_cases = (
        {"APP_ENV": "pilot", "MOCK_MODE": "true", "KNOWLEDGE_BACKEND": "weknora_api"},
        {"APP_ENV": "local", "MOCK_MODE": "false", "KNOWLEDGE_BACKEND": "weknora_api"},
        {"APP_ENV": "pilot", "MOCK_MODE": "true", "KNOWLEDGE_BACKEND": "unknown_backend"},
    )
    for env in strict_cases:
        with _temporary_env(
            {
                **env,
                "WEKNORA_BASE_URL": "",
                "WEKNORA_SERVICE_TOKEN": "",
                "WEKNORA_API_KEY": "",
                "WEKNORA_WORKSPACE_ID": "",
                "WEKNORA_DEFAULT_KB_ID": "",
            }
        ):
            try:
                create_knowledge_engine()
            except KnowledgeBackendUnavailableError:
                continue
            raise SmokeError(f"factory did not fail closed for {env['KNOWLEDGE_BACKEND']}")


def _assert_docs() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required = (
        "supported",
        "partial",
        "unsupported",
        "dev-only",
        "fail closed",
        "do not fallback mock",
        "explicit-only",
        "citation trace",
        "source=weknora_api",
    )
    missing = [phrase for phrase in required if phrase not in text]
    if missing:
        raise SmokeError("capability matrix doc missing required phrases: " + ", ".join(missing))


class _temporary_env:
    def __init__(self, updates: dict[str, str]) -> None:
        self.updates = updates
        self.original: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key in ENV_KEYS:
            self.original[key] = os.environ.get(key)
            os.environ.pop(key, None)
        for key, value in self.updates.items():
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        for key in ENV_KEYS:
            os.environ.pop(key, None)
            if self.original[key] is not None:
                os.environ[key] = self.original[key] or ""


if __name__ == "__main__":
    raise SystemExit(main())
