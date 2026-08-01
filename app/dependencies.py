from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db as get_database_session
from app.models import User

security = HTTPBearer(auto_error=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_database_session():
        yield session


async def _fetch_jwks() -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        return response.json()


def _select_jwk(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    key_id = header.get("kid")
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == key_id:
            return key_data

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication key not found",
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    try:
        jwks = await _fetch_jwks()
        key_data = _select_jwk(token, jwks)
        public_key = jwk.construct(key_data)
        algorithm = key_data.get("alg", "RS256")
        claims = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=[algorithm],
            options={"verify_aud": False},
        )
    except (JWTError, httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        ) from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a subject",
        )
    return user_id


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user
