from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions.admin import AdminAccessRequiredError
from app.domain.users.model import User


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_admin", False):
        raise AdminAccessRequiredError()
    return user
