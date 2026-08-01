from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

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


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    file_type: str
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)
    order_id: UUID | None = None


class UploadURLResponse(BaseModel):
    upload_url: str
    public_url: str
    key: str
    expires_in: int


class UploadConfirm(BaseModel):
    order_id: UUID
    key: str = Field(min_length=1, max_length=1024)
    filename: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=1024)
    file_type: str
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)


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


class OrderCreate(BaseModel):
    package_id: str
    template_id: str
    voucher_code: str | None = None
    cv_data: dict[str, Any] | None = None
    notes: str | None = None


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

    @computed_field
    @property
    def final_price(self) -> int:
        return max(self.price - self.discount_amount, 0)


class RevisionRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class StatusUpdate(BaseModel):
    status: str
    progress: int = Field(ge=0, le=100)
    note: str | None = None


class AdminOrderUser(ORMModel):
    id: str
    email: str
    name: str | None = None


class AdminOrderResponse(OrderResponse):
    user: AdminOrderUser


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderResponse]
    total: int
    page: int
    limit: int
    pages: int


class PaymentRequest(BaseModel):
    order_id: UUID


class PaymentResponse(BaseModel):
    snap_token: str
    order_id: str
    redirect_url: str | None = None


class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str
    payment_status: str
    payment_id: str | None = None
    price: int
    discount_amount: int
    final_price: int


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
