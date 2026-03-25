from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.domain.users.model import User


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user

