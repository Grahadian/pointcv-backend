import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()


def _ensure_sqlite_dir(database_url: str) -> str:
    # sqlite+aiosqlite:///./data/pointcv.db  -> create ./data before connect
    # sqlite+aiosqlite:////app/data/x.db     -> absolute path variant
    if not database_url.startswith("sqlite"):
        return database_url
    path = database_url.partition(":///")[2]
    if not path:
        return database_url
    if path.startswith("/") and not path.startswith("//"):
        directory = os.path.dirname(path)
    else:
        directory = os.path.dirname(os.path.join(os.getcwd(), path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    return database_url


engine = create_async_engine(
    _ensure_sqlite_dir(settings.DATABASE_URL),
    echo=settings.DEBUG,
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
