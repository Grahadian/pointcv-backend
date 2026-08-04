from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User

router = APIRouter(tags=["auth"])


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)) -> dict[str, str | bool | None]:
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "is_admin": user.is_admin,
        "role": user.role,
    }
