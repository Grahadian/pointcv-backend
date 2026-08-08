from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.exceptions import PointCVException
from app.schemas.orders import CvDataUpdate, OrderCreate, OrderResponse, RevisionRequest
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.get_user_orders(db, user_id)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: OrderCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.create_order(db, user_id, data)


@router.get("/{order_id}", response_model=OrderResponse)
async def get(
    order_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id, user_id)
    if order is None:
        raise PointCVException(status.HTTP_404_NOT_FOUND, "Order not found", "not_found")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel(
    order_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await order_service.cancel_order(db, order_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{order_id}/cv-data", response_model=OrderResponse)
async def update_cv_data(
    order_id: UUID,
    data: CvDataUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.update_cv_data(db, order_id, user_id, data.cv_data)


@router.post("/{order_id}/request-revision", response_model=OrderResponse)
async def request_revision(
    order_id: UUID,
    data: RevisionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.request_revision(db, order_id, user_id, data.note)


@router.get("/{order_id}/status-stream")
async def status_stream(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        order_service.get_order_status_stream(db, order_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            # Opt out of the global GZipMiddleware: compressing an endless
            # SSE stream would buffer heartbeat pings and break progress UI.
            "Content-Encoding": "identity",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
