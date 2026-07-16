"""Phase 5 fixture contract checker.

This checker protects the Phase 4 synthetic sanitized corpus that Phase 5 uses
as its fixed 24-question quality baseline. It validates fixture shape only; it
does not run PA, WeKnora, retrieval, Wiki publishing, or model QA.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "apps" / "pa-api" / "fixtures" / "phase4_rag_wiki_qa"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
QUESTIONS_PATH = FIXTURE_ROOT / "questions.json"
HIT_MATRIX_PATH = FIXTURE_ROOT / "hit_matrix.md"
DOCUMENTS_ROOT = FIXTURE_ROOT / "documents"

EXPECTED_CORPUS_ID = "phase4_rag_wiki_qa_v1"
EXPECTED_QUESTION_COUNT = 24
EXPECTED_DOCUMENT_COUNT = 9
ALLOWED_SOURCE_TYPES = {"document_chunk", "wiki_page"}
ALLOWED_RETRIEVAL_SCOPES = {"all", "document", "wiki"}
WIKI_ONLY_IDS = {"P4Q-017", "P4Q-018", "P4Q-019"}
INSUFFICIENT_IDS = {"P4Q-020", "P4Q-021"}
DISTRACTOR_ID = "TEST-DISTRACTOR-001"

PASS = "PASS"
FAIL = "FAIL"

SECRET_PATTERNS = (
    re.compile(r"WEKNORA_SERVICE_TOKEN\s*="),
    re.compile(r"WEKNORA_API_KEY\s*="),
    re.compile(r"CHAT_MODEL_API_KEY\s*="),
    re.compile(r"EMBEDDING_API_KEY\s*="),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)x-api-key\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}"),
    re.compile("sk" + r"-[A-Za-z0-9_-]{12,}"),
    re.compile(r"https?://[^\s\"'<>]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


class ContractError(RuntimeError):
    """Raised when the fixture contract is invalid."""


def main() -> int:
    gates = run_gates()
    failures = [gate for gate in gates if gate.status == FAIL]
    decision = "PASS" if not failures else "FAIL"

    print("Phase 5 fixture contract check")
    print(f"- decision: {decision}")
    print("- scope: fixture contract only; this is not real WeKnora PASS")
    for gate in gates:
        print(f"- {gate.name}: {gate.status} - {gate.detail}")
    return 0 if not failures else 1


def run_gates() -> list[Gate]:
    try:
        manifest = _read_json(MANIFEST_PATH)
        questions_payload = _read_json(QUESTIONS_PATH)
        hit_matrix_text = HIT_MATRIX_PATH.read_text(encoding="utf-8")
        document_texts = _read_document_texts()
    except OSError as exc:
        return [Gate("fixture files", FAIL, _safe_text(str(exc)))]
    except json.JSONDecodeError as exc:
        return [Gate("fixture JSON", FAIL, _safe_text(str(exc)))]

    checks = (
        ("fixture files", lambda: _check_files(manifest)),
        ("corpus identity", lambda: _check_corpus_identity(manifest, questions_payload, hit_matrix_text)),
        ("manifest documents", lambda: _check_manifest_documents(manifest, document_texts)),
        ("question contract", lambda: _check_questions(manifest, questions_payload)),
        ("hit matrix", lambda: _check_hit_matrix(questions_payload, hit_matrix_text)),
        ("sensitive info scan", lambda: _check_sensitive_text(manifest, questions_payload, hit_matrix_text, document_texts)),
    )

    gates: list[Gate] = []
    for name, check in checks:
        try:
            detail = check()
        except Exception as exc:  # noqa: BLE001
            gates.append(Gate(name, FAIL, _safe_text(str(exc))))
        else:
            gates.append(Gate(name, PASS, detail))
    return gates


def _check_files(manifest: dict[str, Any]) -> str:
    required = (MANIFEST_PATH, QUESTIONS_PATH, HIT_MATRIX_PATH, DOCUMENTS_ROOT)
    missing = [path.relative_to(PROJECT_ROOT).as_posix() for path in required if not path.exists()]
    _assert(not missing, "missing required fixture paths: " + ", ".join(missing))
    documents = manifest.get("documents")
    _assert(isinstance(documents, list), "manifest documents must be a list")
    missing_docs = []
    for item in documents:
        filename = str(item.get("filename") or "")
        if not filename or not (FIXTURE_ROOT / filename).is_file():
            missing_docs.append(filename or "<blank>")
    _assert(not missing_docs, "missing manifest document files: " + ", ".join(missing_docs))
    return "manifest, questions, hit_matrix, and document files are present"


def _check_corpus_identity(manifest: dict[str, Any], questions_payload: dict[str, Any], hit_matrix_text: str) -> str:
    _assert(manifest.get("corpus_id") == EXPECTED_CORPUS_ID, "manifest corpus_id mismatch")
    _assert(questions_payload.get("corpus_id") == EXPECTED_CORPUS_ID, "questions corpus_id mismatch")
    _assert(manifest.get("version") == questions_payload.get("version") == "1.0", "fixture version mismatch")
    _assert("questions.json" in hit_matrix_text, "hit_matrix must reference questions.json")
    _assert("Phase 4 RAG / Wiki / QA" in hit_matrix_text, "hit_matrix title mismatch")
    return f"manifest/questions use {EXPECTED_CORPUS_ID}; hit_matrix is tied to questions.json"


def _check_manifest_documents(manifest: dict[str, Any], document_texts: dict[str, str]) -> str:
    documents = manifest.get("documents")
    _assert(isinstance(documents, list), "manifest documents must be a list")
    _assert(len(documents) == EXPECTED_DOCUMENT_COUNT, f"manifest must contain {EXPECTED_DOCUMENT_COUNT} documents")
    upload_order = manifest.get("recommended_upload_order")
    _assert(isinstance(upload_order, list), "recommended_upload_order must be a list")
    _assert(len(upload_order) == EXPECTED_DOCUMENT_COUNT, "recommended_upload_order count mismatch")

    seen_anchors: set[str] = set()
    seen_filenames: set[str] = set()
    for item in documents:
        anchor = _required_str(item, "anchor")
        filename = _required_str(item, "filename")
        _assert(anchor not in seen_anchors, f"duplicate manifest anchor: {anchor}")
        _assert(filename not in seen_filenames, f"duplicate manifest filename: {filename}")
        seen_anchors.add(anchor)
        seen_filenames.add(filename)
        text = document_texts.get(filename)
        _assert(text is not None, f"manifest document text missing: {filename}")
        _assert(anchor in text, f"{filename} does not contain its anchor {anchor}")
        _assert(isinstance(item.get("key_terms"), list) and item["key_terms"], f"{anchor} missing key_terms")
        _assert(isinstance(item.get("test_purpose"), list) and item["test_purpose"], f"{anchor} missing test_purpose")

    _assert(DISTRACTOR_ID in seen_anchors, "distractor anchor missing from manifest")
    _assert("TEST-WIKI-001" in seen_anchors, "wiki anchor missing from manifest")
    upload_paths = {"documents/" + str(path) if not str(path).startswith("documents/") else str(path) for path in upload_order}
    _assert(upload_paths == seen_filenames, "recommended_upload_order must match manifest filenames")
    return f"{len(documents)} documents with unique anchors and existing files"


def _check_questions(manifest: dict[str, Any], questions_payload: dict[str, Any]) -> str:
    questions = questions_payload.get("questions")
    _assert(isinstance(questions, list), "questions must be a list")
    _assert(len(questions) == EXPECTED_QUESTION_COUNT, f"questions must contain {EXPECTED_QUESTION_COUNT} items")
    _assert(questions_payload.get("version") == manifest.get("version"), "question fixture version mismatch")
    _assert(manifest.get("question_count") == EXPECTED_QUESTION_COUNT, "manifest question_count mismatch")

    manifest_anchors = _manifest_anchors(manifest)
    expected_ids = {f"P4Q-{index:03d}" for index in range(1, EXPECTED_QUESTION_COUNT + 1)}
    actual_ids: set[str] = set()
    insufficient_ids: set[str] = set()
    wiki_only_ids: set[str] = set()
    forbidden_anchor_ids: set[str] = set()

    for question in questions:
        qid = _required_str(question, "id")
        _assert(qid not in actual_ids, f"duplicate question id: {qid}")
        actual_ids.add(qid)
        _assert(_required_str(question, "query"), f"{qid} missing query")
        _assert(_required_str(question, "type"), f"{qid} missing type")
        scope = _required_str(question, "retrieval_scope")
        _assert(scope in ALLOWED_RETRIEVAL_SCOPES, f"{qid} invalid retrieval_scope: {scope}")
        source_types = _list_of_str(question, "expected_source_types")
        _assert(set(source_types).issubset(ALLOWED_SOURCE_TYPES), f"{qid} has unsupported source types")
        anchors = _list_of_str(question, "expected_anchors")
        _assert(set(anchors).issubset(manifest_anchors), f"{qid} has unknown expected anchors")
        forbidden = _list_of_str(question, "forbidden_anchors", required=False)
        _assert(set(forbidden).issubset(manifest_anchors), f"{qid} has unknown forbidden anchors")
        _assert(not (set(anchors) & set(forbidden)), f"{qid} expected and forbidden anchors overlap")
        _assert(isinstance(question.get("expected_answer_points"), list), f"{qid} missing expected_answer_points")
        _assert(isinstance(question.get("must_cite_document"), bool), f"{qid} must_cite_document must be bool")
        _assert(isinstance(question.get("must_cite_wiki"), bool), f"{qid} must_cite_wiki must be bool")
        _assert(isinstance(question.get("should_answer_insufficient"), bool), f"{qid} should_answer_insufficient must be bool")

        if question["should_answer_insufficient"]:
            insufficient_ids.add(qid)
            _assert(not anchors, f"{qid} no-answer question must not define expected anchors")
            _assert(not source_types, f"{qid} no-answer question must not define expected source types")
            _assert(question["must_cite_document"] is False, f"{qid} no-answer question must not require document citation")
            _assert(question["must_cite_wiki"] is False, f"{qid} no-answer question must not require wiki citation")

        if scope == "wiki" or source_types == ["wiki_page"]:
            wiki_only_ids.add(qid)
            _assert(question["must_cite_wiki"] is True, f"{qid} wiki-only question must cite wiki")
            _assert(question["must_cite_document"] is False, f"{qid} wiki-only question must not require document citation")
            _assert(anchors == ["TEST-WIKI-001"], f"{qid} wiki-only question must use TEST-WIKI-001")
            _assert(source_types == ["wiki_page"], f"{qid} wiki-only source type must be wiki_page")

        if forbidden:
            forbidden_anchor_ids.add(qid)

    _assert(actual_ids == expected_ids, "question ids must be contiguous P4Q-001 through P4Q-024")
    _assert(wiki_only_ids == WIKI_ONLY_IDS, f"wiki-only ids mismatch: {sorted(wiki_only_ids)}")
    _assert(insufficient_ids == INSUFFICIENT_IDS, f"insufficient-evidence ids mismatch: {sorted(insufficient_ids)}")
    _assert("P4Q-022" in forbidden_anchor_ids, "P4Q-022 must define forbidden anchors")
    _assert(_question_by_id(questions, "P4Q-022")["forbidden_anchors"] == [DISTRACTOR_ID], "P4Q-022 must forbid distractor")
    _assert(_question_by_id(questions, "P4Q-023")["expected_anchors"] == [DISTRACTOR_ID], "P4Q-023 must expect distractor")
    return "24 questions, anchors, source types, wiki-only, no-answer, and distractor contracts are valid"


def _check_hit_matrix(questions_payload: dict[str, Any], hit_matrix_text: str) -> str:
    rows = _parse_hit_matrix_rows(hit_matrix_text)
    questions = questions_payload["questions"]
    question_by_id = {str(item["id"]): item for item in questions}
    _assert(set(rows) == set(question_by_id), "hit_matrix question ids must match questions.json")

    for qid, row in rows.items():
        question = question_by_id[qid]
        row_anchors = _split_anchor_cell(row["anchors"])
        _assert(row_anchors == _list_of_str(question, "expected_anchors"), f"{qid} hit_matrix anchors mismatch")
        _assert(row["scope"] == question["retrieval_scope"], f"{qid} hit_matrix scope mismatch")
        _assert(_zh_bool(row["must_document"]) == question["must_cite_document"], f"{qid} hit_matrix document citation mismatch")
        _assert(_zh_bool(row["must_wiki"]) == question["must_cite_wiki"], f"{qid} hit_matrix wiki citation mismatch")
        _assert(_zh_bool(row["insufficient"]) == question["should_answer_insufficient"], f"{qid} hit_matrix insufficient flag mismatch")

    return f"{len(rows)} hit_matrix rows match questions.json"


def _check_sensitive_text(
    manifest: dict[str, Any],
    questions_payload: dict[str, Any],
    hit_matrix_text: str,
    document_texts: dict[str, str],
) -> str:
    scans: dict[str, str] = {
        MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(): json.dumps(manifest, ensure_ascii=False),
        QUESTIONS_PATH.relative_to(PROJECT_ROOT).as_posix(): json.dumps(questions_payload, ensure_ascii=False),
        HIT_MATRIX_PATH.relative_to(PROJECT_ROOT).as_posix(): hit_matrix_text,
    }
    for filename, text in document_texts.items():
        scans[(FIXTURE_ROOT / filename).relative_to(PROJECT_ROOT).as_posix()] = text

    for name, text in scans.items():
        for pattern in SECRET_PATTERNS:
            _assert(not pattern.search(text), f"{name} matched sensitive pattern")
        for forbidden in (".env", "uploads/", "backend/data/", "node_modules/", "dist/", "BEGIN PRIVATE KEY"):
            _assert(forbidden not in text, f"{name} contains forbidden literal: {forbidden}")

    return f"scanned {len(scans)} fixture files without secret-shaped text"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _assert(isinstance(payload, dict), f"{path.name} must contain a JSON object")
    return payload


def _read_document_texts() -> dict[str, str]:
    if not DOCUMENTS_ROOT.is_dir():
        raise OSError(f"missing documents directory: {DOCUMENTS_ROOT}")
    return {
        path.relative_to(FIXTURE_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(DOCUMENTS_ROOT.glob("*.md"))
    }


def _manifest_anchors(manifest: dict[str, Any]) -> set[str]:
    documents = manifest.get("documents")
    _assert(isinstance(documents, list), "manifest documents must be a list")
    return {_required_str(item, "anchor") for item in documents}


def _question_by_id(questions: list[dict[str, Any]], qid: str) -> dict[str, Any]:
    for question in questions:
        if question.get("id") == qid:
            return question
    raise ContractError(f"missing question: {qid}")


def _parse_hit_matrix_rows(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| P4Q-"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        _assert(len(cells) >= 8, f"invalid hit_matrix row: {stripped}")
        qid = cells[0]
        rows[qid] = {
            "anchors": cells[2],
            "scope": cells[3],
            "must_document": cells[4],
            "must_wiki": cells[5],
            "insufficient": cells[6],
        }
    _assert(rows, "no P4Q rows found in hit_matrix")
    return rows


def _split_anchor_cell(value: str) -> list[str]:
    if value == "无":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _zh_bool(value: str) -> bool:
    if value == "是":
        return True
    if value == "否":
        return False
    raise ContractError(f"invalid Chinese boolean: {value}")


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    _assert(isinstance(value, str) and value.strip(), f"missing string field: {key}")
    return value.strip()


def _list_of_str(payload: dict[str, Any], key: str, *, required: bool = True) -> list[str]:
    value = payload.get(key)
    if value is None and not required:
        return []
    _assert(isinstance(value, list), f"{key} must be a list")
    result = []
    for item in value:
        _assert(isinstance(item, str) and item.strip(), f"{key} contains non-string or blank item")
        result.append(item.strip())
    return result


def _assert(condition: object, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _safe_text(value: str, limit: int = 320) -> str:
    redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]", value)
    redacted = re.sub(
        r"(?i)(authorization|x-api-key|api[_-]?key|token|secret|password)(\s*[:=]\s*)\S+",
        r"\1\2[redacted]",
        redacted,
    )
    redacted = re.sub("sk" + r"-[A-Za-z0-9_-]{12,}", "sk-[redacted]", redacted)
    redacted = re.sub(r"https?://[^\s\"'<>]+", "https://[redacted]", redacted)
    collapsed = " ".join(redacted.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
