"""Smoke-check WeKnora Wiki search/read mapping for PA.

This fixture smoke validates P3-M1-C2 without a live WeKnora service:
- Wiki search calls the WeKnora v1 KB-scoped Wiki search API.
- Wiki read calls the WeKnora v1 KB-scoped Wiki page API with slug addressing.
- WeKnora WikiPage fields map to PA WikiPageSummary / WikiPage schemas.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlparse
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when the Wiki adapter contract fails."""


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="http://weknora.fixture",
            service_token="fixture-token",
            default_kb_id="kb-fixture",
        )
        self.paths: list[str] = []

    def _request_json(  # type: ignore[override]
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if payload is not None:
            raise SmokeError("Wiki search/read should not send a JSON payload")
        if method != "GET":
            raise SmokeError(f"unexpected method: {method}")
        self.paths.append(path)
        parsed = urlparse(path)
        if parsed.path == "/api/v1/knowledgebase/kb-fixture/wiki/search":
            params = parse_qs(parsed.query)
            if params.get("q") != ["policy"] or params.get("limit") != ["2"]:
                raise SmokeError(f"unexpected search params: {params}")
            return {"pages": [_fixture_wiki_page()]}
        if parsed.path == "/api/v1/knowledgebase/kb-fixture/wiki/pages/concept/policy":
            return {"success": True, "data": _fixture_wiki_page()}
        raise SmokeError(f"unexpected request path: {path}")


def main() -> int:
    try:
        result = _run_fixture_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora Wiki smoke failed: {exc}", file=sys.stderr)
        return 1
    print("WeKnora Wiki smoke passed (fixture)")
    print(f"- search path: {result['search_path']}")
    print(f"- read path: {result['read_path']}")
    print(f"- slug: {result['slug']}")
    print(f"- source: {result['source']}")
    return 0


def _run_fixture_smoke() -> dict[str, str]:
    backend = FixtureWeKnoraBackend()
    summaries = backend.search_wiki("policy", limit=2)
    if len(summaries) != 1:
        raise SmokeError(f"expected 1 Wiki summary, got {len(summaries)}")
    summary = summaries[0]
    if summary.slug != "concept/policy" or summary.source != "weknora_api":
        raise SmokeError("Wiki summary slug/source were not mapped")
    if summary.metadata.get("id") != "wiki-page-001":
        raise SmokeError("Wiki summary external id was not preserved")
    if summary.metadata.get("status") != "published":
        raise SmokeError("Wiki summary status was not preserved")
    if summary.metadata.get("source_refs") != ["wk-doc-001|Policy Fixture"]:
        raise SmokeError("Wiki summary source_refs were not preserved")

    page = backend.read_wiki_page("concept/policy")
    if page is None:
        raise SmokeError("expected Wiki page")
    if page.slug != "concept/policy" or page.title != "Policy Fixture":
        raise SmokeError("Wiki page slug/title were not mapped")
    if "sanitized Wiki body" not in page.content:
        raise SmokeError("Wiki page content was not mapped")
    if page.citations:
        raise SmokeError("C2 should preserve refs in metadata, not synthesize citations")
    if page.metadata.get("chunk_refs") != ["chunk-policy-001"]:
        raise SmokeError("Wiki page chunk_refs were not preserved")
    if len(backend.paths) != 2:
        raise SmokeError(f"unexpected request count: {len(backend.paths)}")
    return {
        "search_path": backend.paths[0],
        "read_path": backend.paths[1],
        "slug": page.slug,
        "source": page.source,
    }


def _fixture_wiki_page() -> dict[str, Any]:
    return {
        "id": "wiki-page-001",
        "tenant_id": 1,
        "knowledge_base_id": "kb-fixture",
        "slug": "concept/policy",
        "title": "Policy Fixture",
        "page_type": "concept",
        "status": "published",
        "content": "# Policy Fixture\n\nsanitized Wiki body",
        "summary": "Sanitized Wiki summary",
        "aliases": ["Policy"],
        "source_refs": ["wk-doc-001|Policy Fixture"],
        "chunk_refs": ["chunk-policy-001"],
        "in_links": ["index"],
        "out_links": ["concept/control"],
        "page_metadata": {"tags": ["policy"], "business_area": "internal"},
        "version": 3,
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-02T00:00:00Z",
    }


if __name__ == "__main__":
    raise SystemExit(main())
