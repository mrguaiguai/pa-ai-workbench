# PA Repository Live Workflow Acceptance — PAR-P4-02

## Outcome

`PAR-P4-02` is complete. The PA-first repository now exposes a canonical root
live-acceptance command, and that command passes against the existing local
non-mock WeKnora service:

```bash
make validate-live-acceptance
```

The accepted current-run evidence covers WeKnora health and native status,
document upload/indexing, knowledge RAG, Quick Q&A, ReACT AgentQA, Wiki Mode,
suggested questions, MCP tools/resources and approval-gated execution, live
DuckDuckGo Web Search, PA history/citation/audit persistence, citation blocking,
and desktop/mobile browser routes.

The existing `weknora-main` Compose project was not stopped, restarted,
rebuilt, recreated, or migrated. The checker started only temporary PA API,
Vite, Chrome, safe local MCP, and SQLite subprocesses. No commit, push, merge,
history rewrite, or branch operation was performed.

## Scope and safety boundaries

The user explicitly allowed validation subprocesses to load the application's
local `.env` in the normal way. The validation did not inspect, print, copy, or
record any environment value. Output records only configuration booleans,
counts, status labels, and masked live surfaces.

Every external mutation used a unique current-run name and a cleanup guard:

- document Quick Q&A and ReACT used a temporary document knowledge base;
- Wiki references and suggested questions used temporary Wiki knowledge bases;
- custom Wiki and Web Search Agents were deleted in `finally` blocks;
- the safe MCP `ping` approval policy was read before execution and restored
  when the test changed it;
- PA outputs, history, audit rows, uploads, and browser state used temporary
  SQLite/upload/profile directories;
- the final cleanup query found zero P7/P8 temporary knowledge bases and zero
  temporary Agents.

Real credentials, databases, user documents, uploads, logs, output, caches,
vectors, and protected personal material were not read, moved, deleted, or
staged. `pa-ai-workbench/docs/resume_project` remains untouched. Existing
staged PAR work and ignored/untracked runtime or user work remain preserved.

## Canonical command and checker ownership

Root `Makefile` adds `validate-live-acceptance`, which runs:

```text
scripts/validation/check_pa_repository_live_acceptance.py
```

The orchestrator verifies non-mock `weknora_api` configuration, the live
WeKnora `/health` endpoint, and these repository-owned gates:

1. `check_weknora_native_product_browser_matrix.py`;
2. `check_weknora_native_intelligent_dialogue_browser_matrix.py`;
3. `check_weknora_native_intelligent_dialogue_history_citation_audit.py`.

The product browser matrix was aligned with the current PA-first Chinese
navigation and the frozen analysis route. The WNID browser matrix now separates
custom-Agent suggested-question API proof from the product's intentionally
built-in-only dialogue Agent selector, waits for asynchronous KB/Agent options,
opens the current source-details drawer, and validates its visible run,
citation, and tool-process surfaces.

The history/citation/audit checker was hardened to use temporary document and
Wiki knowledge bases, restore MCP approval state, start and stop its safe MCP
helper, select `builtin-smart-reasoning` for document ReACT, use the verified
`builtin-quick-answer` no-evidence path for citation blocking, and retry only
explicit 503/timeout live failures. Read-only Wiki Mode requires history and
traceable Wiki citations but correctly does not invent a Wiki mutation audit;
strategy, MCP, and Web Search mutations retain real audit proof.

## Live service, workflow, and browser results

| Gate | Result |
| --- | --- |
| Existing WeKnora health | PASS, HTTP 200 / `ok` |
| PA configuration | PASS, `weknora_api`, non-mock, required values present |
| Native status | PASS, schema `wnx-p0-02`, 15 capability groups |
| Document upload and indexing | PASS, unique temporary document KB |
| Quick Q&A / knowledge RAG | PASS, traceable document history |
| ReACT AgentQA | PASS, `builtin-smart-reasoning`, native session persisted |
| Citation blocker | PASS, current-run no-evidence AgentQA found by filter |
| Wiki Mode | PASS, current-run Wiki references and `wiki_page` history |
| Suggested questions | PASS, scoped temporary Wiki page returned |
| MCP live test | PASS, one tool and one resource |
| MCP execution | PASS, approval-gated safe `ping`, history and audit persisted |
| Web Search | PASS, DuckDuckGo provider live test and AgentQA evidence |
| History filters | PASS, Quick/AgentQA/Wiki/Web/MCP/blocker outputs found |
| Mutation audit filters | PASS, strategy 2, MCP 2, Web Search 1 |
| Product browser matrix | PASS, 7 routes × 2 viewports = 14 checks |
| WNID dialogue browser | PASS, desktop/mobile, 15 markers each |
| Layout safety | PASS, zero horizontal overflow and visible overlap |
| Browser secret scan | PASS |
| Temporary external resources | PASS, KB 0 and Agent 0 after cleanup |

The final history summary reported Quick Q&A 1, AgentQA 4, Wiki 1, Web Search
1, MCP 1, and citation blocker 1 in the isolated PA current run. Read-only Wiki
Mode is recorded as `not_required_read_only` for mutation audit while retaining
live Wiki citation and history evidence.

## Static regression and governance results

The final P4-02 code also passes the repository's existing non-live regression
surface:

| Gate | Result |
| --- | --- |
| Root `make validate` | PASS |
| Shell syntax | PASS |
| Python no-cache syntax | PASS, 281 files |
| Backend unit discovery | PASS, 4/4 |
| PA Web TypeScript/Vite | PASS, 1,589 modules; output under `/tmp` |
| Repository static contract | PASS, 7/7 |
| PAR checker self-test | PASS |
| PAR governance / explicit `--root` / JSON | PASS |
| PAR `--final` | Expected exit 1, only three P4-03 blockers |
| PAR Skill quick validation | PASS, repository and `.agents` mirrors |
| PAR Skill file comparison | PASS, `SKILL.md` and `agents/openai.yaml` identical |
| Task Markdown local links | PASS, 19 checked and zero missing |
| Task sensitive-pattern scan | PASS |
| Working-tree and staged `git diff --check` | PASS |

The 4/4 backend result describes the current mixed worktree and includes the
preserved, untracked user file `tests/backend/test_database_runtime_path.py`.
P4-02 neither edits nor stages that file, and its live acceptance contract does
not depend on treating the untracked test as repository-owned evidence.

The three expected final blockers are the unfinished P4-03 task-board row, its
missing Progress Log evidence, and the absent clean-clone handoff file. No
P4-02 evidence, command, path, browser, live-workflow, or cleanup blocker
remains.

## Validation-path repairs and truthful failures

Initial diagnostic runs exposed stale validation contracts rather than product
failures: the current dialogue route no longer mounts the older English
Strategy/MCP/Web panels; several expected strings were HTML `title` or
`aria-label` values rather than visible text; and Wiki/history advanced content
was correctly collapsed. The matrices now validate current visible UI while
their live API gates continue to prove MCP, Web Search, suggested-question, and
status behavior.

The old history checker also selected the Wiki Researcher for document ReACT,
causing repeat SSE timeouts under the configured 60-second service timeout.
Selecting the product's Smart Reasoning Agent made document ReACT pass without
changing timeout configuration. A separate Data Analyst blocker path remained
too slow; an isolated live probe proved Quick Answer completes with zero
citations when explicitly told not to use materials or Web Search. The final
gate uses that truthful path and still requires the persisted
`citation_blocked` filter result.

All failed attempts executed their cleanup guards. Repeated read-only checks
found zero temporary P7/P8 KBs and Agents before the final successful run.

## Repository and recovery evidence

- all four modified/new Python validation files pass no-cache compilation;
- root `make -n validate-live-acceptance` resolves the canonical paths and
  absolute repository `PYTHONPATH` roots;
- `git diff --check` passes for the task files;
- one active Git root and the canonical `origin` remain unchanged;
- read-only Compose status continues to show the existing `weknora-main`
  project running;
- only P4-02-owned files are added to the existing mixed index.

All task changes are ordinary text/index changes. Temporary service processes,
SQLite databases, browser profiles, uploads, and test KBs/Agents are disposable
and already cleaned. Recovery requires only reverting the precisely listed
P4-02 text paths; no destructive Git or runtime rollback is needed.

## Validation limits and residual risk

- Live acceptance depends on the configured local WeKnora models and external
  DuckDuckGo availability; explicit 503/timeouts are retried at most three
  times and are never converted into fixture PASS.
- The existing application's 60-second WeKnora timeout remains unchanged.
- This task does not repeat or expand the P4-01 native Go/Helm/build evidence.
- Fresh-clone setup, build, start, live workflow reproduction, final checker,
  and handoff remain exclusively `PAR-P4-03`.

## Next task

The next and only next task is `PAR-P4-03`: clean-clone final acceptance and
handoff. No clean clone, final handoff, commit, push, or merge was performed by
`PAR-P4-02`.
