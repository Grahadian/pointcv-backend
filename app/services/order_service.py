import asyncio
import json
import logging
import math
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.exceptions import PointCVException
from app.models import (
    CVTemplate,
    File as OrderFile,
    Order,
    OrderStatusHistory,
    Package,
    User,
    Voucher,
)
from app.schemas.orders import OrderCreate

logger = logging.getLogger(__name__)

ORDER_STATUSES = {
    "PENDING",
    "PAID",
    "PROCESSING",
    "REVIEW",
    "DONE",
    "REVISION",
    "CANCELLED",
}


def _order_id(order_id: UUID | str) -> str:
    return str(order_id)


def _not_found(message: str = "Order not found") -> PointCVException:
    return PointCVException(status.HTTP_404_NOT_FOUND, message, "not_found")


def _bad_request(message: str) -> PointCVException:
    return PointCVException(status.HTTP_400_BAD_REQUEST, message, "bad_request")


def _forbidden(message: str = "Forbidden") -> PointCVException:
    return PointCVException(status.HTTP_403_FORBIDDEN, message, "forbidden")


def _conflict(message: str) -> PointCVException:
    return PointCVException(status.HTTP_409_CONFLICT, message, "conflict")


def _order_load_options(include_user: bool = False) -> list[Any]:
    options: list[Any] = [
        selectinload(Order.package),
        selectinload(Order.template),
        selectinload(Order.files),
        selectinload(Order.status_history),
    ]
    if include_user:
        options.append(selectinload(Order.user))
    return options


async def _get_order_loaded(
    db: AsyncSession,
    order_id: UUID | str,
    include_user: bool = False,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == _order_id(order_id))
        .options(*_order_load_options(include_user=include_user))
    )
    return result.scalar_one_or_none()


async def _require_order(
    db: AsyncSession,
    order_id: UUID | str,
    include_user: bool = False,
) -> Order:
    order = await _get_order_loaded(db, order_id, include_user=include_user)
    if order is None:
        raise _not_found()
    return order


def _validate_progress(progress: int) -> None:
    if progress < 0 or progress > 100:
        raise _bad_request("Progress must be between 0 and 100")


def _validate_status(order_status: str) -> None:
    if order_status not in ORDER_STATUSES:
        raise _bad_request("Invalid order status")


def _validate_voucher_window(voucher: Voucher, now: datetime) -> None:
    if not voucher.is_active:
        raise _bad_request("Voucher is not active")
    if voucher.valid_from is not None and voucher.valid_from > now:
        raise _bad_request("Voucher is not active yet")
    if voucher.valid_until is not None and voucher.valid_until < now:
        raise _bad_request("Voucher has expired")
    if voucher.max_uses is not None and voucher.used_count >= voucher.max_uses:
        raise _conflict("Voucher usage limit reached")


def _calculate_discount(voucher: Voucher, package_price: int) -> int:
    if voucher.discount_type == "PERCENTAGE":
        discount = package_price * voucher.discount_value // 100
    elif voucher.discount_type == "FIXED":
        discount = voucher.discount_value
    else:
        raise _bad_request("Invalid voucher discount type")
    return min(max(discount, 0), package_price)


async def _apply_voucher(
    db: AsyncSession,
    voucher_code: str | None,
    package_price: int,
) -> int:
    if not voucher_code:
        return 0

    result = await db.execute(
        select(Voucher).where(func.lower(Voucher.code) == voucher_code.lower())
    )
    voucher = result.scalar_one_or_none()
    if voucher is None:
        raise _bad_request("Voucher not found")

    _validate_voucher_window(voucher, datetime.utcnow())
    discount = _calculate_discount(voucher, package_price)
    voucher.used_count += 1
    return discount


async def validate_voucher(
    db: AsyncSession,
    voucher_code: str | None,
    package_price: int,
) -> dict[str, Any]:
    if not voucher_code:
        return {"valid": True, "discount": 0, "message": ""}

    result = await db.execute(
        select(Voucher).where(func.lower(Voucher.code) == voucher_code.lower())
    )
    voucher = result.scalar_one_or_none()
    if voucher is None:
        return {"valid": False, "discount": 0, "message": "Voucher not found"}

    try:
        _validate_voucher_window(voucher, datetime.utcnow())
    except PointCVException as exc:
        return {"valid": False, "discount": 0, "message": exc.message}

    discount = _calculate_discount(voucher, package_price)
    return {"valid": True, "discount": discount, "message": "Voucher applied"}


def _log_status_change(
    db: AsyncSession,
    order: Order,
    new_status: str,
    new_progress: int,
    changed_by: str | None,
    note: str | None = None,
) -> None:
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=order.status,
            new_status=new_status,
            old_progress=order.progress,
            new_progress=new_progress,
            changed_by=changed_by,
            note=note,
        )
    )


def _log_initial_status(
    db: AsyncSession,
    order: Order,
    changed_by: str | None,
    note: str | None = None,
) -> None:
    db.add(
        OrderStatusHistory(
            order_id=order.id,
            old_status=None,
            new_status=order.status,
            old_progress=None,
            new_progress=order.progress,
            changed_by=changed_by,
            note=note,
        )
    )


ALLOWED_ORDER_FILE_TYPES = {"PHOTO", "CERTIFICATE", "DIPLOMA", "DOCUMENT", "RESULT_PDF"}


async def create_order(db: AsyncSession, user_id: str, data: OrderCreate) -> Order:
    package = await db.get(Package, data.package_id)
    if package is None or not package.is_active:
        raise _bad_request("Package not found or inactive")

    template = await db.get(CVTemplate, data.template_id)
    if template is None or not template.is_active:
        raise _bad_request("Template not found or inactive")

    try:
        discount_amount = await _apply_voucher(db, data.voucher_code, package.price)
        order = Order(
            user_id=user_id,
            package_id=package.id,
            template_id=template.id,
            status="PENDING",
            progress=0,
            price=package.price,
            payment_status="UNPAID",
            voucher_code=data.voucher_code,
            discount_amount=discount_amount,
            cv_data=data.cv_data,
            notes=data.notes,
            revision_count=0,
        )
        db.add(order)
        await db.flush()
        _log_initial_status(db, order, user_id, "Order created")

        for file_input in data.files or []:
            if file_input.file_type not in ALLOWED_ORDER_FILE_TYPES:
                raise _bad_request("Invalid file type")
            if not file_input.key.startswith(f"uploads/{user_id}/"):
                raise _bad_request("Uploaded file key does not belong to this user")
            db.add(
                OrderFile(
                    order_id=order.id,
                    filename=file_input.key,
                    original_name=file_input.filename,
                    url=file_input.url,
                    file_type=file_input.file_type,
                    mime_type=file_input.mime_type,
                    size_bytes=file_input.size_bytes,
                )
            )

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    loaded_order = await _get_order_loaded(db, order.id)
    if loaded_order is None:
        raise _not_found()
    return loaded_order


async def get_user_orders(db: AsyncSession, user_id: str) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .options(*_order_load_options())
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


async def get_order(
    db: AsyncSession,
    order_id: UUID | str,
    user_id: str,
    is_admin: bool = False,
) -> Order | None:
    order = await _get_order_loaded(db, order_id)
    if order is None:
        return None
    if not is_admin and order.user_id != user_id:
        raise _forbidden()
    return order


EDITABLE_CV_STATUSES = {"PENDING", "PROCESSING"}


async def update_cv_data(
    db: AsyncSession,
    order_id: UUID | str,
    user_id: str,
    cv_data: dict,
) -> Order:
    order = await _get_order_loaded(db, order_id)
    if order is None:
        raise _not_found()
    if order.user_id != user_id:
        raise _forbidden()
    if order.status not in EDITABLE_CV_STATUSES:
        raise _conflict("CV data can only be edited while the order is pending or in progress")

    try:
        merged = {**(order.cv_data or {}), **cv_data}
        order.cv_data = merged
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    updated = await _get_order_loaded(db, order.id)
    if updated is None:
        raise _not_found()
    return updated


async def cancel_order(db: AsyncSession, order_id: UUID | str, user_id: str) -> Order:
    order = await _require_order(db, order_id)
    if order.user_id != user_id:
        raise _forbidden()
    if order.status != "PENDING":
        raise _conflict("Only pending orders can be cancelled")

    try:
        _log_status_change(db, order, "CANCELLED", order.progress, user_id)
        order.status = "CANCELLED"
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _require_order(db, order.id)


async def request_revision(
    db: AsyncSession,
    order_id: UUID | str,
    user_id: str,
    note: str,
) -> Order:
    order = await _require_order(db, order_id)
    if order.user_id != user_id:
        raise _forbidden()
    if order.status != "DONE":
        raise _bad_request("Only completed orders can be revised")

    if (
        order.package.max_revisions != -1
        and order.revision_count >= order.package.max_revisions
    ):
        raise _bad_request("Maximum revisions reached")

    try:
        order.revision_count += 1
        _log_status_change(db, order, "REVISION", order.progress, user_id, note)
        order.status = "REVISION"
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _require_order(db, order.id)


async def update_order_status(
    db: AsyncSession,
    order_id: UUID | str,
    status: str,
    progress: int,
    changed_by: str,
    note: str | None = None,
) -> Order:
    _validate_status(status)
    _validate_progress(progress)
    order = await _require_order(db, order_id)

    try:
        _log_status_change(db, order, status, progress, changed_by, note)
        order.status = status
        order.progress = progress
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _require_order(db, order.id)


async def list_admin_orders(
    db: AsyncSession,
    status_filter: str | None = None,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> dict[str, Any]:
    if status_filter is not None:
        _validate_status(status_filter)

    filters = []
    if status_filter:
        filters.append(Order.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Order.id.ilike(term), User.email.ilike(term)))

    base_query = select(Order).join(Order.user)
    count_query = select(func.count(Order.id)).join(Order.user)
    for condition in filters:
        base_query = base_query.where(condition)
        count_query = count_query.where(condition)

    total = (
        await db.execute(count_query)
    ).scalar_one()
    result = await db.execute(
        base_query.options(*_order_load_options(include_user=True))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    return {
        "items": list(result.scalars().all()),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total else 0,
    }


def _safe_filename(filename: str) -> str:
    stem = Path(filename).stem or "result"
    suffix = Path(filename).suffix.lower() or ".pdf"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or "result"
    return f"{safe_stem}{suffix}"


def _result_file_url(key: str) -> str:
    settings = get_settings()
    if settings.R2_PUBLIC_URL:
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"
    return (
        f"{settings.R2_ENDPOINT_URL.rstrip('/')}/"
        f"{settings.R2_BUCKET_NAME}/{key}"
    )


async def _upload_to_r2(file: UploadFile, key: str, body: bytes) -> str:
    settings = get_settings()
    if not all(
        [
            settings.R2_ENDPOINT_URL,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
        ]
    ):
        raise _bad_request("R2 storage is not configured")

    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    )
    await asyncio.to_thread(
        client.put_object,
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=body,
        ContentType=file.content_type or "application/pdf",
    )
    return _result_file_url(key)


async def upload_result_pdf(
    db: AsyncSession,
    order_id: UUID | str,
    file: UploadFile,
    changed_by: str,
) -> OrderFile:
    order = await _require_order(db, order_id)
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise _bad_request("Result file must be a PDF")

    body = await file.read()
    if not body:
        raise _bad_request("Result file is empty")

    filename = _safe_filename(file.filename or "result.pdf")
    key = f"results/{order.id}/{int(datetime.utcnow().timestamp())}-{filename}"
    url = await _upload_to_r2(file, key, body)

    order_file = OrderFile(
        order_id=order.id,
        filename=key,
        original_name=file.filename or filename,
        url=url,
        file_type="RESULT_PDF",
        mime_type=file.content_type or "application/pdf",
        size_bytes=len(body),
    )

    try:
        db.add(order_file)
        if order.status != "DONE":
            _log_status_change(
                db,
                order,
                "DONE",
                100,
                changed_by,
                "Result PDF uploaded",
            )
            order.status = "DONE"
            order.progress = 100
        await db.commit()
        await db.refresh(order_file)
    except Exception:
        await db.rollback()
        raise

    return order_file


async def get_order_status_stream(
    db: AsyncSession,
    order_id: UUID | str,
) -> AsyncGenerator[str, None]:
    order_uuid = _order_id(order_id)
    not_found_polls = 0
    while True:
        try:
            result = await db.execute(
                select(Order.id, Order.status, Order.progress).where(
                    Order.id == order_uuid
                )
            )
            row = result.one_or_none()
            if row is None:
                not_found_polls += 1
                payload = {
                    "order_id": str(order_uuid),
                    "status": "NOT_FOUND",
                    "progress": 0,
                }
            else:
                not_found_polls = 0
                payload = {
                    "order_id": row.id,
                    "status": row.status,
                    "progress": row.progress,
                }
            yield f"data: {json.dumps(payload)}\n\n"
            # Yield an SSE comment as an idle heartbeat for intermediaries.
            yield ": ping\n\n"
            if row is None and not_found_polls >= 10:
                logger.info("Closing SSE stream: order not found %s", order_uuid)
                break
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            # Client disconnected: Starlette cancels the generator here.
            break
        except Exception:
            logger.exception("SSE stream ended for order %s", order_uuid)
            break
