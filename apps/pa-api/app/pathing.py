from pathlib import Path

PA_API_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PA_WEB_ROOT = REPOSITORY_ROOT / "apps" / "pa-web"
AGENT_RUNTIME_ROOT = REPOSITORY_ROOT / "packages" / "agent-runtime"
KNOWLEDGE_ENGINE_ROOT = REPOSITORY_ROOT / "packages" / "knowledge-engine"
PLATFORM_ROOT = REPOSITORY_ROOT / "platform" / "weknora"

# Private runtime state may remain in the bootstrap tree until PAR-P3-02.
# Commands and documentation use canonical root paths; product imports use the
# installable packages declared by the workspace pyproject files.
BOOTSTRAP_ROOT = REPOSITORY_ROOT / "pa-ai-workbench"
SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
DOCS_ROOT = REPOSITORY_ROOT / "docs"

# Source-compatible aliases for callers written before PAR-P2-03/P3-01.
BOOTSTRAP_SCRIPTS_ROOT = SCRIPTS_ROOT
BOOTSTRAP_DOCS_ROOT = DOCS_ROOT

PYTHON_WORKSPACE_ROOTS = (
    PA_API_ROOT,
    AGENT_RUNTIME_ROOT,
    KNOWLEDGE_ENGINE_ROOT,
)

# Kept as a source-compatible name for callers that imported this module before
# the repository reorganization. It now identifies the actual repository root.
PROJECT_ROOT = REPOSITORY_ROOT
