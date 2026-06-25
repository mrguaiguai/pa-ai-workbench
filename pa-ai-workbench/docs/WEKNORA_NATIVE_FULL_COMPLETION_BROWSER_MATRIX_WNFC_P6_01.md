# WNFC-P6-01 Full Local Productivity Browser Matrix

> Date: 2026-06-25
>
> Task: `WNFC-P6-01`
>
> Decision: PASS
>
> Evidence type: live API + live browser + checker execution

## Scope

`WNFC-P6-01` validates that PA can be used locally as a daily knowledge-base
workbench shell while preserving truthful WNFC status. This is a validation and
product-shell task, not a native mutation task.

Validated surfaces:

- live PA status API: `/api/status`;
- live model status API: `/api/model/status`;
- live native status center: `/api/native/status`;
- native mutation audit list endpoint: `/api/native-audit/events`;
- WNFC acceptance checker in in-progress mode;
- desktop and mobile Chrome browser matrix for Home, Library, Analysis, RAG
  debug, Wiki, History, and Capability Center.

No Web Search work was performed. No native Go source was changed. No
confirmation token was required because this task performs no mutation.

## Current-Run Command

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_full_completion_browser_matrix.py
```

Sanitized output:

```text
WeKnora native full-completion local productivity browser matrix
- decision: PASS
- task: WNFC-P6-01
- evidence_type: live_api + live_browser + checker_execution
- api: native_schema=wnx-p0-02 groups=15 model_backend=openai_compatible audit_endpoint=available
- acceptance: score=14.00/14 = 100.0% final_ready=true
- browser: routes=7 viewport_checks=14
- desktop: pass=7 overflow=0 visible_overlap=0
- mobile: pass=7 overflow=0 visible_overlap=0
```

## API Evidence

The smoke starts temporary PA backend/frontend services with an isolated SQLite
database and validates live endpoints before opening the browser:

- `/api/status` exposes PA backend capabilities with `active_backend=weknora_api`;
- `/api/model/status` reports configured model status with `mock_mode=false`;
- `/api/native/status?limit=20` reports `schema_version=wnx-p0-02`,
  `source=pa_backend_bff`, `evidence_type=live_api`, `masked=true`, and
  `group_count=15`;
- native status contains explicit MCP, vector-store, and FAQ/tags/favorites/
  skills groups instead of hidden green states;
- `/api/native-audit/events?limit=1` returns the expected list shape, proving
  the audit endpoint is reachable for prior and future mutation workflows.

## Browser Evidence

The matrix opens each route in both desktop and mobile Chrome:

| Route | Desktop | Mobile | Required visible proof |
| --- | --- | --- | --- |
| Home | PASS | PASS | PA shell, WeKnora-backed status, active backend state |
| Library | PASS | PASS | KB/document work surface, active KB and upload target state |
| Analysis | PASS | PASS | analysis workflow controls and backend-backed empty state |
| RAG debug | PASS | PASS | native knowledge QA/debug controls and empty trace state |
| Wiki | PASS | PASS | native Wiki workflow surface |
| History | PASS | PASS | history and citation evidence-state surface |
| Capability Center | PASS | PASS | native status center, MCP/vector/skills status and blocker text |

Layout safety checks also passed:

- horizontal overflow: `0`;
- incoherent visible overlap: `0`;
- secret-like rendered text: `0`;
- unsafe PASS claim text: `0`.

## Acceptance Evidence

The WNFC acceptance checker runs from the matrix script and remains truthful:

```text
current score: 14.00/14 = 100.0%
final_ready: true
web_search: excluded
```

This means `WNFC-P6-01` remains complete after `WNFC-P6-02`, and the product
shell still passes the desktop/mobile browser matrix at final readiness.
Credential-bearing data-source setup and MCP tool/resource/prompt execution
gaps are explicitly `[b]` for this stage, while vector-store management, native
skill management, advanced chunk residuals, and Wiki global maintenance proof
are closed.

## Sensitive Output Boundary

The script prints only sanitized route names, counts, status labels, and
checker summaries. It does not print raw credentials, provider payloads, local
database paths, native IDs, prompts, uploaded content, logs, vectors, or
browser screenshots.

## Result

`WNFC-P6-01` is complete with live API, live browser, and checker evidence.
The task proves local product usability across the current PA workbench shell,
including explicit deferred-scope state, and reports the final WNFC score as
`14.00/14 = 100.0%`.
