from fastapi import FastAPI

from app import pathing as _pathing  # noqa: F401
from app.api.analysis import router as analysis_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.model import router as model_router
from app.api.wiki import router as wiki_router
from app.config import get_settings
from app.database import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for the independent PA AI Workbench product.",
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)
    app.include_router(analysis_router)
    app.include_router(history_router)
    app.include_router(model_router)
    app.include_router(wiki_router)

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    return app


app = create_app()
