from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


ALLOWED_WEKNORA_LOG_CONTEXT_KEYS = {
    "correlation_id",
    "task_id",
    "conversation_id",
    "document_id",
    "wiki_page_id",
    "output_id",
}

_WEKNORA_LOG_CONTEXT: ContextVar[dict[str, str]] = ContextVar(
    "weknora_log_context",
    default={},
)


@contextmanager
def weknora_log_context(**fields: object) -> Iterator[None]:
    current = dict(_WEKNORA_LOG_CONTEXT.get())
    update = {
        key: str(value).strip()
        for key, value in fields.items()
        if key in ALLOWED_WEKNORA_LOG_CONTEXT_KEYS and value not in (None, "")
    }
    token = _WEKNORA_LOG_CONTEXT.set({**current, **update})
    try:
        yield
    finally:
        _WEKNORA_LOG_CONTEXT.reset(token)


def current_weknora_log_context() -> dict[str, str]:
    return dict(_WEKNORA_LOG_CONTEXT.get())
