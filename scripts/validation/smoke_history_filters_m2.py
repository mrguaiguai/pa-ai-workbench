"""Fixture smoke for P3-M2-C4 history filters and evidence summaries."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.models import Citation  # noqa: E402
from app.models import GeneratedOutput  # noqa: E402
from app.services.history_service import history_output_summary  # noqa: E402
from app.services.history_service import list_history  # noqa: E402


class SmokeError(RuntimeError):
    """Raised when history filter expectations fail."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"History filter smoke failed: {exc}", file=sys.stderr)
        return 1

    print("History filter smoke passed (fixture)")
    print(f"- no evidence: {result['no_evidence']}")
    print(f"- mock output: {result['mock_output']}")
    print(f"- weknora citations: {result['weknora_citations']}")
    print(f"- wiki source: {result['wiki_source']}")
    print(f"- failed tasks: {result['failed_tasks']}")
    print(f"- warnings: {result['warnings']}")
    return 0


def _run_smoke() -> dict[str, Any]:
    with TemporaryDirectory(prefix="pa-history-filter-smoke-") as temp_dir:
        engine = create_engine(f"sqlite:///{Path(temp_dir) / 'smoke.db'}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            outputs = _seed_history(session)

            no_evidence = list_history(session=session, evidence_state="no_evidence")
            no_citation_source = list_history(session=session, citation_source="none")
            mock_output = list_history(session=session, evidence_state="mock_only")
            weknora_citations = list_history(session=session, citation_source="weknora_api")
            wiki_source = list_history(session=session, source_type="wiki_page")
            failed_tasks = list_history(session=session, status="failed")
            warnings = list_history(session=session, has_warnings=True)
            query = list_history(session=session, query="failure")
            policy = list_history(session=session, task_type="policy_analysis")

            _assert(
                {item.id for item in no_evidence}
                == {outputs["empty"].id, outputs["failed"].id, outputs["warning"].id},
                "no evidence filter failed",
            )
            _assert(
                {item.id for item in no_citation_source}
                == {outputs["empty"].id, outputs["failed"].id, outputs["warning"].id},
                "no citation source filter failed",
            )
            _assert([item.id for item in mock_output] == [outputs["mock"].id], "mock evidence filter failed")
            _assert(
                {item.id for item in weknora_citations} == {outputs["weknora_doc"].id, outputs["weknora_wiki"].id},
                "weknora citation filter failed",
            )
            _assert([item.id for item in wiki_source] == [outputs["weknora_wiki"].id], "wiki source filter failed")
            _assert([item.id for item in failed_tasks] == [outputs["failed"].id], "failed status filter failed")
            _assert([item.id for item in warnings] == [outputs["warning"].id], "warning filter failed")
            _assert([item.id for item in query] == [outputs["failed"].id], "query filter failed")
            _assert([item.id for item in policy] == [outputs["weknora_doc"].id], "task type filter failed")

            weknora_summary = history_output_summary(session, outputs["weknora_doc"])
            wiki_summary = history_output_summary(session, outputs["weknora_wiki"])
            warning_summary = history_output_summary(session, outputs["warning"])

            _assert(weknora_summary["evidence_state"] == "weknora", "weknora state failed")
            _assert(weknora_summary["document_citation_count"] == 1, "document citation count failed")
            _assert(wiki_summary["wiki_citation_count"] == 1, "wiki citation count failed")
            _assert(warning_summary["warning_count"] == 1, "warning count failed")

            return {
                "no_evidence": len(no_evidence),
                "mock_output": len(mock_output),
                "weknora_citations": len(weknora_citations),
                "wiki_source": len(wiki_source),
                "failed_tasks": len(failed_tasks),
                "warnings": len(warnings),
            }


def _seed_history(session: Session) -> dict[str, GeneratedOutput]:
    outputs = {
        "empty": GeneratedOutput(
            task_id="task-empty",
            task_type="knowledge_qa",
            title="No Evidence Fixture",
            content_markdown="No evidence available for this fixture.",
            status="completed",
        ),
        "mock": GeneratedOutput(
            task_id="task-mock",
            task_type="case_review",
            title="Mock Evidence Fixture",
            content_markdown="Mock citation summary.",
            status="completed",
        ),
        "weknora_doc": GeneratedOutput(
            task_id="task-weknora-doc",
            task_type="policy_analysis",
            title="WeKnora Document Fixture",
            content_markdown="Real citation summary.",
            status="completed",
        ),
        "weknora_wiki": GeneratedOutput(
            task_id="task-weknora-wiki",
            task_type="knowledge_qa",
            title="WeKnora Wiki Fixture",
            content_markdown="Wiki citation summary.",
            status="completed",
        ),
        "failed": GeneratedOutput(
            task_id="task-failed",
            task_type="knowledge_qa",
            title="Failure Fixture",
            content_markdown="Synthetic failure output.",
            status="failed",
        ),
        "warning": GeneratedOutput(
            task_id="task-warning",
            task_type="case_review",
            title="Warning Fixture",
            content_markdown="Warning output.",
            warnings_json=json.dumps(["fixture warning"]),
            status="completed",
        ),
    }
    for output in outputs.values():
        session.add(output)
    session.commit()
    for output in outputs.values():
        session.refresh(output)

    citations = [
        Citation(
            task_id=outputs["mock"].task_id,
            output_id=outputs["mock"].id,
            title="Mock citation",
            text="Short sanitized mock excerpt.",
            score=0.42,
            source="mock",
            metadata_json=json.dumps({"evidence_id": "ev-mock", "source_type": "document_chunk"}),
        ),
        Citation(
            task_id=outputs["weknora_doc"].task_id,
            output_id=outputs["weknora_doc"].id,
            external_doc_id="wk-doc-1",
            chunk_id="wk-chunk-1",
            title="WeKnora document citation",
            text="Short sanitized document excerpt.",
            score=0.91,
            source="mock",
            metadata_json=json.dumps(
                {
                    "source": "weknora_api",
                    "citation_source_type": "document_chunk",
                    "evidence_id": "ev-weknora-doc",
                }
            ),
        ),
        Citation(
            task_id=outputs["weknora_wiki"].task_id,
            output_id=outputs["weknora_wiki"].id,
            title="WeKnora wiki citation",
            text="Short sanitized wiki excerpt.",
            score=0.88,
            source="weknora_api",
            metadata_json=json.dumps(
                {
                    "source_type": "wiki_page",
                    "wiki_page_id": "wiki-page-1",
                    "evidence_id": "ev-weknora-wiki",
                }
            ),
        ),
    ]
    for citation in citations:
        session.add(citation)
    session.commit()
    return outputs


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
