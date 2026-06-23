"""Fixture smoke for P3-M2-D3 pilot feedback template and regression checklist."""

from __future__ import annotations

from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = PROJECT_ROOT / "docs" / "PHASE3_M2_PILOT_FEEDBACK_TEMPLATE.md"
CHECKLIST_PATH = PROJECT_ROOT / "docs" / "PHASE3_M2_PILOT_REGRESSION_CHECKLIST.md"


class SmokeError(RuntimeError):
    """Raised when pilot feedback docs are incomplete or unsafe."""


def main() -> int:
    try:
        result = _run_smoke()
    except Exception as exc:  # noqa: BLE001
        print(f"Pilot feedback docs smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Pilot feedback docs smoke passed")
    print(f"- template sections: {result['template_sections']}")
    print(f"- checklist sections: {result['checklist_sections']}")
    print(f"- sample scenarios: {result['sample_scenarios']}")
    print(f"- categories: {', '.join(result['categories'])}")
    return 0


def _run_smoke() -> dict[str, object]:
    template = _read(TEMPLATE_PATH)
    checklist = _read(CHECKLIST_PATH)
    combined = f"{template}\n{checklist}"

    required_template_sections = [
        "## Intake",
        "## Linked Ids",
        "## Sanitized Context",
        "## Reproduction",
        "## Privacy Checklist",
        "## Triage Decision",
        "## Regression Checklist",
        "## Known Scenario Samples",
        "## Classification Guide",
    ]
    required_checklist_sections = [
        "## 1. Intake Complete",
        "## 2. Privacy Gate",
        "## 3. Reproduction",
        "## 4. Classification-Specific Checks",
        "## 5. Regression Artifact",
        "## 6. Git Safety",
        "## Example Regression Matrix",
    ]
    categories = ["bug", "config", "data", "product feedback", "out-of-scope"]
    required_ids = [
        "PA task id",
        "Conversation id",
        "Document id",
        "Wiki page id",
        "Output id",
        "RAG debug trace id",
        "WeKnora adapter operation id",
    ]
    required_privacy_terms = [
        "No `.env`",
        "No private endpoint",
        "No original document body",
        "No full user prompt",
        "raw WeKnora response",
    ]

    for section in required_template_sections:
        _assert(section in template, f"missing template section: {section}")
    for section in required_checklist_sections:
        _assert(section in checklist, f"missing checklist section: {section}")
    for category in categories:
        _assert(category in combined, f"missing category: {category}")
    for required_id in required_ids:
        _assert(required_id in template, f"missing linked id: {required_id}")
    for term in required_privacy_terms:
        _assert(term in combined, f"missing privacy rule: {term}")

    sample_count = len(re.findall(r"^### Sample \d+:", template, flags=re.MULTILINE))
    _assert(sample_count >= 3, "expected at least 3 known scenario samples")
    _assert("PILOT-20260610-001" in template, "missing bug sample")
    _assert("PILOT-20260610-002" in template, "missing config sample")
    _assert("PILOT-20260610-003" in template, "missing product feedback sample")
    _assert("WEKNORA_SERVICE_TOKEN=" not in combined, "template includes env assignment")
    _assert("Authorization: Bearer " not in combined, "template includes bearer shape")
    _assert(not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined), "template includes API key shape")
    _assert("http://" not in combined and "https://" not in combined, "template includes endpoint shape")

    return {
        "template_sections": len(required_template_sections),
        "checklist_sections": len(required_checklist_sections),
        "sample_scenarios": sample_count,
        "categories": categories,
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
