from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOTS = (
    REPOSITORY_ROOT / "apps" / "pa-api",
    REPOSITORY_ROOT / "packages" / "agent-runtime",
    REPOSITORY_ROOT / "packages" / "knowledge-engine",
)


class WorkspaceImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for root in reversed(PYTHON_ROOTS):
            sys.path.insert(0, str(root))

    def test_canonical_packages_are_discoverable(self) -> None:
        for package in ("app", "agent", "knowledge_engine"):
            with self.subTest(package=package):
                spec = importlib.util.find_spec(package)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.origin)
                package_path = Path(spec.origin).resolve()
                self.assertTrue(
                    any(package_path.is_relative_to(root.resolve()) for root in PYTHON_ROOTS),
                    package_path,
                )

    def test_api_pathing_uses_repository_boundaries(self) -> None:
        from app import pathing

        self.assertEqual(pathing.REPOSITORY_ROOT, REPOSITORY_ROOT)
        self.assertEqual(pathing.PA_API_ROOT, REPOSITORY_ROOT / "apps" / "pa-api")
        self.assertEqual(pathing.PA_WEB_ROOT, REPOSITORY_ROOT / "apps" / "pa-web")
        self.assertEqual(
            pathing.AGENT_RUNTIME_ROOT,
            REPOSITORY_ROOT / "packages" / "agent-runtime",
        )
        self.assertEqual(
            pathing.KNOWLEDGE_ENGINE_ROOT,
            REPOSITORY_ROOT / "packages" / "knowledge-engine",
        )
        self.assertEqual(pathing.PLATFORM_ROOT, REPOSITORY_ROOT / "platform" / "weknora")

    def test_builtin_skill_documents_are_packaged_sources(self) -> None:
        skill_root = REPOSITORY_ROOT / "packages" / "agent-runtime" / "agent" / "skills" / "builtin"
        self.assertEqual(
            {path.name for path in skill_root.glob("*.md")},
            {"case_review.md", "knowledge_qa.md", "policy_analysis.md"},
        )


if __name__ == "__main__":
    unittest.main()
