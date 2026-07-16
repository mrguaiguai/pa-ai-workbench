# WNID-P7-01 History, Citation, And Audit Unification

Date: 2026-06-26

Task: `WNID-P7-01`

Decision: `PASS`

Evidence type: `live_api + live_browser + citation_history_audit`

## Scope

This task unifies PA history, citation, and native mutation audit visibility for
WeKnora Native Intelligent Dialogue outputs. It does not change WNFC completion
claims and does not add a new dialogue engine.

Covered WNID capability filters:

| Capability | PA evidence surface |
| --- | --- |
| Quick Q&A | `/api/history?wnid_capability=quick_qa` |
| ReACT AgentQA | `/api/history?wnid_capability=react_agentqa` |
| Wiki Mode | `/api/history?wnid_capability=wiki_mode&source_type=wiki_page` |
| MCP Tools | `/api/history?wnid_capability=mcp_tools` and `/api/native-audit/events?wnid_capability=mcp_tools` |
| Web Search | `/api/history?wnid_capability=web_search&source_type=web_search` and `/api/native-audit/events?wnid_capability=web_search` |
| Strategy mutation | `/api/native-audit/events?wnid_capability=strategy_mutation` |
| Citation blocker | `/api/history?wnid_evidence_state=citation_blocked` |

## Implementation

- Added computed WNID fields to PA history output reads:
  - `wnid_capability`
  - `wnid_capabilities`
  - `wnid_evidence_state`
  - `evidence_source_types`
  - `web_search_citation_count`
- Added `wnid_capability` and `wnid_evidence_state` to native audit reads.
- Added history filters for `wnid_capability` and `wnid_evidence_state`.
- Added native audit filtering by computed `wnid_capability`.
- Updated History page filters and evidence panels to show WNID capability,
  WNID evidence state, Web Search citation counts, and recent WNID audit events.
- Added live checker:
  `backend/scripts/check_weknora_native_intelligent_dialogue_history_citation_audit.py`.

`wnid_capabilities` is intentionally a list because an AgentQA output can belong
to `react_agentqa` and also to a more specific WNID capability such as
`wiki_mode` or `web_search`.

## Live Evidence

Final checker output:

```text
WeKnora native intelligent dialogue history/citation/audit unification
- decision: PASS
- task: WNID-P7-01
- evidence_type: live_api + live_browser + citation_history_audit
- history: quick=1 agentqa=4 wiki=2 web=1 mcp=1 citation_blockers=1
- audit: strategy=2 mcp=2 web=1 wiki=1
- browser: route=history wnid_filters=true wnid_audit=true markers=7
```

The safe local MCP server was running on the approved local validation endpoint
during the final run. Before the final run, the MCP execution checker was also
revalidated:

```text
WeKnora native intelligent dialogue MCP tool execution
- decision: PASS
- task: WNID-P3-02
- evidence_type: live_service + live_api + live_browser + audit_history + native_go_test
- api: service=PA Safe Local MCP tool=ping approval_policy=live reject=rejected approve=executed approval_required=true audits=2 history=2
- history: reject_output=out_d0e4bb8672c5 approve_output=out_04c4adf6b859 task_type=native_mcp_tool_execution
- browser: route=dialogue mcp_tool_execution=visible markers=8 hidden_advanced_panel=false
```

## Validation

Passed:

```bash
backend/.venv/bin/python -m py_compile backend/app/services/history_service.py backend/app/api/history.py backend/app/services/native_audit_service.py backend/app/api/native_audit.py backend/scripts/check_weknora_native_intelligent_dialogue_history_citation_audit.py
PATH=/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH node_modules/.bin/tsc --noEmit
PATH=/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH node_modules/.bin/vite build
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_mcp_tool_execution.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_history_citation_audit.py
```

Final PASS depends on a live safe local MCP validation server for MCP execution
evidence. No credential, provider payload, raw prompt, raw web page, private key,
service token, or local database content is included in this report.
