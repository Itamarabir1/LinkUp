"""
Security helpers tests — JWT decode paths (valid, expired, bad signature).
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.core.security import (
    decode_access_token,
    decode_refresh_token,
    create_access_token,
    create_refresh_token,
)
from app.core.config import settings


# --- Fixtures ---


@pytest.fixture
def test_user_id():
    """Fixed user id for token fixtures."""
    return "123"


@pytest.fixture
def valid_access_token(test_user_id):
    """Valid access JWT."""
    return create_access_token(data={"sub": test_user_id})


@pytest.fixture
def valid_refresh_token(test_user_id):
    """Valid refresh JWT."""
    return create_refresh_token(data={"sub": test_user_id})


@pytest.fixture
def expired_access_token(test_user_id):
    """Expired access JWT."""
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": test_user_id, "exp": expired_time}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def expired_refresh_token(test_user_id):
    """Expired refresh JWT."""
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)
    payload = {
        "sub": test_user_id,
        "type": "refresh",
        "exp": expired_time,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class TestDecodeAccessToken:
    """Tests for decode_access_token (short-lived access JWT)."""

    def test_valid_token_returns_payload(self, valid_access_token, test_user_id):
        """Valid token yields payload with sub and exp."""
        payload = decode_access_token(valid_access_token)

        assert payload is not None
        assert payload["sub"] == test_user_id
        assert "exp" in payload

    def test_expired_token_returns_none(self, expired_access_token):
        """Expired token rejected → None."""
        result = decode_access_token(expired_access_token)
        assert result is None

    def test_invalid_signature_returns_none(self, valid_access_token):
        """Tampered signature rejected → None."""
        # Flip one character to break the signature
        invalid_token = valid_access_token[:-1] + "X"

        result = decode_access_token(invalid_token)
        assert result is None

    def test_wrong_secret_key_returns_none(self, test_user_id):
        """Wrong signing secret rejected → None."""
        payload = {
            "sub": test_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, "wrong_secret_key", algorithm=settings.ALGORITHM)

        result = decode_access_token(token)
        assert result is None


class TestDecodeRefreshToken:
    """Tests for decode_refresh_token (long-lived refresh JWT)."""

    def test_valid_refresh_token_returns_payload(self, valid_refresh_token, test_user_id):
        """Valid refresh token includes type=refresh."""
        payload = decode_refresh_token(valid_refresh_token)

        assert payload is not None
        assert payload["sub"] == test_user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_access_token_as_refresh_returns_none(self, valid_access_token):
        """Access token without refresh type rejected → None."""
        result = decode_refresh_token(valid_access_token)
        assert result is None  # missing type="refresh"

    def test_refresh_token_expired_returns_none(self, expired_refresh_token):
        """Expired refresh rejected → None."""
        result = decode_refresh_token(expired_refresh_token)
        assert result is None

    def test_refresh_token_without_type_returns_none(self, test_user_id):
        """Refresh-shaped JWT without type=refresh rejected → None."""
        payload = {
            "sub": test_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            # no "type": "refresh"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        result = decode_refresh_token(token)
        assert result is None
