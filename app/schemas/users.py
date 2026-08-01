from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class UserBase(BaseModel):
    email: str
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False


class UserCreate(UserBase):
    id: str


class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    is_admin: bool | None = None


class UserResponse(UserBase, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
