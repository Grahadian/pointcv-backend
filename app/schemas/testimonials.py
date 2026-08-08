from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TestimonialCreate(BaseModel):
    order_id: UUID
    user_name: str = Field(min_length=1, max_length=255)
    user_role: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=20, max_length=500)
    rating: int = Field(ge=1, le=5)
    avatar_url: str | None = Field(default=None, max_length=1024)


class TestimonialUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class TestimonialResponse(ORMModel):
    id: str
    user_id: str
    order_id: str | None = None
    user_name: str
    user_role: str
    content: str
    rating: int
    avatar_url: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class TestimonialListResponse(BaseModel):
    items: list[TestimonialResponse]
    total: int
    page: int
    limit: int
    pages: int
