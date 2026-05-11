import asyncio
import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

# Import settings object that loads ENV
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


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update(
        {
            "exp": expire,
            "iss": getattr(settings, "JWT_ISSUER", "linkup-api"),
            "jti": str(uuid.uuid4()),
        },
    )
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    """Long-lived refresh token for POST /auth/refresh to obtain a new access token. Expiry from config: REFRESH_TOKEN_EXPIRE_DAYS."""
    to_encode = data.copy()
    expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    to_encode.update(
        {
            "exp": datetime.now(UTC) + timedelta(days=expire_days),
            "type": "refresh",
            "iss": getattr(settings, "JWT_ISSUER", "linkup-api"),
        },
    )
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decodes access JWT and returns payload, or None if invalid."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Reject non-canonical base64url signature segment (prevents accepting
        # tampered tokens that still decode to the same bytes).
        parts = token.split(".")
        if len(parts) != 3:
            return None
        signature_segment = parts[2]
        padded_signature = signature_segment + "=" * (-len(signature_segment) % 4)
        signature_bytes = base64.urlsafe_b64decode(padded_signature.encode("ascii"))
        canonical_signature = base64.urlsafe_b64encode(signature_bytes).decode("ascii").rstrip("=")
        if signature_segment != canonical_signature:
            return None

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e!s}")
        return None
    except Exception as e:
        logger.error(f"Unexpected token decode error: {e!s}")
        return None


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of refresh token for secure DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_refresh_token(token: str) -> dict | None:
    """Decodes refresh JWT, requires type=refresh, returns payload or None."""
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
