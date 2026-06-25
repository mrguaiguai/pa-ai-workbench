"""Live WNFC-P3-01 product-grade native model config source smoke.

The smoke starts a temporary PA backend and proves whether the running
WeKnora service exposes YAML-managed built-in model rows through PA. If the
native runtime has not loaded config/builtin_models.yaml or BUILTIN_MODELS_CONFIG,
the script records a truthful BLOCKED result instead of substituting PA env
variables or fixture models as source-of-truth evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_json


def main() -> int:
    backend_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-model-p3-01-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'model-p3-01.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, None)
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            model_status = _request_json(backend_port, "GET", "/api/model/status")
            _assert(model_status.get("config_source") == "pa_env_bridge", "model status identifies PA env bridge")
            _assert(
                model_status.get("native_source_of_truth_endpoint") == "/api/model/native/overview",
                "model status points to native source-of-truth endpoint",
            )
            _assert(_no_secret_payload(model_status), "model status excludes secret-shaped fields")

            overview = _request_json(backend_port, "GET", "/api/model/native/overview?limit=10")
            _assert(overview.get("source") == "weknora_api", "overview uses native WeKnora source")
            _assert(bool(overview.get("masked")), "overview is masked")
            _assert(_no_secret_payload(overview), "overview excludes secret-shaped fields")
            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            model_catalog = _surface(surfaces, "model_catalog")
            config_source = _surface(surfaces, "config_source")
            bridge_alignment = _surface(surfaces, "pa_bridge_alignment")
            _assert(model_catalog.get("status") == "live", "native model catalog is live")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=5")
            summary = (
                native_status.get("groups", {})
                .get("model_embedding_rerank_parser", {})
                .get("summary", {})
                if isinstance(native_status.get("groups"), dict)
                else {}
            )
            _assert(
                summary.get("config_source_status") == config_source.get("status"),
                "status center mirrors config source status",
            )
            _assert(
                summary.get("pa_bridge_alignment_status") == bridge_alignment.get("status"),
                "status center mirrors PA bridge alignment",
            )
            _assert(_no_secret_payload(native_status), "native status excludes secret-shaped fields")

            decision = _decision(config_source, bridge_alignment)
            print("WeKnora native product-grade model config source")
            print(f"- decision: {decision}")
            print(
                "- evidence_type: "
                + ("live api" if decision == "PASS" else "blocked evidence plus live api")
            )
            print(
                "- config_source: status={status} yaml_managed={count} missing_required={missing}".format(
                    status=config_source.get("status"),
                    count=int(config_source.get("yaml_managed_count") or 0),
                    missing=",".join(config_source.get("missing_required_types") or []) or "none",
                )
            )
            print(
                "- pa_bridge_alignment: status={status} bridge_status={bridge_status}".format(
                    status=bridge_alignment.get("status"),
                    bridge_status=model_status.get("bridge_status"),
                )
            )
            print(
                "- catalog: models={models} yaml_managed={yaml_managed}".format(
                    models=int(model_catalog.get("count") or 0),
                    yaml_managed=int(model_catalog.get("yaml_managed_count") or 0),
                )
            )
            if decision != "PASS":
                print(f"- blocker: {config_source.get('reason') or bridge_alignment.get('reason')}")
            return 0
        finally:
            _terminate(backend)


def _decision(config_source: dict[str, Any], bridge_alignment: dict[str, Any]) -> str:
    if config_source.get("status") == "live" and bridge_alignment.get("status") == "live":
        return "PASS"
    return "BLOCKED"


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _no_secret_payload(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    forbidden = [
        '"api_key":',
        '"app_secret":',
        '"authorization":',
        '"password":',
        '"secret_access_key":',
        '"base_url":',
        '"defaulturls":',
        '"custom_headers":',
    ]
    return not any(token in serialized for token in forbidden)


if __name__ == "__main__":
    raise SystemExit(main())
