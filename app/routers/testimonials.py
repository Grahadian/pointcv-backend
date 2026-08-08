from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db, require_admin
from app.schemas.testimonials import (
    TestimonialCreate,
    TestimonialListResponse,
    TestimonialResponse,
    TestimonialUpdate,
)
from app.services import testimonial_service

router = APIRouter(prefix="/testimonials", tags=["testimonials"])
admin_router = APIRouter(prefix="/admin/testimonials", tags=["admin-testimonials"])
public_router = APIRouter(prefix="/public/testimonials", tags=["public-testimonials"])


@router.post(
    "",
    response_model=TestimonialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_testimonial(
    data: TestimonialCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await testimonial_service.create_testimonial(db, user_id, data)


@router.get("/my", response_model=list[TestimonialResponse])
async def list_my_testimonials(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await testimonial_service.list_my_testimonials(db, user_id)


@admin_router.get("", response_model=TestimonialListResponse)
async def list_all_testimonials(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await testimonial_service.list_all_testimonials(db, status, page, limit)


@admin_router.patch("/{testimonial_id}", response_model=TestimonialResponse)
async def review_testimonial(
    testimonial_id: UUID,
    data: TestimonialUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await testimonial_service.review_testimonial(
        db, testimonial_id, data.status
    )


@public_router.get("", response_model=list[TestimonialResponse])
async def list_approved_testimonials(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await testimonial_service.list_approved_testimonials(db, limit)
