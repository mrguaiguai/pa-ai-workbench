# PA AI Workbench

PA AI Workbench is an independent internal productivity product for a financial public affairs team.

The first version focuses on:

- Local knowledge base and document upload
- RAG question answering
- Policy analysis workflow
- Historical case retrieval
- Wiki knowledge accumulation
- Modular Agent runtime with persistent conversation memory

This repository is intentionally separated from the upstream WeKnora source tree. WeKnora can be used as a reference or RAG capability source, but this product should remain independently structured under `pa-ai-workbench/`.

## Development Entry

Read these files before implementation:

- `DEV_SPEC.md`
- `PRODUCT_SPEC.md`
- `.github/skills/auto-coder/SKILL.md`
- `.github/skills/qa-tester/SKILL.md`
- `.github/skills/setup/SKILL.md`

Suggested development prompt:

```text
Please read pa-ai-workbench/DEV_SPEC.md and use the auto-coder skill to execute the next unchecked task. After finishing, update DEV_SPEC.md and report changed files, validation result, and next task.
```

## Git Safety

Do not commit:

- Real department documents
- Uploaded files
- SQLite databases
- `.env` files
- API keys or credentials
- Local cache/build artifacts

