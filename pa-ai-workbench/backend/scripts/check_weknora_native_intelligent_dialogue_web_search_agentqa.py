"""Live WNID-P4-02 native AgentQA Web Search check.

The script starts temporary PA backend/frontend services, creates a temporary
native Agent, enables a no-credential DuckDuckGo provider through the confirmed
strategy path, runs native AgentQA with Web Search enabled, verifies web
references/citations/history, and proves the dialogue browser surface renders
the Web Search trace markers.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_intelligent_dialogue_quick_qa import _evaluate_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_quick_qa import _read_dom_text_content_via_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _request_json_timeout
from check_weknora_native_kb_management import CHROME_BIN
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_chrome_json
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_chrome
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


AGENT_CONFIRM_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"
WEB_TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER"
SAFE_PROVIDER = "duckduckgo"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    agent_name = f"WNID-P4-02 Web Search Agent {run_id}"
    query = (
        "Use the web_search tool before answering. Search for the official WeKnora "
        "project and answer with source-backed web references."
    )
    created_agent_id = ""
    with tempfile.TemporaryDirectory(prefix="pa-wnid-agentqa-web-search-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'web-search-agentqa.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            provider_id = _ready_duckduckgo_provider_id(backend_port)
            created_agent_id = _create_web_search_agent(backend_port, agent_name, provider_id)

            catalog = _request_json(backend_port, "GET", "/api/analysis/native-agents")
            selected_agent = _agent_by_id(catalog, created_agent_id)
            _assert(bool(selected_agent), "temporary Web Search Agent is listed")
            strategy = selected_agent.get("strategy") if isinstance(selected_agent.get("strategy"), dict) else {}
            _assert(bool(strategy.get("web_search_enabled")), "temporary Agent has Web Search enabled")
            _assert(strategy.get("web_search_provider_id") == provider_id, "temporary Agent uses DuckDuckGo provider")

            result = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": query,
                    "title": f"WNID-P4-02 AgentQA Web Search {run_id}",
                    "agent_id": created_agent_id,
                    "knowledge_base_ids": [],
                    "knowledge_ids": [],
                    "web_search_enabled": True,
                },
                timeout=240,
            )
            _assert_agentqa_web_search_result(result)

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_agentqa")
            _assert(int(history.get("total") or 0) > 0, "history lists native AgentQA Web Search output")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                agent_name,
                "Tool Trace",
                "web_search",
                "web_references",
                "web_providers",
                "Citations",
            )
            dom = _dialogue_dom_after_agentqa_web_search_run(
                frontend_port,
                temp_path / "chrome-profile",
                agent_name,
                query,
                f"WNID-P4-02 browser {run_id}",
                markers,
            )
            _assert("高级工具" not in dom, "AgentQA Web Search trace is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue Web Search AgentQA UI does not render secrets")

            runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
            citations = result.get("citations") if isinstance(result.get("citations"), list) else []
            contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
            provider_names = runtime.get("web_providers") if isinstance(runtime.get("web_providers"), list) else []
            print("WeKnora native intelligent dialogue AgentQA Web Search")
            print("- decision: PASS")
            print("- task: WNID-P4-02")
            print("- evidence_type: native_go_test + live_api + live_browser + citation_history")
            print(
                "- api: "
                f"agent_id={created_agent_id} tool=web_search provider={','.join(str(item) for item in provider_names)} "
                f"tool_call={_event_count(contract, 'tool_call')} "
                f"tool_result={_event_count(contract, 'tool_result')} "
                f"web_refs={int(runtime.get('web_reference_count') or 0)} "
                f"citations={len(citations)} history={int(history.get('total') or 0)}"
            )
            print("- references: source_type=web_search url_count=" + str(_web_citation_url_count(citations)))
            print("- browser: route=dialogue web_search_agentqa=visible markers=7 hidden_advanced_panel=false")
            return 0
        finally:
            if created_agent_id:
                try:
                    _request_json(
                        backend_port,
                        "DELETE",
                        f"/api/analysis/native-agents/{quote(created_agent_id, safe='')}",
                        {"confirm_token": AGENT_CONFIRM_TOKEN},
                    )
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)


def _ready_duckduckgo_provider_id(port: int) -> str:
    overview = _request_json(port, "GET", "/api/web-search/native/overview?limit=10")
    surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
    configured = surfaces.get("configured_providers") if isinstance(surfaces.get("configured_providers"), dict) else {}
    provider_id = _provider_id(configured)
    _assert(bool(provider_id), "ready DuckDuckGo provider is configured")
    test_response = _request_json(
        port,
        "POST",
        f"/api/web-search/native/providers/{quote(provider_id, safe='')}/test",
        {"confirm_token": WEB_TEST_CONFIRM_TOKEN},
    )
    test_surface = _surface(test_response, "provider_test")
    _assert(bool(test_surface.get("success")), "DuckDuckGo provider saved test succeeds")
    return provider_id


def _provider_id(configured: dict[str, Any]) -> str:
    items = configured.get("items") if isinstance(configured.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("provider") or "") == SAFE_PROVIDER:
            provider_id = str(item.get("id") or "").strip()
            if provider_id:
                return provider_id
    return ""


def _create_web_search_agent(port: int, agent_name: str, provider_id: str) -> str:
    created = _request_json(
        port,
        "POST",
        "/api/analysis/native-agents",
        {
            "name": agent_name,
            "description": "WNID-P4-02 temporary native AgentQA Web Search runner",
            "avatar": "search",
            "config": {
                "agent_mode": "smart-reasoning",
                "kb_selection_mode": "none",
                "knowledge_bases": [],
                "allowed_tools": ["web_search"],
                "max_iterations": 6,
                "web_search_max_results": 3,
                "web_search_provider_id": provider_id,
            },
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    created_agent = _surface(created, "create").get("agent")
    _assert(isinstance(created_agent, dict), "temporary Agent create returns agent")
    agent_id = str(created_agent.get("id") or "").strip()
    _assert(bool(agent_id), "temporary Agent id returned")

    strategy = _request_json(
        port,
        "PUT",
        f"/api/analysis/native-agents/{quote(agent_id, safe='')}/strategy",
        {
            "system_prompt": (
                "For this validation run, always call the web_search tool before the final answer. "
                "Use concise source-backed reasoning and preserve web references."
            ),
            "allowed_tools": ["web_search"],
            "web_search_enabled": True,
            "web_search_provider_id": provider_id,
            "web_fetch_enabled": False,
            "multi_turn_enabled": False,
            "history_turns": 0,
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    strategy_surface = _surface(strategy, "strategy_update")
    _assert(strategy_surface.get("status") == "live", "temporary Agent strategy update is live")
    return agent_id


def _surface(payload: dict[str, Any], name: str) -> dict[str, Any]:
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), dict) else {}
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _agent_by_id(catalog: dict[str, Any], agent_id: str) -> dict[str, Any]:
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    for agent in agents:
        if isinstance(agent, dict) and str(agent.get("id") or "") == agent_id:
            return agent
    return {}


def _assert_agentqa_web_search_result(result: dict[str, Any]) -> None:
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
    tool_names = runtime.get("tool_names") if isinstance(runtime.get("tool_names"), list) else []
    warnings = runtime.get("warnings") if isinstance(runtime.get("warnings"), list) else []
    _assert(output.get("status") == "completed", "native AgentQA Web Search output completed")
    _assert("web_search" in [str(item) for item in tool_names], "native AgentQA called web_search")
    _assert(_event_count(contract, "tool_call") > 0, "native AgentQA emitted tool_call events")
    _assert(_event_count(contract, "tool_result") > 0, "native AgentQA emitted tool_result events")
    _assert(int(runtime.get("reference_count") or 0) > 0, "native AgentQA emitted references")
    _assert(int(runtime.get("web_reference_count") or 0) > 0, "native AgentQA emitted Web Search references")
    _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved Web Search citations")
    _assert(any(_citation_source_type(item) == "web_search" for item in citations if isinstance(item, dict)),
            "saved citations include web_search source type")
    _assert(_web_citation_url_count(citations) > 0, "saved Web Search citations include URL locators")
    _assert(not any("WEB_SEARCH_REFERENCE_BLOCKED" in str(item) for item in warnings),
            "Web Search reference blocker is absent")
    _assert(_no_secret_payload(result), "AgentQA Web Search response excludes secret-shaped text")


def _citation_source_type(citation: dict[str, Any]) -> str:
    source_type = str(citation.get("source_type") or "").strip()
    if source_type:
        return source_type
    metadata = _metadata(citation)
    binding = metadata.get("citation_binding") if isinstance(metadata.get("citation_binding"), dict) else {}
    return str(binding.get("source_type") or metadata.get("citation_source_type") or "").strip()


def _web_citation_url_count(citations: list[Any]) -> int:
    urls: set[str] = set()
    for citation in citations:
        if not isinstance(citation, dict) or _citation_source_type(citation) != "web_search":
            continue
        metadata = _metadata(citation)
        binding = metadata.get("citation_binding") if isinstance(metadata.get("citation_binding"), dict) else {}
        url = str(binding.get("locator") or metadata.get("url") or metadata.get("weknora_url") or "").strip()
        if url:
            urls.add(url)
    return len(urls)


def _metadata(citation: dict[str, Any]) -> dict[str, Any]:
    raw = citation.get("metadata_json")
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _event_count(contract: dict[str, Any], event_type: str) -> int:
    try:
        return int(contract.get(f"{event_type}_count") or 0)
    except (TypeError, ValueError):
        return 0


def _dialogue_dom_after_agentqa_web_search_run(
    port: int,
    user_data_dir: Path,
    agent_name: str,
    query: str,
    title: str,
    markers: tuple[str, ...],
) -> str:
    if not CHROME_BIN.exists():
        raise RuntimeError("Google Chrome executable not found")
    debug_port = _free_port()
    chrome = subprocess.Popen(
        [
            str(CHROME_BIN),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            f"--user-data-dir={user_data_dir}",
            f"--remote-debugging-port={debug_port}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_for_chrome(debug_port)
        target = _request_chrome_json(
            debug_port,
            "PUT",
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/dialogue', safe=':/?=&')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        if not ws_url:
            raise RuntimeError("Chrome did not return a page websocket")
        deadline = time.time() + 60
        while time.time() < deadline:
            dom = _read_dom_text_content_via_cdp(ws_url)
            if agent_name in dom and "运行 AgentQA" in dom:
                break
            time.sleep(1)
        _fill_and_submit_web_search_agentqa(ws_url, agent_name, query, title)
        deadline = time.time() + 240
        last_dom = ""
        while time.time() < deadline:
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(2)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue AgentQA Web Search DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _fill_and_submit_web_search_agentqa(
    ws_url: str,
    agent_name: str,
    query: str,
    title: str,
) -> None:
    script = f"""
    const setValue = (element, value) => {{
      const setter = Object.getOwnPropertyDescriptor(element.__proto__, 'value').set;
      setter.call(element, value);
      element.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }};
    const agent = Array.from(document.querySelectorAll('.dialogue-agent-option'))
      .find((button) => (button.textContent || '').includes({json.dumps(agent_name)}));
    if (agent) agent.click();
    const queryArea = document.querySelector('.dialogue-query-field textarea');
    if (queryArea) setValue(queryArea, {json.dumps(query)});
    const inputs = Array.from(document.querySelectorAll('.dialogue-control-grid input'));
    if (inputs[0]) setValue(inputs[0], {json.dumps(title)});
    if (inputs[1]) setValue(inputs[1], '');
    if (inputs[2]) setValue(inputs[2], '');
    const submit = Array.from(document.querySelectorAll('button'))
      .find((button) => (button.textContent || '').includes('运行 AgentQA'));
    if (submit) submit.click();
    true;
    """
    _evaluate_cdp(ws_url, script)


def _no_secret_payload(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, default=str)
    blocked = (
        "Bearer ",
        "BEGIN " + "PRIVATE" + " KEY",
        "BEGIN RSA " + "PRIVATE" + " KEY",
        "BEGIN OPENSSH " + "PRIVATE" + " KEY",
    )
    return not any(marker in text for marker in blocked)


if __name__ == "__main__":
    raise SystemExit(main())
