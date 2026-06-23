# WeKnora Native Expansion Handoff Runbook

Date: 2026-06-24

Task: `WNX-P3-03`

Branch: `weknora-first-mvp`

Evidence type: audit/map, documentation validation, live service/status
evidence from `WNX-P0-05`.

## Current State

The WeKnora Native Expansion stage has reached the minimum internal production
PASS threshold with current live evidence.

Authoritative local state sources for the next agent or operator:

```text
git log --oneline -5
git status -sb
docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md
docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md
docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_PASS_REPORT.md
docs/WEKNORA_NATIVE_PRODUCT_BROWSER_MATRIX_REPORT.md
docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_REPORT.md
docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md
```

Do not rely on copied commit hashes in handoff text when local git can answer
the current truth. The branch currently has one intentionally untracked file:

```text
docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md
```

Keep that file unstaged unless the user explicitly changes scope.

## Completion Snapshot

Completed WNX scope:

- native architecture, coverage ledger, client/status center, acceptance
  harness, and local deployment readiness;
- KB, document, chunk, RAG, knowledge-chat, AgentQA/custom Agent, Wiki,
  history/citation, model/config, MCP, web search, vector store, connector,
  organization, and product browser matrix reports;
- local service/status runbook and browser matrix validation.

Current final-report decision:

```text
WNX-P3-02: [x]
coverage current: 12.00 / 15 = 80.0%
coverage target: 12.00 / 15 = 80.0%
```

The final PASS depends on the two score-moving unblocks that happened after the
original handoff:

- `WNX-P3-08` moved `AgentQA/custom Agent` to `live-full` with traceable Wiki
  references and PA history citation locators.
- `WNX-P3-10` moved `Data sources/connectors` to `live-partial` with a real
  no-credential native RSS connector, one configured live RSS source, sanitized
  resources/validation/sync/pause/resume/log evidence, and browser validation.

## Local Service Recovery

Use the existing deployment runbook for detailed recovery:

```text
docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md
```

Short local service commands:

```bash
scripts/pa-dev-services.sh status
scripts/pa-dev-services.sh start
scripts/pa-dev-services.sh restart
scripts/pa-dev-services.sh stop
scripts/pa-dev-services.sh logs
```

Durable macOS user-session service commands:

```bash
scripts/install-pa-launchagents.sh
scripts/uninstall-pa-launchagents.sh
```

Status checks must go through PA:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8000/api/model/status
curl http://127.0.0.1:8000/api/native/status
```

Healthy local readiness means PA reports WeKnora connected, non-mock chat and
embedding providers, masked native status, 15 capability groups, and visible
partial/backlog states where the stage is incomplete.

## Validation Commands

Use these before claiming readiness or before resuming score-moving work:

```bash
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py
backend/.venv/bin/python backend/scripts/check_weknora_native_expansion_acceptance.py --start-pa-api
backend/.venv/bin/python backend/scripts/check_weknora_native_product_browser_matrix.py
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py
backend/.venv/bin/python backend/scripts/check_weknora_native_deployment_readiness.py --start-services
backend/.venv/bin/python backend/scripts/check_phase5_report_safety.py --self-test
git diff --check
```

The commands with temporary service startup may require local process and port
permissions. They must not write or commit logs, databases, uploads, caches,
screenshots, `dist`, `node_modules`, `.env`, provider payloads, raw chunks,
raw vectors, API keys, service tokens, passwords, private endpoints, or private
key material.

## Remaining Backlog Options

Do not change the coverage score from prose alone. Any future upgrade beyond
the current 80.0% PASS needs real current-run evidence.

Useful future options:

| Option | Expected gain | Required evidence |
| --- | ---: | --- |
| Credential-bearing data source workflow | Optional stretch | Operator-configured Feishu/Notion/Yuque source with masked validation, sanitized resources/sync logs, confirmation-gated sync/pause/resume, and no raw credentials or private endpoints in output. |
| MCP/web-search/vector/model active tests | Optional stretch | Explicit confirmation, masked credentials, sanitized results, and no raw provider payloads. |
| FAQ/tags/favorites/skills workflow | Optional stretch | Native live read/write workflow with ownership, confirmation, and audit boundaries. |

If none of these are explicitly scoped, keep them as backlog and do not broaden
the already-passed internal production scope.

## Copy-Paste New-Chat Prompt

Use this prompt when opening a fresh Codex conversation:

```text
你是 Codex，请用中文继续 PA WeKnora Native Expansion 内部生产版阶段。

工作目录：
/Users/mac/Downloads/WeKnora-main/pa-ai-workbench

使用 skill：
- /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md
- repo-local mirror: .github/skills/pa-weknora-native-expansion/SKILL.md

当前分支：
weknora-first-mvp

请先只读检查：
1. pwd
2. git status -sb
3. git log --oneline -5
4. 读取 docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_SPEC.md
5. 读取 docs/WEKNORA_NATIVE_CAPABILITY_COVERAGE_LEDGER.md
6. 读取 docs/WEKNORA_NATIVE_EXPANSION_INTERNAL_PROD_PASS_REPORT.md
7. 读取 docs/WEKNORA_NATIVE_EXPANSION_HANDOFF_RUNBOOK.md
8. 读取 docs/WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md
9. 读取 .github/skills/pa-weknora-native-expansion/SKILL.md
10. 读取 /Users/mac/Downloads/WeKnora-main/.agents/skills/pa-weknora-native-expansion/SKILL.md

当前事实：
- 信任本地 git log 和 spec，而不是手抄旧 hash。
- WNX-P3-02 是 [x] PASS。
- 当前覆盖率是 12.00 / 15 = 80.0%，目标是 12.00 / 15 = 80.0%。
- WNX-P3-08 已把 AgentQA/custom Agent 推到 live-full。
- WNX-P3-10 已把 Data sources/connectors 推到 live-partial，证据是 native RSS connector + configured RSS source + sanitized resources/validation/sync/pause/resume/log/browser smoke。
- WNX-P3-03 handoff/runbook 已刷新。
- docs/PHASE5_B5_DIALOGUE_RETROSPECTIVE_CN.md 是未跟踪文件，不要 stage，除非我明确改范围。
- 不 push，除非我明确要求。

硬规则：
- 每次只执行一个 WNX-* 或一个用户明确授权的新任务。
- 修改前必须说明任务编号、任务分类、计划修改文件、验证方式、PASS evidence type。
- 不泄露、打印、提交 .env/API key/密钥/私钥/provider payload。
- 不提交数据库、日志、缓存、uploads、node_modules、dist、截图。
- mock、fixture-only、cache、静态 UI、旧报告不能算 PASS。
- spec 状态只能在验证通过或真实 blocked/backlog 后更新。

下一步建议：
不要继续扩大本阶段范围，除非用户明确授权新的 WNX-*。如果继续做，只选择一个明确任务，例如 credential-bearing connector stretch、MCP/web-search/vector/model active test、FAQ/tag/favorite/skill workflow，且必须保持 live evidence 和 secret-safety 边界。
```

## Operator Notes

- Keep the PA frontend as a product shell and BFF client; do not call WeKnora
  directly from the browser.
- Keep PA business DB records separate from WeKnora authoritative chunks,
  vectors, connector configs, and provider credentials.
- Keep partial and backlog states visible. Do not turn blockers into green
  status for presentation.
- Keep local commits narrow and do not push unless the user asks.

## PASS Boundary

`WNX-P3-03` remains valid when this handoff lets a new agent or operator recover
the local service state, understand the final PASS decision and remaining
backlog, find the source-of-truth reports, and continue without leaking secrets
or broadening the scope.
