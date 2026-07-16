"""Smoke-check M3 backend feature flags and capability guardrails.

This fixture smoke covers P3-M3-A3:
- /api/capabilities exposes a sanitized feature flag schema;
- UI code gates RAG debug and Wiki write/recovery actions by feature flags;
- Agent tools block unsupported capabilities before backend calls.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agent.tools.capability_guard import AgentCapabilityError  # noqa: E402
from agent.tools.capability_guard import AgentCapabilityGuard  # noqa: E402
from app.api.health import api_capabilities  # noqa: E402
from app.config import get_settings  # noqa: E402
from knowledge_engine.base import KnowledgeEngine  # noqa: E402
from knowledge_engine.capabilities import BACKEND_CAPABILITY_MATRIX  # noqa: E402
from knowledge_engine.capabilities import CAPABILITY_ORDER  # noqa: E402
from knowledge_engine.capabilities import FEATURE_FLAG_SCHEMA_VERSION  # noqa: E402
from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402
from knowledge_engine.schemas import Evidence  # noqa: E402
from knowledge_engine.schemas import KnowledgeDocument  # noqa: E402
from knowledge_engine.schemas import WikiPage  # noqa: E402
from knowledge_engine.schemas import WikiPageSummary  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_FEATURE_FLAGS.md"
RAG_DEBUG_PATH = PROJECT_ROOT / "apps" / "pa-web" / "src" / "pages" / "RagDebugPage.tsx"
WIKI_PAGE_PATH = PROJECT_ROOT / "apps" / "pa-web" / "src" / "pages" / "WikiPage.tsx"
CLIENT_PATH = PROJECT_ROOT / "apps" / "pa-web" / "src" / "api" / "client.ts"


class SmokeError(RuntimeError):
    """Raised when feature flag expectations fail."""


class FixtureUnsupportedBackend(KnowledgeEngine):
    def __init__(self) -> None:
        self.retrieve_calls = 0
        self.wiki_read_calls = 0

    def health(self) -> dict:
        return {
            "status": "ok",
            "backend": "fixture_unsupported",
            "capabilities": {
                "rag_retrieve": "unsupported",
                "wiki_read": "unsupported",
            },
        }

    def upload_document(self, file_path: str, metadata: dict) -> KnowledgeDocument:
        raise NotImplementedError

    def get_document_status(self, external_doc_id: str) -> dict:
        raise NotImplementedError

    def retrieve(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 8,
    ) -> list[Evidence]:
        self.retrieve_calls += 1
        return []

    def search_wiki(
        self,
        query: str,
        kb_id: str | None = None,
        limit: int = 10,
    ) -> list[WikiPageSummary]:
        return []

    def read_wiki_page(
        self,
        slug: str,
        kb_id: str | None = None,
    ) -> WikiPage | None:
        self.wiki_read_calls += 1
        return None


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"M3 backend feature flags smoke failed: {exc}", file=sys.stderr)
        return 1

    print("M3 backend feature flags smoke passed")
    print(f"- schema version: {result['schema_version']}")
    print(f"- backend snapshots: {result['snapshots']}")
    print(f"- agent blocked calls: {result['agent_blocked_calls']}")
    print(f"- frontend gates: {result['frontend_gates']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    _assert_snapshots()
    _assert_api_capabilities()
    _assert_docs()
    _assert_frontend_gates()
    blocked = _assert_agent_guardrails()
    return {
        "schema_version": FEATURE_FLAG_SCHEMA_VERSION,
        "snapshots": len(BACKEND_CAPABILITY_MATRIX),
        "agent_blocked_calls": blocked,
        "frontend_gates": 3,
    }


def _assert_snapshots() -> None:
    cases = {
        "mock": backend_capability_snapshot(
            backend_name="mock",
            app_env="local",
            mock_mode=True,
            weknora_configured=False,
        ),
        "weknora_api": backend_capability_snapshot(
            backend_name="weknora_api",
            app_env="pilot",
            mock_mode=False,
            weknora_configured=True,
        ),
        "extracted": backend_capability_snapshot(
            backend_name="extracted",
            app_env="local",
            mock_mode=True,
            weknora_configured=False,
        ),
    }
    for backend, snapshot in cases.items():
        flags = snapshot.get("feature_flags")
        if not isinstance(flags, dict):
            raise SmokeError(f"{backend} missing feature_flags")
        if flags.get("schema_version") != FEATURE_FLAG_SCHEMA_VERSION:
            raise SmokeError(f"{backend} schema version mismatch")
        probes = flags.get("probes")
        if not isinstance(probes, dict) or set(probes) != set(CAPABILITY_ORDER):
            raise SmokeError(f"{backend} probes do not cover every capability")
        for capability, status in BACKEND_CAPABILITY_MATRIX[backend].items():
            probe = probes[capability]
            if probe.get("status") != status:
                raise SmokeError(f"{backend}.{capability} probe status drift")
            if probe.get("available") != (status != "unsupported"):
                raise SmokeError(f"{backend}.{capability} availability drift")
            if status == "unsupported" and probe.get("agent_policy") != "block":
                raise SmokeError(f"{backend}.{capability} unsupported not blocked")

    if cases["mock"]["feature_flags"]["ui"]["can_view_document_chunks"]:
        raise SmokeError("mock document chunks must be UI-disabled")
    if cases["mock"]["feature_flags"]["ui"]["can_create_update_publish_wiki"]:
        raise SmokeError("mock Wiki publish must be UI-disabled")
    if not cases["weknora_api"]["feature_flags"]["ui"]["can_create_update_publish_wiki"]:
        raise SmokeError("weknora_api Wiki publish should be UI-enabled")
    if not cases["weknora_api"]["feature_flags"]["agent"]["can_retrieve"]:
        raise SmokeError("weknora_api Agent retrieve should be enabled")
    if cases["extracted"]["feature_flags"]["agent"]["can_publish_wiki"]:
        raise SmokeError("extracted Agent publish must be disabled")


def _assert_api_capabilities() -> None:
    get_settings.cache_clear()
    response = api_capabilities()
    flags = response.get("feature_flags")
    if not isinstance(flags, dict):
        raise SmokeError("/api/capabilities missing feature_flags")
    if "matrix" not in response or "capabilities" not in response:
        raise SmokeError("/api/capabilities missing matrix/capabilities")
    text = repr(response)
    forbidden = ("WEKNORA_SERVICE_TOKEN", "CHAT_MODEL_API_KEY", "EMBEDDING_API_KEY")
    leaked = [value for value in forbidden if value in text]
    if leaked:
        raise SmokeError("/api/capabilities leaked sensitive names: " + ", ".join(leaked))


def _assert_docs() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    required = (
        "GET /api/capabilities",
        "feature_flags.schema_version",
        "can_debug_retrieve",
        "can_create_update_publish_wiki",
        "AgentCapabilityGuard",
        "Unsupported capabilities raise",
    )
    missing = [phrase for phrase in required if phrase not in text]
    if missing:
        raise SmokeError("feature flag doc missing required phrases: " + ", ".join(missing))


def _assert_frontend_gates() -> None:
    rag_debug = RAG_DEBUG_PATH.read_text(encoding="utf-8")
    wiki_page = WIKI_PAGE_PATH.read_text(encoding="utf-8")
    client = CLIENT_PATH.read_text(encoding="utf-8")
    for phrase in ("getCapabilities", "can_debug_retrieve", "Debug unavailable"):
        if phrase not in rag_debug:
            raise SmokeError(f"RagDebugPage missing gate: {phrase}")
    for phrase in (
        "getCapabilities",
        "can_create_update_publish_wiki",
        "can_recover_status",
        "Wiki 写入不可用",
        "状态恢复不可用",
    ):
        if phrase not in wiki_page:
            raise SmokeError(f"WikiPage missing gate: {phrase}")
    for phrase in ("BackendCapabilitiesResponse", "feature_flags", "probes"):
        if phrase not in client:
            raise SmokeError(f"client missing capability schema: {phrase}")


def _assert_agent_guardrails() -> int:
    backend = FixtureUnsupportedBackend()
    guard = AgentCapabilityGuard(backend)
    blocked = 0
    for capability in ("rag_retrieve", "wiki_read"):
        try:
            guard.require(capability)
        except AgentCapabilityError:
            blocked += 1
            continue
        raise SmokeError(f"Agent guard did not block {capability}")
    if backend.retrieve_calls or backend.wiki_read_calls:
        raise SmokeError("Agent guard called backend before blocking unsupported capability")
    return blocked


if __name__ == "__main__":
    raise SystemExit(main())
