# PA AI Workbench Architecture

PA AI Workbench is an independent internal product for a financial public affairs team. It lives under `pa-ai-workbench/` and must not depend on changes to the outer WeKnora source tree.

## Product Boundary

- PA AI Workbench owns its frontend, backend, agent runtime, knowledge engine adapter layer, local storage, and documentation.
- WeKnora may be referenced as an external knowledge capability or implementation reference, but raw WeKnora responses should not leak into higher layers.
- Runtime data, uploads, logs, local databases, API keys, and real department materials must stay out of Git.

## Layering

```text
Frontend
-> Backend API
-> AgentOrchestrator
-> Agent Runtime
-> Knowledge Engine
-> mock / weknora_api / extracted backend
```

- The frontend calls only the FastAPI backend.
- The backend calls agents only through `AgentOrchestrator`.
- Agents obtain evidence only through tools backed by the Knowledge Engine.
- The Knowledge Engine normalizes backend-specific responses before returning evidence or wiki content.

## MVP Defaults

- The mock backend is required so the product remains demoable when external services are unavailable.
- Agent workflows should be represented as runtime profiles and workflows rather than one-off prompt functions.
- User-facing conclusions must include citations or clearly report insufficient evidence.

## A1 Status

This document establishes the architecture placeholder for A1. Later tasks will add concrete backend, frontend, agent, and knowledge engine implementations.
