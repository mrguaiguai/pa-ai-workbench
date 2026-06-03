from collections.abc import Generator
from pathlib import Path
from sqlalchemy import inspect
from sqlalchemy import text
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine

from app.config import BACKEND_DIR
from app.config import Settings
from app.config import get_settings

# Import table models so SQLModel metadata is populated before create_all().
from app import models as _models  # noqa: F401


def _sqlite_path(database_url: str) -> Path | None:
    if database_url == "sqlite:///:memory:":
        return None
    if not database_url.startswith("sqlite:///"):
        return None

    path = Path(database_url.removeprefix("sqlite:///"))
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path


def ensure_sqlite_parent(database_url: str) -> None:
    path = _sqlite_path(database_url)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(settings: Settings | None = None):
    settings = settings or get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    ensure_sqlite_parent(settings.database_url)
    return create_engine(settings.database_url, connect_args=connect_args)


engine = create_db_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    ensure_sqlite_schema(engine)


def ensure_sqlite_schema(db_engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return

    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())
    if "documents" not in table_names:
        return

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "failed_step" not in document_columns:
        with db_engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN failed_step VARCHAR"))


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
