import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Package(TimestampMixin, Base):
    __tablename__ = "packages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[dict] = mapped_column(JSON, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    max_revisions: Mapped[int] = mapped_column(Integer, nullable=False)
    includes_letter: Mapped[bool] = mapped_column(Boolean, default=False)
    includes_linkedin: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_support: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="package")


class CVTemplate(CreatedAtMixin, Base):
    __tablename__ = "cv_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[dict] = mapped_column(JSON, nullable=False)
    preview_image_url: Mapped[str | None] = mapped_column(String(1024))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="template")
    portfolio_items: Mapped[list["PortfolioItem"]] = relationship(
        back_populates="template"
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_orders_progress_between_0_and_100",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    package_id: Mapped[str] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), index=True
    )
    template_id: Mapped[str] = mapped_column(
        ForeignKey("cv_templates.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_id: Mapped[str | None] = mapped_column(String(255), index=True)
    payment_status: Mapped[str] = mapped_column(String(50), default="UNPAID", index=True)
    voucher_code: Mapped[str | None] = mapped_column(String(100), index=True)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    cv_data: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    user: Mapped[User] = relationship(back_populates="orders")
    package: Mapped[Package] = relationship(back_populates="orders")
    template: Mapped[CVTemplate] = relationship(back_populates="orders")
    files: Mapped[list["File"]] = relationship(back_populates="order")
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class File(CreatedAtMixin, Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(
        Enum(
            "PHOTO",
            "CERTIFICATE",
            "DIPLOMA",
            "DOCUMENT",
            "RESULT_PDF",
            name="file_type",
        ),
        index=True,
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[Order] = relationship(back_populates="files")


class OrderStatusHistory(CreatedAtMixin, Base):
    __tablename__ = "order_status_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    old_progress: Mapped[int | None] = mapped_column(Integer)
    new_progress: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    order: Mapped[Order] = relationship(back_populates="status_history")


class PaymentEvent(CreatedAtMixin, Base):
    __tablename__ = "payment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    notification_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    transaction_id: Mapped[str | None] = mapped_column(String(255), index=True)
    transaction_status: Mapped[str | None] = mapped_column(String(50), index=True)
    payment_type: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error: Mapped[str | None] = mapped_column(Text)


class Voucher(CreatedAtMixin, Base):
    __tablename__ = "vouchers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    discount_type: Mapped[str] = mapped_column(
        Enum("PERCENTAGE", "FIXED", name="discount_type"), nullable=False
    )
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class PortfolioItem(CreatedAtMixin, Base):
    __tablename__ = "portfolio_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    title: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[dict | None] = mapped_column(JSON)
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("cv_templates.id", ondelete="SET NULL"), index=True
    )
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(1024))
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    template: Mapped[CVTemplate | None] = relationship(back_populates="portfolio_items")


class BlogPost(TimestampMixin, Base):
    __tablename__ = "blog_posts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    title: Mapped[dict] = mapped_column(JSON, nullable=False)
    excerpt: Mapped[dict] = mapped_column(JSON, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(1024))
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    meta_title: Mapped[str | None] = mapped_column(String(255))
    meta_description: Mapped[str | None] = mapped_column(String(512))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)


Index("idx_users_email", User.email)
Index("idx_users_is_admin", User.is_admin)
Index("idx_orders_user_id", Order.user_id)
Index("idx_orders_status", Order.status)
Index("idx_files_order_id", File.order_id)
Index("idx_order_history_order_id", OrderStatusHistory.order_id)
Index("ix_orders_user_status", Order.user_id, Order.status)
Index("ix_files_order_type", File.order_id, File.file_type)
Index("ix_blog_posts_active_published", BlogPost.is_active, BlogPost.published_at)
