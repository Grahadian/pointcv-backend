from urllib.parse import urlparse, parse_qs
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()
Base = declarative_base()

def _parse_database_url(url: str):
    """Parse PostgreSQL URL and extract asyncpg-compatible params."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    
    # Extract sslmode
    sslmode = query.get('sslmode', [''])[0]
    ssl = sslmode in ('require', 'prefer', 'verify-ca', 'verify-full')
    
    # Rebuild URL without query params (asyncpg doesn't like them in URL)
    # Keep only netloc + path
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    # Convert scheme to asyncpg if needed
    if clean_url.startswith("postgresql://"):
        clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif clean_url.startswith("postgresql+psycopg2://"):
        clean_url = clean_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    
    return clean_url, {"ssl": ssl} if ssl else {}

def get_engine():
    url = settings.DATABASE_URL
    if not url or url.startswith("sqlite"):
        # SQLite fallback for local dev
        return create_async_engine(
            "sqlite+aiosqlite:///./pointcv.db",
            echo=settings.DEBUG,
        )
    
    clean_url, connect_args = _parse_database_url(url)
    return create_async_engine(
        clean_url,
        echo=settings.DEBUG,
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args=connect_args,
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
