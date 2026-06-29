# WNID-P6-01 Suggested Questions Workflow

Date: 2026-06-26

Task: `WNID-P6-01`

Decision: `PASS`

Evidence type: `live_api + live_browser + citation_history`

## Scope

This task proves suggested questions as a working native intelligent dialogue
entry point in PA.

Validated capability:

- PA calls WeKnora native `GET /api/v1/agents/{id}/suggested-questions`.
- Suggested questions are refreshed for the selected Agent plus active
  knowledge-base and knowledge-item scope.
- Suggested question source labels are preserved.
- A native suggested question can launch directly into live AgentQA.
- The launched dialogue saves PA history and locatable Wiki citations.
- The `#/dialogue` browser surface shows suggested-question chips and can run
  one with a click.

## Implementation Summary

- Added a scoped PA BFF endpoint:
  `GET /api/analysis/native-agents/{agent_id}/suggested-questions`.
- Added `NativeAgentSuggestedQuestionsResponse` with status, source counts,
  scope echo, sanitized questions, and surfaces.
- Updated `#/dialogue` to refresh suggested questions when Agent, KB scope, or
  knowledge scope changes.
- Suggested-question chips now launch the current AgentQA or Quick Q&A workflow
  instead of only copying text into the input.
- Added visible source-count state for suggested questions, including empty and
  blocked states.

No native Go patch was required. WeKnora already exposes the required native
handler, service, type, and client contract.

## Native Source Audit

Audited native paths:

- README Intelligent Conversation table: `Suggested Questions`.
- `internal/handler/custom_agent.go`: `GetSuggestedQuestions`.
- `internal/application/service/custom_agent.go`: `GetSuggestedQuestions`,
  including `agent_config`, `faq`, `document`, and `wiki` sources.
- `internal/types/custom_agent.go`: `SuggestedQuestion`.
- `client/agent_manage.go`: `GetSuggestedQuestions` client wrapper.

The native service returns Wiki suggestions only for published Wiki pages. The
live checker therefore creates an isolated temporary published Wiki page before
requesting suggestions.

## Live Evidence

Command:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_suggested_questions.py
```

Sanitized result:

```text
WeKnora native intelligent dialogue Suggested Questions
- decision: PASS
- task: WNID-P6-01
- evidence_type: live_api + live_browser + citation_history
- api: suggestions=1 sources=wiki:1 tool_call=7 tool_result=3 wiki_refs=1 citations=1 history=1
- launch: suggested_question_to_agentqa=live source_type=wiki_page
- browser: route=dialogue suggested_question_click=live markers=7 hidden_advanced_panel=false
```

The checker creates and deletes an isolated temporary Wiki KB and temporary
custom Agent. It does not use mock, fixture-only, stale, or cached PASS
evidence.

## Validation

- `backend/.venv/bin/python -m py_compile backend/app/api/analysis.py backend/app/services/native_agent_service.py backend/app/schemas.py backend/scripts/check_weknora_native_intelligent_dialogue_suggested_questions.py`: passed.
- Frontend `tsc --noEmit`: passed.
- Frontend `vite build`: passed.
- Live API/browser checker: passed.
- WNID acceptance normal mode: passed after this task.
- `git diff --check`: passed.
- Task-marker / secret / private-key scan: passed.

## Safety

- Raw Agent answers, raw Wiki content, credentials, local DB contents, logs, and
  private endpoints are not included.
- The report records only sanitized counts, source labels, statuses, and
  source-type evidence.

## Remaining Work

Recommended next task: `WNID-P7-01` Dialogue history, citation, and audit
unification.
