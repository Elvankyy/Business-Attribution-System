from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.models import Base

settings = get_settings()


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    path_part = url.split("///", 1)[-1]
    if path_part in {"", ":memory:"}:
        return
    Path(path_part).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_storage_root() -> Path:
    root = settings.storage_path
    root.mkdir(parents=True, exist_ok=True)
    return root


def init_storage_dirs() -> None:
    root = get_storage_root()
    for name in ("uploads", "exports", "workspace"):
        (root / name).mkdir(parents=True, exist_ok=True)


async def init_database() -> None:
    init_storage_dirs()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            await conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_tasks_running_conversation "
                "ON analysis_tasks(conversation_id) WHERE task_status = 'running'"
            )


async def dispose_engine() -> None:
    await engine.dispose()
