import math
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import PointCVException
from app.models import Order, Testimonial
from app.schemas.testimonials import TestimonialCreate

ALLOWED_STATUSES = {"pending", "approved", "rejected"}


def _not_found(message: str = "Testimoni tidak ditemukan") -> PointCVException:
    return PointCVException(status.HTTP_404_NOT_FOUND, message, "not_found")


def _bad_request(message: str) -> PointCVException:
    return PointCVException(status.HTTP_400_BAD_REQUEST, message, "bad_request")


def _forbidden(message: str = "Forbidden") -> PointCVException:
    return PointCVException(status.HTTP_403_FORBIDDEN, message, "forbidden")


async def _require_testimonial(
    db: AsyncSession, testimonial_id: UUID | str
) -> Testimonial:
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == str(testimonial_id))
    )
    testimonial = result.scalar_one_or_none()
    if testimonial is None:
        raise _not_found()
    return testimonial


def _validate_status(testimonial_status: str) -> None:
    if testimonial_status not in ALLOWED_STATUSES:
        raise _bad_request("Status testimoni tidak valid")


async def create_testimonial(
    db: AsyncSession, user_id: str, data: TestimonialCreate
) -> Testimonial:
    order = await db.get(Order, str(data.order_id))
    if order is None:
        raise _bad_request("Pesanan tidak ditemukan")
    if order.user_id != user_id:
        raise _forbidden()
    if order.status != "DONE":
        raise _bad_request("Testimoni hanya dapat dikirim untuk pesanan yang selesai")

    existing = (
        await db.execute(
            select(Testimonial.id).where(
                Testimonial.user_id == user_id,
                Testimonial.order_id == str(data.order_id),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise _bad_request("Anda sudah mengirim testimoni untuk pesanan ini")

    testimonial = Testimonial(
        user_id=user_id,
        order_id=str(data.order_id),
        user_name=data.user_name.strip(),
        user_role=data.user_role.strip(),
        content=data.content.strip(),
        rating=data.rating,
        avatar_url=data.avatar_url,
        status="pending",
    )
    db.add(testimonial)
    await db.commit()
    await db.refresh(testimonial)
    return testimonial


async def list_my_testimonials(
    db: AsyncSession, user_id: str
) -> list[Testimonial]:
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.user_id == user_id)
        .order_by(Testimonial.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all_testimonials(
    db: AsyncSession,
    status_filter: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    if status_filter is not None:
        _validate_status(status_filter)

    filters = []
    if status_filter:
        filters.append(Testimonial.status == status_filter)

    count_query = select(func.count(Testimonial.id))
    list_query = select(Testimonial)
    for condition in filters:
        count_query = count_query.where(condition)
        list_query = list_query.where(condition)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(
        list_query.order_by(Testimonial.created_at.desc())
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


async def review_testimonial(
    db: AsyncSession, testimonial_id: UUID | str, new_status: str
) -> Testimonial:
    _validate_status(new_status)
    if new_status == "pending":
        raise _bad_request("Status tidak dapat dikembalikan ke pending")

    testimonial = await _require_testimonial(db, testimonial_id)
    testimonial.status = new_status
    await db.commit()
    await db.refresh(testimonial)
    return testimonial


async def list_approved_testimonials(
    db: AsyncSession, limit: int = 50
) -> list[Testimonial]:
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.status == "approved")
        .order_by(Testimonial.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
