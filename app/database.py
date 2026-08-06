# app/database.py
import os
import ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()
Base = declarative_base()


def _prepare_neon_url(url: str) -> tuple[str, dict]:
    """
    Neon PostgreSQL butuh SSL.
    asyncpg tidak terima 'sslmode' di query string sebagai kwargs.
    Kita ekstrak sslmode, lalu pass ssl context via connect_args.
    """
    if not url or url.startswith("sqlite"):
        return url, {}

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Ekstrak sslmode
    sslmode = None
    if "sslmode" in query_params:
        sslmode = query_params.pop("sslmode")[0]
    
    # Rebuild URL tanpa sslmode di query
    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    # Buat SSL context untuk asyncpg
    connect_args = {}
    if sslmode in ("require", "prefer", "verify-ca", "verify-full"):
        ssl_context = ssl.create_default_context()
        if sslmode == "require":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
    
    return clean_url, connect_args


def get_engine():
    raw_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./data/pointcv.db"
    
    # Jika SQLite, langsung return
    if raw_url.startswith("sqlite"):
        return create_async_engine(raw_url, echo=settings.DEBUG, future=True)
    
    # Normalisasi: postgresql:// → postgresql+asyncpg://
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgresql+psycopg2://"):
        raw_url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    
    clean_url, connect_args = _prepare_neon_url(raw_url)
    
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


# Lazy init
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


# --- Untuk Alembic (sync) ---
def get_sync_database_url() -> str:
    """Generate URL sync untuk Alembic (psycopg2)."""
    raw = settings.DATABASE_URL or "sqlite:///./pointcv.db"
    
    if raw.startswith("sqlite"):
        return raw.replace("sqlite+aiosqlite://", "sqlite://", 1)
    
    # Pastikan pakai psycopg2 dan ada sslmode
    if raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    # Pastikan sslmode=require ada untuk Neon
    if "sslmode" not in raw and "neon.tech" in raw:
        separator = "&" if "?" in raw else "?"
        raw = f"{raw}{separator}sslmode=require"
    
    return raw