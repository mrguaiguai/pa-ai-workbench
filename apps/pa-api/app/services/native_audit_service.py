from __future__ import annotations

import json
import re
from typing import Any

from sqlmodel import Session
from sqlmodel import select

from app.models import NativeMutationAudit

NATIVE_CHUNK_CONFIRM_PHRASE = "CONFIRM_NATIVE_CHUNK_MUTATION"
NATIVE_CHUNK_CONFIRM_PHRASE_ID = "native_chunk_mutation"

MAX_REASON_CHARS = 160
MAX_ERROR_CHARS = 500
MAX_TEXT_SUMMARY_CHARS = 180
MAX_LIST_SUMMARY_ITEMS = 8

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|body|content|credential|dsn|endpoint|"
    r"password|payload|private|prompt|raw|secret|token|url|vector)",
    re.IGNORECASE,
)
_SENSITIVE_TEXT_RE = re.compile(
    r"(Bearer\s+)[A-Za-z0-9._~+/=-]+|"
    r"(api[_-]?key|authorization|password|secret|token)(\s*[:=]\s*)\S+|"
    r"sk-[A-Za-z0-9_-]{12,}",
    re.IGNORECASE,
)


class NativeConfirmationError(ValueError):
    """Raised when a native mutation lacks the required operator confirmation."""


def require_native_confirmation(
    *,
    confirm: bool | None,
    confirm_token: str | None,
    expected_token: str,
    token_id: str,
    action: str,
) -> dict[str, Any]:
    token_value = str(confirm_token or "").strip()
    if token_value == expected_token:
        return {
            "required": True,
            "method": "confirm_token",
            "token_id": token_id,
            "action": action,
        }
    if confirm:
        return {
            "required": True,
            "method": "legacy_confirm_bool",
            "token_id": token_id,
            "action": action,
        }
    raise NativeConfirmationError(
        f"{action} requires confirm_token={expected_token}."
    )


def confirmation_surface(*, token_id: str, confirm_token: str, reason: str) -> dict[str, Any]:
    return {
        "required": True,
        "token_id": token_id,
        "confirm_token": confirm_token,
        "reason": reason,
    }


def masked_credential_status(
    *,
    configured: bool,
    field_count: int = 0,
    configured_field_count: int | None = None,
    source: str = "weknora_api",
) -> dict[str, Any]:
    resolved_configured = field_count if configured_field_count is None else configured_field_count
    return {
        "masked": True,
        "source": source,
        "configured": bool(configured),
        "status": "configured" if configured else "missing",
        "field_count": max(int(field_count or 0), 0),
        "configured_field_count": max(int(resolved_configured or 0), 0),
    }


def record_native_mutation_audit(
    *,
    session: Session,
    capability: str,
    operation: str,
    target_type: str,
    target_id: str | None,
    status: str,
    confirmation: dict[str, Any],
    reason: str | None = None,
    request_summary: dict[str, Any] | None = None,
    response_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
    source: str = "weknora_api",
) -> NativeMutationAudit:
    audit = NativeMutationAudit(
        capability=capability,
        operation=operation,
        target_type=target_type,
        target_id=_safe_identifier(target_id),
        source=source,
        status=status,
        confirmation_required=bool(confirmation.get("required", True)),
        confirmation_method=_safe_identifier(confirmation.get("method")),
        confirm_token_id=_safe_identifier(confirmation.get("token_id")),
        reason=_safe_reason(reason),
        request_summary_json=_safe_json(request_summary),
        response_summary_json=_safe_json(response_summary),
        error_message=_safe_error(error_message),
    )
    session.add(audit)
    session.flush()
    return audit


def update_native_mutation_audit(
    *,
    audit: NativeMutationAudit,
    status: str,
    response_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> NativeMutationAudit:
    audit.status = status
    audit.response_summary_json = _safe_json(response_summary)
    audit.error_message = _safe_error(error_message)
    return audit


def list_native_mutation_audits(
    *,
    session: Session,
    limit: int = 50,
    capability: str | None = None,
    operation: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    status: str | None = None,
    wnid_capability: str | None = None,
) -> list[NativeMutationAudit]:
    statement = select(NativeMutationAudit)
    if capability:
        statement = statement.where(NativeMutationAudit.capability == capability)
    if operation:
        statement = statement.where(NativeMutationAudit.operation == operation)
    if target_type:
        statement = statement.where(NativeMutationAudit.target_type == target_type)
    if target_id:
        statement = statement.where(NativeMutationAudit.target_id == target_id)
    if status:
        statement = statement.where(NativeMutationAudit.status == status)
    statement = statement.order_by(NativeMutationAudit.created_at.desc()).limit(
        max(min(limit, 100), 1)
    )
    audits = list(session.exec(statement).all())
    if wnid_capability and wnid_capability != "all":
        audits = [
            audit
            for audit in audits
            if native_audit_wnid_summary(audit)["wnid_capability"] == wnid_capability
        ]
    return audits


def native_audit_wnid_summary(audit: NativeMutationAudit) -> dict[str, str | None]:
    wnid_capability = _audit_wnid_capability(audit)
    if audit.status == "succeeded":
        evidence_state = "audit_succeeded"
    elif audit.status == "failed":
        evidence_state = "audit_failed"
    elif audit.status == "blocked":
        evidence_state = "audit_blocked"
    else:
        evidence_state = "audit_pending"
    return {
        "wnid_capability": wnid_capability,
        "wnid_evidence_state": evidence_state,
    }


def _safe_json(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return json.dumps(_safe_summary(value), ensure_ascii=False, sort_keys=True, default=str)


def _audit_wnid_capability(audit: NativeMutationAudit) -> str | None:
    operation = str(audit.operation or "")
    capability = str(audit.capability or "")
    if operation == "weknora_agent_strategy_update":
        return "strategy_mutation"
    if operation == "weknora_agentqa_wiki_mode_run":
        return "wiki_mode"
    if capability == "mcp":
        return "mcp_tools"
    if capability == "web_search":
        return "web_search"
    if capability == "custom_agent":
        return "react_agentqa"
    if capability == "wiki":
        return "wiki_mode"
    return None


def _safe_summary(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key)
            if _SENSITIVE_KEY_RE.search(normalized_key):
                if normalized_key.endswith("_id") or normalized_key in {"target_id", "document_id"}:
                    safe[normalized_key] = _safe_identifier(item)
                elif normalized_key in {"external_doc_id", "chunk_id", "question_id"}:
                    safe[normalized_key] = _safe_identifier(item)
                else:
                    safe[normalized_key] = "[redacted]"
                continue
            safe[normalized_key] = _safe_summary(item)
        return safe
    if isinstance(value, list):
        return [_safe_summary(item) for item in value[:MAX_LIST_SUMMARY_ITEMS]]
    if isinstance(value, tuple):
        return [_safe_summary(item) for item in list(value)[:MAX_LIST_SUMMARY_ITEMS]]
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return _safe_text(str(value))


def _safe_text(value: str) -> str:
    text = _SENSITIVE_TEXT_RE.sub("[redacted]", str(value or "").strip())
    if len(text) > MAX_TEXT_SUMMARY_CHARS:
        return text[:MAX_TEXT_SUMMARY_CHARS] + "..."
    return text


def _safe_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _safe_text(text)[:120]


def _safe_reason(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _safe_text(text)[:MAX_REASON_CHARS]


def _safe_error(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _safe_text(text)[:MAX_ERROR_CHARS]
