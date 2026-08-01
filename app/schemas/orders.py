from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.catalog import PackageResponse, TemplateResponse
from app.schemas.common import ORMModel


class FileBase(BaseModel):
    order_id: str
    filename: str
    original_name: str
    url: str
    file_type: str
    mime_type: str
    size_bytes: int


class FileCreate(FileBase):
    pass


class FileUpdate(BaseModel):
    filename: str | None = None
    original_name: str | None = None
    url: str | None = None
    file_type: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


class FileResponse(FileBase, ORMModel):
    id: str
    created_at: datetime


class OrderBase(BaseModel):
    user_id: str
    package_id: str
    template_id: str
    price: int
    status: str = "PENDING"
    progress: int = 0
    payment_id: str | None = None
    payment_status: str = "UNPAID"
    voucher_code: str | None = None
    discount_amount: int = 0
    cv_data: dict[str, Any] | None = None
    notes: str | None = None
    revision_count: int = 0


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    package_id: str | None = None
    template_id: str | None = None
    status: str | None = None
    progress: int | None = None
    price: int | None = None
    payment_id: str | None = None
    payment_status: str | None = None
    voucher_code: str | None = None
    discount_amount: int | None = None
    cv_data: dict[str, Any] | None = None
    notes: str | None = None
    revision_count: int | None = None


class OrderResponse(OrderBase, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
    package: PackageResponse
    template: TemplateResponse
    files: list[FileResponse] = Field(default_factory=list)


class OrderStatusHistoryBase(BaseModel):
    order_id: str
    old_status: str | None = None
    new_status: str
    old_progress: int | None = None
    new_progress: int
    changed_by: str | None = None
    note: str | None = None


class OrderStatusHistoryCreate(OrderStatusHistoryBase):
    pass


class OrderStatusHistoryUpdate(BaseModel):
    note: str | None = None


class OrderStatusHistoryResponse(OrderStatusHistoryBase, ORMModel):
    id: str
    created_at: datetime
