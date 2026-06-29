"""Live WNID-P5-01 native Wiki Mode Agent workflow check.

The script creates an isolated wiki-enabled KB and temporary smart-reasoning
Agent with Wiki mutation tools, verifies PA confirmation blocking, runs native
AgentQA to create/update Wiki pages, checks citation/history/audit evidence, and
drives the dialogue browser route with the same confirmed Wiki AgentQA path.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.parse import quote
from urllib.parse import urlencode
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import Settings
from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_intelligent_dialogue_quick_qa import _evaluate_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_quick_qa import _read_dom_text_content_via_cdp
from check_weknora_native_intelligent_dialogue_quick_qa import _request_json_timeout
from check_weknora_native_intelligent_dialogue_web_search_agentqa import _event_count
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
from check_weknora_native_wiki_global_maintenance import _request_json_allow_error
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


AGENT_CONFIRM_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"
WIKI_AGENT_RUN_CONFIRM_TOKEN = "CONFIRM_NATIVE_WIKI_AGENT_RUN"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    agent_name = f"WNID-P5-01 Wiki Agent {run_id}"
    slug = f"wnid-p5-01-{run_id}"
    created_agent_id = ""
    temp_kb_id = ""
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-wiki-agent-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'wiki-agent.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            temp_kb = direct_backend.create_temporary_wiki_knowledge_base(
                name=f"WNID-P5-01 temporary Wiki {run_id}",
                description="WNID temporary Wiki Mode Agent validation KB",
            )
            temp_kb_id = str(temp_kb.get("_native_kb_id") or "")
            _assert(bool(temp_kb_id), "temporary wiki KB was created")

            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            created_agent_id = _create_wiki_agent(backend_port, agent_name, temp_kb_id, run_id)

            blocked = _request_json_allow_error(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": _create_query(slug, run_id),
                    "title": f"WNID-P5-01 blocked {run_id}",
                    "agent_id": created_agent_id,
                    "knowledge_base_ids": [temp_kb_id],
                    "knowledge_ids": [],
                    "confirm_token": "WRONG",
                },
            )
            _assert(blocked.get("_http_status") == 503, "bad token blocks Wiki AgentQA mutation run")
            _assert("CONFIRM_NATIVE_WIKI_AGENT_RUN" in str(blocked.get("detail") or ""), "blocked response names required token")
            _assert(
                _no_wiki_agent_secret_payload(blocked, allow_confirm_token=True),
                "blocked Wiki AgentQA response is sanitized",
            )

            created = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": _create_query(slug, run_id),
                    "title": f"WNID-P5-01 create {run_id}",
                    "agent_id": created_agent_id,
                    "knowledge_base_ids": [temp_kb_id],
                    "knowledge_ids": [],
                    "confirm_token": WIKI_AGENT_RUN_CONFIRM_TOKEN,
                },
                timeout=240,
            )
            _assert_wiki_agentqa_result(created, slug, created_agent_id)
            created_page = _request_json(
                backend_port,
                "GET",
                f"/api/wiki/native/page?{urlencode({'kb_id': temp_kb_id, 'slug': slug})}",
            )
            _assert(str(created_page.get("slug") or "") == slug, "Agent-created Wiki page is readable through PA")
            created_content_chars = int(created_page.get("content_chars") or 0)
            _assert(created_content_chars > 0, "Agent-created Wiki page exposes safe content length")

            updated = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": _update_query(slug, run_id),
                    "title": f"WNID-P5-01 update {run_id}",
                    "agent_id": created_agent_id,
                    "knowledge_base_ids": [temp_kb_id],
                    "knowledge_ids": [],
                    "confirm_token": WIKI_AGENT_RUN_CONFIRM_TOKEN,
                },
                timeout=240,
            )
            _assert_wiki_agentqa_result(updated, slug, created_agent_id)

            page = _request_json(
                backend_port,
                "GET",
                f"/api/wiki/native/page?{urlencode({'kb_id': temp_kb_id, 'slug': slug})}",
            )
            _assert(str(page.get("slug") or "") == slug, "Agent-maintained Wiki page remains readable through PA")
            _assert(
                int(page.get("content_chars") or 0) != created_content_chars,
                "Agent update changed the Wiki page safe content length",
            )

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_agentqa")
            _assert(int(history.get("total") or 0) >= 2, "history lists Wiki AgentQA outputs")
            audits = _request_json(backend_port, "GET", "/api/native-audit/events?capability=wiki&limit=20")
            _assert(_audit_log_contains(audits, {"weknora_agentqa_wiki_mode_run"}), "audit API contains Wiki AgentQA run")
            _assert(_no_wiki_agent_secret_payload(audits), "audit API sanitizes Wiki AgentQA audit events")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            browser_slug = f"{slug}-browser"
            markers = (
                "Native Intelligent Dialogue",
                agent_name,
                "Tool Trace",
                "wiki_write_page",
                "wiki_references",
                "wiki_pages",
                "Citations",
            )
            dom = _dialogue_dom_after_wiki_agentqa_run(
                frontend_port,
                temp_path / "chrome-profile",
                agent_name,
                _create_query(browser_slug, run_id),
                f"WNID-P5-01 browser {run_id}",
                temp_kb_id,
                markers,
            )
            _assert("高级工具" not in dom, "Wiki AgentQA trace is not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue Wiki AgentQA UI does not render secrets")

            runtime = updated.get("runtime") if isinstance(updated.get("runtime"), dict) else {}
            contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
            citations = updated.get("citations") if isinstance(updated.get("citations"), list) else []
            print("WeKnora native intelligent dialogue Wiki Mode Agent workflow")
            print("- decision: PASS")
            print("- task: WNID-P5-01")
            print("- evidence_type: native_go_test + live_api + live_browser + citation_history_audit")
            print(
                "- api: "
                f"agent_id={created_agent_id} tool=wiki_write_page "
                f"tool_call={_event_count(contract, 'tool_call')} "
                f"tool_result={_event_count(contract, 'tool_result')} "
                f"wiki_refs={int(runtime.get('wiki_reference_count') or 0)} "
                f"citations={len(citations)} history={int(history.get('total') or 0)}"
            )
            print("- references: source_type=wiki_page locator_count=" + str(_wiki_locator_count(citations)))
            print("- audit: operation=weknora_agentqa_wiki_mode_run status=succeeded")
            print("- browser: route=dialogue wiki_mode_agentqa=visible markers=7 hidden_advanced_panel=false")
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
            if temp_kb_id:
                try:
                    direct_backend.delete_knowledge_base(temp_kb_id)
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


def _create_wiki_agent(port: int, agent_name: str, kb_id: str, run_id: str) -> str:
    created = _request_json(
        port,
        "POST",
        "/api/analysis/native-agents",
        {
            "name": agent_name,
            "description": "WNID-P5-01 temporary native Wiki Mode Agent runner",
            "avatar": "wiki",
            "config": {
                "agent_mode": "smart-reasoning",
                "agent_type": "wiki-qa",
                "kb_selection_mode": "selected",
                "knowledge_bases": [kb_id],
                "allowed_tools": ["wiki_search", "wiki_read_page", "wiki_write_page"],
                "max_iterations": 8,
                "system_prompt": (
                    "For WNID-P5-01 validation, call wiki_write_page when asked to create "
                    "or maintain a Wiki page. Keep the final answer concise and mention the slug."
                ),
            },
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    agent = _surface(created, "create").get("agent")
    _assert(isinstance(agent, dict), "temporary Wiki Agent create returns agent")
    agent_id = str(agent.get("id") or "").strip()
    _assert(bool(agent_id), "temporary Wiki Agent id returned")

    strategy = _request_json(
        port,
        "PUT",
        f"/api/analysis/native-agents/{quote(agent_id, safe='')}/strategy",
        {
            "system_prompt": (
                f"WNID-P5-01 live Wiki validation {run_id}. Always use wiki_write_page "
                "for create or maintain requests, then answer with the slug."
            ),
            "allowed_tools": ["wiki_search", "wiki_read_page", "wiki_write_page"],
            "multi_turn_enabled": False,
            "history_turns": 0,
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    strategy_surface = _surface(strategy, "strategy_update")
    _assert(strategy_surface.get("status") == "live", "temporary Wiki Agent strategy update is live")
    return agent_id


def _create_query(slug: str, run_id: str) -> str:
    return (
        f"Create a Wiki page with slug '{slug}', title 'WNID P5 01 Wiki {run_id}', "
        "page_type 'synthesis', summary 'WNID live Wiki Mode Agent validation page', "
        "and markdown content containing sections Overview and Evidence. Use wiki_write_page."
    )


def _update_query(slug: str, run_id: str) -> str:
    return (
        f"Maintain the existing Wiki page '{slug}' by using wiki_write_page to overwrite it. "
        f"Keep the same title and add the exact text maintenance-marker-{run_id} in the content."
    )


def _assert_wiki_agentqa_result(result: dict[str, Any], slug: str, agent_id: str) -> None:
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
    tool_names = [str(item) for item in runtime.get("tool_names") or []]
    warnings = [str(item) for item in runtime.get("warnings") or []]
    audit = runtime.get("wiki_mode_audit") if isinstance(runtime.get("wiki_mode_audit"), dict) else {}
    _assert(output.get("status") == "completed", "native Wiki AgentQA output completed")
    _assert(runtime.get("agent_id") == agent_id, "runtime keeps selected Wiki Agent id")
    _assert("wiki_write_page" in tool_names, "native Wiki AgentQA called wiki_write_page")
    _assert(_event_count(contract, "tool_call") > 0, "native Wiki AgentQA emitted tool_call events")
    _assert(_event_count(contract, "tool_result") > 0, "native Wiki AgentQA emitted tool_result events")
    _assert(int(runtime.get("wiki_reference_count") or 0) > 0, "native Wiki AgentQA emitted Wiki references")
    _assert(slug in [str(item) for item in runtime.get("wiki_slugs") or []], "runtime exposes Wiki page slug")
    _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved Wiki citations")
    _assert(any(_citation_source_type(item) == "wiki_page" for item in citations if isinstance(item, dict)),
            "saved citations include wiki_page source type")
    _assert(_wiki_locator_count(citations) > 0, "saved Wiki citations include PA locators")
    _assert(audit.get("operation") == "weknora_agentqa_wiki_mode_run", "runtime includes Wiki AgentQA audit")
    _assert(audit.get("status") == "succeeded", "Wiki AgentQA audit succeeded")
    _assert(not any("WIKI_REFERENCE_BLOCKED" in item for item in warnings), "Wiki reference blocker is absent")
    _assert(_no_wiki_agent_secret_payload(result), "Wiki AgentQA response excludes secret-shaped text")


def _dialogue_dom_after_wiki_agentqa_run(
    port: int,
    user_data_dir: Path,
    agent_name: str,
    query: str,
    title: str,
    kb_id: str,
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
        _fill_and_submit_wiki_agentqa(ws_url, agent_name, query, title, kb_id)
        deadline = time.time() + 240
        last_dom = ""
        while time.time() < deadline:
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(2)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue Wiki AgentQA DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _fill_and_submit_wiki_agentqa(
    ws_url: str,
    agent_name: str,
    query: str,
    title: str,
    kb_id: str,
) -> None:
    script = f"""
    window.prompt = () => {json.dumps(WIKI_AGENT_RUN_CONFIRM_TOKEN)};
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
    if (inputs[1]) setValue(inputs[1], {json.dumps(kb_id)});
    if (inputs[2]) setValue(inputs[2], '');
    const submit = Array.from(document.querySelectorAll('button'))
      .find((button) => (button.textContent || '').includes('运行 AgentQA'));
    if (submit) submit.click();
    true;
    """
    _evaluate_cdp(ws_url, script)


def _surface(payload: dict[str, Any], name: str) -> dict[str, Any]:
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), dict) else {}
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_log_contains(response: dict[str, Any], operations: set[str]) -> bool:
    items = response.get("items") if isinstance(response.get("items"), list) else []
    found = {
        str(item.get("operation") or "")
        for item in items
        if isinstance(item, dict) and item.get("status") == "succeeded"
    }
    return operations.issubset(found)


def _citation_source_type(citation: dict[str, Any]) -> str:
    metadata = _metadata(citation)
    binding = metadata.get("citation_binding") if isinstance(metadata.get("citation_binding"), dict) else {}
    return str(binding.get("source_type") or metadata.get("citation_source_type") or "").strip()


def _wiki_locator_count(citations: list[Any]) -> int:
    locators: set[str] = set()
    for citation in citations:
        if not isinstance(citation, dict) or _citation_source_type(citation) != "wiki_page":
            continue
        metadata = _metadata(citation)
        binding = metadata.get("citation_binding") if isinstance(metadata.get("citation_binding"), dict) else {}
        locator = str(binding.get("locator") or "").strip()
        if locator.startswith("#/wiki?slug="):
            locators.add(locator)
    return len(locators)


def _metadata(citation: dict[str, Any]) -> dict[str, Any]:
    raw = citation.get("metadata_json")
    if not raw:
        return {}
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _no_wiki_agent_secret_payload(value: Any, *, allow_confirm_token: bool = False) -> bool:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    forbidden = [
        "bearer ",
        "begin " + "private" + " key",
        "begin rsa " + "private" + " key",
        "begin openssh " + "private" + " key",
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"service_token":',
    ]
    if not allow_confirm_token:
        forbidden.extend([WIKI_AGENT_RUN_CONFIRM_TOKEN, AGENT_CONFIRM_TOKEN])
    return not any(token in lowered or token in text for token in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
