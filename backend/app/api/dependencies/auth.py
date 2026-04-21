from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.auth import InvalidAccessTokenError, UserInactiveOrMissingError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.infrastructure.redis.client import redis_client
from app.domain.users.crud import crud_user
from app.domain.users.model import User

# HTTPBearer: paste token directly in Swagger (more convenient than OAuth2)
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

    jti = payload.get("jti")
    if jti and await redis_client.is_denied(str(jti)):
        logger.warning("❌ Access token jti is denylisted")
        raise InvalidAccessTokenError()

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
    """Returns User if a valid token is present, else None. For optional-auth endpoints (e.g. search)."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    jti = payload.get("jti")
    if jti and await redis_client.is_denied(str(jti)):
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
    WebSocket auth via JWT only (?token=...) — no DB round-trip.
    decode_access_token verifies signature, expiry, and canonical base64.
    Disabled users may still connect until token expiry (trade-off vs DB pool load).
    Denied tokens (post-logout denylist) are rejected. Redis failures remain fail-open.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    jti = payload.get("jti")
    if jti and await redis_client.is_denied(str(jti)):
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return WsUser(id=UUID(str(user_id)))


# WebSocket dependency lives here because it is tied to the API layer
