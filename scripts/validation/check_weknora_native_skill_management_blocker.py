"""Live WNFC-P4-03 native skill management smoke.

The script proves the current native/PA skill path truthfully: native WeKnora
now exposes SKILL.md list/read/create/update/delete/test routes, while PA gates
create/update/delete/test with confirmation and NativeMutationAudit. The native
test endpoint validates metadata/files only; it does not execute scripts.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import quote
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pa-api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from check_weknora_native_chunk_management import _start_backend_with_cors
from check_weknora_native_faq_workflow import _dump_capability_dom
from check_weknora_native_faq_workflow import _no_secret_payload
from check_weknora_native_kb_management import _assert
from check_weknora_native_kb_management import _free_port
from check_weknora_native_kb_management import _request_json
from check_weknora_native_kb_management import _start_frontend
from check_weknora_native_kb_management import _terminate
from check_weknora_native_kb_management import _wait_for_html
from check_weknora_native_kb_management import _wait_for_json


CONFIRM_TOKEN = "CONFIRM_NATIVE_SKILL_MUTATION"


def main() -> int:
    browser_mode = "--browser" in sys.argv[1:]
    backend_port = _free_port()
    frontend_port = _free_port() if browser_mode else None
    skill_name = f"wnfc-p4-03-{uuid4().hex[:8]}"
    encoded_name = quote(skill_name, safe="")
    created = False
    with tempfile.TemporaryDirectory(prefix="pa-wnfc-skills-") as temp_dir:
        database_url = f"sqlite:///{Path(temp_dir) / 'skills-p4-03.db'}"
        backend = _start_backend_with_cors(backend_port, database_url, frontend_port)
        frontend: subprocess.Popen[str] | None = None
        try:
            _wait_for_json(f"http://127.0.0.1:{backend_port}/health")
            overview = _request_json(backend_port, "GET", "/api/organization/native/overview?limit=10")
            _assert(_no_secret_payload(overview), "organization overview is sanitized")
            surfaces = overview.get("surfaces") if isinstance(overview.get("surfaces"), dict) else {}
            skills = _surface(surfaces, "skills")
            mutations = _surface(surfaces, "mutations")
            _assert(skills.get("status") == "live", "native skill list is live")
            _assert(skills.get("read_status") == "live", "native skill read is live")
            _assert(skills.get("management_status") == "live", "native skill management routes are live")
            _assert(skills.get("management_scope") == "managed_skill_md_only", "skill management scope is explicit")
            _assert(skills.get("test_status") == "confirmation_required", "skill test is confirmation-gated")
            _assert(skills.get("script_upload_status") == "not_supported", "script upload boundary is explicit")
            _assert(mutations.get("skill_mutations") == "live", "skill mutations are live")

            blocked = _request_json(
                backend_port,
                "POST",
                "/api/organization/native/skills",
                _skill_payload(skill_name, confirm_token="WRONG"),
            )
            _assert(_no_secret_payload(blocked), "blocked create response is sanitized")
            blocked_surface = _surface(blocked.get("surfaces") if isinstance(blocked.get("surfaces"), dict) else {}, "create")
            _assert(blocked_surface.get("status") == "blocked", "wrong token blocks skill create")

            created_response = _request_json(
                backend_port,
                "POST",
                "/api/organization/native/skills",
                _skill_payload(skill_name, confirm_token=CONFIRM_TOKEN),
            )
            created = True
            _assert(_no_secret_payload(created_response), "create response is sanitized")
            create_surface = _surface(created_response.get("surfaces") if isinstance(created_response.get("surfaces"), dict) else {}, "create")
            _assert(create_surface.get("status") == "live", "confirmed skill create is live")
            _assert(_audit_operation(created_response, "weknora_skill_create"), "skill create audit recorded")

            read_response = _request_json(backend_port, "GET", f"/api/organization/native/skills/{encoded_name}")
            _assert(_no_secret_payload(read_response), "read response is sanitized")
            read_surface = _surface(read_response.get("surfaces") if isinstance(read_response.get("surfaces"), dict) else {}, "skill_read")
            _assert(read_surface.get("status") == "live", "skill read through PA is live")
            read_skill = read_surface.get("skill") if isinstance(read_surface.get("skill"), dict) else {}
            _assert(read_skill.get("instructions_present") is True, "skill read exposes safe instruction presence")

            updated_response = _request_json(
                backend_port,
                "PUT",
                f"/api/organization/native/skills/{encoded_name}",
                _skill_payload(skill_name, description="Updated WNFC skill management proof.", confirm_token=CONFIRM_TOKEN),
            )
            _assert(_no_secret_payload(updated_response), "update response is sanitized")
            update_surface = _surface(updated_response.get("surfaces") if isinstance(updated_response.get("surfaces"), dict) else {}, "update")
            _assert(update_surface.get("status") == "live", "confirmed skill update is live")
            _assert(_audit_operation(updated_response, "weknora_skill_update"), "skill update audit recorded")

            tested_response = _request_json(
                backend_port,
                "POST",
                f"/api/organization/native/skills/{encoded_name}/test",
                {"confirm_token": CONFIRM_TOKEN},
            )
            _assert(_no_secret_payload(tested_response), "test response is sanitized")
            test_surface = _surface(tested_response.get("surfaces") if isinstance(tested_response.get("surfaces"), dict) else {}, "test")
            skill_test = test_surface.get("skill_test") if isinstance(test_surface.get("skill_test"), dict) else {}
            _assert(test_surface.get("status") == "live", "confirmed skill test is live")
            _assert(skill_test.get("valid") is True, "skill test validates metadata")
            _assert(skill_test.get("execution_performed") is False, "skill test does not execute scripts")
            _assert(_audit_operation(tested_response, "weknora_skill_test"), "skill test audit recorded")

            deleted_response = _request_json(
                backend_port,
                "DELETE",
                f"/api/organization/native/skills/{encoded_name}",
                {"confirm_token": CONFIRM_TOKEN},
            )
            created = False
            _assert(_no_secret_payload(deleted_response), "delete response is sanitized")
            delete_surface = _surface(deleted_response.get("surfaces") if isinstance(deleted_response.get("surfaces"), dict) else {}, "delete")
            _assert(delete_surface.get("status") == "live", "confirmed skill delete is live")
            _assert(delete_surface.get("deleted") is True, "skill delete returned deleted=true")
            _assert(_audit_operation(deleted_response, "weknora_skill_delete"), "skill delete audit recorded")

            audit_events = _request_json(backend_port, "GET", "/api/native-audit/events?capability=skill&limit=10")
            _assert(_no_secret_payload(audit_events), "audit response is sanitized")
            operations = {
                item.get("operation")
                for item in audit_events.get("items", [])
                if isinstance(item, dict) and item.get("status") == "succeeded"
            }
            for operation in (
                "weknora_skill_create",
                "weknora_skill_update",
                "weknora_skill_test",
                "weknora_skill_delete",
            ):
                _assert(operation in operations, f"{operation} audit exists")

            native_status = _request_json(backend_port, "GET", "/api/native/status?limit=10")
            groups = native_status.get("groups") if isinstance(native_status.get("groups"), dict) else {}
            organization = groups.get("faq_tags_favorites_skills") if isinstance(groups.get("faq_tags_favorites_skills"), dict) else {}
            summary = organization.get("summary") if isinstance(organization.get("summary"), dict) else {}
            _assert(summary.get("skill_read_status") == "live", "status center exposes skill read live")
            _assert(summary.get("skill_management_status") == "live", "status center exposes management live")
            _assert(summary.get("skill_test_status") == "confirmation_required", "status center exposes test confirmation gate")
            _assert(summary.get("skill_mutations") == "live", "status center exposes mutation live")

            if browser_mode:
                assert frontend_port is not None
                frontend = _start_frontend(frontend_port, backend_port)
                _wait_for_html(f"http://127.0.0.1:{frontend_port}/index.html")
                dom = _dump_capability_dom(frontend_port, Path(temp_dir) / "chrome-profile")
                for marker in (
                    "FAQ / tags / favorites / skills",
                    "skill_read_status: live",
                    "skill_management_status: live",
                    "skill_test_status: confirmation_required",
                    "skill_mutations: live",
                    "skill_management_scope: managed_skill_md_only",
                    "/api/organization/native/overview",
                ):
                    _assert(marker in dom, f"browser DOM contains {marker}")

            print("WeKnora native skill management")
            print("- decision: PASS")
            print("- evidence_type: live api/browser plus audit proof" if browser_mode else "- evidence_type: live api plus audit proof")
            print("- skills: list=live read=live create=live update=live delete=live test=live")
            print("- test_scope: metadata/file validation only; execution_performed=false")
            print("- audit: create/update/test/delete succeeded")
            if browser_mode:
                print("- browser: Capability Center rendered skill management live/status proof")
            print("- output: sanitized")
            return 0
        finally:
            if created:
                try:
                    _request_json(
                        backend_port,
                        "DELETE",
                        f"/api/organization/native/skills/{encoded_name}",
                        {"confirm_token": CONFIRM_TOKEN},
                    )
                except Exception:
                    pass
            _terminate(frontend)
            _terminate(backend)


def _skill_payload(
    name: str,
    *,
    description: str = "WNFC skill management proof.",
    confirm_token: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "instructions": "Use this temporary skill only to validate the WNFC-P4-03 managed SKILL.md lifecycle.",
        "confirm_token": confirm_token,
    }


def _surface(surfaces: dict[str, Any], name: str) -> dict[str, Any]:
    surface = surfaces.get(name)
    _assert(isinstance(surface, dict), f"{name} surface is present")
    return surface


def _audit_operation(response: dict[str, Any], operation: str) -> bool:
    audit = response.get("audit") if isinstance(response.get("audit"), dict) else {}
    return audit.get("operation") == operation and audit.get("status") == "succeeded"


if __name__ == "__main__":
    raise SystemExit(main())
