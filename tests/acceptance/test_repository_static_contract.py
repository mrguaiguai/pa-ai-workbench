from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import tomllib
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LEGACY_PRODUCT_ROOT = "pa-ai-" + "workbench"
OLD_ABSOLUTE_ROOT = "/Users/mac/Downloads/" + "WeKnora-" + "main"

TARGET_DIRECTORIES = (
    "apps/pa-api",
    "apps/pa-web",
    "packages/agent-runtime",
    "packages/knowledge-engine",
    "platform/weknora",
    "infra/compose",
    "infra/docker",
    "infra/helm",
    "infra/env",
    "scripts/dev",
    "scripts/ops",
    "scripts/release",
    "scripts/validation",
    "tests/backend",
    "tests/acceptance",
    "docs/stages/current",
    "docs/evidence",
)

TARGET_FILES = (
    "compose.yaml",
    "Makefile",
    "pnpm-workspace.yaml",
    "README.md",
    "PRODUCT_SPEC.md",
    "ARCHITECTURE.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "platform/weknora/UPSTREAM.md",
    "platform/weknora/PA_PATCHES.md",
    "scripts/validation/check_pa_repository_reorganization.py",
    "scripts/validation/check_pa_repository_clean_clone_acceptance.py",
    "docs/handoff/PA_REPOSITORY_CLEAN_CLONE_HANDOFF_PAR_P4_03.md",
)

COMPATIBILITY_LINKS = {
    "apps/pa-api/.env.example": "infra/env/pa-api.env.example",
    "apps/pa-web/.env.example": "infra/env/pa-web.env.example",
    "platform/weknora/.env.example": "infra/env/compose.env.example",
    "platform/weknora/docker-compose.yml": "infra/compose/weknora.yaml",
    "platform/weknora/docker-compose.dev.yml": "infra/compose/weknora.dev.yaml",
    "platform/weknora/helm": "infra/helm/weknora",
}

WORKFLOW_FILES = (
    ".github/workflows/cli-e2e.yml",
    ".github/workflows/cli.yml",
    ".github/workflows/docker-image.yml",
    ".github/workflows/pa-images.yml",
    ".github/workflows/release-lite.yml",
)

DOCKER_CONTEXTS = {
    "infra/docker/pa-api/Dockerfile": ".",
    "infra/docker/pa-web/Dockerfile": ".",
    "infra/docker/weknora/Dockerfile.app": "platform/weknora",
    "infra/docker/weknora/Dockerfile.docreader": "platform/weknora",
    "infra/docker/weknora/Dockerfile.sandbox": "platform/weknora",
    "infra/docker/weknora/Dockerfile.frontend": "platform/weknora/frontend",
    "infra/docker/weknora/Dockerfile.mcp": "platform/weknora/mcp-server",
}


class RepositoryStaticContractTests(unittest.TestCase):
    def test_pa_first_target_boundaries_exist(self) -> None:
        for relative in TARGET_DIRECTORIES:
            with self.subTest(directory=relative):
                self.assertTrue((REPOSITORY_ROOT / relative).is_dir(), relative)
        for relative in TARGET_FILES:
            with self.subTest(file=relative):
                self.assertTrue((REPOSITORY_ROOT / relative).is_file(), relative)

        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# PA AI Workbench\n"))

    def test_root_workspace_and_command_contract(self) -> None:
        python_workspace = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            python_workspace["tool"]["uv"]["workspace"]["members"],
            [
                "apps/pa-api",
                "packages/agent-runtime",
                "packages/knowledge-engine",
            ],
        )

        node_workspace = json.loads(
            (REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8")
        )
        self.assertTrue(node_workspace["private"])
        self.assertEqual(node_workspace["workspaces"], ["apps/pa-web"])

        pnpm_workspace = (
            REPOSITORY_ROOT / "pnpm-workspace.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("- apps/pa-web", pnpm_workspace)
        self.assertIn("allowBuilds:\n  esbuild: true", pnpm_workspace)

        makefile = (REPOSITORY_ROOT / "Makefile").read_text(encoding="utf-8")
        for target in (
            "setup",
            "start",
            "status",
            "compose-config",
            "native-build",
            "native-test",
            "validate",
            "validate-static-acceptance",
            "validate-clean-clone",
            "validate-par-final",
        ):
            with self.subTest(make_target=target):
                self.assertIn(f"\n{target}:", "\n" + makefile)

        setup = (REPOSITORY_ROOT / "scripts/dev/pa-workbench-setup.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'copy_if_missing "$PLATFORM_ROOT/.env.example" "$REPOSITORY_ROOT/.env"',
            setup,
        )

    def test_controlled_compatibility_links_resolve(self) -> None:
        for link_value, target_value in COMPATIBILITY_LINKS.items():
            link = REPOSITORY_ROOT / link_value
            target = REPOSITORY_ROOT / target_value
            with self.subTest(link=link_value):
                self.assertTrue(link.is_symlink(), link_value)
                self.assertEqual(link.resolve(), target.resolve())
                self.assertTrue(target.exists(), target_value)

    def test_workflows_use_canonical_repository_paths(self) -> None:
        for relative in WORKFLOW_FILES:
            path = REPOSITORY_ROOT / relative
            with self.subTest(workflow=relative):
                text = path.read_text(encoding="utf-8")
                for marker in (
                    f"working-directory: {LEGACY_PRODUCT_ROOT}",
                    f"context: {LEGACY_PRODUCT_ROOT}",
                    f"file: {LEGACY_PRODUCT_ROOT}",
                    f"cd {LEGACY_PRODUCT_ROOT}",
                    f"./{LEGACY_PRODUCT_ROOT}/",
                ):
                    self.assertNotIn(marker, text)
                self.assertNotIn(OLD_ABSOLUTE_ROOT, text)
                self.assertNotIn("backend/scripts/", text)
                self.assertNotIn("frontend/", text.replace("platform/weknora/frontend/", ""))

    def test_dockerfile_copy_sources_stay_in_context(self) -> None:
        validated_sources = 0
        for dockerfile_value, context_value in DOCKER_CONTEXTS.items():
            dockerfile = REPOSITORY_ROOT / dockerfile_value
            context = (REPOSITORY_ROOT / context_value).resolve()
            for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line.startswith("COPY ") or "--from=" in line:
                    continue
                fields = shlex.split(line)[1:]
                for source_value in fields[:-1]:
                    with self.subTest(dockerfile=dockerfile_value, source=source_value):
                        matches = [context] if source_value == "." else list(
                            context.glob(source_value)
                        )
                        self.assertTrue(matches, source_value)
                        for source in matches:
                            self.assertTrue(source.resolve().is_relative_to(context))
                            self.assertTrue(source.exists())
                            validated_sources += 1
        self.assertEqual(validated_sources, 33)

    def test_attribution_and_native_patch_boundaries(self) -> None:
        notices = (REPOSITORY_ROOT / "THIRD_PARTY_NOTICES.md").read_text(
            encoding="utf-8"
        )
        upstream = (REPOSITORY_ROOT / "platform/weknora/UPSTREAM.md").read_text(
            encoding="utf-8"
        )
        patches = (REPOSITORY_ROOT / "platform/weknora/PA_PATCHES.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "https://github.com/Tencent/WeKnora",
            "b0094ff47917b5abece91acff4c7e16710368f2c",
            "482686d17ee89aefea54cf05bf843c04d152db27",
            "42a6f0ac810dd04a64a6b0999b06554ac76a5e0b",
            "e7b258c61d56bd44ce477ef29cf761d8ab07cdfc",
        ):
            with self.subTest(attribution_marker=marker):
                self.assertIn(marker, notices)
                self.assertIn(marker, upstream)
        self.assertIn("exactly 50", patches)
        self.assertIn("35 paths", patches)

    def test_legacy_product_tree_is_not_repository_visible(self) -> None:
        for arguments in (
            ("ls-files", "-z", "--", LEGACY_PRODUCT_ROOT),
            (
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                LEGACY_PRODUCT_ROOT,
            ),
        ):
            result = subprocess.run(
                ("git", "-C", str(REPOSITORY_ROOT), *arguments),
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
