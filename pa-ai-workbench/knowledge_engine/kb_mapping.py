from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import os

from knowledge_engine.errors import KnowledgeBackendUnavailableError


SELECTOR_KEYS = (
    "kb_mapping",
    "kb_scope",
    "kb_name",
    "business_area",
    "team",
    "pilot",
    "workspace",
    "document_type",
)
EXPLICIT_KB_KEYS = (
    "knowledge_base_ids",
    "knowledge_base_id",
    "kb_ids",
    "kb_id",
)


@dataclass(frozen=True)
class KbMappingEntry:
    name: str
    workspace_id: str
    kb_id: str
    selectors: dict[str, str]


@dataclass(frozen=True)
class KbTarget:
    workspace_id: str | None
    kb_id: str
    mapping_name: str | None
    selection_source: str
    default_used: bool = False

    def metadata(self) -> dict[str, str | bool]:
        data: dict[str, str | bool] = {
            "kb_selection_source": self.selection_source,
            "kb_default_used": self.default_used,
        }
        if self.mapping_name:
            data["kb_mapping_name"] = self.mapping_name
        return data


class KbMappingResolver:
    def __init__(
        self,
        *,
        default_workspace_id: str | None = None,
        default_kb_id: str | None = None,
        mapping_config: str | None = None,
        allow_default: bool | None = None,
    ) -> None:
        self.default_workspace_id = _clean(default_workspace_id or os.getenv("WEKNORA_WORKSPACE_ID", ""))
        self.default_kb_id = _clean(default_kb_id or os.getenv("WEKNORA_DEFAULT_KB_ID", ""))
        raw_config = mapping_config if mapping_config is not None else os.getenv("WEKNORA_KB_MAPPINGS", "")
        parsed_config = _parse_mapping_config(raw_config)
        self.entries = parsed_config["entries"]
        env_allow_default = _env_bool("WEKNORA_KB_ALLOW_DEFAULT", True)
        self.allow_default = (
            parsed_config["allow_default"]
            if parsed_config["allow_default"] is not None
            else env_allow_default
            if allow_default is None
            else allow_default
        )

    def resolve_one(
        self,
        selectors: dict | None = None,
        *,
        explicit_kb_id: str | None = None,
        operation: str = "knowledge",
    ) -> KbTarget:
        merged = dict(selectors or {})
        if explicit_kb_id:
            merged["kb_id"] = explicit_kb_id
        explicit = _first_explicit_kb_ids(merged)
        if explicit:
            if len(explicit) > 1:
                raise KnowledgeBackendUnavailableError(
                    f"{operation} requires a single knowledge base mapping."
                )
            return self._target_for_explicit_kb(explicit[0], operation=operation)

        entry = self._match_entry(merged)
        if entry is not None:
            return KbTarget(
                workspace_id=entry.workspace_id,
                kb_id=entry.kb_id,
                mapping_name=entry.name,
                selection_source="mapping",
            )
        return self._default_target(operation=operation)

    def resolve_many(
        self,
        selectors: dict | None = None,
        *,
        operation: str = "retrieve",
    ) -> list[KbTarget]:
        selectors = dict(selectors or {})
        explicit = _first_explicit_kb_ids(selectors)
        if explicit:
            return [
                self._target_for_explicit_kb(kb_id, operation=operation)
                for kb_id in explicit
            ]
        entry = self._match_entry(selectors)
        if entry is not None:
            return [
                KbTarget(
                    workspace_id=entry.workspace_id,
                    kb_id=entry.kb_id,
                    mapping_name=entry.name,
                    selection_source="mapping",
                )
            ]
        return [self._default_target(operation=operation)]

    def public_summary(self) -> dict[str, Any]:
        selectors = sorted(
            {
                key
                for entry in self.entries
                for key, value in entry.selectors.items()
                if value
            }
        )
        return {
            "schema_version": "p3-m3-a4",
            "configured": bool(self.entries),
            "mapping_count": len(self.entries),
            "selector_keys": selectors,
            "default_workspace_configured": bool(self.default_workspace_id),
            "default_kb_configured": bool(self.default_kb_id),
            "default_fallback_allowed": self.allow_default,
            "ids_redacted": True,
        }

    def _match_entry(self, selectors: dict) -> KbMappingEntry | None:
        normalized = _selector_values(selectors)
        if not normalized:
            return None
        for entry in self.entries:
            if entry.name and entry.name in {
                normalized.get("kb_mapping"),
                normalized.get("kb_scope"),
                normalized.get("kb_name"),
            }:
                return entry
            if any(
                normalized.get(key) == value
                for key, value in entry.selectors.items()
                if value
            ):
                return entry
        if self.entries:
            raise KnowledgeBackendUnavailableError(
                "No WeKnora KB mapping matched the request selectors."
            )
        return None

    def _target_for_explicit_kb(self, kb_id: str, *, operation: str) -> KbTarget:
        named_entry = self._entry_by_name(kb_id)
        if named_entry is not None:
            return KbTarget(
                workspace_id=named_entry.workspace_id,
                kb_id=named_entry.kb_id,
                mapping_name=named_entry.name,
                selection_source="explicit_mapping_name",
            )
        entry = self._entry_by_kb_id(kb_id)
        if entry is not None:
            return KbTarget(
                workspace_id=entry.workspace_id,
                kb_id=entry.kb_id,
                mapping_name=entry.name,
                selection_source="explicit_allowed_mapping",
            )
        if kb_id == self.default_kb_id and self.default_kb_id and self.allow_default:
            return KbTarget(
                workspace_id=self.default_workspace_id,
                kb_id=kb_id,
                mapping_name=None,
                selection_source="explicit_default",
                default_used=True,
            )
        if self.entries:
            raise KnowledgeBackendUnavailableError(
                f"{operation} requested a knowledge base outside configured mappings."
            )
        return KbTarget(
            workspace_id=self.default_workspace_id,
            kb_id=kb_id,
            mapping_name=None,
            selection_source="explicit_unmapped",
        )

    def _default_target(self, *, operation: str) -> KbTarget:
        if self.default_kb_id and (self.allow_default or not self.entries):
            return KbTarget(
                workspace_id=self.default_workspace_id,
                kb_id=self.default_kb_id,
                mapping_name=None,
                selection_source="default",
                default_used=True,
            )
        raise KnowledgeBackendUnavailableError(
            f"No WeKnora KB mapping resolved for {operation}, and default fallback is disabled."
        )

    def _entry_by_kb_id(self, kb_id: str) -> KbMappingEntry | None:
        for entry in self.entries:
            if entry.kb_id == kb_id:
                return entry
        return None

    def _entry_by_name(self, name: str) -> KbMappingEntry | None:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


def _parse_mapping_config(raw_config: str | None) -> dict[str, Any]:
    raw = (raw_config or "").strip()
    if not raw:
        return {"entries": [], "allow_default": None}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KnowledgeBackendUnavailableError("WEKNORA_KB_MAPPINGS is invalid JSON") from exc

    allow_default = None
    raw_entries: list[Any]
    if isinstance(parsed, list):
        raw_entries = parsed
    elif isinstance(parsed, dict):
        raw_entries = parsed.get("mappings") if isinstance(parsed.get("mappings"), list) else []
        if isinstance(parsed.get("allow_default"), bool):
            allow_default = parsed["allow_default"]
    else:
        raise KnowledgeBackendUnavailableError("WEKNORA_KB_MAPPINGS must be an object or list")

    entries = [_entry_from_raw(item) for item in raw_entries if isinstance(item, dict)]
    return {"entries": entries, "allow_default": allow_default}


def _entry_from_raw(item: dict) -> KbMappingEntry:
    name = _clean(item.get("name") or item.get("kb_mapping") or item.get("kb_scope"))
    workspace_id = _clean(item.get("workspace_id") or item.get("workspace"))
    kb_id = _clean(item.get("kb_id") or item.get("knowledge_base_id"))
    if not name or not kb_id:
        raise KnowledgeBackendUnavailableError("Each KB mapping requires name and kb_id")
    raw_selectors = item.get("selectors")
    selectors = _selector_values(raw_selectors if isinstance(raw_selectors, dict) else item)
    selectors.pop("kb_id", None)
    return KbMappingEntry(
        name=name,
        workspace_id=workspace_id,
        kb_id=kb_id,
        selectors=selectors,
    )


def _selector_values(values: dict | None) -> dict[str, str]:
    output: dict[str, str] = {}
    for key in SELECTOR_KEYS:
        value = _clean((values or {}).get(key))
        if value:
            output[key] = value
    return output


def _first_explicit_kb_ids(values: dict) -> list[str]:
    for key in EXPLICIT_KB_KEYS:
        ids = _list_value(values.get(key))
        if ids:
            return ids
    return []


def _list_value(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        values = [str(part).strip() for part in value]
    else:
        values = [str(value).strip()]
    return [value for value in values if value]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "KbMappingEntry",
    "KbMappingResolver",
    "KbTarget",
]
