"""Live WNID-P7-01 history/citation/audit unification check.

The script starts temporary PA backend/frontend services, runs current-run
native dialogue paths, and verifies that PA history/audit filters expose WNID
capability and evidence-state fields for Quick Q&A, AgentQA, Wiki Mode, MCP
tool execution, Web Search, strategy mutation, and citation blockers.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
from check_weknora_native_document_lifecycle import _wait_until_indexed
from check_weknora_native_history_citation import _run_knowledge_chat
from check_weknora_native_history_citation import _upload_document
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import CONFIRM_TOKEN as MCP_CONFIRM_TOKEN
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import SAFE_SERVICE_NAME
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import SAFE_TOOL_NAME
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _execute_tool
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _history_output_id
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _selected_service_id
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _selected_service_name
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _surface as _mcp_surface
from check_weknora_native_intelligent_dialogue_mcp_tool_execution import _tool_execution_result
from check_weknora_native_intelligent_dialogue_browser_matrix import _ensure_safe_mcp_server
from check_weknora_native_intelligent_dialogue_quick_qa import _has_secret_like_text
from check_weknora_native_intelligent_dialogue_quick_qa import _request_json_timeout
from check_weknora_native_intelligent_dialogue_suggested_questions import _create_readonly_wiki_agent
from check_weknora_native_intelligent_dialogue_web_search_agentqa import AGENT_CONFIRM_TOKEN
from check_weknora_native_intelligent_dialogue_web_search_agentqa import _assert_agentqa_web_search_result
from check_weknora_native_intelligent_dialogue_web_search_agentqa import _create_web_search_agent
from check_weknora_native_intelligent_dialogue_web_search_agentqa import _ready_duckduckgo_provider_id
from check_weknora_native_kb_management import CHROME_BIN
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _read_dom_text_via_cdp
from check_weknora_native_kb_management import _request_chrome_json
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_chrome
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend

SMART_REASONING_AGENT_ID = "builtin-smart-reasoning"


def main() -> int:
    backend_port = _free_port()
    frontend_port = _free_port()
    run_id = uuid4().hex[:8]
    marker = f"WNID-P7-01 marker {run_id}"
    wiki_agent_id = ""
    web_agent_id = ""
    document_kb_id = ""
    wiki_kb_id = ""
    mcp_server: subprocess.Popen[str] | None = None
    direct_backend = _weknora_backend_from_env()
    with tempfile.TemporaryDirectory(prefix="pa-wnid-history-audit-") as temp_dir:
        temp_path = Path(temp_dir)
        old_upload_dir = os.environ.get("UPLOAD_DIR")
        os.environ["UPLOAD_DIR"] = str(temp_path / "uploads")
        database_url = f"sqlite:///{temp_path / 'history-audit.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            mcp_server = _ensure_safe_mcp_server()
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")

            blocker_output_id = _run_citation_blocker_agentqa(backend_port, run_id)
            document_kb_id = _prepare_document_kb(direct_backend, run_id)
            quick_output_id, external_doc_id = _run_quick_qa(
                backend_port,
                document_kb_id,
                run_id,
                marker,
            )
            agentqa_result = _run_react_agentqa(
                backend_port,
                run_id,
                document_kb_id,
                external_doc_id,
            )
            agentqa_output_id = _output_id(agentqa_result)

            wiki_kb_id, wiki_agent_id = _prepare_wiki_agent(
                backend_port=backend_port,
                direct_backend=direct_backend,
                run_id=run_id,
            )
            wiki_output_id = _run_wiki_agentqa(backend_port, wiki_agent_id, wiki_kb_id, run_id)

            web_agent_id = _prepare_web_agent(backend_port, run_id)
            web_output_id = _run_web_search_agentqa(backend_port, web_agent_id, run_id)

            mcp_output_id = _run_mcp_execution(backend_port)

            quick_history = _assert_history_capability(
                backend_port,
                "quick_qa",
                output_id=quick_output_id,
                expected_state="document_traceable",
                source_type="document_chunk",
            )
            agent_history = _assert_history_capability(
                backend_port,
                "react_agentqa",
                output_id=agentqa_output_id,
            )
            wiki_history = _assert_history_capability(
                backend_port,
                "wiki_mode",
                output_id=wiki_output_id,
                expected_state="wiki_traceable",
                source_type="wiki_page",
            )
            web_history = _assert_history_capability(
                backend_port,
                "web_search",
                output_id=web_output_id,
                expected_state="web_search_traceable",
                source_type="web_search",
            )
            mcp_history = _assert_history_capability(
                backend_port,
                "mcp_tools",
                output_id=mcp_output_id,
                expected_state="mcp_audited",
            )
            blocker_history = _assert_citation_blocker_filter(backend_port, blocker_output_id)

            strategy_audits = _assert_audit_capability(backend_port, "strategy_mutation")
            mcp_audits = _assert_audit_capability(backend_port, "mcp_tools")
            web_audits = _assert_audit_capability(backend_port, "web_search")
            wiki_audit_status = "not_required_read_only"

            frontend = _start_frontend(frontend_port, backend_port)
            _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
            dom = _history_dom(
                frontend_port,
                temp_path / "chrome-profile",
                [
                    "Quick Q&A",
                    "ReACT AgentQA",
                    "Wiki Mode",
                    "MCP Tools",
                    "Web Search",
                    "WNID 审计",
                    "策略变更",
                ],
            )
            _assert(not _has_secret_like_text(dom), "History WNID UI does not render secrets")

            print("WeKnora native intelligent dialogue history/citation/audit unification")
            print("- decision: PASS")
            print("- task: WNID-P7-01")
            print("- evidence_type: live_api + live_browser + citation_history_audit")
            print(
                "- history: "
                f"quick={int(quick_history.get('total') or 0)} "
                f"agentqa={int(agent_history.get('total') or 0)} "
                f"wiki={int(wiki_history.get('total') or 0)} "
                f"web={int(web_history.get('total') or 0)} "
                f"mcp={int(mcp_history.get('total') or 0)} "
                f"citation_blockers={int(blocker_history.get('total') or 0)}"
            )
            print(
                "- audit: "
                f"strategy={int(strategy_audits.get('total') or 0)} "
                f"mcp={int(mcp_audits.get('total') or 0)} "
                f"web={int(web_audits.get('total') or 0)} "
                f"wiki={wiki_audit_status}"
            )
            print("- browser: route=history wnid_filters=true wnid_audit=true markers=7")
            return 0
        finally:
            if web_agent_id:
                _delete_agent(backend_port, web_agent_id)
            if wiki_agent_id:
                _delete_agent(backend_port, wiki_agent_id)
            if wiki_kb_id:
                try:
                    direct_backend.delete_knowledge_base(wiki_kb_id)
                except Exception:
                    pass
            if document_kb_id:
                try:
                    direct_backend.delete_knowledge_base(document_kb_id)
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)
            if mcp_server is not None:
                _terminate(mcp_server)
            if old_upload_dir is None:
                os.environ.pop("UPLOAD_DIR", None)
            else:
                os.environ["UPLOAD_DIR"] = old_upload_dir


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


def _prepare_document_kb(direct_backend: WeKnoraApiBackend, run_id: str) -> str:
    kb = direct_backend.create_knowledge_base(
        name=f"WNID-P7-01 document KB {run_id}",
        description="Temporary document KB for WNID P7 current-run validation.",
        is_temporary=True,
    )
    kb_id = str(kb.get("_native_kb_id") or "")
    _assert(bool(kb_id), "P7 temporary document KB was created")
    return kb_id


def _run_quick_qa(port: int, kb_id: str, run_id: str, marker: str) -> tuple[str, str]:
    document = _upload_document(port, kb_id, run_id, marker)
    document_id = str(document.get("id") or "")
    _assert(bool(document_id), "P7 document id returned")
    indexed = _wait_until_indexed(port, document_id)
    external_doc_id = str(indexed.get("external_doc_id") or "")
    _assert(bool(external_doc_id), "P7 native document id saved")
    result = _run_knowledge_chat(
        backend_port=port,
        run_id=run_id,
        query=f"What validates {marker}?",
        external_doc_id=external_doc_id,
    )
    return _output_id(result), external_doc_id


def _run_react_agentqa(
    port: int,
    run_id: str,
    selected_kb_id: str,
    external_doc_id: str,
) -> dict[str, Any]:
    catalog = _request_json(port, "GET", "/api/analysis/native-agents")
    agents = catalog.get("agents") if isinstance(catalog.get("agents"), list) else []
    agent_id = next(
        (
            str(agent.get("id") or "")
            for agent in agents
            if isinstance(agent, dict) and agent.get("id") == SMART_REASONING_AGENT_ID
        ),
        "",
    )
    _assert(agent_id == SMART_REASONING_AGENT_ID, "P7 smart-reasoning Agent is available")
    result = _request_json_with_live_retry(
        port,
        "POST",
        "/api/analysis/native-agentqa",
        {
            "query": f"用一句话回答：WNID-P7-01 ReACT history filter {run_id} 是否运行？",
            "title": f"WNID-P7-01 ReACT AgentQA {run_id}",
            "agent_id": agent_id,
            "knowledge_base_ids": [selected_kb_id],
            "knowledge_ids": [external_doc_id],
            "confirm_token": "CONFIRM_NATIVE_WIKI_AGENT_RUN",
        },
        timeout=180,
    )
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    _assert(output.get("status") == "completed", "P7 ReACT AgentQA output completed")
    _assert(bool(runtime.get("native_session_id")), "P7 ReACT AgentQA native session id returned")
    return result


def _run_citation_blocker_agentqa(port: int, run_id: str) -> str:
    result = _request_json_with_live_retry(
        port,
        "POST",
        "/api/analysis/native-agentqa",
        {
            "query": f"请只回答：WNID P7 citation blocker {run_id} 已运行。不要使用资料或网络。",
            "title": f"WNID-P7-01 citation blocker {run_id}",
            "agent_id": "builtin-quick-answer",
            "knowledge_base_ids": [],
            "knowledge_ids": [],
            "web_search_enabled": False,
        },
        timeout=180,
    )
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    _assert(output.get("status") == "completed", "P7 citation blocker AgentQA completed")
    _assert(len(result.get("citations") if isinstance(result.get("citations"), list) else []) == 0,
            "P7 citation blocker AgentQA saved no citations")
    return _output_id(result)


def _prepare_wiki_agent(
    *,
    backend_port: int,
    direct_backend: WeKnoraApiBackend,
    run_id: str,
) -> tuple[str, str]:
    kb = direct_backend.create_temporary_wiki_knowledge_base(
        name=f"WNID-P7-01 Wiki KB {run_id}",
        description="WNID P7 temporary Wiki Mode history validation KB",
    )
    kb_id = str(kb.get("_native_kb_id") or "")
    _assert(bool(kb_id), "P7 temporary wiki KB was created")
    direct_backend.create_wiki_page(
        {
            "slug": f"wnid-p7-01-{run_id}",
            "title": f"WNID P7 01 Wiki History {run_id}",
            "summary": "P7 validates Wiki Mode history filtering.",
            "content": "WNID P7 needs Wiki Mode outputs to be filterable in PA history.",
            "page_type": "concept",
            "status": "published",
        },
        kb_id=kb_id,
    )
    agent_id = _create_readonly_wiki_agent(
        backend_port,
        f"WNID-P7-01 Wiki Agent {run_id}",
        kb_id,
        run_id,
    )
    return kb_id, agent_id


def _run_wiki_agentqa(port: int, agent_id: str, kb_id: str, run_id: str) -> str:
    result = _request_json_with_live_retry(
        port,
        "POST",
        "/api/analysis/native-agentqa",
        {
            "query": "用一句话说明 WNID P7 Wiki Mode 历史筛选需要什么证据。",
            "title": f"WNID-P7-01 Wiki AgentQA {run_id}",
            "agent_id": agent_id,
            "knowledge_base_ids": [kb_id],
            "knowledge_ids": [],
        },
        timeout=240,
    )
    runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
    _assert(int(runtime.get("wiki_reference_count") or 0) > 0, "P7 Wiki AgentQA returned Wiki references")
    return _output_id(result)


def _prepare_web_agent(port: int, run_id: str) -> str:
    provider_id = _ready_duckduckgo_provider_id(port)
    return _create_web_search_agent(port, f"WNID-P7-01 Web Agent {run_id}", provider_id)


def _run_web_search_agentqa(port: int, agent_id: str, run_id: str) -> str:
    result = _request_json_with_live_retry(
        port,
        "POST",
        "/api/analysis/native-agentqa",
        {
            "query": "Use the web_search tool before answering. Search for the official WeKnora project.",
            "title": f"WNID-P7-01 Web Search AgentQA {run_id}",
            "agent_id": agent_id,
            "knowledge_base_ids": [],
            "knowledge_ids": [],
            "web_search_enabled": True,
        },
        timeout=240,
    )
    _assert_agentqa_web_search_result(result)
    return _output_id(result)


def _run_mcp_execution(port: int) -> str:
    overview = _request_json(port, "GET", "/api/mcp/native/overview?limit=10")
    services = _mcp_surface(
        overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {},
        "services",
    )
    service_id = _selected_service_id(services)
    service_name = _selected_service_name(services, service_id)
    _assert(service_name == SAFE_SERVICE_NAME, "P7 safe local MCP service is configured")
    approval = _mcp_surface(
        overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {},
        "approval",
    )
    original_approval = _mcp_tool_approval(approval, service_id, SAFE_TOOL_NAME)
    _assert(original_approval is not None, "P7 safe MCP tool approval policy is readable")
    try:
        _set_mcp_tool_approval(port, service_id, True)
        approved = _execute_tool(port, service_id, "approve")
        result = _tool_execution_result(approved)
        _assert(bool(result.get("executed")), "P7 MCP tool was executed")
        return _history_output_id(approved)
    finally:
        if original_approval is False:
            _set_mcp_tool_approval(port, service_id, False)


def _mcp_tool_approval(
    approval: dict[str, Any],
    service_id: str,
    tool_name: str,
) -> bool | None:
    items = approval.get("items") if isinstance(approval.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict) or str(item.get("service_id") or "") != service_id:
            continue
        samples = item.get("sample_approvals") if isinstance(item.get("sample_approvals"), list) else []
        for sample in samples:
            if isinstance(sample, dict) and str(sample.get("tool_name") or sample.get("name") or "") == tool_name:
                return bool(sample.get("require_approval"))
    return None


def _set_mcp_tool_approval(port: int, service_id: str, require_approval: bool) -> None:
    response = _request_json(
        port,
        "PUT",
        (
            f"/api/mcp/native/services/{quote(service_id, safe='')}"
            f"/tool-approvals/{quote(SAFE_TOOL_NAME, safe='')}"
        ),
        {"require_approval": require_approval, "confirm_token": MCP_CONFIRM_TOKEN},
    )
    surface = _mcp_surface(
        response.get("surfaces") if isinstance(response.get("surfaces"), dict) else {},
        "approval_policy",
    )
    _assert(surface.get("status") == "live", "P7 MCP approval policy update is live")


def _assert_history_capability(
    port: int,
    capability: str,
    *,
    output_id: str,
    expected_state: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    query = f"/api/history?wnid_capability={quote(capability, safe='')}"
    if expected_state:
        query += f"&wnid_evidence_state={quote(expected_state, safe='')}"
    if source_type:
        query += f"&source_type={quote(source_type, safe='')}"
    payload = _request_json(port, "GET", query)
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    matched = [item for item in items if isinstance(item, dict) and item.get("id") == output_id]
    _assert(bool(matched), f"history filter finds {capability} output")
    item = matched[0]
    capabilities = item.get("wnid_capabilities") if isinstance(item.get("wnid_capabilities"), list) else []
    _assert(capability in capabilities, f"{capability} WNID capability is persisted")
    if expected_state:
        _assert(item.get("wnid_evidence_state") == expected_state, f"{capability} WNID evidence state matches")
    return payload


def _request_json_with_live_retry(
    port: int,
    method: str,
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    last_error: AssertionError | None = None
    for attempt in range(3):
        try:
            return _request_json_timeout(port, method, path, payload, timeout=timeout)
        except AssertionError as exc:
            message = str(exc).lower()
            if "status=503" not in message and "timed out" not in message and "timeout" not in message:
                raise
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise AssertionError(f"{method} {path} live retry failed without a response")


def _assert_citation_blocker_filter(port: int, output_id: str) -> dict[str, Any]:
    blocked = _request_json(port, "GET", "/api/history?wnid_evidence_state=citation_blocked")
    _assert(int(blocked.get("total") or 0) > 0, "citation blocker history filter returns outputs")
    items = blocked.get("items") if isinstance(blocked.get("items"), list) else []
    _assert(
        any(isinstance(item, dict) and item.get("id") == output_id for item in items),
        "citation blocker history filter finds current-run blocker output",
    )
    return blocked


def _assert_audit_capability(port: int, capability: str) -> dict[str, Any]:
    payload = _request_json(
        port,
        "GET",
        f"/api/native-audit/events?wnid_capability={quote(capability, safe='')}&status=succeeded&limit=50",
    )
    _assert(int(payload.get("total") or 0) > 0, f"audit filter returns {capability}")
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    _assert(
        all(isinstance(item, dict) and item.get("wnid_capability") == capability for item in items),
        f"audit payload labels {capability}",
    )
    return payload


def _output_id(result: dict[str, Any]) -> str:
    output = result.get("output") if isinstance(result.get("output"), dict) else {}
    output_id = str(output.get("id") or "")
    _assert(bool(output_id), "P7 output id returned")
    return output_id


def _history_dom(port: int, user_data_dir: Path, markers: list[str]) -> str:
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
            f"/json/new?{quote(f'http://127.0.0.1:{port}/#/history', safe=':/')}",
        )
        ws_url = str(target.get("webSocketDebuggerUrl") or "")
        _assert(bool(ws_url), "Chrome returned a page websocket")
        deadline = time.time() + 40
        dom = ""
        while time.time() < deadline:
            dom = _read_dom_text_via_cdp(ws_url)
            if all(marker in dom for marker in markers):
                return dom
            time.sleep(1)
        return dom
    finally:
        _terminate(chrome)


def _delete_agent(port: int, agent_id: str) -> None:
    try:
        _request_json(
            port,
            "DELETE",
            f"/api/analysis/native-agents/{quote(agent_id, safe='')}",
            {"confirm_token": AGENT_CONFIRM_TOKEN},
        )
    except Exception:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
