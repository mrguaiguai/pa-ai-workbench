"""Smoke-check M3 multi-KB / workspace mapping.

This fixture smoke covers P3-M3-A4 without live WeKnora side effects:
- upload/retrieve/wiki operations resolve KBs through the adapter mapping layer;
- explicit KBs outside configured mappings fail closed;
- missing mapping can fail closed when default fallback is disabled;
- status capability output exposes only a redacted mapping summary.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from app.config import Settings  # noqa: E402
from app.services.backend_capability_service import get_backend_capabilities  # noqa: E402
from knowledge_engine.backends.weknora_api_backend import WeKnoraApiBackend  # noqa: E402
from knowledge_engine.errors import KnowledgeBackendUnavailableError  # noqa: E402


MAPPING_CONFIG = json.dumps(
    {
        "allow_default": False,
        "mappings": [
            {
                "name": "policy-team",
                "workspace_id": "workspace-policy-fixture",
                "kb_id": "kb-policy-fixture",
                "selectors": {"business_area": "policy", "team": "pilot-a"},
            },
            {
                "name": "case-team",
                "workspace_id": "workspace-case-fixture",
                "kb_id": "kb-case-fixture",
                "selectors": {"business_area": "case", "team": "pilot-b"},
            },
        ],
    }
)


class SmokeError(RuntimeError):
    """Raised when multi-KB mapping expectations fail."""


class FixtureWeKnoraBackend(WeKnoraApiBackend):
    def __init__(self) -> None:
        super().__init__(
            base_url="fixture://weknora",
            service_token="fixture",
            workspace_id="workspace-default-fixture",
            default_kb_id="kb-default-fixture",
            kb_mapping_config=MAPPING_CONFIG,
        )
        self.upload_paths: list[str] = []
        self.upload_metadata: list[dict[str, str]] = []
        self.retrieve_payloads: list[dict[str, Any]] = []
        self.wiki_paths: list[str] = []

    def _request_multipart_json(
        self,
        path: str,
        *,
        file_path: Path,
        fields: dict[str, str],
    ) -> dict | list:
        self.upload_paths.append(path)
        self.upload_metadata.append(json.loads(fields["metadata"]))
        kb_id = _kb_from_upload_path(path)
        return {
            "data": {
                "id": f"doc-{kb_id}",
                "file_name": file_path.name,
                "status": "indexed",
                "knowledge_base_id": kb_id,
                "metadata": {"fixture": "multi-kb"},
            }
        }

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list:
        if method == "POST" and path == "/api/v1/knowledge-search":
            self.retrieve_payloads.append(dict(payload or {}))
            kb_id = (payload or {}).get("knowledge_base_ids", ["unknown"])[0]
            return {
                "data": [
                    {
                        "id": f"chunk-{kb_id}",
                        "knowledge_id": f"doc-{kb_id}",
                        "knowledge_base_id": kb_id,
                        "title": "Multi KB fixture evidence",
                        "content": "Short sanitized multi-KB fixture evidence.",
                        "score": 0.9,
                    }
                ]
            }
        if method == "GET" and "/wiki/search?" in path:
            self.wiki_paths.append(path)
            return {
                "data": {
                    "pages": [
                        {
                            "id": "wiki-policy-fixture",
                            "slug": "policy-fixture",
                            "title": "Policy Fixture",
                            "summary": "Policy fixture summary.",
                            "content": "Policy fixture body.",
                            "knowledge_base_id": "kb-policy-fixture",
                        }
                    ]
                }
            }
        if method == "GET" and "/wiki/pages/" in path:
            self.wiki_paths.append(path)
            return {
                "data": {
                    "id": "wiki-policy-fixture",
                    "slug": "policy-fixture",
                    "title": "Policy Fixture",
                    "summary": "Policy fixture summary.",
                    "content": "Policy fixture body.",
                    "knowledge_base_id": "kb-policy-fixture",
                }
            }
        raise SmokeError(f"unexpected fixture request: {method} {path}")


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"WeKnora multi-KB mapping smoke failed: {exc}", file=sys.stderr)
        return 1

    print("WeKnora multi-KB mapping smoke passed")
    print(f"- upload kb: {result['upload_kb']}")
    print(f"- retrieve kb: {result['retrieve_kb']}")
    print(f"- wiki kb: {result['wiki_kb']}")
    print(f"- fail-closed checks: {result['fail_closed_checks']}")
    print(f"- summary redacted: {result['summary_redacted']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    backend = FixtureWeKnoraBackend()
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "multi-kb-fixture.md"
        path.write_text("# Fixture\n\nShort sanitized multi-KB body.\n", encoding="utf-8")
        document = backend.upload_document(
            str(path),
            {
                "title": "Policy fixture",
                "business_area": "policy",
                "team": "pilot-a",
            },
        )
    upload_kb = _kb_from_upload_path(backend.upload_paths[-1])
    _assert(upload_kb == "kb-policy-fixture", f"upload routed to wrong KB: {upload_kb}")
    _assert(document.metadata.get("kb_mapping_name") == "policy-team", "upload mapping metadata missing")
    _assert(document.metadata.get("kb_default_used") is False, "upload unexpectedly used default")

    evidence = backend.retrieve("case query", filters={"business_area": "case"}, top_k=3)
    retrieve_kb = backend.retrieve_payloads[-1]["knowledge_base_ids"][0]
    _assert(retrieve_kb == "kb-case-fixture", f"retrieve routed to wrong KB: {retrieve_kb}")
    _assert(evidence[0].external_doc_id == "doc-kb-case-fixture", "retrieve evidence mixed KB")

    summaries = backend.search_wiki("policy", kb_id="policy-team", limit=5)
    wiki_kb = _kb_from_wiki_path(backend.wiki_paths[-1])
    _assert(wiki_kb == "kb-policy-fixture", f"wiki search routed to wrong KB: {wiki_kb}")
    _assert(summaries[0].metadata.get("knowledge_base_id") == "kb-policy-fixture", "wiki metadata lost KB")

    fail_closed_checks = 0
    for action in (
        lambda: backend.retrieve("unknown", filters={"kb_id": "kb-outside-fixture"}, top_k=1),
        lambda: backend.retrieve("missing", filters={"business_area": "unmapped"}, top_k=1),
        lambda: backend.search_wiki("missing", kb_id="kb-outside-fixture", limit=1),
    ):
        try:
            action()
        except KnowledgeBackendUnavailableError:
            fail_closed_checks += 1
            continue
        raise SmokeError("mapping boundary did not fail closed")

    summary = _capability_summary()
    summary_text = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    for secret_value in (
        "workspace-policy-fixture",
        "workspace-case-fixture",
        "kb-policy-fixture",
        "kb-case-fixture",
    ):
        _assert(secret_value not in summary_text, f"mapping summary leaked id: {secret_value}")

    return {
        "upload_kb": upload_kb,
        "retrieve_kb": retrieve_kb,
        "wiki_kb": wiki_kb,
        "fail_closed_checks": fail_closed_checks,
        "summary_redacted": summary["ids_redacted"],
    }


def _capability_summary() -> dict[str, Any]:
    settings = Settings(
        knowledge_backend="weknora_api",
        mock_mode=False,
        weknora_base_url="fixture://weknora",
        weknora_service_token="fixture",
        weknora_workspace_id="workspace-default-fixture",
        weknora_default_kb_id="kb-default-fixture",
        weknora_kb_mappings=MAPPING_CONFIG,
        weknora_kb_allow_default=False,
    )
    return get_backend_capabilities(settings)["kb_mapping"]


def _kb_from_upload_path(path: str) -> str:
    marker = "/knowledge-bases/"
    return path.split(marker, 1)[1].split("/", 1)[0]


def _kb_from_wiki_path(path: str) -> str:
    marker = "/knowledgebase/"
    return path.split(marker, 1)[1].split("/", 1)[0]


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
