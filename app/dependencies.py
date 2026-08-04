from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db as get_database_session
from app.models import User
from app.services.auth_service import ensure_user_exists, get_or_create_user
from app.services.jwt_service import jwt_service

security = HTTPBearer(auto_error=False)

DEV_AUTH_TOKEN = "test_token"
DEV_AUTH_USER_ID = "test_user"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_database_session():
        yield session


def _verify_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.BETTER_AUTH_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        )
    return jwt_service.verify_token(token)


def _extract_claims(claims: dict[str, Any]) -> tuple[str, str | None, str | None, str | None]:
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a subject",
        )
    email = claims.get("email")
    name = claims.get("name")
    avatar_url = claims.get("image")
    return user_id, email, name, avatar_url


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication bearer token required",
        )

    token = credentials.credentials
    settings = get_settings()
    if token == DEV_AUTH_TOKEN and settings.DEBUG:
        await ensure_user_exists(db, DEV_AUTH_USER_ID)
        return DEV_AUTH_USER_ID

    claims = _verify_token(token)
    user_id, email, name, avatar_url = _extract_claims(claims)

    await get_or_create_user(
        db,
        user_id=user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
    )

    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> str:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return user_id
