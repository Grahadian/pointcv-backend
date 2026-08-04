import asyncio
import logging

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "pointcv-api"}


async def _check_database() -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("Database health check failed")
        return {"status": "error"}


async def _check_storage() -> dict[str, str]:
    settings = get_settings()
    if not all(
        [
            settings.R2_ENDPOINT_URL,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
        ]
    ):
        return {"status": "skipped", "note": "R2 not configured"}

    try:
        from app.services.file_service import get_s3_client

        client = get_s3_client()
        await asyncio.to_thread(client.head_bucket, Bucket=settings.R2_BUCKET_NAME)
        return {"status": "ok"}
    except Exception:
        logger.exception("R2 health check failed")
        return {"status": "error"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict[str, object]:
    checks = {
        "database": await _check_database(),
        "storage": await _check_storage(),
    }
    failed = [name for name, result in checks.items() if result["status"] == "error"]
    status = "ok" if not failed else "error"
    if status == "error":
        response.status_code = 503
    return {"status": status, "service": "pointcv-api", "checks": checks}
