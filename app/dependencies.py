import time
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

security = HTTPBearer(auto_error=False)

JWKS_CACHE_TTL_SECONDS = 300
DEV_AUTH_TOKEN = "test_token"
DEV_AUTH_USER_ID = "test_user"
_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at = 0.0


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_database_session():
        yield session


async def _fetch_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_cache_expires_at

    now = time.time()
    if _jwks_cache is not None and now < _jwks_cache_expires_at:
        return _jwks_cache

    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        jwks = response.json()

    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise ValueError("Invalid JWKS response")

    _jwks_cache = jwks
    _jwks_cache_expires_at = now + JWKS_CACHE_TTL_SECONDS
    return jwks


def _select_jwk(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    key_id = header.get("kid")
    if not key_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing a key id",
        )

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == key_id:
            return key_data

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication key not found",
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication bearer token required",
        )

    token = credentials.credentials
    settings = get_settings()
    if (
        token == DEV_AUTH_TOKEN
        and (settings.DEBUG or settings.CLERK_SECRET_KEY.startswith("sk_test_"))
    ):
        return DEV_AUTH_USER_ID

    try:
        jwks = await _fetch_jwks()
        key_data = _select_jwk(token, jwks)
        public_key = jwk.construct(key_data)
        algorithm = key_data.get("alg") or "RS256"
        claims = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=[algorithm],
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_nbf": True,
            },
        )
    except HTTPException:
        raise
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
) -> str:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return user_id
