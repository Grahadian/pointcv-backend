from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_admin
from app.schemas.catalog import PackageCreate, PackageResponse, PackageUpdate
from app.schemas.content import (
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
    DashboardStatsResponse,
    PortfolioItemCreate,
    PortfolioItemResponse,
    PortfolioItemUpdate,
    VoucherCreate,
    VoucherResponse,
    VoucherUpdate,
)
from app.schemas.orders import (
    AdminOrderListResponse,
    OrderResponse,
    StatusUpdate,
    UploadRequest,
    UploadURLResponse,
)
from app.services import admin_service, file_service, order_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me")
async def get_admin(user_id: str = Depends(require_admin)) -> dict[str, str | bool]:
    return {"user_id": user_id, "is_admin": True}


@router.get("/orders", response_model=AdminOrderListResponse)
async def list_all_orders(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_admin_orders(db, status, page, limit, search)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def update_status(
    order_id: UUID,
    data: StatusUpdate,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await order_service.update_order_status(
        db, order_id, data.status, data.progress, user_id, data.note
    )


@router.post("/orders/{order_id}/upload-result", response_model=UploadURLResponse)
async def upload_result(
    order_id: UUID,
    data: UploadRequest,
    user_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await file_service.generate_result_upload_url(
        db, order_id, user_id, data.filename, data.mime_type, data.size_bytes
    )


@router.get("/packages", response_model=list[PackageResponse])
async def list_packages(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_packages(db, page, limit)


@router.post(
    "/packages",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_package(
    data: PackageCreate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.create_package(db, data)


@router.patch("/packages/{id}", response_model=PackageResponse)
async def update_package(
    id: str,
    data: PackageUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_package(db, id, data)


@router.delete("/packages/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package(
    id: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_package(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/vouchers", response_model=list[VoucherResponse])
async def list_vouchers(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_vouchers(db, page, limit)


@router.post(
    "/vouchers",
    response_model=VoucherResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voucher(
    data: VoucherCreate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.create_voucher(db, data)


@router.patch("/vouchers/{id}", response_model=VoucherResponse)
async def update_voucher(
    id: str,
    data: VoucherUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_voucher(db, id, data)


@router.delete("/vouchers/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voucher(
    id: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_voucher(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/portfolio", response_model=list[PortfolioItemResponse])
async def list_portfolio(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_portfolio(db, page, limit)


@router.post(
    "/portfolio",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio(
    data: PortfolioItemCreate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.create_portfolio_item(db, data)


@router.patch("/portfolio/{id}", response_model=PortfolioItemResponse)
async def update_portfolio(
    id: str,
    data: PortfolioItemUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_portfolio_item(db, id, data)


@router.delete("/portfolio/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    id: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_portfolio_item(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/blog", response_model=list[BlogPostListResponse])
async def list_blog(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_blog(db, page, limit)


@router.post(
    "/blog",
    response_model=BlogPostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_blog(
    data: BlogPostCreate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.create_blog_post(db, data)


@router.patch("/blog/{id}", response_model=BlogPostResponse)
async def update_blog(
    id: str,
    data: BlogPostUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.update_blog_post(db, id, data)


@router.delete("/blog/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blog(
    id: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_service.delete_blog_post(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_stats(
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_dashboard_stats(db)
