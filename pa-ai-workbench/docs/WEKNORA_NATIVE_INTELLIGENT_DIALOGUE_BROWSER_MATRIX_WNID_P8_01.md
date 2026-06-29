# WNID-P8-01 Intelligent Dialogue Browser Matrix

Date: 2026-06-26

Task: `WNID-P8-01`

Decision: `PASS`

Evidence type: `live_browser + live_api + live_service`

## Scope

This task validates the first-class PA intelligent dialogue surface across
desktop and mobile browser viewports. It does not change WNFC completion claims
and does not create new native Agent, MCP, Web Search, or Wiki orchestration.

The browser matrix covers:

- dialogue shell at `#/dialogue`;
- Agent picker and AgentQA/Quick Q&A mode controls;
- strategy summary and online strategy editor;
- Tool Trace / RAG Trace and run-contract markers;
- MCP read path, prompt parity, and execution controls;
- Web Search provider status/test controls;
- citation panel;
- native suggested-question panel and scoped KB controls;
- desktop/mobile horizontal overflow checks.

## Implementation

Added:

- `backend/scripts/check_weknora_native_intelligent_dialogue_browser_matrix.py`

Adjusted:

- `frontend/src/styles.css`

The style change fixes a real browser-matrix issue where trace rows inside the
dialogue inspector could force horizontal overflow. The fix adds shrink
constraints to the page surface and dialogue trace rows so long status values
use existing ellipsis behavior instead of widening the viewport.

## Live Evidence

Final checker output:

```text
WeKnora native intelligent dialogue browser matrix
- decision: PASS
- task: WNID-P8-01
- evidence_type: live_browser + live_api + live_service
- api: agents=5 suggestions=1 mcp_tools=1 mcp_resources=1 web_provider=duckduckgo web_test=live
- browser: viewport=desktop size=1440x900 markers=17 horizontal_overflow=false suggested_questions=panel_visible+api_live hidden_advanced_panel=false
- browser: viewport=mobile size=390x844 markers=17 horizontal_overflow=false suggested_questions=panel_visible+api_live hidden_advanced_panel=false
```

The checker creates a temporary Wiki KB and read-only Wiki Agent for scoped
native suggested questions, starts the approved safe local MCP server when it is
not already reachable, validates the safe MCP service through PA, validates the
saved DuckDuckGo Web Search provider test through PA, and opens the live
frontend in headless Chrome for both viewports.

## Validation

Passed:

```bash
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_browser_matrix.py
PATH=/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH node_modules/.bin/tsc --noEmit
PATH=/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH node_modules/.bin/vite build
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_browser_matrix.py
```

No screenshots, raw prompts, raw web pages, provider payloads, credentials,
service tokens, private keys, local database contents, uploads, logs, or cache
contents are included in this report.

## Remaining Work

`WNID-P8-02` remains open for the final WNID PASS report and final acceptance
harness run.
