from __future__ import annotations

import jwt

from app.config import get_settings
from app.exceptions import PointCVException


class JWTService:
    ALGORITHM = "HS256"

    @staticmethod
    def verify_token(token: str) -> dict:
        settings = get_settings()
        if not settings.BETTER_AUTH_SECRET:
            raise PointCVException(
                status_code=503,
                detail="Authentication service is not configured",
                code="AUTH_NOT_CONFIGURED",
            )
        try:
            return jwt.decode(
                token,
                settings.BETTER_AUTH_SECRET,
                algorithms=[JWTService.ALGORITHM],
                audience=settings.BETTER_AUTH_URL or None,
                issuer=settings.BETTER_AUTH_URL or None,
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_aud": bool(settings.BETTER_AUTH_URL),
                    "verify_iss": bool(settings.BETTER_AUTH_URL),
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise PointCVException(
                status_code=401,
                detail="Token has expired",
                code="TOKEN_EXPIRED",
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise PointCVException(
                status_code=401,
                detail="Invalid token",
                code="INVALID_TOKEN",
            ) from exc
        except jwt.PyJWTError as exc:
            raise PointCVException(
                status_code=401,
                detail="Invalid token",
                code="INVALID_TOKEN",
            ) from exc

    @staticmethod
    def get_user_id_from_token(token: str) -> str:
        payload = JWTService.verify_token(token)
        return payload.get("sub") or payload.get("id")

    @staticmethod
    def get_user_role_from_token(token: str) -> str:
        payload = JWTService.verify_token(token)
        return payload.get("role", "customer")


jwt_service = JWTService()
