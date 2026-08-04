from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()
Base = declarative_base()

def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url

def get_engine():
    return create_async_engine(
        _normalize_url(settings.DATABASE_URL),
        echo=settings.DEBUG,
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

def get_sessionmaker(engine):
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

_engine = None
_sessionmaker = None

def get_db_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine

def get_db_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = get_sessionmaker(get_db_engine())
    return _sessionmaker

async def get_db():
    session = get_db_sessionmaker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
