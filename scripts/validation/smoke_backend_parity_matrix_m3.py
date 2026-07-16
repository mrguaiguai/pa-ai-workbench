"""Smoke-check M3 backend parity matrix and status-page summary.

This fixture smoke covers P3-M3-A2:
- the parity doc uses the same supported/partial/unsupported/dev-only matrix as code;
- /api/status capability snapshots expose a short parity_summary;
- unsupported capabilities are not treated as successful fallbacks;
- the Home page renders a Capability status summary from parity_summary.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from knowledge_engine.backends import ExtractedKnowledgeBackend  # noqa: E402
from knowledge_engine.backends import MockKnowledgeBackend  # noqa: E402
from knowledge_engine.capabilities import BACKEND_CAPABILITY_MATRIX  # noqa: E402
from knowledge_engine.capabilities import CAPABILITY_ORDER  # noqa: E402
from knowledge_engine.capabilities import CAPABILITY_STATUSES  # noqa: E402
from knowledge_engine.capabilities import backend_capability_snapshot  # noqa: E402


DOC_PATH = PROJECT_ROOT / "docs" / "archive" / "phase3" / "PHASE3_M3_BACKEND_PARITY_MATRIX.md"
HOME_PAGE_PATH = PROJECT_ROOT / "apps" / "pa-web" / "src" / "pages" / "HomePage.tsx"
CLIENT_PATH = PROJECT_ROOT / "apps" / "pa-web" / "src" / "api" / "client.ts"


class SmokeError(RuntimeError):
    """Raised when parity matrix expectations fail."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"M3 backend parity matrix smoke failed: {exc}", file=sys.stderr)
        return 1

    print("M3 backend parity matrix smoke passed")
    print(f"- matrix rows checked: {result['matrix_rows']}")
    print(f"- status summaries checked: {result['status_summaries']}")
    print(f"- unsupported checks: {result['unsupported_checks']}")
    print(f"- frontend summary: {result['frontend_summary']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    _assert_doc_matrix()
    _assert_status_summaries()
    unsupported_checks = _assert_unsupported_behavior()
    _assert_frontend_summary()
    return {
        "matrix_rows": len(CAPABILITY_ORDER),
        "status_summaries": len(BACKEND_CAPABILITY_MATRIX),
        "unsupported_checks": unsupported_checks,
        "frontend_summary": "Capability card",
    }


def _assert_doc_matrix() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    for status in CAPABILITY_STATUSES:
        if status not in lower:
            raise SmokeError(f"parity doc missing status vocabulary: {status}")
    for phrase in (
        "data fact source",
        "citation trace",
        "status recovery",
        "retrieve debug",
        "quality limits",
        "unsupported capability must not silently succeed",
        "status page summary",
    ):
        if phrase not in lower:
            raise SmokeError(f"parity doc missing required phrase: {phrase}")

    rows = _markdown_matrix_rows(text)
    for capability in CAPABILITY_ORDER:
        expected = BACKEND_CAPABILITY_MATRIX
        actual = rows.get(capability)
        if actual is None:
            raise SmokeError(f"parity doc missing capability row: {capability}")
        for backend in ("mock", "weknora_api", "extracted"):
            if actual.get(backend) != expected[backend][capability]:
                raise SmokeError(
                    f"parity doc drift for {capability}.{backend}: "
                    f"{actual.get(backend)} != {expected[backend][capability]}"
                )


def _assert_status_summaries() -> None:
    snapshots = {
        "mock": backend_capability_snapshot(
            backend_name="mock",
            app_env="local",
            mock_mode=True,
            weknora_configured=False,
        ),
        "weknora_api": backend_capability_snapshot(
            backend_name="weknora_api",
            app_env="pilot",
            mock_mode=False,
            weknora_configured=True,
        ),
        "extracted": backend_capability_snapshot(
            backend_name="extracted",
            app_env="local",
            mock_mode=True,
            weknora_configured=False,
        ),
    }
    for backend, snapshot in snapshots.items():
        summary = snapshot.get("parity_summary")
        if not isinstance(summary, dict):
            raise SmokeError(f"{backend} snapshot missing parity_summary")
        if summary.get("backend") != backend:
            raise SmokeError(f"{backend} summary backend mismatch")
        if summary.get("citation_trace") != BACKEND_CAPABILITY_MATRIX[backend]["citation_trace"]:
            raise SmokeError(f"{backend} citation trace summary drift")
        if summary.get("wiki") != BACKEND_CAPABILITY_MATRIX[backend]["wiki_create_update_publish"]:
            raise SmokeError(f"{backend} wiki summary drift")
        if summary.get("debug") != BACKEND_CAPABILITY_MATRIX[backend]["rag_debug"]:
            raise SmokeError(f"{backend} debug summary drift")
        if summary.get("unsupported_must_fail") is not True:
            raise SmokeError(f"{backend} unsupported_must_fail missing")
        counts = summary.get("status_counts")
        if not isinstance(counts, dict):
            raise SmokeError(f"{backend} status_counts missing")
        for status in CAPABILITY_STATUSES:
            expected = sum(
                1
                for value in BACKEND_CAPABILITY_MATRIX[backend].values()
                if value == status
            )
            if counts.get(status) != expected:
                raise SmokeError(f"{backend}.{status} count drift: {counts.get(status)} != {expected}")

    if snapshots["mock"]["parity_summary"].get("release_evidence"):
        raise SmokeError("mock must not be release evidence")
    if not snapshots["weknora_api"]["parity_summary"].get("release_evidence"):
        raise SmokeError("configured weknora_api should be release evidence candidate")
    if snapshots["extracted"]["parity_summary"].get("release_evidence"):
        raise SmokeError("extracted must not be release evidence")


def _assert_unsupported_behavior() -> int:
    checks = 0
    mock = MockKnowledgeBackend()
    if hasattr(mock, "list_document_chunks"):
        raise SmokeError("mock list_document_chunks must not silently exist")
    checks += 1
    if hasattr(mock, "create_wiki_page"):
        raise SmokeError("mock create_wiki_page must not silently exist")
    checks += 1

    extracted = ExtractedKnowledgeBackend()
    created = extracted.create_wiki_page(
        {
            "slug": "partial-local",
            "title": "Partial Local",
            "content": "Sanitized local fallback body.",
        }
    )
    published = extracted.publish_wiki_page("partial-local")
    indexed = extracted.index_wiki_page("partial-local")
    if created.source != "extracted" or published.source != "extracted":
        raise SmokeError("extracted local Wiki fallback used wrong source")
    if published.metadata.get("weknora_retrievable") is not False:
        raise SmokeError("extracted local Wiki fallback claimed WeKnora retrievable")
    if indexed.get("wiki_retrievable") is not False:
        raise SmokeError("extracted local Wiki index claimed retrievable")
    checks += 3
    return checks


def _assert_frontend_summary() -> None:
    home = HOME_PAGE_PATH.read_text(encoding="utf-8")
    client = CLIENT_PATH.read_text(encoding="utf-8")
    for phrase in (
        "Capability",
        "parity_summary",
        "status_counts",
        "data_fact_source",
        "unsupported",
        "wiki publish",
    ):
        if phrase not in home:
            raise SmokeError(f"HomePage missing parity summary phrase: {phrase}")
    for phrase in (
        "parity_summary",
        "release_evidence",
        "unsupported_capabilities",
        "unsupported_must_fail",
    ):
        if phrase not in client:
            raise SmokeError(f"client type missing parity field: {phrase}")


def _markdown_matrix_rows(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"^\|\s*([a-z_]+)\s*\|\s*([a-z-]+)\s*\|\s*([a-z_]+|[a-z-]+)\s*\|\s*([a-z-]+)\s*\|$"
    )
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        capability, mock, weknora_api, extracted = match.groups()
        if capability in CAPABILITY_ORDER:
            rows[capability] = {
                "mock": mock,
                "weknora_api": weknora_api,
                "extracted": extracted,
            }
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
