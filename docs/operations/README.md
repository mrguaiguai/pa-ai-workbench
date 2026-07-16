# Operations documentation

The root `Makefile` is the public operations surface. Run `make help` from the
repository root. `make status` is read-only; start, migration, LaunchAgent,
release, and live-validation commands are explicit state-changing operations.

Command ownership and safety are documented in
[`scripts/README.md`](../../scripts/README.md). The retained native readiness
runbook is [WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md](WEKNORA_NATIVE_DEPLOYMENT_READINESS_RUNBOOK.md).

Local env, database, upload, log, cache, dependency, and build-output ownership
is defined in [LOCAL_RUNTIME_DATA.md](LOCAL_RUNTIME_DATA.md). New PA local state
uses the ignored root `.local/` convention; existing runtime data stays in
place until an explicit, backed-up migration is approved.

Historical runbooks and checklists are stored by stage under
[`docs/archive`](../archive/README.md).
