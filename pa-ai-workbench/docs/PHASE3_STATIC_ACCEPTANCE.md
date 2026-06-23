# Phase 3 Static Acceptance

This is the repository-level closure note for Phase 3. It records the static
and sanitized fixture gate that can be run without live WeKnora credentials,
public model API calls, uploads, databases, logs, or real materials.

Run from `pa-ai-workbench`:

```bash
backend/.venv/bin/python backend/scripts/check_phase3_static_acceptance.py
```

The checker verifies:

- every `P3-*` task row in `PHASE3_SPEC.md` is complete;
- required M1/M2/M3 release, runbook, golden-set, RAG-quality, and Agent
  faithfulness artifacts exist;
- M2 runbook and pilot feedback documentation smokes pass;
- `backend/scripts/check_m3_local_product.py` passes in static fixture mode;
- git status does not show sensitive tracked or staged paths.

This gate does not claim live WeKnora acceptance. Live product acceptance still
requires:

```bash
backend/.venv/bin/python backend/scripts/check_m3_local_product.py --run-live-smokes
```

That live command should run only in an approved environment with sanitized
materials and runtime secrets provided outside Git.

For a full M2 release recheck, run `backend/scripts/check_m2_release.py --static-only`
in an environment that permits local fixture HTTP servers; this
desktop sandbox may block local socket binding even though the fixture does not
call live WeKnora.
