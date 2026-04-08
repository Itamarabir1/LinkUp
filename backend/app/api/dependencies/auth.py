from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.auth import InvalidAccessTokenError, UserInactiveOrMissingError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.users.crud import crud_user
from app.domain.users.model import User

# HTTPBearer מאפשר הזנת טוקן ישירה ב-Swagger (יותר נוח מ-OAuth2)
bearer_scheme = HTTPBearer()
bearer_scheme_optional = HTTPBearer(auto_error=False)


@dataclass
class WsUser:
    id: UUID

    @property
    def user_id(self) -> UUID:
        return self.id


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
        raise InvalidAccessTokenError()

    logger.debug(f"✅ Token decoded successfully, payload: {payload}")

    user_id = payload.get("sub")
    if not user_id:
        logger.error("❌ Token payload missing 'sub' field")
        raise InvalidAccessTokenError()

    user = await crud_user.get_by_id(db, id=UUID(str(user_id)))

    if not user or not user.is_active:
        logger.warning(f"❌ User {user_id} not found or inactive")
        raise UserInactiveOrMissingError()

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
    token: str | None = Query(None, alias="token"),
) -> WsUser | None:
    """
    אימות WS לפי JWT בלבד (?token=...) — ללא קריאת DB.
    decode_access_token מאמת חתימה, תוקף ו-base64 קנוני.
    משתמש מושבת עדיין יכול להתחבר עד פקיעת הטוקן (trade-off מול עומס על ה-DB pool).
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return WsUser(id=UUID(str(user_id)))


# ה-WebSocket Dependency נשאר כאן כי הוא קשור ל-API
