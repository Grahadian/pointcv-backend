from fastapi import APIRouter, Depends

from app.dependencies import require_admin
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me")
async def get_admin(user: User = Depends(require_admin)) -> dict[str, str | bool]:
    return {"user_id": user.id, "is_admin": user.is_admin}
