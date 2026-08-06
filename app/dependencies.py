import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.models import User, UserRole

settings = get_settings()
security = HTTPBearer(auto_error=False)


def verify_better_auth_token(token: str) -> dict:
    """Verify Better Auth JWT token."""
    try:
        return jwt.decode(
            token,
            settings.BETTER_AUTH_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _extract_token(request: Request) -> str:
    """Extract the Better Auth JWT from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_user_id(payload: dict) -> str:
    user_id = payload.get("sub") or payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return str(user_id)


async def get_current_user_id(request: Request) -> str:
    """Extract user ID from the Better Auth JWT in the Authorization header."""
    return _extract_user_id(verify_better_auth_token(_extract_token(request)))


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get user from database or create if not exists (lazy sync)."""
    payload = verify_better_auth_token(_extract_token(request))
    user_id = _extract_user_id(payload)
    role = payload.get("role")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Lazy create user, reflecting the token role when known.
        user = User(
            id=user_id,
            email=f"user_{user_id[:8]}@pointcv.id",
            role=role or UserRole.CUSTOMER.value,
            is_admin=role == "admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def require_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Require admin role.

    Decodes the Better Auth HS256 JWT (signed with BETTER_AUTH_SECRET) and
    grants access when the token carries an "admin" role claim. As a fallback
    for tokens that do not embed a role, the backend `users` table is checked.
    The backend user row is upserted so downstream DB-based admin checks (e.g.
    file uploads) are consistent with the JWT decision.
    """
    payload = verify_better_auth_token(_extract_token(request))
    user_id = _extract_user_id(payload)

    if payload.get("role") == "admin":
        user = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                id=user_id,
                email=f"user_{user_id[:8]}@pointcv.id",
                role="admin",
                is_admin=True,
            )
            db.add(user)
            await db.commit()
        elif user.role != "admin" or not user.is_admin:
            user.role = "admin"
            user.is_admin = True
            await db.commit()
        return user_id

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is not None and (user.role == "admin" or user.is_admin):
        return user_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )
