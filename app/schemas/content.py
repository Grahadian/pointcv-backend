from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.catalog import TemplateResponse
from app.schemas.common import ORMModel


class VoucherBase(BaseModel):
    code: str
    description: str | None = None
    discount_type: str
    discount_value: int
    max_uses: int | None = None
    used_count: int = 0
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseModel):
    code: str | None = None
    description: str | None = None
    discount_type: str | None = None
    discount_value: int | None = None
    max_uses: int | None = None
    used_count: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None


class VoucherResponse(VoucherBase, ORMModel):
    id: str
    created_at: datetime


class VoucherValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    package_id: str


class VoucherValidateResponse(BaseModel):
    valid: bool
    discount: int
    message: str


class PortfolioItemBase(BaseModel):
    title: dict[str, Any]
    description: dict[str, Any] | None = None
    template_id: str | None = None
    image_url: str
    pdf_url: str | None = None
    category: str | None = None
    is_active: bool = True
    sort_order: int = 0


class PortfolioItemCreate(PortfolioItemBase):
    pass


class PortfolioItemUpdate(BaseModel):
    title: dict[str, Any] | None = None
    description: dict[str, Any] | None = None
    template_id: str | None = None
    image_url: str | None = None
    pdf_url: str | None = None
    category: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class PortfolioItemResponse(PortfolioItemBase, ORMModel):
    id: str
    created_at: datetime
    template: TemplateResponse | None = None


class BlogPostBase(BaseModel):
    slug: str
    title: dict[str, Any]
    excerpt: dict[str, Any]
    content: dict[str, Any]
    cover_image_url: str | None = None
    author: str
    tags: list[Any] = Field(default_factory=list)
    meta_title: str | None = None
    meta_description: str | None = None
    published_at: datetime | None = None
    is_active: bool = True
    view_count: int = 0


class BlogPostCreate(BlogPostBase):
    pass


class BlogPostUpdate(BaseModel):
    slug: str | None = None
    title: dict[str, Any] | None = None
    excerpt: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    cover_image_url: str | None = None
    author: str | None = None
    tags: list[Any] | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    published_at: datetime | None = None
    is_active: bool | None = None
    view_count: int | None = None


class BlogPostResponse(BlogPostBase, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class BlogPostListResponse(ORMModel):
    id: str
    slug: str
    title: dict[str, Any]
    excerpt: dict[str, Any]
    cover_image_url: str | None = None
    author: str
    tags: list[Any] = Field(default_factory=list)
    published_at: datetime | None = None
    view_count: int = 0
    created_at: datetime
    updated_at: datetime


class BlogListResponse(BaseModel):
    items: list[BlogPostListResponse]
    total: int
    page: int
    limit: int
    pages: int


class DashboardStatsResponse(BaseModel):
    total_orders: int
    pending_orders: int
    processing_orders: int
    completed_orders: int
    total_revenue: int
    revenue_this_month: int
    total_users: int
    new_users_this_month: int
