from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PA AI Workbench API",
        version="0.1.0",
        description="Backend API for the independent PA AI Workbench product.",
    )
    app.include_router(health_router)
    return app


app = create_app()

