"""Deterministic acceptance checker for PA repository reorganization.

Default mode validates the current PAR governance contract and reports whether
the repository is final-ready without requiring an in-progress migration to be
complete. ``--final`` turns every structural, path, artifact, and evidence gap
into a blocking failure. ``--self-test`` proves the checker accepts a complete
fixture and rejects each required negative gate.

The checker reads governance text and Git path metadata only. It never reads
environment values, databases, uploads, logs, output bodies, or credentials.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


SPEC_NAME = "PA_REPOSITORY_ARCHITECTURE_REORGANIZATION_SPEC.md"
BASELINE_REPORT_NAME = "PA_REPOSITORY_BASELINE_MAP_PAR_0_02.md"
HARNESS_REPORT_NAME = "PA_REPOSITORY_REORGANIZATION_ACCEPTANCE_HARNESS_PAR_0_03.md"
SKILL_NAME = "pa-repository-architecture-reorganization"
CHECKER_NAME = "check_pa_repository_reorganization.py"

EXPECTED_TASK_IDS = (
    "PAR-0-01",
    "PAR-0-02",
    "PAR-0-03",
    "PAR-P0-01",
    "PAR-P0-02",
    "PAR-P1-01",
    "PAR-P1-02",
    "PAR-P2-01",
    "PAR-P2-02",
    "PAR-P2-03",
    "PAR-P3-01",
    "PAR-P3-02",
    "PAR-P3-03",
    "PAR-P4-01",
    "PAR-P4-02",
    "PAR-P4-03",
)

GOVERNANCE_COMPLETE_TASKS = ("PAR-0-01", "PAR-0-02", "PAR-0-03")

TARGET_DIRECTORIES = (
    "apps/pa-api",
    "apps/pa-web",
    "packages/agent-runtime/agent",
    "packages/knowledge-engine/knowledge_engine",
    "platform/weknora",
    "infra",
    "scripts/validation",
    "tests/acceptance",
    "docs/product",
    "docs/architecture",
    "docs/operations",
    "docs/stages/current",
    "docs/evidence",
    "docs/handoff",
    ".github/skills",
)

TARGET_FILES = (
    ".gitignore",
    "LICENSE",
    "platform/weknora/UPSTREAM.md",
    "platform/weknora/PA_PATCHES.md",
    "compose.yaml",
    "Makefile",
    "README.md",
    "PRODUCT_SPEC.md",
    "ARCHITECTURE.md",
    "THIRD_PARTY_NOTICES.md",
)

UPSTREAM_REPOSITORY = "https://github.com/Tencent/WeKnora"
UPSTREAM_VERSION = "0.6.0"
OFFICIAL_VERSION_COMMIT = "b0094ff47917b5abece91acff4c7e16710368f2c"
RECONSTRUCTED_UPSTREAM_COMMIT = "482686d17ee89aefea54cf05bf843c04d152db27"
LOCAL_NATIVE_IMPORT_COMMIT = "42a6f0ac810dd04a64a6b0999b06554ac76a5e0b"
COHERENT_NATIVE_BASELINE_COMMIT = "e7b258c61d56bd44ce477ef29cf761d8ab07cdfc"

CONTROLLED_NATIVE_EXCEPTION_PATHS = (
    ".gitignore",
    "README.md",
    "config/builtin_agents.yaml",
    "config/builtin_models.yaml",
    "docker-compose.yml",
    "internal/agent/act.go",
    "internal/agent/act_references_test.go",
    "internal/agent/engine.go",
    "internal/agent/skills/skill.go",
    "internal/agent/tools/knowledge_search.go",
    "internal/agent/tools/wiki_tools.go",
    "internal/agent/tools/wiki_write_page.go",
    "internal/application/repository/wiki_page.go",
    "internal/application/service/chat_pipeline/merge.go",
    "internal/application/service/chat_pipeline/search.go",
    "internal/application/service/chat_pipeline/search_scope_test.go",
    "internal/application/service/chunk.go",
    "internal/application/service/mcp_service.go",
    "internal/application/service/mcp_service_execution_test.go",
    "internal/application/service/session_knowledge_qa.go",
    "internal/application/service/session_search_targets_test.go",
    "internal/application/service/skill_service.go",
    "internal/application/service/skill_service_test.go",
    "internal/application/service/wiki_page.go",
    "internal/container/container.go",
    "internal/datasource/connector/rss/connector.go",
    "internal/datasource/connector/rss/connector_test.go",
    "internal/handler/chunk.go",
    "internal/handler/dto/model.go",
    "internal/handler/dto/model_test.go",
    "internal/handler/mcp_service.go",
    "internal/handler/mcp_service_ssrf.go",
    "internal/handler/mcp_service_ssrf_test.go",
    "internal/handler/session/agent_stream_handler.go",
    "internal/handler/session/helpers.go",
    "internal/handler/skill_handler.go",
    "internal/handler/web_search_provider.go",
    "internal/handler/wiki_page.go",
    "internal/mcp/client.go",
    "internal/mcp/client_prompt_test.go",
    "internal/models/rerank/aliyun_reranker.go",
    "internal/models/rerank/aliyun_reranker_test.go",
    "internal/router/router.go",
    "internal/types/chunk.go",
    "internal/types/interfaces/chunk.go",
    "internal/types/interfaces/mcp_service.go",
    "internal/types/interfaces/skill.go",
    "internal/types/interfaces/wiki_page.go",
    "internal/types/mcp.go",
    "internal/types/search.go",
)

IMPORT_TO_COHERENT_EXCEPTION_PATHS = (
    ".gitignore",
    "config/builtin_agents.yaml",
    "config/builtin_models.yaml",
    "docker-compose.yml",
    "internal/agent/act.go",
    "internal/agent/act_references_test.go",
    "internal/agent/skills/skill.go",
    "internal/agent/tools/wiki_write_page.go",
    "internal/application/repository/wiki_page.go",
    "internal/application/service/chunk.go",
    "internal/application/service/mcp_service.go",
    "internal/application/service/mcp_service_execution_test.go",
    "internal/application/service/skill_service.go",
    "internal/application/service/skill_service_test.go",
    "internal/application/service/wiki_page.go",
    "internal/handler/chunk.go",
    "internal/handler/dto/model.go",
    "internal/handler/dto/model_test.go",
    "internal/handler/mcp_service.go",
    "internal/handler/mcp_service_ssrf.go",
    "internal/handler/mcp_service_ssrf_test.go",
    "internal/handler/skill_handler.go",
    "internal/handler/web_search_provider.go",
    "internal/handler/wiki_page.go",
    "internal/mcp/client.go",
    "internal/mcp/client_prompt_test.go",
    "internal/models/rerank/aliyun_reranker.go",
    "internal/models/rerank/aliyun_reranker_test.go",
    "internal/router/router.go",
    "internal/types/chunk.go",
    "internal/types/interfaces/chunk.go",
    "internal/types/interfaces/mcp_service.go",
    "internal/types/interfaces/skill.go",
    "internal/types/interfaces/wiki_page.go",
    "internal/types/mcp.go",
)

FINAL_EVIDENCE_FILES = (
    "docs/evidence/PA_REPOSITORY_STATIC_BUILD_ACCEPTANCE_PAR_P4_01.md",
    "docs/evidence/PA_REPOSITORY_LIVE_WORKFLOW_ACCEPTANCE_PAR_P4_02.md",
    "docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md",
)

OLD_CANONICAL_MARKERS = (
    "/Users/mac/Downloads/WeKnora-main",
    "pa-ai-workbench/",
    "cd pa-ai-workbench",
)

ACTIVE_REFERENCE_ROOTS = (
    ".github/skills",
    "apps",
    "packages",
    "infra",
    "scripts",
    "tests",
    "docs/product",
    "docs/architecture",
    "docs/operations",
    "docs/stages/current",
    "docs/handoff",
)

ACTIVE_ROOT_FILES = (
    "README.md",
    "PRODUCT_SPEC.md",
    "ARCHITECTURE.md",
    "compose.yaml",
    "Makefile",
)

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".txt",
}

PRUNE_DIRECTORY_NAMES = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pnpm-store",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "output",
    "tmp",
    "logs",
    "uploads",
}

UNSAFE_PARTS = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pnpm-store",
    "dist",
    "tmp",
    "logs",
    "uploads",
}

UNSAFE_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".log", ".pem", ".key")

RUNTIME_IGNORE_REQUIRED = (
    ".local/pa-api/data/pa_workbench.db",
    ".env",
    "apps/pa-api/.env",
    "apps/pa-api/data/pa_workbench.db",
    "apps/pa-api/uploads/private.pdf",
    "node_modules/package/index.js",
    "apps/pa-web/dist/index.html",
    "packages/agent-runtime/agent/__pycache__/module.pyc",
    "scripts/validation/__pycache__/checker.pyc",
    "tmp/par-validation/report.json",
    "output/local-report.json",
    "platform/weknora/data/weknora.db",
    "platform/weknora/data/files/private.pdf",
    "platform/weknora/frontend/node_modules/package/index.js",
    "platform/weknora/frontend/dist/index.html",
)

RUNTIME_SOURCE_REQUIRED = (
    ".env.example",
    "apps/pa-api/.env.example",
    "infra/env/pa-api.env.example",
    "platform/weknora/.env.example",
    "platform/weknora/cli/internal/build/new-source.go",
    "platform/weknora/cli/internal/output/new-source.go",
    "platform/weknora/cmd/desktop/build/new-resource.txt",
    "apps/pa-api/app/storage/new-source.py",
)

SENSITIVE_TEXT_PATTERNS = {
    "secret_bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    "secret_openai_key": re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{14,}\b"),
    "secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|service[_-]?token|password|secret|private[_-]?key|authorization)"
        r"\s*[:=]\s*(?!\[?redacted\]?|omitted|configured\b|true\b|false\b|masked\b)"
        r"[^\s`|,;]{8,}"
    ),
    "private_key_block": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
}


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    path: str = "-"


@dataclass(frozen=True)
class Summary:
    mode: str
    governance_ready: bool
    final_ready: bool
    task_rows: int
    completed_tasks: int
    progress_rows: int
    git_roots: int
    final_blockers: int
    final_blocker_codes: tuple[str, ...]


@dataclass(frozen=True)
class Inspection:
    summary: Summary
    governance_issues: tuple[Issue, ...]
    final_issues: tuple[Issue, ...]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()

    try:
        root = args.root.resolve() if args.root else _discover_root(Path(__file__).resolve())
        inspection = inspect_repository(root, final_mode=args.final)
    except Exception as exc:  # noqa: BLE001
        print(f"PA repository reorganization acceptance failed: {_safe_reason(exc)}", file=sys.stderr)
        return 1

    blocking = list(inspection.governance_issues)
    if args.final:
        blocking.extend(inspection.final_issues)

    if args.json:
        print(
            json.dumps(
                {
                    "summary": asdict(inspection.summary),
                    "governance_issues": [asdict(issue) for issue in inspection.governance_issues],
                    "final_issues": [asdict(issue) for issue in inspection.final_issues],
                    "blocking_issues": [asdict(issue) for issue in blocking],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_result(inspection, blocking)
    return 1 if blocking else 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check PA repository-reorganization governance and final readiness.",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="fail on every final one-root, target-path, artifact, path, and evidence gap",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run complete and negative fixtures for every required final gate",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="repository root override for clean-clone or fixture validation",
    )
    return parser.parse_args(argv)


def inspect_repository(root: Path, *, final_mode: bool) -> Inspection:
    root = root.resolve()
    governance_issues: list[Issue] = []

    spec_path, spec_text = _resolve_text_artifact(
        root,
        ("docs/stages/current/" + SPEC_NAME,),
        "spec",
        governance_issues,
    )
    baseline_path, baseline_text = _resolve_text_artifact(
        root,
        ("docs/evidence/" + BASELINE_REPORT_NAME,),
        "baseline_report",
        governance_issues,
    )
    harness_path, harness_text = _resolve_text_artifact(
        root,
        ("docs/evidence/" + HARNESS_REPORT_NAME,),
        "harness_report",
        governance_issues,
    )
    skill_path, skill_text = _resolve_text_artifact(
        root,
        (f".github/skills/{SKILL_NAME}/SKILL.md",),
        "repo_skill",
        governance_issues,
    )

    mirror_path = root / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    mirror_text = _read_optional_text(mirror_path, governance_issues, "skill_mirror_unreadable")
    if skill_text and mirror_text and skill_text != mirror_text:
        governance_issues.append(
            Issue(
                "skill_mirror_diverged",
                "repo-local and .agents Skill contents differ",
                _relative(root, mirror_path),
            )
        )

    governance_texts = (
        (spec_path, spec_text),
        (baseline_path, baseline_text),
        (harness_path, harness_text),
        (skill_path, skill_text),
        (mirror_path if mirror_text else None, mirror_text),
    )
    governance_issues.extend(_check_governance_text_safety(root, governance_texts))

    task_statuses = _parse_task_statuses(spec_text)
    progress_statuses = _parse_progress_statuses(spec_text)
    _check_governance_contract(
        task_statuses,
        baseline_text,
        harness_text,
        governance_issues,
        spec_path,
        baseline_path,
        harness_path,
    )

    git_entries = _find_git_entries(root)
    final_issues = _check_final_contract(
        root,
        spec_path=spec_path,
        spec_text=spec_text,
        skill_path=skill_path,
        skill_text=skill_text,
        task_statuses=task_statuses,
        progress_statuses=progress_statuses,
        git_entries=git_entries,
    )

    governance_issues = _deduplicate_issues(governance_issues)
    final_issues = _deduplicate_issues(final_issues)
    blocker_codes = tuple(sorted(Counter(issue.code for issue in final_issues)))
    completed = sum(1 for status in task_statuses.values() if status == "[x]")
    summary = Summary(
        mode="final" if final_mode else "governance",
        governance_ready=not governance_issues,
        final_ready=not governance_issues and not final_issues,
        task_rows=len(task_statuses),
        completed_tasks=completed,
        progress_rows=len(progress_statuses),
        git_roots=len(git_entries),
        final_blockers=len(final_issues),
        final_blocker_codes=blocker_codes,
    )
    return Inspection(summary, tuple(governance_issues), tuple(final_issues))


def _check_governance_contract(
    task_statuses: dict[str, str],
    baseline_text: str,
    harness_text: str,
    issues: list[Issue],
    spec_path: Path | None,
    baseline_path: Path | None,
    harness_path: Path | None,
) -> None:
    missing_tasks = [task_id for task_id in EXPECTED_TASK_IDS if task_id not in task_statuses]
    if missing_tasks:
        issues.append(
            Issue(
                "missing_task_rows",
                "missing PAR task rows: " + ", ".join(missing_tasks),
                str(spec_path or "-"),
            )
        )
    incomplete_governance = [
        task_id for task_id in GOVERNANCE_COMPLETE_TASKS if task_statuses.get(task_id) != "[x]"
    ]
    if incomplete_governance:
        issues.append(
            Issue(
                "governance_tasks_incomplete",
                "governance tasks must be [x]: " + ", ".join(incomplete_governance),
                str(spec_path or "-"),
            )
        )

    baseline_markers = ("e7b258c", "e3402c7", "a4231cb", "c053ea53")
    missing_baseline = [marker for marker in baseline_markers if marker not in baseline_text]
    if baseline_text and missing_baseline:
        issues.append(
            Issue(
                "baseline_report_incomplete",
                "baseline report misses preservation markers: " + ", ".join(missing_baseline),
                str(baseline_path or "-"),
            )
        )

    harness_markers = ("PAR-0-03", CHECKER_NAME, "--final", "--self-test")
    missing_harness = [marker for marker in harness_markers if marker not in harness_text]
    if harness_text and missing_harness:
        issues.append(
            Issue(
                "harness_report_incomplete",
                "harness report misses contract markers: " + ", ".join(missing_harness),
                str(harness_path or "-"),
            )
        )


def _check_final_contract(
    root: Path,
    *,
    spec_path: Path | None,
    spec_text: str,
    skill_path: Path | None,
    skill_text: str,
    task_statuses: dict[str, str],
    progress_statuses: dict[str, str],
    git_entries: list[Path],
) -> list[Issue]:
    issues: list[Issue] = []

    root_git = root / ".git"
    if not root_git.exists():
        issues.append(Issue("missing_root_git", "final repository must have a root .git", ".git"))
    nested_git = [path for path in git_entries if path != root_git]
    if nested_git:
        issues.append(
            Issue(
                "nested_git",
                "nested Git entries remain: " + ", ".join(_relative(root, path) for path in nested_git[:12]),
            )
        )

    legacy_tracked, legacy_unignored, legacy_inventory_valid = _legacy_product_residue(root)
    if legacy_tracked or legacy_unignored or not legacy_inventory_valid:
        detail = f"tracked={len(legacy_tracked)} unignored={len(legacy_unignored)}"
        if not legacy_inventory_valid:
            detail += " inventory=unavailable"
        issues.append(
            Issue(
                "legacy_product_tree_present",
                "legacy pa-ai-workbench retains repository-visible entries: " + detail,
                "pa-ai-workbench",
            )
        )

    missing_dirs = [path for path in TARGET_DIRECTORIES if not (root / path).is_dir()]
    missing_files = [path for path in TARGET_FILES if not (root / path).is_file()]
    if missing_dirs or missing_files:
        detail = []
        if missing_dirs:
            detail.append("directories=" + ", ".join(missing_dirs))
        if missing_files:
            detail.append("files=" + ", ".join(missing_files))
        issues.append(Issue("missing_target_boundaries", "; ".join(detail)))

    issues.extend(_check_attribution_contract(root))

    canonical_spec = root / "docs" / "stages" / "current" / SPEC_NAME
    if spec_path != canonical_spec:
        issues.append(
            Issue(
                "canonical_spec_missing",
                "final mode requires the canonical current-stage Spec path",
                _relative(root, canonical_spec),
            )
        )
    canonical_skill = root / ".github" / "skills" / SKILL_NAME / "SKILL.md"
    if skill_path != canonical_skill:
        issues.append(
            Issue(
                "canonical_skill_missing",
                "final mode requires the root repo-local Skill path",
                _relative(root, canonical_skill),
            )
        )

    readme = _read_text_safely(root / "README.md")
    if not _root_readme_is_pa_first(readme):
        issues.append(Issue("root_product_identity", "root README is not PA AI Workbench-first", "README.md"))

    incomplete = [task_id for task_id in EXPECTED_TASK_IDS if task_statuses.get(task_id) != "[x]"]
    if incomplete:
        issues.append(
            Issue(
                "incomplete_task_board",
                "final task board has unfinished rows: " + ", ".join(incomplete),
                _relative(root, spec_path) if spec_path else "-",
            )
        )
    missing_progress = [task_id for task_id in EXPECTED_TASK_IDS if progress_statuses.get(task_id) != "[x]"]
    if missing_progress:
        issues.append(
            Issue(
                "incomplete_progress_evidence",
                "final progress log lacks [x] evidence: " + ", ".join(missing_progress),
                _relative(root, spec_path) if spec_path else "-",
            )
        )

    missing_evidence = [path for path in FINAL_EVIDENCE_FILES if not (root / path).is_file()]
    if missing_evidence:
        issues.append(
            Issue(
                "missing_final_evidence",
                "missing final evidence files: " + ", ".join(missing_evidence),
            )
        )

    unsafe_paths = _unsafe_tracked_paths(root, git_entries)
    if unsafe_paths:
        issues.append(
            Issue(
                "unsafe_tracked_artifact",
                "unsafe tracked paths: " + ", ".join(unsafe_paths[:16]),
            )
        )

    missing_ignored, overbroad_ignored, ignore_inventory_valid = _runtime_ignore_gaps(root)
    if missing_ignored or overbroad_ignored or not ignore_inventory_valid:
        detail = []
        if missing_ignored:
            detail.append("not_ignored=" + ", ".join(missing_ignored[:12]))
        if overbroad_ignored:
            detail.append("source_ignored=" + ", ".join(overbroad_ignored[:12]))
        if not ignore_inventory_valid:
            detail.append("git_check_ignore=unavailable")
        issues.append(Issue("runtime_ignore_contract", "; ".join(detail), ".gitignore"))

    stale_markers = [marker for marker in OLD_CANONICAL_MARKERS if marker in skill_text]
    if stale_markers:
        issues.append(
            Issue(
                "stale_skill_path",
                "repo-local Skill retains old canonical markers: " + ", ".join(stale_markers),
                _relative(root, skill_path) if skill_path else "-",
            )
        )

    old_references = _old_canonical_references(root)
    if old_references:
        issues.append(
            Issue(
                "old_canonical_reference",
                "active files retain old canonical paths: " + ", ".join(old_references[:16]),
            )
        )

    if spec_text and len(task_statuses) != len(EXPECTED_TASK_IDS):
        issues.append(
            Issue(
                "unexpected_task_board_shape",
                f"expected {len(EXPECTED_TASK_IDS)} unique task rows, found {len(task_statuses)}",
                _relative(root, spec_path) if spec_path else "-",
            )
        )
    return issues


def _check_attribution_contract(root: Path) -> list[Issue]:
    license_text = _read_text_safely(root / "LICENSE")
    notices_text = _read_text_safely(root / "THIRD_PARTY_NOTICES.md")
    upstream_text = _read_text_safely(root / "platform" / "weknora" / "UPSTREAM.md")
    patches_text = _read_text_safely(root / "platform" / "weknora" / "PA_PATCHES.md")
    gaps: list[str] = []

    required_license_markers = (
        "PA AI Workbench",
        "no public license",
        "platform/weknora/LICENSE",
        "THIRD_PARTY_NOTICES.md",
    )
    if any(marker not in license_text for marker in required_license_markers):
        gaps.append("root LICENSE boundary")

    common_provenance_markers = (
        UPSTREAM_REPOSITORY,
        UPSTREAM_VERSION,
        OFFICIAL_VERSION_COMMIT,
        RECONSTRUCTED_UPSTREAM_COMMIT,
        LOCAL_NATIVE_IMPORT_COMMIT,
        COHERENT_NATIVE_BASELINE_COMMIT,
    )
    if any(marker not in notices_text for marker in common_provenance_markers) or any(
        marker not in notices_text
        for marker in ("platform/weknora/LICENSE", "platform/weknora/mcp-server/LICENSE")
    ):
        gaps.append("root third-party notice index")

    if any(marker not in upstream_text for marker in common_provenance_markers) or any(
        marker not in upstream_text
        for marker in ("not a claim of tree equality", "520 paths", "25 paths", "358")
    ):
        gaps.append("upstream provenance reconstruction")

    if any(marker not in patches_text for marker in common_provenance_markers[1:]) or any(
        marker not in patches_text
        for marker in ("exactly 50", "35 paths", "infra/compose/weknora.yaml")
    ):
        gaps.append("patch ledger baselines")

    complete_paths = _parse_ledger_paths(
        patches_text,
        "## Complete controlled native exception inventory",
        "## Import-to-coherent 35-path stage subset",
        with_status=True,
    )
    if complete_paths != set(CONTROLLED_NATIVE_EXCEPTION_PATHS):
        gaps.append("50-path controlled native inventory")

    stage_paths = _parse_ledger_paths(
        patches_text,
        "## Import-to-coherent 35-path stage subset",
        "## Contract ownership by exception area",
        with_status=False,
    )
    if stage_paths != set(IMPORT_TO_COHERENT_EXCEPTION_PATHS):
        gaps.append("35-path import-to-coherent inventory")

    if not gaps:
        return []
    return [
        Issue(
            "attribution_contract",
            "incomplete upstream/license/patch attribution: " + ", ".join(gaps),
            "THIRD_PARTY_NOTICES.md",
        )
    ]


def _parse_ledger_paths(
    text: str,
    start_heading: str,
    end_heading: str,
    *,
    with_status: bool,
) -> set[str]:
    if start_heading not in text or end_heading not in text:
        return set()
    section = text.split(start_heading, 1)[1].split(end_heading, 1)[0]
    pattern = r"^[AM]\s+(.+)$" if with_status else r"^([^`\s].+)$"
    code_blocks = re.findall(r"```text\n(.*?)\n```", section, re.DOTALL)
    if len(code_blocks) != 1:
        return set()
    return {
        match.group(1).strip()
        for match in re.finditer(pattern, code_blocks[0], re.MULTILINE)
    }


def _resolve_text_artifact(
    root: Path,
    relative_candidates: tuple[str, ...],
    label: str,
    issues: list[Issue],
) -> tuple[Path | None, str]:
    candidates = [root / value for value in relative_candidates if (root / value).is_file()]
    if not candidates:
        issues.append(
            Issue(
                f"missing_{label}",
                f"missing {label}; checked " + ", ".join(relative_candidates),
            )
        )
        return None, ""

    texts: list[tuple[Path, str]] = []
    for path in candidates:
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError) as exc:
            issues.append(Issue(f"unreadable_{label}", _safe_reason(exc), _relative(root, path)))
    if not texts:
        return candidates[0], ""
    if len({text for _, text in texts}) > 1:
        issues.append(
            Issue(
                f"divergent_{label}",
                f"multiple {label} files differ",
                ", ".join(_relative(root, path) for path, _ in texts),
            )
        )
    final_candidate = root / relative_candidates[-1]
    for path, text in texts:
        if path == final_candidate:
            return path, text
    return texts[0]


def _check_governance_text_safety(
    root: Path,
    artifacts: tuple[tuple[Path | None, str], ...],
) -> list[Issue]:
    issues: list[Issue] = []
    for path, text in artifacts:
        if not path or not text:
            continue
        for code, pattern in SENSITIVE_TEXT_PATTERNS.items():
            if pattern.search(text):
                issues.append(
                    Issue(
                        code,
                        "governance artifact contains secret-shaped text",
                        _relative(root, path),
                    )
                )
    return issues


def _parse_task_statuses(text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    pattern = re.compile(r"^\|\s*(PAR-(?:0|P\d)-\d{2})\s*\|.*?\|\s*(\[[x~!b ]\])\s*\|", re.MULTILINE)
    for task_id, status in pattern.findall(text):
        statuses[task_id] = status
    return statuses


def _parse_progress_statuses(text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    pattern = re.compile(
        r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*(PAR-(?:0|P\d)-\d{2})\s*\|\s*(\[[x~!b ]\])\s*\|",
        re.MULTILINE,
    )
    for task_id, status in pattern.findall(text):
        statuses[task_id] = status
    return statuses


def _find_git_entries(root: Path) -> list[Path]:
    entries: list[Path] = []
    for current, dir_names, file_names in os.walk(root):
        current_path = Path(current)
        if ".git" in dir_names:
            entries.append(current_path / ".git")
            dir_names.remove(".git")
        if ".git" in file_names:
            entries.append(current_path / ".git")
        dir_names[:] = [name for name in dir_names if name not in PRUNE_DIRECTORY_NAMES]
    return sorted(set(path.resolve() for path in entries))


def _unsafe_tracked_paths(root: Path, git_entries: list[Path]) -> list[str]:
    paths: set[str] = set()
    repositories = [entry.parent for entry in git_entries]
    if not repositories:
        repositories = [root]
    valid_git_inventory = False
    for repository in repositories:
        result = subprocess.run(
            ["git", "-C", str(repository), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        valid_git_inventory = True
        prefix = repository.relative_to(root).as_posix() if repository != root else ""
        for raw_path in result.stdout.split(b"\0"):
            if not raw_path:
                continue
            value = raw_path.decode("utf-8", errors="replace")
            full_value = f"{prefix}/{value}" if prefix else value
            if _is_unsafe_path(full_value):
                paths.add(full_value)

    if not valid_git_inventory:
        for path in _iter_files(root):
            relative = _relative(root, path)
            if _is_unsafe_path(relative):
                paths.add(relative)
    return sorted(paths)


def _legacy_product_residue(root: Path) -> tuple[list[str], list[str], bool]:
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "pa-ai-workbench"],
        capture_output=True,
        check=False,
    )
    unignored = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "pa-ai-workbench",
        ],
        capture_output=True,
        check=False,
    )
    valid = tracked.returncode == 0 and unignored.returncode == 0
    return (
        _decode_git_paths(tracked.stdout) if tracked.returncode == 0 else [],
        _decode_git_paths(unignored.stdout) if unignored.returncode == 0 else [],
        valid,
    )


def _runtime_ignore_gaps(root: Path) -> tuple[list[str], list[str], bool]:
    missing: list[str] = []
    overbroad: list[str] = []
    valid = True
    for value in RUNTIME_IGNORE_REQUIRED:
        ignored = _git_path_is_ignored(root, value)
        if ignored is None:
            valid = False
        elif not ignored:
            missing.append(value)
    for value in RUNTIME_SOURCE_REQUIRED:
        ignored = _git_path_is_ignored(root, value)
        if ignored is None:
            valid = False
        elif ignored:
            overbroad.append(value)
    return missing, overbroad, valid


def _git_path_is_ignored(root: Path, value: str) -> bool | None:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", "-q", "--", value],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def _decode_git_paths(value: bytes) -> list[str]:
    return sorted(
        path.decode("utf-8", errors="replace")
        for path in value.split(b"\0")
        if path
    )


def _is_unsafe_path(value: str) -> bool:
    normalized = value.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    name = parts[-1] if parts else normalized
    lower = normalized.lower()
    if name == ".DS_Store":
        return True
    if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
        return True
    if any(part in UNSAFE_PARTS for part in parts):
        return True
    artifact_prefixes = (
        "output/",
        "build/",
        "dist/",
        "apps/pa-api/build/",
        "apps/pa-api/dist/",
        "apps/pa-web/build/",
        "apps/pa-web/dist/",
        "platform/weknora/frontend/dist/",
    )
    if any(lower.startswith(prefix) for prefix in artifact_prefixes):
        return True
    if "docs/resume_project/" in lower:
        return True
    return lower.endswith(UNSAFE_SUFFIXES)


def _root_readme_is_pa_first(text: str) -> bool:
    heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return bool(heading and "PA AI Workbench" in heading.group(1))


def _old_canonical_references(root: Path) -> list[str]:
    matches: set[str] = set()
    candidates: list[Path] = []
    for relative in ACTIVE_ROOT_FILES:
        path = root / relative
        if path.is_file():
            candidates.append(path)
    for relative in ACTIVE_REFERENCE_ROOTS:
        path = root / relative
        if path.is_dir():
            candidates.extend(_iter_files(path))

    for path in sorted(set(candidates)):
        # The checker intentionally names the bootstrap pa-ai-workbench paths
        # until PAR-P2-03/P3-01 move governance to its final root locations.
        # Do not report that compatibility contract as an application residue.
        if path.name == CHECKER_NAME:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "Makefile":
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        markers = [marker for marker in OLD_CANONICAL_MARKERS if marker in text]
        if markers:
            matches.add(_relative(root, path) + " (" + ", ".join(markers) + ")")
    return sorted(matches)


def _iter_files(root: Path):
    for current, dir_names, file_names in os.walk(root):
        dir_names[:] = [
            name for name in dir_names if name != ".git" and name not in PRUNE_DIRECTORY_NAMES
        ]
        current_path = Path(current)
        for file_name in file_names:
            yield current_path / file_name


def _read_optional_text(path: Path, issues: list[Issue], code: str) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(Issue(code, _safe_reason(exc), str(path)))
        return ""


def _read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeError):
        return ""


def _discover_root(script_path: Path) -> Path:
    for candidate in script_path.parents:
        if (candidate / "pa-ai-workbench" / "docs" / SPEC_NAME).is_file():
            return candidate
        if (candidate / "docs" / "stages" / "current" / SPEC_NAME).is_file():
            return candidate
    raise RuntimeError("could not discover repository root; pass --root")


def _deduplicate_issues(issues: list[Issue]) -> list[Issue]:
    return sorted(set(issues), key=lambda issue: (issue.code, issue.path, issue.message))


def _relative(root: Path, path: Path | None) -> str:
    if path is None:
        return "-"
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _print_result(inspection: Inspection, blocking: list[Issue]) -> None:
    if blocking:
        print("PA repository reorganization acceptance check failed")
        for issue in blocking:
            print(f"- {issue.path}: {issue.code}: {issue.message}")
    else:
        print("PA repository reorganization acceptance check passed")
    summary = inspection.summary
    print("- evidence_type: checker_execution")
    print(f"- mode: {summary.mode}")
    print(f"- governance_ready: {str(summary.governance_ready).lower()}")
    print(f"- final_ready: {str(summary.final_ready).lower()}")
    print(f"- task_rows: {summary.task_rows}")
    print(f"- completed_tasks: {summary.completed_tasks}")
    print(f"- progress_rows: {summary.progress_rows}")
    print(f"- git_roots: {summary.git_roots}")
    print(f"- final_blockers: {summary.final_blockers}")
    print("- final_blocker_codes: " + (", ".join(summary.final_blocker_codes) or "none"))


def _run_self_test() -> int:
    try:
        with TemporaryDirectory(prefix="par-checker-") as temp_dir:
            base = Path(temp_dir)
            positive_root = base / "positive"
            negative_root = base / "negative"
            _write_fixture(positive_root, complete=True)
            _write_fixture(negative_root, complete=False)

            positive = inspect_repository(positive_root, final_mode=True)
            if positive.governance_issues or positive.final_issues or not positive.summary.final_ready:
                raise RuntimeError(
                    "positive fixture failed: "
                    + ", ".join(
                        issue.code for issue in (*positive.governance_issues, *positive.final_issues)
                    )
                )

            negative = inspect_repository(negative_root, final_mode=True)
            if negative.governance_issues:
                raise RuntimeError(
                    "negative fixture broke governance instead of final gates: "
                    + ", ".join(issue.code for issue in negative.governance_issues)
                )
            codes = {issue.code for issue in negative.final_issues}
            expected = {
                "attribution_contract",
                "nested_git",
                "missing_target_boundaries",
                "unsafe_tracked_artifact",
                "old_canonical_reference",
                "stale_skill_path",
                "incomplete_task_board",
                "incomplete_progress_evidence",
                "missing_final_evidence",
                "runtime_ignore_contract",
            }
            missing = expected - codes
            if missing:
                raise RuntimeError("negative fixture missed gates: " + ", ".join(sorted(missing)))
    except Exception as exc:  # noqa: BLE001
        print(f"PA repository reorganization checker self-test failed: {_safe_reason(exc)}")
        return 1

    print("PA repository reorganization checker self-test passed")
    print("- positive_final_fixture: passed")
    print("- negative_required_gates: passed")
    return 0


def _write_fixture(root: Path, *, complete: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative in TARGET_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in TARGET_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "README.md":
            path.write_text("# PA AI Workbench\n", encoding="utf-8")
        else:
            path.write_text(f"fixture {relative}\n", encoding="utf-8")
    if complete:
        _write_attribution_fixture(root)

    ignore_text = """\
.env
.env.*
!.env.example
!.env.*.example
/.local/
/tmp/
/output/
*.db
apps/pa-api/data/
apps/pa-api/uploads/
node_modules/
**/__pycache__/
apps/pa-web/dist/
platform/weknora/data/files/
platform/weknora/frontend/dist/
"""
    if not complete:
        ignore_text = ".env\n**/build/\n"
    (root / ".gitignore").write_text(ignore_text, encoding="utf-8")

    skill_text = "---\nname: pa-repository-architecture-reorganization\ndescription: Final PA repository checks.\n---\n"
    if not complete:
        skill_text += "Legacy path: pa-ai-workbench/\n"
    skill_path = root / ".github" / "skills" / SKILL_NAME / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(skill_text, encoding="utf-8")
    mirror_path = root / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.write_text(skill_text, encoding="utf-8")

    spec_path = root / "docs" / "stages" / "current" / SPEC_NAME
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(_fixture_spec(complete=complete), encoding="utf-8")

    evidence_root = root / "docs" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / BASELINE_REPORT_NAME).write_text(
        "PAR-0-02 e7b258c e3402c7 a4231cb c053ea53\n",
        encoding="utf-8",
    )
    (evidence_root / HARNESS_REPORT_NAME).write_text(
        f"PAR-0-03 {CHECKER_NAME} --final --self-test\n",
        encoding="utf-8",
    )
    for relative in FINAL_EVIDENCE_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"validated {relative}\n", encoding="utf-8")

    for relative in (
        "cli/internal/build/build.go",
        "cli/internal/output/envelope.go",
        "cmd/desktop/build/appicon.png",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("legitimate source fixture\n", encoding="utf-8")

    if not complete:
        pa_web = root / "apps" / "pa-web"
        pa_web.rmdir()
        (root / "apps" / "pa-api" / ".env").write_text("masked fixture\n", encoding="utf-8")
        (root / "README.md").write_text(
            "# PA AI Workbench\nLegacy command references pa-ai-workbench/\n",
            encoding="utf-8",
        )
        (root / FINAL_EVIDENCE_FILES[-1]).unlink()

    init_result = subprocess.run(
        ["git", "init", "-q", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )
    if init_result.returncode != 0:
        raise RuntimeError("fixture git init failed: " + _safe_reason(RuntimeError(init_result.stderr)))
    add_result = subprocess.run(
        ["git", "-C", str(root), "add", "-A"],
        text=True,
        capture_output=True,
        check=False,
    )
    if add_result.returncode != 0:
        raise RuntimeError("fixture git add failed: " + _safe_reason(RuntimeError(add_result.stderr)))
    if not complete:
        force_add_result = subprocess.run(
            ["git", "-C", str(root), "add", "-f", "apps/pa-api/.env"],
            text=True,
            capture_output=True,
            check=False,
        )
        if force_add_result.returncode != 0:
            raise RuntimeError(
                "fixture forced git add failed: "
                + _safe_reason(RuntimeError(force_add_result.stderr))
            )
    if not complete:
        (root / "legacy" / ".git").mkdir(parents=True)


def _write_attribution_fixture(root: Path) -> None:
    (root / "LICENSE").write_text(
        "PA AI Workbench: no public license. See platform/weknora/LICENSE and "
        "THIRD_PARTY_NOTICES.md.\n",
        encoding="utf-8",
    )
    provenance = "\n".join(
        (
            UPSTREAM_REPOSITORY,
            UPSTREAM_VERSION,
            OFFICIAL_VERSION_COMMIT,
            RECONSTRUCTED_UPSTREAM_COMMIT,
            LOCAL_NATIVE_IMPORT_COMMIT,
            COHERENT_NATIVE_BASELINE_COMMIT,
        )
    )
    (root / "THIRD_PARTY_NOTICES.md").write_text(
        provenance
        + "\nplatform/weknora/LICENSE\nplatform/weknora/mcp-server/LICENSE\n",
        encoding="utf-8",
    )
    (root / "platform" / "weknora" / "UPSTREAM.md").write_text(
        provenance
        + "\nnot a claim of tree equality\n520 paths\n25 paths\n358 official commits\n",
        encoding="utf-8",
    )
    complete_inventory = "\n".join(
        f"M {path}" for path in CONTROLLED_NATIVE_EXCEPTION_PATHS
    )
    stage_inventory = "\n".join(IMPORT_TO_COHERENT_EXCEPTION_PATHS)
    (root / "platform" / "weknora" / "PA_PATCHES.md").write_text(
        "\n".join(
            (
                provenance,
                "exactly 50 paths; 35 paths; infra/compose/weknora.yaml",
                "## Complete controlled native exception inventory",
                "```text",
                complete_inventory,
                "```",
                "## Import-to-coherent 35-path stage subset",
                "```text",
                stage_inventory,
                "```",
                "## Contract ownership by exception area",
                "",
            )
        ),
        encoding="utf-8",
    )


def _fixture_spec(*, complete: bool) -> str:
    task_lines = []
    progress_lines = []
    for task_id in EXPECTED_TASK_IDS:
        status = "[ ]" if not complete and task_id == "PAR-P4-03" else "[x]"
        task_lines.append(f"| {task_id} | P0 | Fixture task | {status} | Evidence. |")
        progress_lines.append(f"| 2026-07-14 | {task_id} | {status} | Evidence. | Done. |")
    return "\n".join(
        (
            "# PA Repository Architecture Reorganization Spec",
            "",
            "## Task Board",
            "",
            "| Task id | Priority | Title | Status | Required evidence |",
            "| --- | --- | --- | --- | --- |",
            *task_lines,
            "",
            "## Progress Log",
            "",
            "| Date | Task id | Status | Evidence | Notes |",
            "| --- | --- | --- | --- | --- |",
            *progress_lines,
            "",
        )
    )


def _safe_reason(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", text)
    text = re.sub(
        r"(?i)(authorization|api[_-]?key|service[_-]?token|password|secret)(\s*[:=]\s*)\S+",
        r"\1\2[redacted]",
        text,
    )
    text = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "sk-[redacted]", text)
    return text[:320]


if __name__ == "__main__":
    raise SystemExit(main())
