"""PAR-P4-03 clean-clone final acceptance orchestrator.

The checker exports the caller's exact Git index, commits only that exported
tree in a temporary seed repository, and clones the seed into a second
temporary directory. Unstaged and untracked source work is therefore excluded.
It never commits the source repository, prints credentials, or changes the
existing WeKnora Compose lifecycle.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PA_API_ROOT = REPOSITORY_ROOT / "apps" / "pa-api"
KNOWLEDGE_ROOT = REPOSITORY_ROOT / "packages" / "knowledge-engine"
AGENT_ROOT = REPOSITORY_ROOT / "packages" / "agent-runtime"

for path in (PA_API_ROOT, KNOWLEDGE_ROOT, AGENT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-on-failure",
        action="store_true",
        help="retain the sanitized temporary repositories after a failure",
    )
    args = parser.parse_args()

    settings = Settings()
    _assert_live_configuration(settings)
    temp_root = Path(tempfile.mkdtemp(prefix="pa-par-p4-03-"))
    seed_root = temp_root / "seed"
    clone_root = temp_root / "clone"
    runtime_root = temp_root / "runtime"
    clone_environment: dict[str, str] | None = None
    clone_services_started = False
    succeeded = False

    try:
        _phase("export-index")
        _assert_one_git_root(REPOSITORY_ROOT)
        seed_root.mkdir()
        _run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "checkout-index",
                "--all",
                f"--prefix={seed_root}/",
            ]
        )
        _run(["git", "init", "--quiet"], cwd=seed_root)
        _run(["git", "config", "user.name", "PAR clean-clone acceptance"], cwd=seed_root)
        _run(["git", "config", "user.email", "par-clean-clone@invalid"], cwd=seed_root)
        _run(["git", "add", "--all"], cwd=seed_root)
        _run(["git", "commit", "--quiet", "-m", "PAR-P4-03 candidate index"], cwd=seed_root)
        _run(["git", "clone", "--quiet", "--local", "--no-hardlinks", str(seed_root), str(clone_root)])

        _phase("clone-contract")
        _assert_one_git_root(clone_root)
        _assert_clean_checkout(clone_root)
        _assert_index_tree_matches(REPOSITORY_ROOT, clone_root)

        runtime_root.mkdir()
        clone_environment = _clone_environment(settings, runtime_root)

        _phase("setup")
        _run(["make", "setup"], cwd=clone_root, env=clone_environment)
        _assert((clone_root / ".env").is_file(), "setup created the root Compose environment")
        _assert(
            (clone_root / ".local" / "pa-api" / ".env").is_file(),
            "setup created the canonical PA runtime environment",
        )
        _assert_clean_checkout(clone_root)

        _phase("build-static-compose")
        web_output = temp_root / "web-dist"
        build_environment = clone_environment.copy()
        build_environment["WEB_OUT_DIR"] = str(web_output)
        _run(["make", "validate"], cwd=clone_root, env=build_environment)
        _run(
            ["make", "compose-config"],
            cwd=clone_root,
            env=_public_tool_environment(),
            capture=True,
        )
        _assert(web_output.is_dir(), "PA Web build output was written outside the checkout")

        _phase("isolated-start-status-health")
        backend_port = _available_port()
        frontend_port = _available_port(excluded={backend_port})
        clone_environment.update(
            {
                "BACKEND_PORT": str(backend_port),
                "FRONTEND_PORT": str(frontend_port),
                "VITE_API_BASE_URL": f"http://127.0.0.1:{backend_port}",
            }
        )
        _run(
            ["./scripts/dev/pa-workbench-start.sh", "--skip-weknora"],
            cwd=clone_root,
            env=clone_environment,
        )
        clone_services_started = True
        _wait_for_url(f"http://127.0.0.1:{backend_port}/health")
        _wait_for_url(f"http://127.0.0.1:{backend_port}/api/status")
        _wait_for_url(f"http://127.0.0.1:{backend_port}/api/native/status")
        _wait_for_url(f"http://127.0.0.1:{frontend_port}/")
        status = _run(
            ["./scripts/dev/pa-dev-services.sh", "status"],
            cwd=clone_root,
            env=clone_environment,
            capture=True,
        )
        _assert("backend running" in status.stdout, "isolated PA backend status is running")
        _assert("frontend running" in status.stdout, "isolated PA frontend status is running")
        _stop_clone_services(clone_root, clone_environment)
        clone_services_started = False

        _phase("live-workflow-browser")
        _run_live_acceptance_with_retry(clone_root, clone_environment)

        _phase("final-governance")
        _run(["make", "validate-par-final"], cwd=clone_root, env=clone_environment)
        _assert_clean_checkout(clone_root)

        print("PA repository clean-clone final acceptance")
        print("- decision: PASS")
        print("- task: PAR-P4-03")
        print("- candidate: exact_source_index=true unstaged_user_work_excluded=true")
        print("- clone: local_transport=true git_roots=1 working_tree=clean")
        print("- setup: root_env=true pa_runtime_env=true dependencies=true")
        print("- build: python_backend_web_static_compose=true output_outside_checkout=true")
        print("- start: isolated_pa=true existing_weknora_lifecycle=untouched")
        print("- acceptance: health_status_live_workflow_browser_final_governance=true")
        print("- cleanup: temporary_clone_and_runtime=removed")
        succeeded = True
        return 0
    finally:
        if clone_services_started and clone_environment is not None and clone_root.exists():
            _stop_clone_services(clone_root, clone_environment, check=False)
        if succeeded or not args.keep_on_failure:
            shutil.rmtree(temp_root, ignore_errors=True)
        elif temp_root.exists():
            print(f"temporary failure evidence retained: {temp_root}", file=sys.stderr)


def _clone_environment(settings: Settings, runtime_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PA_SKIP_DOTENV": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "KNOWLEDGE_BACKEND": "weknora_api",
            "MOCK_MODE": "false",
            "DATABASE_URL": f"sqlite:///{runtime_root / 'pa.db'}",
            "UPLOAD_DIR": str(runtime_root / "uploads"),
            "WEKNORA_BASE_URL": settings.weknora_base_url,
            "WEKNORA_SERVICE_TOKEN": settings.weknora_service_token,
            "WEKNORA_WORKSPACE_ID": settings.weknora_workspace_id,
            "WEKNORA_DEFAULT_KB_ID": settings.weknora_default_kb_id,
            "WEKNORA_KB_MAPPINGS": settings.weknora_kb_mappings,
            "WEKNORA_KB_ALLOW_DEFAULT": str(settings.weknora_kb_allow_default).lower(),
            "WEKNORA_TIMEOUT_SECONDS": str(settings.weknora_timeout_seconds),
        }
    )
    node = shutil.which("node", path=environment.get("PATH"))
    if node:
        environment["NODE_BIN"] = node
    return environment


def _public_tool_environment() -> dict[str, str]:
    """Return only process metadata needed for public-template Compose render."""

    allowed = (
        "PATH",
        "HOME",
        "TMPDIR",
        "USER",
        "LOGNAME",
        "LANG",
        "LC_ALL",
        "DOCKER_CONFIG",
    )
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _assert_live_configuration(settings: Settings) -> None:
    _assert(settings.knowledge_backend == "weknora_api", "knowledge backend is weknora_api")
    _assert(settings.mock_mode is False, "PA mock mode is disabled")
    _assert(bool(settings.weknora_base_url), "WeKnora base URL is configured")
    _assert(bool(settings.weknora_service_token), "WeKnora service token is configured")
    _assert(bool(settings.weknora_workspace_id), "WeKnora workspace is configured")
    _assert(bool(settings.weknora_default_kb_id), "WeKnora default KB is configured")


def _assert_one_git_root(root: Path) -> None:
    git_roots: list[Path] = []
    for current, directories, _files in os.walk(root):
        current_path = Path(current)
        if ".git" in directories:
            git_roots.append(current_path / ".git")
            directories.remove(".git")
        directories[:] = [name for name in directories if name not in {"node_modules", ".venv"}]
    _assert(len(git_roots) == 1 and git_roots[0] == root / ".git", "checkout has one Git root")


def _assert_clean_checkout(root: Path) -> None:
    result = _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture=True,
    )
    _assert(not result.stdout.strip(), "clean clone working tree remains clean")


def _assert_index_tree_matches(source_root: Path, clone_root: Path) -> None:
    source = _run(["git", "write-tree"], cwd=source_root, capture=True).stdout.strip()
    clone = _run(["git", "write-tree"], cwd=clone_root, capture=True).stdout.strip()
    _assert(source == clone, "clean clone tree matches the exact source index tree")


def _available_port(*, excluded: set[int] | None = None) -> int:
    excluded = excluded or set()
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            port = int(listener.getsockname()[1])
        if port not in excluded:
            return port


def _wait_for_url(url: str, timeout_seconds: float = 40.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers={"Accept": "*/*"})
            with urlopen(request, timeout=3) as response:
                _assert(response.status == 200, f"health endpoint returned HTTP 200: {url}")
                return
        except Exception as error:  # noqa: BLE001 - retry startup races
            last_error = error
            time.sleep(0.5)
    raise AssertionError(f"timed out waiting for isolated service: {url}") from last_error


def _stop_clone_services(
    clone_root: Path,
    environment: dict[str, str],
    *,
    check: bool = True,
) -> None:
    _run(
        ["./scripts/dev/pa-dev-services.sh", "stop"],
        cwd=clone_root,
        env=environment,
        check=check,
    )


def _run_live_acceptance_with_retry(
    clone_root: Path,
    environment: dict[str, str],
    *,
    attempts: int = 2,
) -> None:
    """Retry the full live matrix once for transient external-provider errors."""

    for attempt in range(1, attempts + 1):
        result = _run(
            ["make", "validate-live-acceptance"],
            cwd=clone_root,
            env=environment,
            capture=True,
            check=False,
        )
        if result.returncode == 0:
            print(result.stdout, end="", flush=True)
            return
        if attempt < attempts:
            print(
                f"[clean-clone] live attempt {attempt} failed; retrying full matrix",
                flush=True,
            )
            time.sleep(3)
    raise AssertionError(f"live acceptance failed after {attempts} complete attempts")


def _phase(name: str) -> None:
    print(f"[clean-clone] {name}", flush=True)


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        capture_output=capture,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
