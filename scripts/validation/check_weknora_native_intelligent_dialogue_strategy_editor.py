"""Live WNID-P2-01 native Agent strategy editor check.

The script creates an isolated custom Agent, verifies confirmation-gated
strategy updates through PA, checks NativeMutationAudit, opens `#/dialogue` in
headless Chrome, and deletes the temporary Agent. Output is sanitized to counts
and statuses only.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import quote
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_custom_agent_admin import _agent_payload
from check_weknora_native_custom_agent_admin import _audit_log_contains
from check_weknora_native_custom_agent_admin import _audit_succeeded
from check_weknora_native_custom_agent_admin import _surface
from check_weknora_native_faq_workflow import _no_raw_confirm_token
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_intelligent_dialogue_shell import _wait_for_dialogue_dom
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


CONFIRM_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    created_agent_id = ""
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-strategy-editor-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'strategy-editor.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            catalog = _request_json(backend_port, "GET", "/api/analysis/native-agents")
            _assert(catalog.get("status") in {"live", "partial"}, "native Agent catalog is reachable")
            _assert(_catalog_has_strategy(catalog), "native Agent catalog exposes safe strategy fields")
            _assert(_no_secret_payload(catalog), "Agent catalog response is sanitized")

            created = _request_json(
                backend_port,
                "POST",
                "/api/analysis/native-agents",
                {
                    **_agent_payload(run_id, "strategy"),
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(created, "weknora_agent_create"), "Agent create audit succeeded")
            created_agent = _surface(created.get("surfaces", {}), "create").get("agent")
            _assert(isinstance(created_agent, dict), "Agent create returned safe agent")
            created_agent_id = str(created_agent.get("id") or "")
            _assert(bool(created_agent_id), "created Agent id is available internally")

            blocked = _request_json(
                backend_port,
                "PUT",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}/strategy",
                {
                    "system_prompt": f"WNID P2 01 blocked prompt {run_id}",
                    "confirm_token": "WRONG",
                },
            )
            _assert(
                _surface(blocked.get("surfaces", {}), "strategy_update").get("status") == "blocked",
                "bad token blocks strategy update",
            )
            _assert(_no_secret_payload(blocked), "blocked strategy response is sanitized")

            strategy_payload = _strategy_payload(run_id)
            updated = _request_json(
                backend_port,
                "PUT",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}/strategy",
                {
                    **strategy_payload,
                    "confirm_token": CONFIRM_TOKEN,
                },
            )
            _assert(_audit_succeeded(updated, "weknora_agent_strategy_update"), "strategy update audit succeeded")
            strategy_surface = _surface(updated.get("surfaces", {}), "strategy_update")
            _assert(strategy_surface.get("status") == "live", "strategy update surface is live")
            _assert(_strategy_surface_matches(strategy_surface, strategy_payload), "strategy fields persisted")
            _assert(_no_raw_confirm_token(updated), "strategy update response hides confirm token")
            _assert(_no_secret_payload(updated), "strategy update response is sanitized")

            refreshed = _request_json(backend_port, "GET", "/api/analysis/native-agents")
            _assert(_agent_catalog_matches(refreshed, created_agent_id, strategy_payload), "catalog reflects strategy update")

            audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=custom_agent&limit=20")
            _assert(
                _audit_log_contains(audits, {"weknora_agent_create", "weknora_agent_strategy_update"}),
                "audit API contains strategy update event",
            )
            _assert(_no_raw_confirm_token(audits), "audit API hides strategy confirm token")
            _assert(_no_secret_payload(audits), "audit API sanitizes strategy event")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "Strategy",
                "system_prompt",
                "context_template",
                "allowed_tools",
                "mcp_selection_mode",
                "保存 Strategy",
            )
            dom = _wait_for_dialogue_dom(frontend_port, Path(temp_dir) / "chrome-profile", markers)
            _assert("高级工具" not in dom, "strategy editor is not hidden behind advanced tools")

            deleted = _request_json(
                backend_port,
                "DELETE",
                f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_audit_succeeded(deleted, "weknora_agent_delete"), "temporary Agent delete audit succeeded")
            created_agent_id = ""

            print("WeKnora native intelligent dialogue strategy editor")
            print("- decision: PASS")
            print("- task: WNID-P2-01")
            print("- evidence_type: live_api + live_browser + audit")
            print("- api: strategy_update=live updated_fields=14 audit=succeeded catalog=persisted")
            print("- browser: route=dialogue strategy_editor=visible markers=7 hidden_advanced_panel=false")
            print("- cleanup: temporary_agent_deleted=true")
            return 0
        finally:
            if created_agent_id:
                try:
                    direct_backend.delete_agent(created_agent_id)
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)


def _weknora_backend_from_env() -> WeKnoraApiBackend:
    settings = Settings()
    return WeKnoraApiBackend(
        base_url=settings.weknora_base_url,
        service_token=settings.weknora_service_token,
        timeout=settings.weknora_timeout_seconds,
        workspace_id=settings.weknora_workspace_id,
        default_kb_id=settings.weknora_default_kb_id,
        kb_mapping_config=settings.weknora_kb_mappings,
        kb_allow_default=settings.weknora_kb_allow_default,
    )


def _strategy_payload(run_id: str) -> dict[str, Any]:
    return {
        "system_prompt": f"WNID P2 01 sanitized strategy prompt {run_id}",
        "context_template": f"WNID P2 01 sanitized context template {run_id}",
        "allowed_tools": ["knowledge_search"],
        "mcp_selection_mode": "none",
        "mcp_services": [],
        "web_search_enabled": False,
        "web_search_provider_id": "",
        "web_fetch_enabled": False,
        "web_fetch_top_n": 2,
        "multi_turn_enabled": True,
        "history_turns": 3,
        "embedding_top_k": 6,
        "keyword_threshold": 0.12,
        "vector_threshold": 0.22,
        "rerank_top_k": 4,
        "rerank_threshold": 0.18,
        "suggested_prompts": [f"WNID P2 01 suggested prompt {run_id}"],
    }


def _catalog_has_strategy(catalog: dict[str, Any]) -> bool:
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        strategy = agent.get("strategy") if isinstance(agent.get("strategy"), dict) else {}
        if {"system_prompt", "context_template", "allowed_tools", "history_turns"}.issubset(strategy):
            return True
    return False


def _strategy_surface_matches(surface: dict[str, Any], expected: dict[str, Any]) -> bool:
    strategy = surface.get("strategy") if isinstance(surface.get("strategy"), dict) else {}
    return _strategy_matches(strategy, expected)


def _agent_catalog_matches(catalog: dict[str, Any], agent_id: str, expected: dict[str, Any]) -> bool:
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    for agent in agents:
        if not isinstance(agent, dict) or agent.get("id") != agent_id:
            continue
        strategy = agent.get("strategy") if isinstance(agent.get("strategy"), dict) else {}
        return _strategy_matches(strategy, expected)
    return False


def _strategy_matches(strategy: dict[str, Any], expected: dict[str, Any]) -> bool:
    scalar_keys = {
        "system_prompt",
        "context_template",
        "mcp_selection_mode",
        "web_search_enabled",
        "web_search_provider_id",
        "web_fetch_enabled",
        "web_fetch_top_n",
        "multi_turn_enabled",
        "history_turns",
        "embedding_top_k",
        "keyword_threshold",
        "vector_threshold",
        "rerank_top_k",
        "rerank_threshold",
    }
    for key in scalar_keys:
        if strategy.get(key) != expected.get(key):
            return False
    for key in ("allowed_tools", "mcp_services", "suggested_prompts"):
        if list(strategy.get(key) or []) != list(expected.get(key) or []):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
