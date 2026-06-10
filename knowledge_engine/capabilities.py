from __future__ import annotations

import os
from copy import deepcopy
from typing import Any


SUPPORTED_BACKENDS = ("mock", "weknora_api", "extracted")
CAPABILITY_STATUSES = {"supported", "partial", "unsupported", "dev-only"}
CAPABILITY_ORDER = (
    "document_upload",
    "document_status",
    "document_chunks",
    "rag_retrieve",
    "rag_debug",
    "wiki_search",
    "wiki_read",
    "wiki_create_update_publish",
    "citation_trace",
    "status_recovery",
    "real_data_source",
)
FEATURE_FLAG_SCHEMA_VERSION = "p3-m3-a3"
RELEASE_ENVIRONMENTS = {
    "prod",
    "production",
    "release",
    "pilot",
    "staging",
    "stage",
    "intranet",
}

BACKEND_CAPABILITY_MATRIX: dict[str, dict[str, str]] = {
    "mock": {
        "document_upload": "dev-only",
        "document_status": "dev-only",
        "document_chunks": "unsupported",
        "rag_retrieve": "dev-only",
        "rag_debug": "dev-only",
        "wiki_search": "dev-only",
        "wiki_read": "dev-only",
        "wiki_create_update_publish": "unsupported",
        "citation_trace": "unsupported",
        "status_recovery": "dev-only",
        "real_data_source": "unsupported",
    },
    "weknora_api": {
        "document_upload": "supported",
        "document_status": "supported",
        "document_chunks": "supported",
        "rag_retrieve": "supported",
        "rag_debug": "supported",
        "wiki_search": "supported",
        "wiki_read": "supported",
        "wiki_create_update_publish": "supported",
        "citation_trace": "supported",
        "status_recovery": "supported",
        "real_data_source": "supported",
    },
    "extracted": {
        "document_upload": "partial",
        "document_status": "partial",
        "document_chunks": "partial",
        "rag_retrieve": "partial",
        "rag_debug": "partial",
        "wiki_search": "partial",
        "wiki_read": "partial",
        "wiki_create_update_publish": "partial",
        "citation_trace": "partial",
        "status_recovery": "partial",
        "real_data_source": "unsupported",
    },
}


def normalize_backend_name(value: str | None) -> str:
    return (value or "mock").strip().lower() or "mock"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_strict_fallback_mode(
    app_env: str | None = None,
    mock_mode: bool | None = None,
) -> bool:
    normalized_env = (app_env or os.getenv("APP_ENV", "local")).strip().lower()
    if normalized_env in RELEASE_ENVIRONMENTS:
        return True
    selected_mock_mode = env_bool("MOCK_MODE", True) if mock_mode is None else mock_mode
    return not selected_mock_mode


def should_fail_closed_for_unavailable_backend(
    backend_name: str | None,
    *,
    app_env: str | None = None,
    mock_mode: bool | None = None,
) -> bool:
    selected = normalize_backend_name(backend_name)
    if selected in {"mock", "extracted"}:
        return False
    return is_strict_fallback_mode(app_env=app_env, mock_mode=mock_mode)


def capability_status_counts(capabilities: dict[str, str]) -> dict[str, int]:
    return {
        status: sum(1 for value in capabilities.values() if value == status)
        for status in sorted(CAPABILITY_STATUSES)
    }


def backend_parity_summary(
    *,
    backend_name: str,
    capabilities: dict[str, str],
    release_eligible: bool,
    fail_closed: bool,
) -> dict[str, Any]:
    unsupported = [
        capability
        for capability in CAPABILITY_ORDER
        if capabilities.get(capability) == "unsupported"
    ]
    partial = [
        capability
        for capability in CAPABILITY_ORDER
        if capabilities.get(capability) == "partial"
    ]
    dev_only = [
        capability
        for capability in CAPABILITY_ORDER
        if capabilities.get(capability) == "dev-only"
    ]
    return {
        "backend": backend_name,
        "release_evidence": release_eligible,
        "quality_limit": _quality_limit(backend_name),
        "data_fact_source": _data_fact_source(backend_name),
        "citation_trace": capabilities.get("citation_trace", "unsupported"),
        "wiki": capabilities.get("wiki_create_update_publish", "unsupported"),
        "debug": capabilities.get("rag_debug", "unsupported"),
        "status_recovery": capabilities.get("status_recovery", "unsupported"),
        "unsupported_capabilities": unsupported,
        "partial_capabilities": partial,
        "dev_only_capabilities": dev_only,
        "status_counts": capability_status_counts(capabilities),
        "unsupported_must_fail": True,
        "fail_closed": fail_closed,
    }


def backend_feature_flags(
    *,
    backend_name: str,
    capabilities: dict[str, str],
    release_eligible: bool,
    fail_closed: bool,
) -> dict[str, Any]:
    probes = capability_probes(
        backend_name=backend_name,
        capabilities=capabilities,
        release_eligible=release_eligible,
    )
    return {
        "schema_version": FEATURE_FLAG_SCHEMA_VERSION,
        "backend": backend_name,
        "ui": {
            "can_upload_documents": _available(capabilities, "document_upload"),
            "can_view_document_chunks": _available(capabilities, "document_chunks"),
            "can_retrieve": _available(capabilities, "rag_retrieve"),
            "can_debug_retrieve": _available(capabilities, "rag_debug"),
            "can_search_wiki": _available(capabilities, "wiki_search"),
            "can_read_wiki": _available(capabilities, "wiki_read"),
            "can_create_update_publish_wiki": _supported(
                capabilities,
                "wiki_create_update_publish",
            ),
            "can_recover_status": _available(capabilities, "status_recovery"),
            "can_use_real_citations": _real_citations_supported(
                capabilities=capabilities,
                release_eligible=release_eligible,
            ),
            "can_count_release_evidence": _release_evidence_supported(
                capabilities=capabilities,
                release_eligible=release_eligible,
            ),
        },
        "agent": {
            "can_retrieve": _available(capabilities, "rag_retrieve"),
            "can_read_wiki": _available(capabilities, "wiki_read"),
            "can_publish_wiki": _supported(capabilities, "wiki_create_update_publish"),
            "can_use_real_citations": _real_citations_supported(
                capabilities=capabilities,
                release_eligible=release_eligible,
            ),
            "must_not_call": [
                capability
                for capability in CAPABILITY_ORDER
                if capabilities.get(capability) == "unsupported"
            ],
            "requires_citation_trace_for_real_citation": True,
        },
        "rules": {
            "unsupported_behavior": "hide_disable_or_fail",
            "dev_only_release_evidence_allowed": False,
            "partial_release_evidence_allowed": False,
            "fail_closed": fail_closed,
        },
        "probes": probes,
    }


def capability_probes(
    *,
    backend_name: str,
    capabilities: dict[str, str],
    release_eligible: bool,
) -> dict[str, dict[str, Any]]:
    return {
        capability: {
            "status": capabilities.get(capability, "unsupported"),
            "available": capabilities.get(capability) != "unsupported",
            "release_evidence": (
                release_eligible
                and backend_name == "weknora_api"
                and capabilities.get(capability) == "supported"
            ),
            "ui_policy": _ui_policy(capability, capabilities.get(capability, "unsupported")),
            "agent_policy": _agent_policy(capability, capabilities.get(capability, "unsupported")),
        }
        for capability in CAPABILITY_ORDER
    }


def backend_capability_snapshot(
    *,
    backend_name: str | None,
    app_env: str | None,
    mock_mode: bool,
    weknora_configured: bool | None = None,
) -> dict[str, Any]:
    selected = normalize_backend_name(backend_name)
    known_backend = selected in BACKEND_CAPABILITY_MATRIX
    active_backend = selected if known_backend else "mock"
    strict_mode = is_strict_fallback_mode(app_env=app_env, mock_mode=mock_mode)
    weknora_ready = bool(weknora_configured) if weknora_configured is not None else None
    selected_weknora_missing = selected == "weknora_api" and weknora_ready is False
    unknown_backend = selected not in BACKEND_CAPABILITY_MATRIX
    fallback_to_mock_would_be_silent = unknown_backend or selected_weknora_missing
    fail_closed = strict_mode and fallback_to_mock_would_be_silent
    release_eligible = selected == "weknora_api" and weknora_ready is not False
    capabilities = deepcopy(BACKEND_CAPABILITY_MATRIX[active_backend])

    return {
        "active_backend": active_backend,
        "selected_backend": selected,
        "environment": (app_env or "local").strip().lower() or "local",
        "strict_fallback_mode": strict_mode,
        "known_backend": known_backend,
        "release_eligible": release_eligible,
        "capabilities": capabilities,
        "matrix": deepcopy(BACKEND_CAPABILITY_MATRIX),
        "fallback_policy": {
            "mock_release_pass_allowed": False,
            "silent_mock_fallback_allowed": not strict_mode,
            "extracted_fallback": "explicit-only",
            "weknora_missing_config": "fail-closed" if strict_mode else "dev-test-mock",
            "unknown_backend": "fail-closed" if strict_mode else "dev-test-mock",
            "citation_trace_required_for_real_citation": True,
            "fail_closed": fail_closed,
        },
        "parity_summary": backend_parity_summary(
            backend_name=active_backend,
            capabilities=capabilities,
            release_eligible=release_eligible,
            fail_closed=fail_closed,
        ),
        "feature_flags": backend_feature_flags(
            backend_name=active_backend,
            capabilities=capabilities,
            release_eligible=release_eligible,
            fail_closed=fail_closed,
        ),
        "retrieval_parameters": {
            "schema_version": "p3-m3-c1",
            "requires_explicit_enable": True,
            "default_forwarding": False,
            "hybrid": "reserved" if active_backend == "weknora_api" else "local_or_unsupported",
            "rerank": "reserved" if active_backend == "weknora_api" else "unsupported",
            "threshold": "reserved" if active_backend == "weknora_api" else "local_or_unsupported",
        },
        "notes": [
            "Mock and extracted results must not be counted as WeKnora release evidence.",
            "Extracted is selectable only as an explicit backend, never as automatic fallback.",
            "Evidence without citation trace must not be marked as a real WeKnora citation.",
        ],
    }


def _data_fact_source(backend_name: str) -> str:
    if backend_name == "weknora_api":
        return "WeKnora KB/Wiki"
    if backend_name == "extracted":
        return "local extracted fixtures"
    return "synthetic mock data"


def _quality_limit(backend_name: str) -> str:
    if backend_name == "weknora_api":
        return "release candidate after live gates"
    if backend_name == "extracted":
        return "local fallback only; no WeKnora parity guarantee"
    return "demo only; no release evidence"


def _available(capabilities: dict[str, str], capability: str) -> bool:
    return capabilities.get(capability) != "unsupported"


def _supported(capabilities: dict[str, str], capability: str) -> bool:
    return capabilities.get(capability) == "supported"


def _real_citations_supported(
    *,
    capabilities: dict[str, str],
    release_eligible: bool,
) -> bool:
    return (
        release_eligible
        and capabilities.get("citation_trace") == "supported"
        and capabilities.get("real_data_source") == "supported"
    )


def _release_evidence_supported(
    *,
    capabilities: dict[str, str],
    release_eligible: bool,
) -> bool:
    return release_eligible and capabilities.get("real_data_source") == "supported"


def _ui_policy(capability: str, status: str) -> str:
    if status == "unsupported":
        return "hide_or_disable"
    if capability == "wiki_create_update_publish" and status != "supported":
        return "disable_write_action"
    if status in {"partial", "dev-only"}:
        return "show_with_badge"
    return "show"


def _agent_policy(capability: str, status: str) -> str:
    if status == "unsupported":
        return "block"
    if capability in {"citation_trace", "real_data_source"} and status != "supported":
        return "fallback_only"
    if status in {"partial", "dev-only"}:
        return "allow_non_release"
    return "allow"


__all__ = [
    "BACKEND_CAPABILITY_MATRIX",
    "CAPABILITY_ORDER",
    "CAPABILITY_STATUSES",
    "RELEASE_ENVIRONMENTS",
    "SUPPORTED_BACKENDS",
    "FEATURE_FLAG_SCHEMA_VERSION",
    "backend_parity_summary",
    "backend_feature_flags",
    "backend_capability_snapshot",
    "capability_probes",
    "capability_status_counts",
    "env_bool",
    "is_strict_fallback_mode",
    "normalize_backend_name",
    "should_fail_closed_for_unavailable_backend",
]
