import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ייבוא האובייקט שטוען את ה-ENV
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_sync(password: str) -> str:
    return pwd_context.hash(password)


def _verify_sync(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _hash_sync, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _verify_sync, plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": expire,
            "iss": getattr(settings, "JWT_ISSUER", "linkup-api"),
        }
    )
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    """טוקן ארוך תוקף (Refresh) – לשימוש ב-POST /auth/refresh לקבלת Access Token חדש. תוקף נקבע ב-config: REFRESH_TOKEN_EXPIRE_DAYS."""
    to_encode = data.copy()
    expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    to_encode.update(
        {
            "exp": datetime.now(timezone.utc) + timedelta(days=expire_days),
            "type": "refresh",
            "iss": getattr(settings, "JWT_ISSUER", "linkup-api"),
        }
    )
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """מפענח Access Token (JWT) ומחזיר payload, או None אם לא תקין."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected token decode error: {str(e)}")
        return None


def decode_refresh_token(token: str) -> dict | None:
    """מפענח Refresh Token (JWT), בודק type=refresh, מחזיר payload או None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None
