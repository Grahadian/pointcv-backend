import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import text

from app.config import get_settings
from app.database import get_db_engine
from app.exceptions import (
    PointCVException,
    pointcv_exception_handler,
    request_validation_exception_handler,
    validation_exception_handler,
)
from app.routers import admin, auth, files, health, orders, payments, public

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    if not settings.DATABASE_URL.strip():
        raise RuntimeError(
            "DATABASE_URL is not set. PointCV will not start without a database. "
            "Production: set DATABASE_URL to your Neon PostgreSQL URL "
            "(postgresql://user:pass@host/db?sslmode=require). "
            "Local dev: set DATABASE_URL=sqlite+aiosqlite:///./pointcv.db"
        )
    if not settings.BETTER_AUTH_SECRET:
        raise RuntimeError(
            "BETTER_AUTH_SECRET is not set. It must match the frontend's "
            "BETTER_AUTH_SECRET (generate with `openssl rand -base64 32`)."
        )

    logger.info("Starting %s", app.title)
    try:
        engine = get_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connection FAILED at startup")
        raise RuntimeError(
            "Could not connect to the database on startup. "
            "Check DATABASE_URL and that the database is reachable."
        ) from None
    logger.info("Database connected")
    yield
    logger.info("Stopping %s", app.title)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    origins = [
        origin.strip()
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Origin", "Accept", "X-Requested-With"],
        expose_headers=["X-Total-Count"],
    )
    # Added last so it is the outermost middleware: compresses JSON responses
    # for bandwidth savings on the free Render tier.
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        logger.info(
            "%s %s -> %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response

    @app.middleware("http")
    async def unexpected_exception_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except PointCVException:
            raise
        except Exception:
            logger.exception(
                "Unhandled error during %s %s",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error",
                },
            )

    @app.exception_handler(PointCVException)
    async def handle_pointcv_exception(
        request: Request,
        exc: PointCVException,
    ) -> JSONResponse:
        return await pointcv_exception_handler(request, exc)

    @app.exception_handler(ValidationError)
    async def handle_validation_exception(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        return await validation_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_exception(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return await request_validation_exception_handler(request, exc)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    app.include_router(files.router)
    app.include_router(admin.router)
    app.include_router(public.router)
    return app


app = create_app()
