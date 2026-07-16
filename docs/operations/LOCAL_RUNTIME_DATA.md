# Local runtime data boundary

PA AI Workbench keeps source and runtime state separate. New local checkouts use
the ignored repository-root `.local/` tree for PA process state:

```text
.local/
├── pa-api/            local PA API env, database, uploads, and vector state
└── pa-dev/            local process pid files and logs
```

Docker deployments keep PA and WeKnora state in named volumes or explicitly
configured external storage. Build and validation output belongs in `/tmp` or
the ignored root `output/` directory, never in tracked evidence.

## Existing local state

PAR-P3-02 does not move or delete existing state. When the retained legacy PA
runtime contains an env file, virtual environment, database directory, upload
directory, pid directory, or log directory, setup and process-management
commands continue to use that location. This prevents an unrequested switch to
an empty database or upload tree.

Migration of existing data into `.local/` is deliberately manual and outside
this task. It requires an explicit user decision, a stopped service, a backup,
and path-specific verification. The protected personal-material directory is
also retained in place and ignored; it is not runtime data and must not be
published or moved without a user-selected destination.

## Git contract

The root `.gitignore` owns the PA-wide boundary. It excludes credentials,
private env files, `.local/`, databases, uploads, logs, caches, virtual
environments, package stores, and generated bundles while keeping env examples
and legitimate source directories visible. Native-specific rules remain in
`platform/weknora/.gitignore`.

Use metadata-only checks when auditing this boundary:

```bash
git ls-files
git status --ignored --short
git check-ignore --no-index -v .local/pa-api/data/pa_workbench.db
git check-ignore --no-index -v platform/weknora/cli/internal/build/new-source.go
```

The first probe must be ignored. The second is a legitimate hypothetical source
path and must not be ignored. Never print env values or inspect database,
upload, log, cache, vector, or personal-material contents for this audit.
