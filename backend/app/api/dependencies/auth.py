from typing import Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.users.crud import crud_user
from app.domain.users.model import User

# HTTPBearer מאפשר הזנת טוקן ישירה ב-Swagger (יותר נוח מ-OAuth2)
bearer_scheme = HTTPBearer()
bearer_scheme_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    import logging

    logger = logging.getLogger(__name__)

    token = credentials.credentials
    logger.debug(f"🔍 Attempting to decode token: {token[:20]}...")

    payload = decode_access_token(token)
    if not payload:
        logger.warning("❌ Token decode failed - invalid token or expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    logger.debug(f"✅ Token decoded successfully, payload: {payload}")

    user_id = payload.get("sub")
    if not user_id:
        logger.error("❌ Token payload missing 'sub' field")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = await crud_user.get_by_id(db, id=UUID(str(user_id)))

    if not user or not user.is_active:
        logger.warning(f"❌ User {user_id} not found or inactive")
        raise HTTPException(status_code=401, detail="User not found or inactive")

    logger.debug(f"✅ User authenticated: {user.email}")
    return user


async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme_optional),
):
    """מחזיר User אם יש טוקן תקף, אחרת None. לשימוש ב-endpoints ללא auth (חיפוש)."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await crud_user.get_by_id(db, id=UUID(str(user_id)))
    if not user or not user.is_active:
        return None
    return user


async def get_current_user_ws(
    token: Optional[str] = Query(None, alias="token"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    אימות למשתמש ב-WebSocket לפי טוקן ב-query string (?token=...).
    מחזיר User אם הטוקן תקף, אחרת None. מתאים ל-/ws ול-/bookings/ws/{id}/location.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await crud_user.get_by_id(db, id=UUID(str(user_id)))
    if not user or not user.is_active:
        return None
    return user


# ה-WebSocket Dependency נשאר כאן כי הוא קשור ל-API
