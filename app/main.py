from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import text

from app.config import get_settings
from app.database import get_db_engine, get_db_sessionmaker
from app.exceptions import (
    PointCVException,
    pointcv_exception_handler,
    request_validation_exception_handler,
    validation_exception_handler,
)
from app.routers import auth, health, orders, payments, files, public, admin, testimonials
from app.seed import seed_data

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        engine = get_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise RuntimeError("Could not connect to the database on startup.")

    if not settings.BETTER_AUTH_SECRET:
        raise RuntimeError("BETTER_AUTH_SECRET is not set")

    # Idempotent catalog seed as a safety net — if the DB is empty (e.g. a
    # fresh Neon instance) the packages & templates exist before uvicorn serves
    # the first request. Never crash the app if the seed fails (migrations run
    # beforehand in render-start.sh, but local dev may not have run alembic).
    session = get_db_sessionmaker()()
    try:
        await seed_data(session)
        logger.info("Catalog seeded (packages & templates).")
    except Exception as exc:
        logger.warning(f"Catalog seed skipped/failed: {exc}")
    finally:
        await session.close()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(PointCVException, pointcv_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(files.router)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(testimonials.router)
app.include_router(testimonials.admin_router)
app.include_router(testimonials.public_router)


@app.get("/")
async def root():
    return {"message": "PointCV API is running"}
