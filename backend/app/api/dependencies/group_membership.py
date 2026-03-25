from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user_optional
from app.db.session import get_db
from app.domain.groups.crud import get_membership
from app.domain.users.model import User


async def require_group_member(
    group_id: Optional[UUID] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[UUID]:
    """
    Dependency לשימוש בראוטרים.
    - אם אין group_id → מחזיר None (זרימה ציבורית רגילה)
    - אם יש group_id אבל אין משתמש מחובר → 401
    - אם יש group_id אבל המשתמש לא חבר → 403
    - אם חבר → מחזיר את ה-group_id
    """
    if group_id is None:
        return None
    if current_user is None:
        raise HTTPException(
            status_code=401, detail="נדרשת התחברות לגישה לקבוצה"
        )
    member = await get_membership(db, group_id, current_user.user_id)
    if not member:
        raise HTTPException(status_code=403, detail="אינך חבר בקבוצה זו")
    return group_id


async def verify_group_membership(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
) -> None:
    """
    בדיקת חברות ישירה (לא Dependency).
    משמשת ב־POST /rides/ שם group_id מגיע מה־body.
    זורקת 403 אם המשתמש אינו חבר בקבוצה.
    """
    member = await get_membership(db, group_id, user_id)
    if not member:
        raise HTTPException(status_code=403, detail="אינך חבר בקבוצה זו")
