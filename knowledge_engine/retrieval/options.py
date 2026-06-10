from __future__ import annotations

from typing import Any


RETRIEVAL_OPTIONS_KEY = "retrieval_options"
HYBRID_KEYS = {"enabled", "keyword_weight", "vector_weight", "match_count"}
RERANK_KEYS = {"enabled", "model", "top_n"}
THRESHOLD_KEYS = {"score"}


def normalize_retrieval_options(value: object | None) -> dict[str, Any]:
    if value in (None, ""):
        return {
            "hybrid": {"enabled": False},
            "rerank": {"enabled": False},
            "threshold": {},
        }
    if not isinstance(value, dict):
        raise ValueError("retrieval_options must be an object")

    unknown = sorted(set(value) - {"hybrid", "rerank", "threshold"})
    if unknown:
        raise ValueError("Unsupported retrieval_options key(s): " + ", ".join(unknown))

    hybrid = _normalize_hybrid(value.get("hybrid"))
    rerank = _normalize_rerank(value.get("rerank"))
    threshold = _normalize_threshold(value.get("threshold"))
    return {
        "hybrid": hybrid,
        "rerank": rerank,
        "threshold": threshold,
    }


def retrieval_options_payload(options: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    hybrid = options.get("hybrid") if isinstance(options.get("hybrid"), dict) else {}
    rerank = options.get("rerank") if isinstance(options.get("rerank"), dict) else {}
    threshold = options.get("threshold") if isinstance(options.get("threshold"), dict) else {}

    if hybrid.get("enabled"):
        payload["hybrid"] = {
            key: value
            for key, value in hybrid.items()
            if key != "enabled" and value is not None
        }
        payload["hybrid"]["enabled"] = True
    if rerank.get("enabled"):
        payload["rerank"] = {
            key: value
            for key, value in rerank.items()
            if key != "enabled" and value is not None
        }
        payload["rerank"]["enabled"] = True
    if threshold:
        payload["threshold"] = threshold
    return payload


def retrieval_debug_trace(options: dict[str, Any]) -> list[dict[str, Any]]:
    hybrid = options.get("hybrid") if isinstance(options.get("hybrid"), dict) else {}
    rerank = options.get("rerank") if isinstance(options.get("rerank"), dict) else {}
    threshold = options.get("threshold") if isinstance(options.get("threshold"), dict) else {}
    return [
        {
            "stage": "hybrid",
            "status": "requested" if hybrid.get("enabled") else "skipped",
            "reason": None if hybrid.get("enabled") else "not_enabled",
        },
        {
            "stage": "rerank",
            "status": "requested" if rerank.get("enabled") else "skipped",
            "reason": None if rerank.get("enabled") else "not_enabled",
        },
        {
            "stage": "threshold",
            "status": "requested" if threshold else "skipped",
            "reason": None if threshold else "not_enabled",
        },
    ]


def _normalize_hybrid(value: object | None) -> dict[str, Any]:
    if value in (None, ""):
        return {"enabled": False}
    if not isinstance(value, dict):
        raise ValueError("retrieval_options.hybrid must be an object")
    unknown = sorted(set(value) - HYBRID_KEYS)
    if unknown:
        raise ValueError("Unsupported retrieval_options.hybrid key(s): " + ", ".join(unknown))
    enabled = _bool(value.get("enabled"), default=False)
    output: dict[str, Any] = {"enabled": enabled}
    if "keyword_weight" in value:
        output["keyword_weight"] = _bounded_float(value["keyword_weight"], "keyword_weight")
    if "vector_weight" in value:
        output["vector_weight"] = _bounded_float(value["vector_weight"], "vector_weight")
    if "match_count" in value:
        output["match_count"] = _positive_int(value["match_count"], "match_count")
    return output


def _normalize_rerank(value: object | None) -> dict[str, Any]:
    if value in (None, ""):
        return {"enabled": False}
    if not isinstance(value, dict):
        raise ValueError("retrieval_options.rerank must be an object")
    unknown = sorted(set(value) - RERANK_KEYS)
    if unknown:
        raise ValueError("Unsupported retrieval_options.rerank key(s): " + ", ".join(unknown))
    enabled = _bool(value.get("enabled"), default=False)
    output: dict[str, Any] = {"enabled": enabled}
    if "model" in value and value.get("model") not in (None, ""):
        output["model"] = str(value["model"]).strip()[:120]
    if "top_n" in value:
        output["top_n"] = _positive_int(value["top_n"], "top_n")
    return output


def _normalize_threshold(value: object | None) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("retrieval_options.threshold must be an object")
    unknown = sorted(set(value) - THRESHOLD_KEYS)
    if unknown:
        raise ValueError("Unsupported retrieval_options.threshold key(s): " + ", ".join(unknown))
    output: dict[str, Any] = {}
    if "score" in value:
        output["score"] = _bounded_float(value["score"], "score")
    return output


def _bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("enabled must be a boolean")


def _bounded_float(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if number < 0 or number > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


def _positive_int(value: object, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if number <= 0 or number > 100:
        raise ValueError(f"{name} must be between 1 and 100")
    return number
