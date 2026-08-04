import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole

logger = logging.getLogger(__name__)


async def _is_first_user(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one() == 0


def _normalize_profile(
    email: str | None,
    name: str | None,
    avatar_url: str | None,
) -> dict[str, Any]:
    return {
        "email": email.strip() if email else None,
        "name": name.strip() if name else None,
        "avatar_url": avatar_url,
    }


def _update_user_fields(
    user: User,
    email: str | None,
    name: str | None,
    avatar_url: str | None,
) -> None:
    if email:
        user.email = email
    if name:
        user.name = name
    if avatar_url:
        user.avatar_url = avatar_url


async def get_or_create_user(
    db: AsyncSession,
    user_id: str,
    email: str | None = None,
    name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        _update_user_fields(user, email, name, avatar_url)
        await db.commit()
        await db.refresh(user)
        return user

    profile = _normalize_profile(email, name, avatar_url)
    is_first = await _is_first_user(db)
    user = User(
        id=user_id,
        email=profile["email"] or f"{user_id}@pointcv.local",
        name=profile["name"],
        avatar_url=profile["avatar_url"],
        is_admin=is_first,
        role=(
            UserRole.ADMIN.value if is_first else UserRole.CUSTOMER.value
        ),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def ensure_user_exists(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    is_first = await _is_first_user(db)
    user = User(
        id=user_id,
        email=f"{user_id}@pointcv.local",
        is_admin=is_first,
        role=UserRole.ADMIN.value if is_first else UserRole.CUSTOMER.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user