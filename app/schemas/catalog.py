from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PackageBase(BaseModel):
    name: str
    slug: str
    description: dict[str, Any]
    price: int
    max_revisions: int
    includes_letter: bool = False
    includes_linkedin: bool = False
    priority_support: bool = False
    is_active: bool = True
    sort_order: int = 0


class PackageCreate(PackageBase):
    pass


class PackageUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: dict[str, Any] | None = None
    price: int | None = None
    max_revisions: int | None = None
    includes_letter: bool | None = None
    includes_linkedin: bool | None = None
    priority_support: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class PackageResponse(PackageBase, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class TemplateBase(BaseModel):
    name: str
    slug: str
    description: dict[str, Any]
    preview_image_url: str | None = None
    is_active: bool = True
    sort_order: int = 0


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: dict[str, Any] | None = None
    preview_image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class TemplateResponse(TemplateBase, ORMModel):
    id: str
    created_at: datetime
