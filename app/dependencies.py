import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.models import User

settings = get_settings()
security = HTTPBearer(auto_error=False)


def verify_better_auth_token(token: str) -> dict:
    """Verify Better Auth JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.BETTER_AUTH_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_id(request: Request) -> str:
    """
    Extract user ID from Better Auth session.
    Tries: 1) Authorization header, 2) Cookie
    """
    token = None
    
    # 1. Try Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    # 2. Try Better Auth cookie (cross-origin fallback)
    if not token:
        cookie = request.cookies.get("better-auth.session_token")
        if cookie:
            token = cookie
    
    # 3. Try chunked cookie (Better Auth sometimes splits long tokens)
    if not token:
        token = request.cookies.get("__Secure-better-auth.session_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_better_auth_token(token)
    user_id = payload.get("sub") or payload.get("id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get user from database or create if not exists (lazy sync)."""
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # Lazy create user
        user = User(id=user_id, email=f"user_{user_id[:8]}@pointcv.id")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
