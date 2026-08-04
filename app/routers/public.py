from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from cachetools import TTLCache
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.exceptions import PointCVException
from app.models import Package
from app.schemas.catalog import PackageResponse, TemplateResponse
from app.schemas.content import (
    BlogListResponse,
    BlogPostResponse,
    PortfolioItemResponse,
    VoucherValidateRequest,
    VoucherValidateResponse,
)
from app.services import admin_service, order_service

router = APIRouter(prefix="/public", tags=["public"])

# In-memory cache for read-only public content. 5-minute TTL so marketing
# pages load instantly without hammering SQLite on a cold Render instance.
_public_cache: TTLCache = TTLCache(maxsize=100, ttl=300)

P = ParamSpec("P")
T = TypeVar("T")


def cached_public(*param_names: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = "|".join(f"{name}={kwargs.get(name)}" for name in param_names)
            cache_key = f"{func.__name__}:{key}"
            if cache_key in _public_cache:
                return _public_cache[cache_key]
            result = await func(*args, **kwargs)
            _public_cache[cache_key] = result
            return result

        return wrapper

    return decorator


@router.post("/vouchers/validate", response_model=VoucherValidateResponse)
async def validate_voucher(
    data: VoucherValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    package = await db.get(Package, data.package_id)
    if package is None:
        raise PointCVException(404, "Package not found", "not_found")
    return await order_service.validate_voucher(db, data.code, package.price)


@router.get("/packages", response_model=list[PackageResponse])
@cached_public("page", "limit")
async def list_packages(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_packages(db, page, limit)


@router.get("/templates", response_model=list[TemplateResponse])
@cached_public("page", "limit")
async def list_templates(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_templates(db, page, limit)


@router.get("/portfolio", response_model=list[PortfolioItemResponse])
@cached_public("category", "page", "limit")
async def list_portfolio(
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_portfolio(db, category, page, limit)


@router.get("/blog", response_model=BlogListResponse)
@cached_public("page", "limit", "tag")
async def list_blog(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_blog(db, page, limit, tag)


# Blog detail is NOT cached: the endpoint increments view_count on every read
# and should always reflect the latest published state.
@router.get("/blog/{slug}", response_model=BlogPostResponse)
async def get_blog_post(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_public_blog_post(db, slug)
