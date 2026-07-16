# PA AI Workbench command surface

Run repository commands from the monorepo root. The root `Makefile` is the
public entry point; these directories own the implementation commands:

- `dev/`: local setup, PA process management, and native development mode;
- `ops/`: service, migration, LaunchAgent, and confirmation-gated helper
  operations;
- `release/`: image, version, package, Homebrew, and cloud-image delivery;
- `validation/`: static, fixture, live, browser, release, and PAR acceptance
  checks.

Use `make help` for the stable command list. A specific historical validation
program can be run as `python3 scripts/validation/<name>.py`; mutation-capable
programs remain explicit under `scripts/ops/` and are not part of the default
`make validate` target.

`make validate` is static/offline by default. It writes the PA Web Vite output
to `/tmp`, disables PA dotenv loading for backend discovery, and does not start,
stop, rebuild, or migrate services. `make status` is read-only. In contrast,
`make start`, `make pa-start`, LaunchAgent targets, migration commands, release
commands, cloud-image scripts, and live validation programs can change local or
external state and must be invoked deliberately.

New PA process and API runtime state uses the ignored root `.local/pa-dev` and
`.local/pa-api` directories. If path-only checks find retained legacy env,
database, uploads, virtual environment, pid, or log state, the commands keep
using it rather than silently creating a replacement runtime. The migration
policy is documented in `docs/operations/LOCAL_RUNTIME_DATA.md`.

Component-internal scripts stay beside the component when their path is part
of a build/runtime contract rather than a developer command. The intentional
exceptions are:

- `platform/weknora/scripts/docker-entrypoint.sh` (native image runtime);
- `platform/weknora/frontend/docker-entrypoint.sh` (native frontend runtime);
- `platform/weknora/docreader/scripts/generate_proto.sh` (docreader build);
- Skill-local scripts below `platform/weknora/skills/` and examples.

PAR-P2-03 removes the former `apps/backend`, `apps/frontend`, and
`apps/scripts` command aliases after active callers moved. Bootstrap stage
documents still containing `backend/scripts`, `frontend`, or old native
`scripts/*.sh` examples are preserved historical records under `docs/archive`,
not active command owners. PAR-P3-01 removes the `apps/docs` alias after tracked
documentation moves to root `docs/`; the protected personal-material directory
remains untouched at its legacy location. The six bounded infrastructure links
from PAR-P2-02 remain under their existing infrastructure contracts.
