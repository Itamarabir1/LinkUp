from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user_optional
from app.core.exceptions.group import GroupFilterAuthRequiredError, GroupNotMemberError
from app.db.session import get_db
from app.domain.groups.crud import get_membership
from app.domain.users.model import User


async def require_group_member(
    group_id: UUID | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> UUID | None:
    """
    Router dependency.
    - No group_id → return None (normal public flow)
    - group_id but no logged-in user → 401
    - group_id but user is not a member → 403
    - Member → return group_id
    """
    if group_id is None:
        return None
    if current_user is None:
        raise GroupFilterAuthRequiredError()
    member = await get_membership(db, group_id, current_user.user_id)
    if not member:
        raise GroupNotMemberError()
    return group_id


async def verify_group_membership(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
) -> None:
    """
    Direct membership check (not a FastAPI dependency).
    Used by POST /rides/ where group_id comes from the body.
    Raises 403 if the user is not a group member.
    """
    member = await get_membership(db, group_id, user_id)
    if not member:
        raise GroupNotMemberError()
