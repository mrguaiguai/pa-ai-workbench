FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PA_SKIP_DOTENV=1

WORKDIR /workspace

COPY packages/knowledge-engine/pyproject.toml packages/knowledge-engine/pyproject.toml
COPY packages/knowledge-engine/knowledge_engine packages/knowledge-engine/knowledge_engine
COPY packages/agent-runtime/pyproject.toml packages/agent-runtime/pyproject.toml
COPY packages/agent-runtime/agent packages/agent-runtime/agent
COPY apps/pa-api/pyproject.toml apps/pa-api/pyproject.toml
COPY apps/pa-api/app apps/pa-api/app

RUN python -m pip install --no-cache-dir \
    ./packages/knowledge-engine \
    ./packages/agent-runtime \
    ./apps/pa-api

WORKDIR /srv/pa
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
