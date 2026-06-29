"""Live WNID-P6-01 native suggested questions workflow check.

The script creates an isolated Wiki KB and a temporary read-only Wiki Agent,
pulls native suggested questions through PA with the active KB scope, launches
one suggestion into live AgentQA, verifies Wiki citations/history, and clicks a
suggestion chip in the `#/dialogue` browser surface.
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
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend


AGENT_CONFIRM_TOKEN = "CONFIRM_NATIVE_AGENT_MUTATION"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    agent_name = f"WNID-P6-01 Suggested Agent {run_id}"
    slug = f"wnid-p6-01-{run_id}"
    page_title = f"WNID P6 01 Suggested Questions {run_id}"
    created_agent_id = ""
    temp_kb_id = ""
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-suggested-questions-") as temp_dir:
        temp_path = Path(temp_dir)
        database_url = f"sqlite:///{temp_path / 'suggested-questions.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            temp_kb = direct_backend.create_temporary_wiki_knowledge_base(
                name=f"WNID-P6-01 temporary Wiki {run_id}",
                description="WNID temporary suggested questions validation KB",
            )
            temp_kb_id = str(temp_kb.get("_native_kb_id") or "")
            _assert(bool(temp_kb_id), "temporary wiki KB was created")
            direct_backend.create_wiki_page(
                {
                    "slug": slug,
                    "title": page_title,
                    "summary": "WNID live suggested questions validation page.",
                    "content": (
                        "This page exists only to validate native suggested questions. "
                        "It contains a concise explanation of scoped suggestion launch evidence."
                    ),
                    "page_type": "concept",
                    "status": "published",
                },
                kb_id=temp_kb_id,
            )

            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            created_agent_id = _create_readonly_wiki_agent(backend_port, agent_name, temp_kb_id, run_id)

            suggestion_response = _request_json(
                backend_port,
                "GET",
                "/api/analysis/native-agents/{agent_id}/suggested-questions?{query}".format(
                    agent_id=quote(created_agent_id, safe=""),
                    query=urlencode({"knowledge_base_ids": temp_kb_id, "limit": 6}),
                ),
            )
            question = _assert_suggestions(suggestion_response, page_title)

            launched = _request_json_timeout(
                backend_port,
                "POST",
                "/api/analysis/native-agentqa",
                {
                    "query": question,
                    "title": f"WNID-P6-01 suggestion launch {run_id}",
                    "agent_id": created_agent_id,
                    "knowledge_base_ids": [temp_kb_id],
                    "knowledge_ids": [],
                },
                timeout=240,
            )
            _assert_suggestion_launch_result(launched, created_agent_id)

            history = _request_json(backend_port, "GET", "/api/history?task_type=native_agentqa")
            _assert(int(history.get("total") or 0) > 0, "history lists launched suggested-question AgentQA output")

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            markers = (
                "Native Intelligent Dialogue",
                "Suggested Questions",
                agent_name,
                "wiki 1",
                "Tool Trace",
                "wiki_references",
                "Citations",
            )
            dom = _dialogue_dom_after_suggestion_launch(
                frontend_port,
                temp_path / "chrome-profile",
                agent_name,
                temp_kb_id,
                page_title,
                markers,
            )
            _assert("高级工具" not in dom, "suggested questions are not hidden behind advanced tools")
            _assert(not _has_secret_like_text(dom), "dialogue suggested-question UI does not render secrets")

            runtime = launched.get("runtime") if isinstance(launched.get("runtime"), dict) else {}
            citations = launched.get("citations") if isinstance(launched.get("citations"), list) else []
            contract = runtime.get("run_contract") if isinstance(runtime.get("run_contract"), dict) else {}
            print("WeKnora native intelligent dialogue Suggested Questions")
            print("- decision: PASS")
            print("- task: WNID-P6-01")
            print("- evidence_type: live_api + live_browser + citation_history")
            print(
                "- api: "
                f"agent_id={created_agent_id} suggestions={len(suggestion_response.get('questions') or [])} "
                f"sources={_source_counts_text(suggestion_response.get('source_counts'))} "
                f"tool_call={_event_count(contract, 'tool_call')} "
                f"tool_result={_event_count(contract, 'tool_result')} "
                f"wiki_refs={int(runtime.get('wiki_reference_count') or 0)} "
                f"citations={len(citations)} history={int(history.get('total') or 0)}"
            )
            print("- launch: suggested_question_to_agentqa=live source_type=wiki_page")
            print("- browser: route=dialogue suggested_question_click=live markers=7 hidden_advanced_panel=false")
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


def _create_readonly_wiki_agent(port: int, agent_name: str, kb_id: str, run_id: str) -> str:
    created = _request_json(
        port,
        "POST",
        "/api/analysis/native-agents",
        {
            "name": agent_name,
            "description": "WNID-P6-01 temporary native suggested questions runner",
            "avatar": "sparkles",
            "config": {
                "agent_mode": "smart-reasoning",
                "agent_type": "wiki-qa",
                "kb_selection_mode": "selected",
                "knowledge_bases": [kb_id],
                "allowed_tools": ["wiki_search", "wiki_read_page"],
                "max_iterations": 6,
                "system_prompt": (
                    "For WNID-P6-01 validation, answer suggested questions with native Wiki tools "
                    "and keep final answers concise."
                ),
            },
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    agent = _surface(created, "create").get("agent")
    _assert(isinstance(agent, dict), "temporary suggested-question Agent create returns agent")
    agent_id = str(agent.get("id") or "").strip()
    _assert(bool(agent_id), "temporary suggested-question Agent id returned")

    strategy = _request_json(
        port,
        "PUT",
        f"/api/analysis/native-agents/{quote(agent_id, safe='')}/strategy",
        {
            "system_prompt": (
                f"WNID-P6-01 live suggested questions validation {run_id}. "
                "Use wiki_search and wiki_read_page before answering scoped suggestions."
            ),
            "allowed_tools": ["wiki_search", "wiki_read_page"],
            "multi_turn_enabled": False,
            "history_turns": 0,
            "confirm_token": AGENT_CONFIRM_TOKEN,
        },
    )
    strategy_surface = _surface(strategy, "strategy_update")
    _assert(strategy_surface.get("status") == "live", "temporary Agent strategy update is live")
    return agent_id


def _assert_suggestions(response: dict[str, Any], page_title: str) -> str:
    _assert(response.get("status") == "live", "native suggested questions endpoint is live")
    _assert(response.get("source") == "weknora_api", "suggested questions come from WeKnora API")
    questions = response.get("questions") if isinstance(response.get("questions"), list) else []
    _assert(len(questions) > 0, "native suggested questions returned at least one item")
    source_counts = response.get("source_counts") if isinstance(response.get("source_counts"), dict) else {}
    _assert(int(source_counts.get("wiki") or 0) > 0, "suggested questions include wiki source")
    for item in questions:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if question and page_title in question:
            return question
    first = questions[0] if isinstance(questions[0], dict) else {}
    question = str(first.get("question") or "").strip()
    _assert(bool(question), "suggested question text is available")
    return question


def _assert_suggestion_launch_result(result: dict[str, Any], agent_id: str) -> None:
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    warnings = [str(item) for item in runtime.get("warnings") or []]
    _assert(output.get("status") == "completed", "suggested question launch output completed")
    _assert(runtime.get("agent_id") == agent_id, "runtime keeps selected suggested-question Agent id")
    _assert(int(runtime.get("wiki_reference_count") or 0) > 0, "suggested question launch emitted Wiki references")
    _assert(int(runtime.get("saved_citation_count") or 0) > 0, "PA saved suggested-question citations")
    _assert(any(_citation_source_type(item) == "wiki_page" for item in citations if isinstance(item, dict)),
            "saved suggested-question citations include wiki_page source type")
    _assert(_wiki_locator_count(citations) > 0, "saved suggested-question Wiki citations include PA locators")
    _assert(not any("CITATION_BLOCKED" in item for item in warnings), "suggested-question citation blocker is absent")
    _assert(_no_secret_payload(result), "suggested-question response excludes secret-shaped text")


def _dialogue_dom_after_suggestion_launch(
    port: int,
    user_data_dir: Path,
    agent_name: str,
    kb_id: str,
    page_title: str,
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
        _select_scope_and_click_suggestion(ws_url, agent_name, kb_id, page_title)
        deadline = time.time() + 240
        last_dom = ""
        while time.time() < deadline:
            last_dom = _read_dom_text_content_via_cdp(ws_url)
            if all(marker in last_dom for marker in markers):
                return last_dom
            time.sleep(2)
        missing = [marker for marker in markers if marker not in last_dom]
        raise AssertionError(f"dialogue suggested-question DOM missing markers: {', '.join(missing)}")
    finally:
        _terminate(chrome)


def _select_scope_and_click_suggestion(ws_url: str, agent_name: str, kb_id: str, page_title: str) -> None:
    setup_script = f"""
    const setValue = (element, value) => {{
      const setter = Object.getOwnPropertyDescriptor(element.__proto__, 'value').set;
      setter.call(element, value);
      element.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }};
    const agent = Array.from(document.querySelectorAll('.dialogue-agent-option'))
      .find((button) => (button.textContent || '').includes({json.dumps(agent_name)}));
    if (agent) agent.click();
    const inputs = Array.from(document.querySelectorAll('.dialogue-control-grid input'));
    if (inputs[0]) setValue(inputs[0], '');
    if (inputs[1]) setValue(inputs[1], {json.dumps(kb_id)});
    if (inputs[2]) setValue(inputs[2], '');
    true;
    """
    _evaluate_cdp(ws_url, setup_script)
    deadline = time.time() + 90
    while time.time() < deadline:
        dom = _read_dom_text_content_via_cdp(ws_url)
        if page_title in dom and "wiki" in dom:
            break
        time.sleep(1)
    click_script = f"""
    const suggestion = Array.from(document.querySelectorAll('.dialogue-suggestion-list button'))
      .find((button) => (button.textContent || '').includes({json.dumps(page_title)}));
    if (suggestion) suggestion.click();
    Boolean(suggestion);
    """
    clicked = _evaluate_cdp(ws_url, click_script)
    _assert(bool(clicked), "browser clicked a scoped suggested-question chip")


def _surface(payload: dict[str, Any], name: str) -> dict[str, Any]:
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), dict) else {}
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


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


def _source_counts_text(value: Any) -> str:
    if not isinstance(value, dict):
        return "none"
    return ",".join(f"{key}:{value[key]}" for key in sorted(value)) or "none"


def _no_secret_payload(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    forbidden = (
        AGENT_CONFIRM_TOKEN,
        "bearer ",
        "begin " + "private" + " key",
        "begin rsa " + "private" + " key",
        "begin openssh " + "private" + " key",
        '"api_key":',
        '"authorization":',
        '"password":',
        '"secret":',
        '"service_token":',
    )
    return not any(token in lowered or token in text for token in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
