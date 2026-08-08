import asyncio
import re
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.exceptions import PointCVException
from app.models import File, Order, OrderStatusHistory, User

ALLOWED_FILE_TYPES = {"PHOTO", "CERTIFICATE", "DIPLOMA", "DOCUMENT", "RESULT_PDF"}
IMAGE_MAX_BYTES = 5_242_880
DOCUMENT_MAX_BYTES = 10_485_760
PRESIGNED_URL_EXPIRES_SECONDS = 300
MAX_USER_FILES_PER_ORDER = 5


def _bad_request(message: str) -> PointCVException:
    return PointCVException(400, message, "bad_request")


def _not_found(message: str) -> PointCVException:
    return PointCVException(404, message, "not_found")


def _forbidden(message: str = "Forbidden") -> PointCVException:
    return PointCVException(403, message, "forbidden")


def get_s3_client():
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

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _validate_file_type(file_type: str) -> None:
    if file_type not in ALLOWED_FILE_TYPES:
        raise _bad_request("Invalid file type")


def _validate_size(file_type: str, size_bytes: int) -> None:
    if size_bytes <= 0:
        raise _bad_request("File size must be greater than 0")

    max_size = IMAGE_MAX_BYTES if file_type == "PHOTO" else DOCUMENT_MAX_BYTES
    if size_bytes > max_size:
        raise _bad_request(f"File size exceeds {max_size} bytes")


def _sanitize_filename(filename: str) -> str:
    name = filename.strip().lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9.-]+", "", name)
    name = re.sub(r"-+", "-", name).strip(".-")
    return name or "file"


def _public_url(key: str) -> str:
    settings = get_settings()
    if settings.R2_PUBLIC_URL:
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{key}"
    return (
        f"{settings.R2_ENDPOINT_URL.rstrip('/')}/"
        f"{settings.R2_BUCKET_NAME}/{key}"
    )


async def _get_order_for_user(
    db: AsyncSession,
    order_id: UUID | str,
    user_id: str,
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == str(order_id), Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise _not_found("Order not found")
    return order


async def _require_admin(db: AsyncSession, user_id: str) -> None:
    user = await db.get(User, user_id)
    if user is None or not user.is_admin:
        raise _forbidden("Administrator access required")


async def generate_upload_url(
    user_id: str,
    filename: str,
    file_type: str,
    mime_type: str,
    size_bytes: int,
    db: AsyncSession | None = None,
    order_id: UUID | None = None,
) -> dict[str, str | int]:
    _validate_file_type(file_type)
    _validate_size(file_type, size_bytes)

    sanitized_filename = _sanitize_filename(filename)
    if file_type == "RESULT_PDF":
        if db is None or order_id is None:
            raise _bad_request("Result uploads require an order id")
        await _require_admin(db, user_id)
        if await db.get(Order, str(order_id)) is None:
            raise _not_found("Order not found")
        key = f"results/{order_id}/{uuid4()}-result.pdf"
    else:
        key = f"uploads/{user_id}/{uuid4()}-{sanitized_filename}"

    settings = get_settings()
    client = get_s3_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": key,
            "ContentType": mime_type,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRES_SECONDS,
        HttpMethod="PUT",
    )

    return {
        "upload_url": upload_url,
        "public_url": _public_url(key),
        "key": key,
        "expires_in": PRESIGNED_URL_EXPIRES_SECONDS,
    }


async def generate_result_upload_url(
    db: AsyncSession,
    order_id: UUID,
    user_id: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
) -> dict[str, str | int]:
    return await generate_upload_url(
        user_id,
        filename,
        "RESULT_PDF",
        mime_type,
        size_bytes,
        db,
        order_id,
    )


async def confirm_upload(
    db: AsyncSession,
    order_id: UUID,
    key: str,
    filename: str,
    url: str,
    file_type: str,
    mime_type: str,
    size_bytes: int,
    user_id: str,
) -> File:
    _validate_file_type(file_type)
    _validate_size(file_type, size_bytes)

    if file_type == "RESULT_PDF":
        await _require_admin(db, user_id)
        order = await db.get(Order, str(order_id))
        if order is None:
            raise _not_found("Order not found")
        if not key.startswith(f"results/{order_id}/"):
            raise _forbidden("Result key does not belong to this order")
    else:
        order = await _get_order_for_user(db, order_id, user_id)
        if not key.startswith(f"uploads/{user_id}/"):
            raise _forbidden("Upload key does not belong to this user")
        existing_count = await db.scalar(
            select(func.count(File.id)).where(
                File.order_id == str(order_id),
                File.file_type != "RESULT_PDF",
            )
        )
        if (existing_count or 0) >= MAX_USER_FILES_PER_ORDER:
            raise _bad_request(f"Maximum {MAX_USER_FILES_PER_ORDER} files per order")

    if url != _public_url(key):
        raise _bad_request("Upload URL does not match storage key")

    file = File(
        order_id=str(order_id),
        filename=key,
        original_name=filename,
        url=url,
        file_type=file_type,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )

    try:
        db.add(file)
        if file_type == "RESULT_PDF" and order.status != "DONE":
            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    old_status=order.status,
                    new_status="DONE",
                    old_progress=order.progress,
                    new_progress=100,
                    changed_by=user_id,
                    note="Result PDF uploaded",
                )
            )
            order.status = "DONE"
            order.progress = 100
        await db.commit()
        await db.refresh(file)
    except Exception:
        await db.rollback()
        raise

    return file


async def get_order_files(
    db: AsyncSession,
    order_id: UUID,
    user_id: str,
) -> list[File]:
    await _get_order_for_user(db, order_id, user_id)
    result = await db.execute(
        select(File).where(File.order_id == str(order_id)).order_by(File.created_at)
    )
    return list(result.scalars().all())


async def delete_file(db: AsyncSession, file_id: UUID, user_id: str) -> None:
    result = await db.execute(
        select(File)
        .where(File.id == str(file_id))
        .options(selectinload(File.order))
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise _not_found("File not found")

    user = await db.get(User, user_id)
    if file.order.user_id != user_id and not (user and user.is_admin):
        raise _forbidden()

    client = get_s3_client()
    settings = get_settings()
    try:
        await asyncio.to_thread(
            client.delete_object,
            Bucket=settings.R2_BUCKET_NAME,
            Key=file.filename,
        )
        await db.delete(file)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
