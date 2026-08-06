import math
from datetime import datetime
from typing import Any

from sqlalchemy import case, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import String

from app.exceptions import PointCVException
from app.models import BlogPost, CVTemplate, Order, Package, PortfolioItem, User, Voucher
from app.schemas.catalog import PackageCreate, PackageUpdate, TemplateCreate, TemplateUpdate
from app.schemas.content import (
    BlogPostCreate,
    BlogPostUpdate,
    PortfolioItemCreate,
    PortfolioItemUpdate,
    VoucherCreate,
    VoucherUpdate,
)


def _bad_request(message: str) -> PointCVException:
    return PointCVException(400, message, "bad_request")


def _not_found(message: str) -> PointCVException:
    return PointCVException(404, message, "not_found")


def _conflict(message: str) -> PointCVException:
    return PointCVException(409, message, "conflict")


def _pages(total: int, limit: int) -> int:
    return math.ceil(total / limit) if total else 0


def _month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def _validate_bilingual(value: dict[str, Any], field_name: str) -> None:
    if not isinstance(value.get("id"), str) or not value["id"].strip():
        raise _bad_request(f"{field_name}.id is required")
    if not isinstance(value.get("en"), str) or not value["en"].strip():
        raise _bad_request(f"{field_name}.en is required")


def _validate_package_data(data: PackageCreate | PackageUpdate) -> None:
    values = data.model_dump(exclude_unset=True)
    if "description" in values and values["description"] is not None:
        _validate_bilingual(values["description"], "description")
    if "price" in values and values["price"] is not None and values["price"] < 0:
        raise _bad_request("Package price must be greater than or equal to 0")
    if (
        "max_revisions" in values
        and values["max_revisions"] is not None
        and values["max_revisions"] < -1
    ):
        raise _bad_request("Package max_revisions must be -1 or greater")
    if "features" in values and values["features"] is not None:
        for feature in values["features"]:
            if not isinstance(feature, str) or not feature.strip():
                raise _bad_request("Package features must be non-empty strings")


def _validate_template_data(data: TemplateCreate | TemplateUpdate) -> None:
    values = data.model_dump(exclude_unset=True)
    if "description" in values and values["description"] is not None:
        _validate_bilingual(values["description"], "description")
    if "category" in values and values["category"] is not None:
        category = values["category"].upper()
        valid = {"MODERN", "CLASSIC", "ATS_FRIENDLY"}
        if category not in valid:
            raise _bad_request("Invalid template category")


def _validate_voucher_data(data: VoucherCreate | VoucherUpdate) -> None:
    values = data.model_dump(exclude_unset=True)
    discount_type = values.get("discount_type")
    if discount_type is not None and discount_type not in {"PERCENTAGE", "FIXED"}:
        raise _bad_request("Invalid voucher discount type")
    if (
        "discount_value" in values
        and values["discount_value"] is not None
        and values["discount_value"] <= 0
    ):
        raise _bad_request("Voucher discount_value must be greater than 0")
    if discount_type == "PERCENTAGE" and values.get("discount_value", 0) > 100:
        raise _bad_request("Percentage voucher cannot exceed 100")
    if (
        "max_uses" in values
        and values["max_uses"] is not None
        and values["max_uses"] <= 0
    ):
        raise _bad_request("Voucher max_uses must be greater than 0")
    if (
        "used_count" in values
        and values["used_count"] is not None
        and values["used_count"] < 0
    ):
        raise _bad_request("Voucher used_count must be greater than or equal to 0")
    valid_from = values.get("valid_from")
    valid_until = values.get("valid_until")
    if valid_from and valid_until and valid_from > valid_until:
        raise _bad_request("Voucher valid_from must be before valid_until")


def _validate_voucher_entity(voucher: Voucher) -> None:
    if voucher.discount_type not in {"PERCENTAGE", "FIXED"}:
        raise _bad_request("Invalid voucher discount type")
    if voucher.discount_value <= 0:
        raise _bad_request("Voucher discount_value must be greater than 0")
    if voucher.discount_type == "PERCENTAGE" and voucher.discount_value > 100:
        raise _bad_request("Percentage voucher cannot exceed 100")
    if voucher.max_uses is not None and voucher.max_uses <= 0:
        raise _bad_request("Voucher max_uses must be greater than 0")
    if voucher.used_count < 0:
        raise _bad_request("Voucher used_count must be greater than or equal to 0")
    if (
        voucher.valid_from
        and voucher.valid_until
        and voucher.valid_from > voucher.valid_until
    ):
        raise _bad_request("Voucher valid_from must be before valid_until")


def _validate_portfolio_data(data: PortfolioItemCreate | PortfolioItemUpdate) -> None:
    values = data.model_dump(exclude_unset=True)
    if "title" in values and values["title"] is not None:
        _validate_bilingual(values["title"], "title")
    if "description" in values and values["description"] is not None:
        _validate_bilingual(values["description"], "description")
    if "image_url" in values and not values["image_url"]:
        raise _bad_request("Portfolio image_url is required")


def _validate_blog_data(data: BlogPostCreate | BlogPostUpdate) -> None:
    values = data.model_dump(exclude_unset=True)
    for field_name in ["title", "excerpt", "content"]:
        if field_name in values and values[field_name] is not None:
            _validate_bilingual(values[field_name], field_name)
    if "tags" in values and values["tags"] is not None:
        for tag in values["tags"]:
            if not isinstance(tag, str) or not tag.strip():
                raise _bad_request("Blog tags must be non-empty strings")


async def _commit_refresh(db: AsyncSession, entity: Any) -> Any:
    try:
        await db.commit()
        await db.refresh(entity)
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict("Record conflicts with existing data") from exc
    except Exception:
        await db.rollback()
        raise
    return entity


async def _delete_entity(db: AsyncSession, entity: Any) -> None:
    try:
        await db.delete(entity)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict("Record is still referenced") from exc
    except Exception:
        await db.rollback()
        raise


def _apply_update(entity: Any, data: Any) -> None:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(entity, key, value)


async def list_public_packages(db: AsyncSession, page: int, limit: int) -> list[Package]:
    result = await db.execute(
        select(Package)
        .where(Package.is_active.is_(True))
        .order_by(Package.sort_order, Package.price)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_public_templates(db: AsyncSession, page: int, limit: int) -> list[CVTemplate]:
    result = await db.execute(
        select(CVTemplate)
        .where(CVTemplate.is_active.is_(True))
        .order_by(CVTemplate.sort_order, CVTemplate.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_public_portfolio(
    db: AsyncSession,
    category: str | None,
    page: int,
    limit: int,
) -> list[PortfolioItem]:
    query = (
        select(PortfolioItem)
        .where(PortfolioItem.is_active.is_(True))
        .options(selectinload(PortfolioItem.template))
    )
    if category:
        query = query.where(PortfolioItem.category == category)
    result = await db.execute(
        query.order_by(PortfolioItem.sort_order)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_public_blog(
    db: AsyncSession,
    page: int,
    limit: int,
    tag: str | None,
) -> dict[str, Any]:
    filters = [BlogPost.is_active.is_(True), BlogPost.published_at.is_not(None)]
    if tag:
        filters.append(cast(BlogPost.tags, String).contains(tag))

    total = (
        await db.execute(select(func.count(BlogPost.id)).where(*filters))
    ).scalar_one()
    result = await db.execute(
        select(BlogPost)
        .where(*filters)
        .order_by(BlogPost.published_at.desc(), BlogPost.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return {
        "items": list(result.scalars().all()),
        "total": total,
        "page": page,
        "limit": limit,
        "pages": _pages(total, limit),
    }


async def get_public_blog_post(db: AsyncSession, slug: str) -> BlogPost:
    result = await db.execute(
        select(BlogPost).where(
            BlogPost.slug == slug,
            BlogPost.is_active.is_(True),
            BlogPost.published_at.is_not(None),
        )
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise _not_found("Blog post not found")

    post.view_count += 1
    return await _commit_refresh(db, post)


async def list_packages(db: AsyncSession, page: int, limit: int) -> list[Package]:
    result = await db.execute(
        select(Package)
        .order_by(Package.sort_order, Package.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_package(db: AsyncSession, data: PackageCreate) -> Package:
    _validate_package_data(data)
    package = Package(**data.model_dump())
    db.add(package)
    return await _commit_refresh(db, package)


async def update_package(db: AsyncSession, package_id: str, data: PackageUpdate) -> Package:
    _validate_package_data(data)
    package = await db.get(Package, package_id)
    if package is None:
        raise _not_found("Package not found")
    _apply_update(package, data)
    return await _commit_refresh(db, package)


async def delete_package(db: AsyncSession, package_id: str) -> None:
    package = await db.get(Package, package_id)
    if package is None:
        raise _not_found("Package not found")
    await _delete_entity(db, package)


async def list_templates(db: AsyncSession, page: int, limit: int) -> list[CVTemplate]:
    result = await db.execute(
        select(CVTemplate)
        .order_by(CVTemplate.sort_order, CVTemplate.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_template(db: AsyncSession, data: TemplateCreate) -> CVTemplate:
    _validate_template_data(data)
    template = CVTemplate(**data.model_dump())
    db.add(template)
    return await _commit_refresh(db, template)


async def update_template(
    db: AsyncSession,
    template_id: str,
    data: TemplateUpdate,
) -> CVTemplate:
    _validate_template_data(data)
    template = await db.get(CVTemplate, template_id)
    if template is None:
        raise _not_found("Template not found")
    _apply_update(template, data)
    return await _commit_refresh(db, template)


async def delete_template(db: AsyncSession, template_id: str) -> None:
    template = await db.get(CVTemplate, template_id)
    if template is None:
        raise _not_found("Template not found")
    await _delete_entity(db, template)


async def list_vouchers(db: AsyncSession, page: int, limit: int) -> list[Voucher]:
    result = await db.execute(
        select(Voucher)
        .order_by(Voucher.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_voucher(db: AsyncSession, data: VoucherCreate) -> Voucher:
    _validate_voucher_data(data)
    voucher = Voucher(**data.model_dump())
    db.add(voucher)
    return await _commit_refresh(db, voucher)


async def update_voucher(db: AsyncSession, voucher_id: str, data: VoucherUpdate) -> Voucher:
    _validate_voucher_data(data)
    voucher = await db.get(Voucher, voucher_id)
    if voucher is None:
        raise _not_found("Voucher not found")
    _apply_update(voucher, data)
    _validate_voucher_entity(voucher)
    return await _commit_refresh(db, voucher)


async def delete_voucher(db: AsyncSession, voucher_id: str) -> None:
    voucher = await db.get(Voucher, voucher_id)
    if voucher is None:
        raise _not_found("Voucher not found")
    await _delete_entity(db, voucher)


async def list_portfolio(db: AsyncSession, page: int, limit: int) -> list[PortfolioItem]:
    result = await db.execute(
        select(PortfolioItem)
        .options(selectinload(PortfolioItem.template))
        .order_by(PortfolioItem.sort_order, PortfolioItem.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_portfolio_item(
    db: AsyncSession,
    data: PortfolioItemCreate,
) -> PortfolioItem:
    _validate_portfolio_data(data)
    if data.template_id and await db.get(CVTemplate, data.template_id) is None:
        raise _bad_request("Template not found")
    item = PortfolioItem(**data.model_dump())
    db.add(item)
    await _commit_refresh(db, item)
    return await get_portfolio_item(db, item.id)


async def get_portfolio_item(db: AsyncSession, item_id: str) -> PortfolioItem:
    result = await db.execute(
        select(PortfolioItem)
        .where(PortfolioItem.id == item_id)
        .options(selectinload(PortfolioItem.template))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise _not_found("Portfolio item not found")
    return item


async def update_portfolio_item(
    db: AsyncSession,
    item_id: str,
    data: PortfolioItemUpdate,
) -> PortfolioItem:
    _validate_portfolio_data(data)
    item = await db.get(PortfolioItem, item_id)
    if item is None:
        raise _not_found("Portfolio item not found")
    if data.template_id and await db.get(CVTemplate, data.template_id) is None:
        raise _bad_request("Template not found")
    _apply_update(item, data)
    await _commit_refresh(db, item)
    return await get_portfolio_item(db, item.id)


async def delete_portfolio_item(db: AsyncSession, item_id: str) -> None:
    item = await db.get(PortfolioItem, item_id)
    if item is None:
        raise _not_found("Portfolio item not found")
    await _delete_entity(db, item)


async def list_blog(db: AsyncSession, page: int, limit: int) -> list[BlogPost]:
    result = await db.execute(
        select(BlogPost)
        .order_by(BlogPost.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_blog_post(db: AsyncSession, data: BlogPostCreate) -> BlogPost:
    _validate_blog_data(data)
    post = BlogPost(**data.model_dump())
    db.add(post)
    return await _commit_refresh(db, post)


async def update_blog_post(
    db: AsyncSession,
    post_id: str,
    data: BlogPostUpdate,
) -> BlogPost:
    _validate_blog_data(data)
    post = await db.get(BlogPost, post_id)
    if post is None:
        raise _not_found("Blog post not found")
    _apply_update(post, data)
    return await _commit_refresh(db, post)


async def delete_blog_post(db: AsyncSession, post_id: str) -> None:
    post = await db.get(BlogPost, post_id)
    if post is None:
        raise _not_found("Blog post not found")
    await _delete_entity(db, post)


async def get_dashboard_stats(db: AsyncSession) -> dict[str, int]:
    month_start = _month_start()

    revenue_expr = func.coalesce(
        func.sum(
            case(
                (Order.payment_status == "PAID", Order.price - Order.discount_amount),
                else_=0,
            )
        ),
        0,
    )
    month_revenue_expr = func.coalesce(
        func.sum(
            case(
                (
                    (Order.payment_status == "PAID")
                    & (Order.updated_at >= month_start),
                    Order.price - Order.discount_amount,
                ),
                else_=0,
            )
        ),
        0,
    )

    order_row = (
        await db.execute(
            select(
                func.count(Order.id).label("total_orders"),
                func.count(case((Order.status == "PENDING", 1))).label("pending_orders"),
                func.count(case((Order.status == "PROCESSING", 1))).label("processing_orders"),
                func.count(case((Order.status == "DONE", 1))).label("completed_orders"),
                revenue_expr.label("total_revenue"),
                month_revenue_expr.label("revenue_this_month"),
            )
        )
    ).one()

    user_row = (
        await db.execute(
            select(
                func.count(User.id).label("total_users"),
                func.count(case((User.created_at >= month_start, 1))).label(
                    "new_users_this_month"
                ),
            )
        )
    ).one()

    return {
        "total_orders": order_row.total_orders,
        "pending_orders": order_row.pending_orders,
        "processing_orders": order_row.processing_orders,
        "completed_orders": order_row.completed_orders,
        "total_revenue": order_row.total_revenue,
        "revenue_this_month": order_row.revenue_this_month,
        "total_users": user_row.total_users,
        "new_users_this_month": user_row.new_users_this_month,
    }
