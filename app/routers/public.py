from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.catalog import PackageResponse, TemplateResponse
from app.schemas.content import BlogListResponse, BlogPostResponse, PortfolioItemResponse
from app.services import admin_service

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/packages", response_model=list[PackageResponse])
async def list_packages(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_packages(db, page, limit)


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_templates(db, page, limit)


@router.get("/portfolio", response_model=list[PortfolioItemResponse])
async def list_portfolio(
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_portfolio(db, category, page, limit)


@router.get("/blog", response_model=BlogListResponse)
async def list_blog(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.list_public_blog(db, page, limit, tag)


@router.get("/blog/{slug}", response_model=BlogPostResponse)
async def get_blog_post(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_public_blog_post(db, slug)
