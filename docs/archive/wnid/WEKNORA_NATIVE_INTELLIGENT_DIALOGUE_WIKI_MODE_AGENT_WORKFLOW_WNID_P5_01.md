# WNID-P5-01 Wiki Mode Agent Workflow

Date: 2026-06-26

Task: `WNID-P5-01`

Decision: `PASS`

Evidence type: `native_go_test + docker_runtime + live_api + live_browser + citation_history_audit`

## Scope

This task proves Wiki Mode as an Agent-driven intelligent dialogue workflow in PA.
It does not rely on Wiki admin-only CRUD evidence.

Validated capability:

- A temporary native `smart-reasoning` Wiki-capable Agent can run from PA AgentQA.
- Wiki mutation tools require `CONFIRM_NATIVE_WIKI_AGENT_RUN`.
- The Agent calls native `wiki_write_page` to create and maintain a Wiki page in an isolated temporary Wiki KB.
- Native `wiki_write_page` emits traceable `wiki_page` references.
- PA persists locatable Wiki citations, conversation history, output metadata, and `NativeMutationAudit`.
- `#/dialogue` shows the Wiki AgentQA workflow and Tool Trace markers in browser validation.

## Implementation Summary

- Native `wiki_write_page` now returns structured page identity fields:
  `knowledge_base_id`, `wiki_page_id`, `wiki_page_slug`, and `source_type=wiki_page`.
- Native Agent reference extraction now converts `wiki_write_page` tool results into `wiki_page` references.
- PA AgentQA now detects selected Agents with Wiki mutation tools and requires confirmation before running.
- PA records a `weknora_agentqa_wiki_mode_run` audit event for confirmed Wiki AgentQA mutation runs.
- PA AgentQA runtime/output/message metadata now include `wiki_reference_count`, `wiki_slugs`, `wiki_mode_mutation_required`, and `wiki_mode_audit`.
- The dialogue page prompts for the Wiki AgentQA confirmation token when the selected strategy contains Wiki mutation tools and displays `wiki_references` / `wiki_pages` in Tool Trace.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_wiki_mode_agent.py
```

Sanitized result:

```text
WeKnora native intelligent dialogue Wiki Mode Agent workflow
- decision: PASS
- task: WNID-P5-01
- evidence_type: native_go_test + live_api + live_browser + citation_history_audit
- api: tool=wiki_write_page tool_call=7 tool_result=3 wiki_refs=1 citations=1 history=2
- references: source_type=wiki_page locator_count=1
- audit: operation=weknora_agentqa_wiki_mode_run status=succeeded
- browser: route=dialogue wiki_mode_agentqa=visible markers=7 hidden_advanced_panel=false
```

The checker creates and deletes an isolated temporary Wiki KB and temporary custom Agent.
It validates a bad-token block before confirmed execution.

## Native Tests

Command:

```bash
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -v /private/tmp/pa-go-mod-cache:/go/pkg/mod -w /workspace golang:1.26.0 go test ./internal/agent -run 'TestExtractKnowledgeReferencesFromToolResult|TestExtractWikiReferencesFromToolResult|TestExtractWikiWriteReferenceFromToolResult|TestExtractWebSearchReferencesFromToolResult|TestAppendUniqueKnowledgeReferences' -count=1
```

Result:

```text
ok github.com/Tencent/WeKnora/internal/agent
```

## Runtime Validation

- `docker compose build app`: passed.
- `docker compose up -d --no-deps app`: passed.
- WeKnora health probe after restart: HTTP `200`.
- Frontend `tsc --noEmit`: passed.
- Frontend `vite build`: passed.
- Python `py_compile` for changed PA API/service/schema/checker files: passed.

## Safety

- No mock, demo, or fixture-only PASS was used.
- Raw Agent answers, raw Wiki page content, provider payloads, credentials, local DB contents, logs, and private endpoints are not included.
- The report records only sanitized counts, statuses, operation names, and source-type evidence.

## Remaining Work

Recommended next task: `WNID-P6-01` Suggested questions workflow.
