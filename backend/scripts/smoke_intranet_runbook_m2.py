"""Fixture smoke for P3-M2-D4 intranet runbook completeness and safety."""

from __future__ import annotations

from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = PROJECT_ROOT / "docs" / "PHASE3_M2_INTRANET_RUNBOOK.md"


class SmokeError(RuntimeError):
    """Raised when the intranet runbook is incomplete or unsafe."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Intranet runbook smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Intranet runbook smoke passed")
    print(f"- sections: {result['sections']}")
    print(f"- commands: {result['commands']}")
    print(f"- required terms: {result['required_terms']}")
    return 0


def _run_smoke() -> dict[str, int]:
    text = _read(RUNBOOK_PATH)
    required_sections = [
        "## Operating Rule",
        "## Startup Order",
        "## Required Preflight Commands",
        "## Model And KB Checks",
        "## Common Failures",
        "## Log Troubleshooting",
        "## Recovery Steps",
        "## Rollback",
        "## Git Safety Before Any Fix Commit",
        "## Operator Escalation Checklist",
    ]
    required_terms = [
        "DeepSeek Chat Is Not Embedding",
        "KB Must Bind `embedding_model_id`",
        "DashScope/Aliyun `Embedding`",
        "DocReader",
        "Redis",
        "vector store",
        "backend/.venv/bin/python backend/scripts/check_m2_preflight.py",
        "adapter_operation_id",
        "MOCK_MODE",
        "KNOWLEDGE_BACKEND",
    ]
    forbidden_patterns = [
        r"WEKNORA_SERVICE_TOKEN\s*=",
        r"WEKNORA_API_KEY\s*=",
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+",
        r"sk-[A-Za-z0-9_-]{12,}",
        r"https?://",
    ]

    for section in required_sections:
        _assert(section in text, f"missing section: {section}")
    for term in required_terms:
        _assert(term in text, f"missing required term: {term}")
    for pattern in forbidden_patterns:
        _assert(not re.search(pattern, text), f"forbidden pattern found: {pattern}")

    _assert(
        "DeepSeek chat / `KnowledgeQA` is used for answer generation" in text,
        "missing DeepSeek vs embedding explanation",
    )
    _assert(
        "The KB `embedding_model_id` points to an Embedding model, not a chat model." in text,
        "missing KB embedding_model_id acceptance check",
    )

    return {
        "sections": len(required_sections),
        "commands": text.count("backend/.venv/bin/python"),
        "required_terms": len(required_terms),
    }


def _read(path: Path) -> str:
    if not path.is_file():
        raise SmokeError(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
