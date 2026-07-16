# PA repository compatibility aliases

PAR-P1-02 moved PA source into `apps` and `packages`. PAR-P2-03 then moved the
developer, operations, release, and validation commands to the root `scripts/`
surface and migrated every active caller. The `apps/backend`, `apps/frontend`,
and `apps/scripts` command aliases are therefore removed. PAR-P3-01 moved the
tracked documentation tree to root `docs/` and removed the final `apps/docs`
alias after active callers migrated.

PAR-P2-01 removed the former `apps/agent` and `apps/knowledge_engine` import
aliases. Python consumers now use the installable projects declared at
`apps/pa-api`, `packages/agent-runtime`, and `packages/knowledge-engine`; root
`pyproject.toml` provides workspace and test-discovery metadata. The frontend
is declared by the root Node workspace and owns its TypeScript/Vite aliases.

No PA source, import, command, or documentation alias remains under `apps/`.
The protected personal-material directory stays at its legacy location until
the user explicitly selects an archive/export destination; it is not exposed
through an `apps` alias.

PAR-P2-02 also retains relative infrastructure entry-point links at the former
native Compose, Helm, and env-example paths. PAR-P2-03 command implementations
now use canonical `infra/` paths directly; the links remain bounded by the
P2-02 infrastructure and P3-01 documentation contracts. Dockerfile paths were
repaired directly because Docker does not allow a Dockerfile symlink to escape
its build context. GitHub workflows are active only from root
`.github/workflows/`.

Private backend runtime state remains in its existing ignored directory. The
API config and launchers select that directory explicitly, while clean clones
without legacy local state use `apps/pa-api`. `PAR-P3-02` owns the final local
data convention.
