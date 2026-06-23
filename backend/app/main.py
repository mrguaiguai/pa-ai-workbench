from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import pathing as _pathing  # noqa: F401
from app.api.analysis import router as analysis_router
from app.api.citations import router as citations_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.mcp import router as mcp_router
from app.api.model import router as model_router
from app.api.native_status import router as native_status_router
from app.api.rag import router as rag_router
from app.api.vector_store import router as vector_store_router
from app.api.web_search import router as web_search_router
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(citations_router)
    app.include_router(conversations_router)
    app.include_router(analysis_router)
    app.include_router(history_router)
    app.include_router(mcp_router)
    app.include_router(model_router)
    app.include_router(native_status_router)
    app.include_router(rag_router)
    app.include_router(vector_store_router)
    app.include_router(web_search_router)
    app.include_router(wiki_router)

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    return app


app = create_app()
