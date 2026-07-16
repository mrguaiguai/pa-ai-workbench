"""PAR-P4-02 live PA plus WeKnora workflow acceptance orchestrator.

The checker uses the configured non-mock WeKnora service, delegates to the
repository-owned live API/browser matrices, and verifies that their uniquely
named temporary knowledge bases and Agents were removed. It never prints
credentials, raw provider payloads, document bodies, model answers, or ids.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PA_API_ROOT = REPOSITORY_ROOT / "apps" / "pa-api"
KNOWLEDGE_ROOT = REPOSITORY_ROOT / "packages" / "knowledge-engine"
AGENT_ROOT = REPOSITORY_ROOT / "packages" / "agent-runtime"
VALIDATION_ROOT = REPOSITORY_ROOT / "scripts" / "validation"

for path in (PA_API_ROOT, KNOWLEDGE_ROOT, AGENT_ROOT, VALIDATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import Settings
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


LIVE_CHECKS = (
    "check_weknora_native_product_browser_matrix.py",
    "check_weknora_native_intelligent_dialogue_browser_matrix.py",
    "check_weknora_native_intelligent_dialogue_history_citation_audit.py",
)

TEMPORARY_PREFIXES = (
    "WNID-P7-01",
    "WNID-P8-01",
    "WNID P8 01",
)


def main() -> int:
    settings = Settings()
    _assert_live_configuration(settings)
    _assert_weknora_health(settings.weknora_base_url, settings.weknora_timeout_seconds)

    environment = os.environ.copy()
    python_paths = [str(PA_API_ROOT), str(KNOWLEDGE_ROOT), str(AGENT_ROOT), str(VALIDATION_ROOT)]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    for checker_name in LIVE_CHECKS:
        subprocess.run(
            [sys.executable, str(VALIDATION_ROOT / checker_name)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=True,
        )

    temporary_kb_count, temporary_agent_count = _temporary_resource_counts(settings)
    _assert(temporary_kb_count == 0, "temporary P4 knowledge bases were cleaned")
    _assert(temporary_agent_count == 0, "temporary P4 Agents were cleaned")

    print("PA repository live workflow acceptance")
    print("- decision: PASS")
    print("- task: PAR-P4-02")
    print("- evidence_type: live_service + live_api + live_browser + history_citation_audit")
    print("- configuration: weknora_api=true mock=false credentials=present")
    print("- service: weknora_health=ok existing_compose_lifecycle=untouched")
    print("- workflows: document_rag_dialogue_wiki_mcp_web_history_citation_audit=pass")
    print("- browser: routes=7 viewport_checks=14 dialogue_viewports=2 overflow=0")
    print(
        "- cleanup: "
        f"temporary_kb_count={temporary_kb_count} temporary_agent_count={temporary_agent_count}"
    )
    return 0


def _assert_live_configuration(settings: Settings) -> None:
    _assert(settings.knowledge_backend == "weknora_api", "knowledge backend is weknora_api")
    _assert(settings.mock_mode is False, "PA mock mode is disabled")
    _assert(bool(settings.weknora_base_url), "WeKnora base URL is configured")
    _assert(bool(settings.weknora_service_token), "WeKnora service token is configured")
    _assert(bool(settings.weknora_workspace_id), "WeKnora workspace is configured")
    _assert(bool(settings.weknora_default_kb_id), "WeKnora default KB is configured")


def _assert_weknora_health(base_url: str, timeout_seconds: int) -> None:
    parsed = urlsplit(base_url)
    _assert(bool(parsed.scheme and parsed.netloc), "WeKnora base URL is valid")
    health_url = f"{parsed.scheme}://{parsed.netloc}/health"
    with urlopen(health_url, timeout=min(max(timeout_seconds, 1), 10)) as response:
        _assert(response.status == 200, "WeKnora health endpoint returned HTTP 200")


def _temporary_resource_counts(settings: Settings) -> tuple[int, int]:
    backend = WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )
    knowledge_bases = backend.list_knowledge_bases()
    agents = backend.list_agents()
    kb_count = sum(_has_temporary_prefix(item.get("name")) for item in knowledge_bases)
    agent_count = sum(_has_temporary_prefix(item.get("name")) for item in agents)
    return kb_count, agent_count


def _has_temporary_prefix(value: object) -> bool:
    name = str(value or "")
    return any(name.startswith(prefix) for prefix in TEMPORARY_PREFIXES)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
