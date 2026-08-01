import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.schemas.orders import PaymentRequest, PaymentResponse, PaymentStatusResponse
from app.services import payment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    data: PaymentRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.create_payment(db, data.order_id, user_id)


@router.post("/webhook")
async def midtrans_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {"raw_payload": payload}
        await payment_service.process_notification(db, payload)
    except Exception:
        await db.rollback()
        logger.exception("Failed to process Midtrans webhook")
    return {"status": "ok"}


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await payment_service.get_payment_status(db, order_id, user_id)
