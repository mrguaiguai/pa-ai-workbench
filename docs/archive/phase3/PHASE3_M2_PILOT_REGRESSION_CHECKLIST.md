# P3-M2 Pilot Regression Checklist

Use this checklist after a pilot feedback item is triaged. Each regression item
must be reproducible with sanitized data or an explicit live gate. Never store
real documents, raw WeKnora responses, `.env` values, tokens, private endpoints,
logs with secrets, uploads, databases, or long evidence excerpts in Git.

## 1. Intake Complete

- [ ] Feedback id is assigned.
- [ ] Category is one of: bug / config / data / product feedback / out-of-scope.
- [ ] Severity and owner are set.
- [ ] Environment is named without exposing private hostnames.
- [ ] Related PA ids are captured when available:
  - PA task id
  - conversation id
  - document id
  - wiki page id
  - output id
  - RAG debug trace id
  - WeKnora adapter operation id

## 2. Privacy Gate

- [ ] No API key, service token, password, or Authorization header is present.
- [ ] No `.env`, upload, database, log, dist, node_modules, or real data file is attached.
- [ ] No full user prompt, generated report, document body, chunk text, or raw WeKnora response is included.
- [ ] Excerpts are sanitized and short.
- [ ] Internal endpoint, workspace id, and KB id are replaced with descriptive placeholders.

## 3. Reproduction

- [ ] Steps start from a known route or API command.
- [ ] Inputs use sanitized fixture data or named synthetic ids.
- [ ] Expected behavior is concrete.
- [ ] Actual behavior is concrete.
- [ ] The issue can be reproduced by another engineer or is marked live-only with reason.
- [ ] A related `correlation_id`, `task_id`, or `adapter_operation_id` can be found in logs.

## 4. Classification-Specific Checks

Bug:

- [ ] Violates a PHASE3_SPEC acceptance criterion or a committed API/UI contract.
- [ ] Has a fixture smoke or targeted test plan.
- [ ] Regression fails before the fix and passes after the fix when feasible.

Config:

- [ ] Preflight or release checker can detect the issue.
- [ ] Remediation avoids printing secrets.
- [ ] Required environment variables are described by name only.

Data:

- [ ] Sanitized fixture demonstrates the parse/index/retrieve behavior.
- [ ] Unsupported or malformed input is clearly labeled.
- [ ] No real customer/person/case content is required to reproduce.

Product feedback:

- [ ] Current behavior is documented as working or ambiguous.
- [ ] Proposed UX/API/doc change is scoped.
- [ ] No workaround asks users to bypass the PA Adapter boundary.

Out-of-scope:

- [ ] Reason is tied to Phase 3 boundary, security, timeline, or product direction.
- [ ] A safe alternative or future backlog note is recorded if useful.

## 5. Regression Artifact

- [ ] Fixture smoke, unit test, docs update, or live gate is selected.
- [ ] Test name references the phase/task or feedback id.
- [ ] Verification commands are recorded.
- [ ] UI/API output is checked for redaction.
- [ ] Adapter logs are checked for context ids and no sensitive payload.
- [ ] `PHASE3_SPEC.md` task status is updated only after validation passes.

## 6. Git Safety

- [ ] `git status --short` reviewed.
- [ ] `git status --ignored --short` reviewed for `.env`, uploads, data, logs, db, dist, node_modules, and real data.
- [ ] Secret pattern grep run against changed files or staged diff.
- [ ] Commit includes only task-scoped files.
- [ ] No push unless explicitly requested.

## Example Regression Matrix

| Feedback id | Category | Artifact | Required ids | Gate |
| --- | --- | --- | --- | --- |
| `PILOT-20260610-001` | bug | fixture smoke | `trace_id`, `adapter_operation_id` | API smoke |
| `PILOT-20260610-002` | config | preflight checker | `document_id`, `adapter_operation_id` | M2 preflight |
| `PILOT-20260610-003` | product feedback | UI/doc check | `wiki_page_id`, `output_id` | frontend build |
