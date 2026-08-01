import logging

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user_id, get_db
from app.services.auth_service import handle_clerk_webhook, verify_clerk_webhook

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    return {"user_id": user_id}


@router.post("/webhooks/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        payload = await request.body()
        verified_payload = await verify_clerk_webhook(
            payload=payload,
            headers=dict(request.headers),
            secret=get_settings().CLERK_WEBHOOK_SECRET,
        )
        await handle_clerk_webhook(db, verified_payload)
    except Exception:
        logger.exception("Failed to process Clerk webhook")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"received": True},
    )
