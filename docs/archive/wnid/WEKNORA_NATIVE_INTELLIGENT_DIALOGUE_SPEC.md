# PA WeKnora Native Intelligent Dialogue Spec

> Date: 2026-06-25
>
> Branch: `weknora-first-mvp`
>
> Stage: WeKnora Native Intelligent Dialogue
>
> Task prefix: `WNID-*`
>
> Previous stage source: `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`

## 1. Stage Positioning

WNID is a new post-WNFC stage. It does not rewrite the WNFC conclusion that PA
reached scoped local productivity completion with Web Search excluded. Instead,
WNID reopens the exact WeKnora README **Intelligent Conversation** surface and
makes it a first-class PA product workflow.

The target is the full intelligent dialogue board:

| Capability | WNID product meaning |
| --- | --- |
| Intelligent Reasoning | Native ReACT multi-step AgentQA runs from PA, using knowledge retrieval, MCP tools, Web Search, and custom Agents when configured. |
| Quick Q&A | Native knowledge-chat/RAG answers from selected knowledge bases with traceable document/Wiki citations. |
| Wiki Mode | Native Wiki-capable Agent workflow can generate, maintain, and reference structured Markdown Wiki pages. |
| Tool Calling | Built-in tools, MCP tools, and Web Search are visible in the dialogue trace and validated with live execution evidence. |
| Conversation Strategy | PA can edit native custom Agent prompt, context template, tool selection, web search, MCP selection, multi-turn, and retrieval thresholds online. |
| Suggested Questions | PA exposes native suggested questions based on the active Agent and knowledge scope, and can launch them into live dialogue. |

## 2. Goals And Non-Goals

### Goals

- Create a spec-driven `WNID-*` stage for future intelligent dialogue work.
- Preserve PA as an independent product shell and BFF that reuses WeKnora native
  Agent, chat, Wiki, MCP, Web Search, prompt, and retrieval capabilities.
- Make Web Search a final PASS requirement for WNID. A provider must be
  configured/tested and a native AgentQA run must prove web-search tool use.
- Make MCP tool execution a final PASS requirement for WNID. At least one safe
  MCP tool must prove list/read, approval policy, approval/denial handling,
  execution, audit, and history evidence.
- Require conversation strategy editing through native custom Agent config:
  `system_prompt`, `context_template`, `allowed_tools`, `mcp_selection_mode`,
  `mcp_services`, `web_search_enabled`, `web_search_provider_id`,
  `web_fetch_enabled`, `web_fetch_top_n`, `multi_turn_enabled`,
  `history_turns`, `embedding_top_k`, `keyword_threshold`,
  `vector_threshold`, `rerank_top_k`, `rerank_threshold`, and
  `suggested_prompts`.
- Keep document/Wiki citations, Web Search references, MCP execution records,
  and PA audit/history separate and truthful.

### Non-Goals

- Do not expand this stage into IM channels, SaaS tenant/org management,
  WeKnora Cloud, or unrelated admin surfaces.
- Do not rebuild a PA-owned general Agent, RAG, Wiki, MCP, or Web Search engine
  when WeKnora has the native path.
- Do not count mock providers, fixture-only tests, static pages, old reports,
  cached browser output, hidden fallbacks, or untraceable answer text as PASS.
- Do not print or persist raw prompts, raw provider payloads, raw web pages,
  credentials, service tokens, API keys, private endpoints, local DB contents,
  uploads, logs, caches, or raw vector/chunk bodies.

## 3. Architecture Rules

WNID inherits the `PA-first + controlled native exception lane` rule:

| Decision path | Use when | Required result |
| --- | --- | --- |
| `PA-first` | WeKnora already exposes the needed route, event, field, config, reference, tool, provider, or execution path. | PA adapter/BFF/UI/history/audit/citation uses the native capability without duplicating platform logic. |
| `native exception` | WeKnora lacks a required field, event, reference shape, prompt/config route, MCP execution surface, Web Search evidence shape, or safe API. | Make the smallest native Go change, test it, deploy it locally, and prove it through PA live evidence. |
| `blocked` | The gap is a missing provider key, MCP service, OAuth scope, workspace, account, approval, permission, or sample data. | Record the exact blocker and ask for the missing item. No mock/demo replacement can pass. |

PA owns:

- the intelligent dialogue product page and workflow ergonomics;
- BFF normalization, masked status, timeouts, trace ids, and safe errors;
- PA conversation/history/output/citation persistence;
- `NativeMutationAudit` and explicit confirmation for mutations/external runs;
- browser matrix, acceptance harness, final report, and handoff prompt.

WeKnora owns:

- native knowledge-chat and AgentQA/ReACT orchestration;
- built-in tools, Wiki tools, MCP tools, Web Search tools, and tool approval;
- custom Agent config, prompt/context templates, retrieval thresholds, and
  suggested prompts/questions;
- knowledge retrieval, Wiki, MCP, Web Search provider, model, rerank, parser,
  vector, and connector internals.

## 4. Completion States

Use these states in WNID reports and task rows:

| State | Score | Meaning |
| --- | ---: | --- |
| `complete` | 1.0 | Real PA workflow uses real WeKnora native capability with required live API/browser/history/citation/audit evidence. |
| `partial` | 0.5 | Real native calls work but a required workflow, reference, audit, browser, provider, or execution contract is incomplete. |
| `visibility-only` | 0.25 | PA can inspect status/list/catalog, but cannot run the user workflow. |
| `blocked` | 0 | A real API, credential, service, provider, runtime, safety, or native-source gap blocks completion. |
| `removed` | N/A | User explicitly removes the slice from WNID scope. Web Search and MCP execution must not be removed unless the user explicitly changes the final WNID goal. |

Final WNID PASS requires every in-scope capability group below to be
`complete`:

| Capability group | Baseline signal | WNID target | Hard evidence |
| --- | --- | --- | --- |
| Intelligent dialogue shell | Analysis page has a native AgentQA panel | `complete` | Browser-validated first-class dialogue UI with Agent, strategy, tools, citations, and history visible. |
| Quick Q&A | Native knowledge-chat/RAG already live in earlier stages | `complete` | Live knowledge-chat or RAG answer with traceable document/Wiki citations from selected KB scope. |
| ReACT/custom Agent reasoning | AgentQA and custom Agent admin are live, but strategy UI is incomplete | `complete` | Native ReACT run with thinking/tool events, selected custom Agent, and PA history/citations. |
| Wiki Mode | Native Wiki workflows and Wiki Agent references are live | `complete` | Wiki-capable Agent creates/maintains/references Markdown Wiki pages with locatable Wiki citations. |
| Built-in tool calling | Native Agent tools are present | `complete` | Dialogue trace exposes built-in tool call/result events without treating tool text as citations. |
| MCP tool calling | MCP CRUD exists; tools/resources/prompts/execution were previously removed from WNFC | `complete` | Live safe MCP service lists tools/resources/prompts, executes at least one tool with approval/audit/history. |
| Web Search | Provider management is live-partial; WNFC excluded it | `complete` | Saved or raw provider test passes, AgentQA web search runs, and references include provider/url/title/snippet/rank. |
| Conversation strategy | Native custom Agent config supports prompt/tool/retrieval fields | `complete` | PA can edit and persist prompt, context, tools, MCP, web, multi-turn, and retrieval thresholds with audit. |
| Suggested questions | Native agent suggested questions endpoint exists | `complete` | PA lists native suggested questions for active scope and can launch one into a live answer. |
| History/citation/audit | PA history/citation/audit exists | `complete` | New dialogue runs save traceable citations, tool events, web evidence, MCP audits, and strategy mutation audits. |

## 5. Execution Protocol

Every WNID run must:

1. Work in `/Users/mac/Downloads/WeKnora-main/pa-ai-workbench`.
2. Read this spec.
3. Read `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md`.
4. Read `docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md`.
5. Read `.github/skills/pa-weknora-native-intelligent-dialogue/SKILL.md`.
6. Read `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-intelligent-dialogue/SKILL.md` when available.
7. Run `git status -sb` and `git log --oneline -5`.
8. Execute exactly one `WNID-*` task id per run.
9. Before editing, state in Chinese:
   - task id;
   - task type;
   - planned files;
   - validation method;
   - expected PASS evidence type.
10. For native capability tasks, inspect WeKnora routes, handlers, services,
    types, and client structs before PA changes.
11. Update task status only after validation passes or a real blocker is
    recorded.
12. Stage only current-task files with explicit paths.

Task types:

- WeKnora native Agent capability接入
- PA BFF/business DB/history/citation/audit
- PA intelligent dialogue product shell
- MCP/Web Search credential/approval/security foundation
- validation/ops/deployment
- native-source patch/runtime validation

## 6. Required Evidence

| Evidence type | Required when |
| --- | --- |
| Native source audit | Every native Agent, MCP, Web Search, Wiki, prompt/config, or strategy task before PA edits. |
| Live API smoke | Every backend/BFF/native task. |
| Live browser proof | Every user-visible dialogue workflow. |
| Native Go test | Every native Go source change. |
| Docker runtime validation | Every native runtime behavior change that must affect live WeKnora. |
| Credential masking proof | Every provider, MCP, web search, model, or config task. |
| Confirmation/audit proof | Every mutation, external test, MCP execution, Web Search provider test, or strategy edit. |
| Citation proof | Every answer-producing workflow where document/Wiki/Web evidence is part of the contract. |
| Sensitive scan | Every spec/skill/report/provider/config task. |

Evidence boundaries:

- Document/Wiki citations must be locatable through PA.
- Web Search PASS needs provider identity plus URL/title/snippet/rank or an
  equivalent native reference shape. Web status alone is not answer evidence.
- MCP PASS needs service id/name, tool name, approval requirement, approval or
  denial result, execution summary, timeout/error class, audit id, and history
  visibility. Tool result text alone is not citation evidence.
- Built-in Agent tool events can prove tool use, but only native references can
  prove factual citation.
- Raw prompts and raw provider payloads must never appear in reports or logs.

## 7. Task Board

| Task id | Phase | Title | Status | Acceptance |
| --- | --- | --- | --- | --- |
| WNID-0-01 | Governance | Intelligent dialogue spec and skill | [x] | This spec plus repo-local and outer skills exist; skill validation, diff check, keyword checks, and sensitive scan pass. |
| WNID-0-02 | Governance | Native intelligent dialogue parity map | [x] | Audit/map complete in [WNID-0-02 parity map](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md); maps README Intelligent Conversation rows to WeKnora routes/services/types/client fields and current PA surfaces; no capability PASS from map alone. |
| WNID-0-03 | Governance | WNID acceptance harness | [x] | Checker and [WNID-0-03 harness report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md) enforce Web Search in-scope, MCP execution in-scope, current-run evidence, no unsafe PASS wording, and final readiness truth. |
| WNID-P1-01 | P1 | First-class intelligent dialogue shell | [x] | PA exposes a main `#/dialogue` workspace, not a hidden advanced panel, with Agent picker, run controls, strategy summary, tool trace, citations, and history. See [WNID-P1-01 shell report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SHELL_WNID_P1_01.md). |
| WNID-P1-02 | P1 | Quick Q&A live path | [x] | Native knowledge-chat/RAG launches from the dialogue shell and saves traceable citations in PA history. See [WNID-P1-02 Quick Q&A report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_QUICK_QA_WNID_P1_02.md). |
| WNID-P2-01 | P2 | ReACT/custom Agent strategy editor | [x] | PA can view/edit native custom Agent prompt, context template, allowed tools, KB scope, multi-turn, and retrieval thresholds with confirmation/audit where needed. See [WNID-P2-01 strategy editor report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_STRATEGY_EDITOR_WNID_P2_01.md). |
| WNID-P2-02 | P2 | ReACT reasoning trace and run contract | [x] | Native AgentQA run exposes thinking/tool/reference/answer events, selected Agent config, and PA conversation continuity. See [WNID-P2-02 ReACT contract report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_REACT_CONTRACT_WNID_P2_02.md). |
| WNID-P3-01 | P3 | MCP tools/resources/prompts read path | [x] | Safe local MCP service is configured through confirmed PA native mutation; live native confirmed test returns `tools=1 resources=1`; prompt parity remains recorded as `native_mcp_prompt_api_missing`. See [WNID-P3-01 MCP read path report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_READ_PATH_WNID_P3_01.md). |
| WNID-P3-02 | P3 | MCP approval-gated tool execution | [x] | Safe local MCP `ping` tool is approval-gated through native policy; PA proves rejected and approved execution with audit/history and masked browser evidence. See [WNID-P3-02 MCP execution report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_TOOL_EXECUTION_WNID_P3_02.md). |
| WNID-P3-03 | P3 | MCP prompt parity decision | [x] | Native MCP prompt list/read support is added and live-proven through `PA Safe Local MCP` prompt `pa-safe-summary`; prior `native_mcp_prompt_api_missing` blocker is resolved. See [WNID-P3-03 MCP prompt parity report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_PROMPT_PARITY_WNID_P3_03.md). |
| WNID-P4-01 | P4 | Web Search provider setup and test | [x] | PA supports confirmed masked provider create/update/delete, credential update/clear, raw/saved test, and audit; live DuckDuckGo saved-provider test passes. See [WNID-P4-01 Web Search provider report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WEB_SEARCH_PROVIDER_SETUP_WNID_P4_01.md). |
| WNID-P4-02 | P4 | AgentQA Web Search run | [x] | Native AgentQA with `web_search_enabled=true` calls Web Search and returns traceable web references. See [WNID-P4-02 AgentQA Web Search report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WEB_SEARCH_AGENTQA_WNID_P4_02.md). |
| WNID-P5-01 | P5 | Wiki Mode Agent workflow | [x] | Wiki-capable Agent generates/maintains/references Wiki pages with locatable Wiki citations and safe mutation controls. See [WNID-P5-01 Wiki Mode Agent workflow report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WIKI_MODE_AGENT_WORKFLOW_WNID_P5_01.md). |
| WNID-P6-01 | P6 | Suggested questions workflow | [x] | Native suggested questions list for active Agent/KB scope and at least one suggestion launches into a live answer. See [WNID-P6-01 Suggested Questions report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SUGGESTED_QUESTIONS_WNID_P6_01.md). |
| WNID-P7-01 | P7 | Dialogue history, citation, and audit unification | [x] | New Agent, quick Q&A, Wiki, MCP, Web Search, and strategy mutation outputs are filterable in PA history/audit with truthful evidence states. See [WNID-P7-01 history/citation/audit report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_HISTORY_CITATION_AUDIT_UNIFICATION_WNID_P7_01.md). |
| WNID-P8-01 | P8 | Intelligent dialogue browser matrix | [x] | Desktop/mobile browser matrix proves dialogue shell, strategy editor, tool trace, MCP/Web Search status, citations, and suggested questions. See [WNID-P8-01 browser matrix report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_BROWSER_MATRIX_WNID_P8_01.md). |
| WNID-P8-02 | P8 | Final WNID PASS report | [x] | [Final WNID PASS report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md) and acceptance harness prove every in-scope README Intelligent Conversation row is complete with current-run evidence. |

## 8. Progress Log

| Date | Task | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 2026-06-25 | WNID-0-01 | [x] | Governance artifact: this spec plus repo-local and outer WNID skills. | Establishes WNID as a new post-WNFC stage, keeps WNFC completion intact, reopens Web Search as a hard gate, makes MCP tool execution a hard gate, and defines one-task-at-a-time progress rules. |
| 2026-06-25 | WNID-0-02 | [x] | Audit/map: [WNID-0-02 parity map](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md). | Maps all six README Intelligent Conversation rows to native WeKnora routes/handlers/services/types/client fields and current PA adapter/BFF/UI/check surfaces. Records partial/blocker states for first-class dialogue shell, MCP execution, Web Search provider/reference proof, strategy editor, Wiki Mode dialogue flow, suggested-question launch, and unified history/citation/audit. No product code was implemented and no final capability PASS is claimed from the map. |
| 2026-06-25 | WNID-0-03 | [x] | Checker execution evidence: [WNID-0-03 harness report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py`. | Adds the WNID acceptance checker. Normal mode verifies governance guardrails and reports `final_ready=false`; final mode is expected to fail until later WNID tasks complete Web Search, MCP execution, browser matrix, final report, and current-run evidence. |
| 2026-06-25 | WNID-P1-01 | [x] | Live API/browser evidence: [WNID-P1-01 shell report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SHELL_WNID_P1_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_shell.py`. | Adds first-class `#/dialogue` shell with Agent picker, AgentQA run controls, KB/knowledge scope fields, suggested-question chips, message history, strategy summary, tool trace, and citations. Current-run checker starts temporary PA backend/frontend services, validates native Agent catalog `agents=4 catalog_status=live`, opens `#/dialogue` in headless Chrome, and proves the shell is not hidden behind the Analysis advanced panel. |
| 2026-06-25 | WNID-P1-02 | [x] | Live API/browser evidence: [WNID-P1-02 Quick Q&A report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_QUICK_QA_WNID_P1_02.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_quick_qa.py`. | Adds AgentQA / Quick Q&A mode switching to `#/dialogue` and launches native knowledge-chat through PA. Current-run checker uploads a sanitized document, waits for native indexing, runs knowledge-chat with `references=2`, verifies `saved_citations=2`, confirms PA history lists `native_knowledge_chat`, opens the dialogue shell in Chrome, switches to Quick Q&A, and proves RAG Trace/Citations/Messages markers are visible without using a hidden advanced panel. |
| 2026-06-25 | WNID-P2-01 | [x] | Live API/browser/audit evidence: [WNID-P2-01 strategy editor report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_STRATEGY_EDITOR_WNID_P2_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_strategy_editor.py`. | Adds a confirmation-gated strategy editor to `#/dialogue`, returns safe native Agent strategy config through the catalog, and exposes `PUT /api/analysis/native-agents/{agent_id}/strategy`. Current-run checker creates an isolated custom Agent, proves bad-token blocking, persists 14 strategy fields through native `PUT /api/v1/agents/{id}`, verifies `NativeMutationAudit`, validates catalog readback, proves browser strategy-editor markers, and deletes the temporary Agent. |
| 2026-06-25 | WNID-P2-02 | [x] | Live API/browser evidence: [WNID-P2-02 ReACT contract report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_REACT_CONTRACT_WNID_P2_02.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_react_contract.py`. | Adds a structured AgentQA run contract from native stream events to PA runtime/output/message metadata and the `#/dialogue` Tool Trace panel. Current-run checker uploads a sanitized document, runs native AgentQA with current native document scope, verifies thinking/tool_call/tool_result/answer/complete events, selected Agent summary, PA conversation continuity, saved citations, history, and browser-visible Run Contract markers. |
| 2026-06-25 | WNID-P3-01 | [x] | Native Go test + Docker runtime + live service/API/browser evidence: [WNID-P3-01 MCP read path report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_READ_PATH_WNID_P3_01.md), `backend/scripts/configure_safe_local_mcp.py`, and `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_read_path.py`. | Adds a controlled native MCP URL SSRF exception via exact `WEKNORA_MCP_SSRF_ALLOWLIST`, configures `PA Safe Local MCP` through confirmed PA native mutation, cleans up the old temporary MCP service via confirmed delete, and revalidates `#/dialogue` MCP Read Path. Current-run checker reports `services=1 selected=PA Safe Local MCP detail=live confirmed_test=live success=true tools=1 resources=1 approval=live`; prompts remain blocked by `native_mcp_prompt_api_missing` and are carried to `WNID-P3-03`. |
| 2026-06-25 | WNID-P3-02 | [x] | Native Go test + Docker runtime + live service/API/browser/audit/history evidence: [WNID-P3-02 MCP execution report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_TOOL_EXECUTION_WNID_P3_02.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_tool_execution.py`. | Adds a minimal native direct MCP execution endpoint backed by the existing native MCP client and approval policy, plus PA confirmation, audit, history, API client, and `#/dialogue` execution panel. Current-run checker sets approval policy for `PA Safe Local MCP` `ping`, proves `reject=rejected` and `approve=executed`, records `audits=2 history=2`, and validates browser-visible MCP execution markers. MCP prompt parity remains `WNID-P3-03`; Web Search remains open. |
| 2026-06-25 | WNID-P3-03 | [x] | Native Go test + Docker runtime + live service/API/browser evidence: [WNID-P3-03 MCP prompt parity report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_MCP_PROMPT_PARITY_WNID_P3_03.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_prompt_parity.py`. | Adds native `prompts/list` and `prompts/get` wrappers, safe prompt message sanitization, PA confirmed prompt read, and `#/dialogue` Prompt Parity UI. Current-run checker proves `PA Safe Local MCP` prompt `pa-safe-summary` with `prompts=1 prompt_read=live messages=1`; the prior `native_mcp_prompt_api_missing` blocker is resolved. Web Search remains open. |
| 2026-06-25 | WNID-P4-01 | [x] | Native Go test + Docker runtime + live API/browser/audit evidence: [WNID-P4-01 Web Search provider report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WEB_SEARCH_PROVIDER_SETUP_WNID_P4_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_web_search_provider_setup.py`. | Adds PA confirmed native Web Search provider setup/test APIs, safe adapter wrappers, `NativeMutationAudit` records, a small native provider-update safety fix, and a `#/dialogue` Web Search Provider panel. Current-run checker proves native provider type/list surfaces, blocks a bad mutation token, reuses no-credential DuckDuckGo provider `80cc11c4-c392-4e67-a7a5-fad85cbf6451`, runs saved-provider test `live success=true`, verifies masked payloads/audit, and validates browser-visible setup markers. AgentQA Web Search answer/reference proof remains `WNID-P4-02`. |
| 2026-06-26 | WNID-P4-02 | [x] | Native Go test + Docker runtime + live API/browser/citation/history evidence: [WNID-P4-02 AgentQA Web Search report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WEB_SEARCH_AGENTQA_WNID_P4_02.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_web_search_agentqa.py`. | Adds native Web Search reference extraction from `web_search` tool results, PA `web_search` evidence/citation mapping, AgentQA runtime `web_reference_count` and `web_providers`, and browser Tool Trace markers. Current-run checker creates a temporary `smart-reasoning` Agent, enables DuckDuckGo Web Search through confirmed strategy update, runs native AgentQA with `web_search_enabled=true`, proves `tool=web_search`, `tool_call=16`, `tool_result=6`, `web_refs=25`, `citations=25`, `url_count=7`, history visibility, and browser-visible Web Search trace markers. |
| 2026-06-26 | WNID-P5-01 | [x] | Native Go test + Docker runtime + live API/browser/citation/history/audit evidence: [WNID-P5-01 Wiki Mode Agent workflow report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_WIKI_MODE_AGENT_WORKFLOW_WNID_P5_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_wiki_mode_agent.py`. | Adds native `wiki_write_page` reference emission, PA Wiki AgentQA confirmation gating, `weknora_agentqa_wiki_mode_run` audit records, Wiki citation/runtime metadata, and browser Tool Trace markers. Current-run checker creates an isolated temporary Wiki KB and temporary `smart-reasoning` Wiki Agent, proves bad-token blocking, runs confirmed create and maintain AgentQA turns, verifies `tool=wiki_write_page`, `tool_call=7`, `tool_result=3`, `wiki_refs=1`, `citations=1`, `history=2`, locatable `wiki_page` citations, audit success, and browser-visible Wiki Mode Agent markers. |
| 2026-06-26 | WNID-P6-01 | [x] | Live API/browser/citation/history evidence: [WNID-P6-01 Suggested Questions report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SUGGESTED_QUESTIONS_WNID_P6_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_suggested_questions.py`. | Adds a scoped PA BFF endpoint for native Agent suggested questions and makes `#/dialogue` suggestion chips refresh by selected Agent/KB/knowledge scope and launch real dialogue runs. Current-run checker creates an isolated temporary published Wiki page and read-only Wiki Agent, proves native suggestions `suggestions=1`, `sources=wiki:1`, launches one suggestion into AgentQA, verifies `tool_call=7`, `tool_result=3`, `wiki_refs=1`, `citations=1`, `history=1`, locatable `wiki_page` citations, and browser-visible suggested-question click markers. |
| 2026-06-26 | WNID-P7-01 | [x] | Live API/browser/citation/history/audit evidence: [WNID-P7-01 history/citation/audit report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_HISTORY_CITATION_AUDIT_UNIFICATION_WNID_P7_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_history_citation_audit.py`. | Adds computed `wnid_capability`, `wnid_capabilities`, `wnid_evidence_state`, `evidence_source_types`, and Web Search citation counts to PA history; adds WNID audit labels and filters for strategy mutation, MCP, Web Search, and Wiki Mode; exposes WNID filters and audit cards on History. Current-run checker proves `quick=1`, `agentqa=4`, `wiki=2`, `web=1`, `mcp=1`, `citation_blockers=1`, and audits `strategy=2`, `mcp=2`, `web=1`, `wiki=1` with browser-visible History markers. |
| 2026-06-26 | WNID-P8-01 | [x] | Live API/browser/service evidence: [WNID-P8-01 browser matrix report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_BROWSER_MATRIX_WNID_P8_01.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_browser_matrix.py`. | Adds desktop/mobile Chrome browser matrix validation for `#/dialogue`, backed by live native Agent catalog, scoped suggested questions, safe MCP service test, and DuckDuckGo provider test. Current-run checker proves `agents=5`, `suggestions=1`, `mcp_tools=1`, `mcp_resources=1`, `web_provider=duckduckgo`, `web_test=live`, and both `desktop 1440x900` and `mobile 390x844` render `markers=17`, `horizontal_overflow=false`, `hidden_advanced_panel=false`. Also fixes a real dialogue inspector horizontal-overflow issue by allowing page surface and trace rows to shrink. |
| 2026-06-26 | WNID-P8-02 | [x] | Checker execution + final report evidence: [WNID-P8-02 final report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_FINAL_REPORT_WNID_P8_02.md) and `backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --final`. | Closes WNID with all 17 task rows complete, no open tasks, Web Search and MCP execution still in scope, browser matrix present, final report present, and `final_ready=true`. The report maps all README Intelligent Conversation rows to current-run evidence and preserves the WNFC 100% conclusion without rewriting it. |

## 9. Task Cards

### WNID-0-01: Intelligent dialogue spec and skill

- Goal: create this spec and the paired Codex skill.
- Editable files:
  - `docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md`;
  - `.github/skills/pa-weknora-native-intelligent-dialogue/SKILL.md`;
  - `/Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-intelligent-dialogue/SKILL.md`.
- Acceptance: skill frontmatter validates, template placeholders are removed,
  Web Search is in-scope, MCP execution is in-scope, and sensitive scan passes.
- Evidence type: audit/map.

### WNID-0-02: Native intelligent dialogue parity map

- Goal: map every README Intelligent Conversation capability to native WeKnora
  and PA surfaces.
- Scope: AgentQA, custom Agent config, knowledge-chat, Wiki tools, built-in
  tools, MCP services/tools/resources/prompts/approvals, Web Search provider
  and tools, suggested questions, prompt templates, retrieval thresholds,
  multi-turn context, and PA history/citation/audit.
- Acceptance: report identifies current complete/partial/blocked state and the
  exact next WNID task for each gap. Evidence: [WNID-0-02 parity map](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_PARITY_MAP_WNID_0_02.md).

### WNID-0-03: WNID acceptance harness

- Goal: make final readiness mechanically checkable.
- Required checks: task rows, progress log, final report, Web Search in-scope,
  MCP execution in-scope, current-run evidence links, browser matrix hook,
  no mock/demo/fixture-only/stale-report PASS, no sensitive-shaped text.
- Acceptance: checker self-test passes and normal mode reports current WNID
  readiness truthfully before final mode is allowed. Evidence:
  [WNID-0-03 harness report](WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md).

### WNID-P1: Dialogue shell and quick Q&A

- Goal: make intelligent dialogue the primary PA user workflow.
- Required: main dialogue page or promoted Analysis page surface, native Agent
  picker, native knowledge-chat/RAG quick Q&A, selected KB scope, suggested
  questions entry, citations, tool trace placeholder, and history continuity.
- Acceptance: browser proof shows the workflow is visible without opening a
  hidden advanced panel.
- Current `WNID-P1-01` status: complete with live API/browser evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_shell.py`.
- Current `WNID-P1-02` status: complete with live API/browser evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_quick_qa.py`.

### WNID-P2: ReACT and conversation strategy

- Goal: expose native custom Agent strategy editing and ReACT run evidence.
- Required config fields: prompt/context templates, allowed tools, MCP
  selection, Web Search provider/fetch settings, KB scope, multi-turn/history,
  retrieval thresholds, rerank thresholds, and suggested prompts.
- Acceptance: strategy edits persist to native custom Agent config, audits are
  recorded, and a live AgentQA run uses the selected strategy.
- Current `WNID-P2-01` status: complete with live API/browser/audit evidence
  from `backend/scripts/check_weknora_native_intelligent_dialogue_strategy_editor.py`.
- Current `WNID-P2-02` status: complete with live API/browser evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_react_contract.py`.

### WNID-P3: MCP tool calling

- Goal: complete MCP tool calling instead of only MCP service management.
- Required: configured safe MCP service, tools/resources list, prompt capability
  if native API exists, approval policy, approval/denial path, at least one
  safe tool execution, timeout/error handling, audit, history.
- Blocker protocol: if no safe live MCP service/tool exists, ask for exact
  service config and expected tool; do not claim PASS from an empty service.
- Current `WNID-P3-01` status: complete for tools/resources read path with
  native Go test, Docker runtime, live service/API/browser evidence from
  `backend/scripts/configure_safe_local_mcp.py` and
  `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_read_path.py`.
- Current `WNID-P3-02` status: complete for approval-gated tool execution with
  native Go test, Docker runtime, live service/API/browser/audit/history
  evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_tool_execution.py`.
- Current `WNID-P3-03` status: complete for MCP prompt list/read parity with
  native Go test, Docker runtime, live service/API/browser evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_mcp_prompt_parity.py`.
  The prior `native_mcp_prompt_api_missing` blocker is resolved.

### WNID-P4: Web Search tool calling

- Goal: complete Web Search as a native Agent capability.
- Required: provider type/list/create/update/credential/test or exact
  credential blocker, native AgentQA run with `web_search_enabled=true`, and
  traceable web references.
- Blocker protocol: if provider credentials are unavailable, ask for provider,
  key/scope, expected config location, and post-supply validation command.
- Current `WNID-P4-01` status: complete for provider setup and saved-provider
  test with live API/browser/audit evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_web_search_provider_setup.py`.
- Current `WNID-P4-02` status: complete for native AgentQA Web Search run with
  native Go test, Docker runtime, live API/browser/citation/history evidence
  from
  `backend/scripts/check_weknora_native_intelligent_dialogue_web_search_agentqa.py`.
  A no-credential DuckDuckGo provider is configured, tested, selected by a
  temporary smart-reasoning Agent, and proven through real `web_search`
  references and PA citations.

### WNID-P5: Wiki Mode Agent workflow

- Goal: prove Wiki Mode through Agent-driven dialogue, not only Wiki admin UI.
- Required: Wiki-capable KB, Wiki Agent or custom Agent strategy, document to
  Wiki generation/maintenance, safe page mutation controls, issue/status
  visibility where applicable, and locatable Wiki citations in dialogue history.
- Current `WNID-P5-01` status: complete with native Go test, Docker runtime,
  live API/browser/citation/history/audit evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_wiki_mode_agent.py`.

### WNID-P6: Suggested questions

- Goal: make native suggested questions a working dialogue entry point.
- Required: active Agent/KB-scoped question list, source labels, empty/blocked
  states, click-to-run, and live answer evidence.
- Current `WNID-P6-01` status: complete with live API/browser/citation/history
  evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_suggested_questions.py`.

### WNID-P7: History, citation, and audit unification

- Goal: keep every native dialogue capability traceable in PA.
- Required: filters and evidence states for quick Q&A, AgentQA, Wiki Mode,
  MCP tool execution, Web Search, strategy mutation, and citation blockers.
- Current `WNID-P7-01` status: complete with live API/browser/citation/history
  and audit evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_history_citation_audit.py`.
  History outputs now expose WNID capability/evidence fields and native audits
  are filterable by WNID capability.

### WNID-P8: Final acceptance

- Goal: prove README Intelligent Conversation parity through PA.
- Required: browser matrix, acceptance harness, final report, handoff prompt,
  and explicit list of any user-removed scope. Web Search and MCP execution
  must remain in-scope unless the user explicitly changes WNID's goal.
- Current `WNID-P8-01` status: complete with live desktop/mobile browser matrix
  evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_browser_matrix.py`.
- Current `WNID-P8-02` status: complete with final report and final-mode
  acceptance evidence from
  `backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --final`.

## 10. Validation Commands For Governance Tasks

### WNID-0-01

```bash
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/pa-ai-workbench/.github/skills/pa-weknora-native-intelligent-dialogue
python3 /Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-intelligent-dialogue
git diff --check -- docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md .github/skills/pa-weknora-native-intelligent-dialogue/SKILL.md
rg -n "T[O]DO|\\[T[O]DO|BEGIN (RSA|OPENSSH|PRIVATE) KEY|[A-Za-z0-9_]*(API_KEY|SERVICE_TOKEN|PASSWORD|SECRET|AUTHORIZATION)[A-Za-z0-9_]*\\s*=" docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md .github/skills/pa-weknora-native-intelligent-dialogue/SKILL.md /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-intelligent-dialogue/SKILL.md
```

The `rg` command is expected to return no matches.

### WNID-0-03

```bash
backend/.venv/bin/python -m py_compile backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --self-test
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py --final
git diff --check -- backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md
rg -n "T[O]DO|\\[T[O]DO|BEGIN (RSA|OPENSSH|PRIVATE) KEY|[A-Za-z0-9_]*(API_KEY|SERVICE_TOKEN|PASSWORD|SECRET|AUTHORIZATION)[A-Za-z0-9_]*\\s*=" backend/scripts/check_weknora_native_intelligent_dialogue_acceptance.py docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_SPEC.md docs/WEKNORA_NATIVE_INTELLIGENT_DIALOGUE_ACCEPTANCE_HARNESS_WNID_0_03.md
```

Normal mode is expected to pass with `final_ready=false` until later WNID
capability tasks complete. `--final` is expected to fail before `WNID-P8-02`.

## 11. Safety And Commit Rules

- Keep `docs/WEKNORA_NATIVE_FULL_COMPLETION_SPEC.md` unchanged unless a later
  task explicitly needs to reference WNID as a next stage.
- Keep `docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md` untouched and unstaged.
- Do not stage `.env`, databases, logs, caches, uploads, `node_modules`,
  `dist`, screenshots, raw provider payloads, or unrelated reports.
- Do not push or merge unless the user explicitly asks.
- Do not mark Web Search or MCP execution complete from status/catalog
  visibility alone.
