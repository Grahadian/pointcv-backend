from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import get_db_engine
from app.routers import health, orders, payments, files, public, admin

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

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(files.router)
app.include_router(public.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {"message": "PointCV API is running"}
