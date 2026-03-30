"""
טסטים לפונקציות אבטחה - פענוח טוקנים (JWT).
בודק את המקרים הקריטיים: טוקן תקין, פג תוקף, חתימה שגויה.
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
    """user_id קבוע לטסטים."""
    return "123"


@pytest.fixture
def valid_access_token(test_user_id):
    """טוקן access תקין מוכן לשימוש."""
    return create_access_token(data={"sub": test_user_id})


@pytest.fixture
def valid_refresh_token(test_user_id):
    """טוקן refresh תקין מוכן לשימוש."""
    return create_refresh_token(data={"sub": test_user_id})


@pytest.fixture
def expired_access_token(test_user_id):
    """טוקן access פג תוקף."""
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": test_user_id, "exp": expired_time}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.fixture
def expired_refresh_token(test_user_id):
    """טוקן refresh פג תוקף."""
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)
    payload = {
        "sub": test_user_id,
        "type": "refresh",
        "exp": expired_time,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class TestDecodeAccessToken:
    """טסטים ל-decode_access_token() - פענוח טוקן קצר (Access Token)."""

    def test_valid_token_returns_payload(self, valid_access_token, test_user_id):
        """טוקן תקין - מחזיר payload עם sub ו-exp."""
        payload = decode_access_token(valid_access_token)

        assert payload is not None
        assert payload["sub"] == test_user_id
        assert "exp" in payload

    def test_expired_token_returns_none(self, expired_access_token):
        """טוקן פג תוקף - נדחה ומחזיר None."""
        result = decode_access_token(expired_access_token)
        assert result is None

    def test_invalid_signature_returns_none(self, valid_access_token):
        """טוקן עם חתימה שגויה - נדחה ומחזיר None."""
        # שינוי תו אחד בטוקן כדי לפגום את החתימה
        invalid_token = valid_access_token[:-1] + "X"

        result = decode_access_token(invalid_token)
        assert result is None

    def test_wrong_secret_key_returns_none(self, test_user_id):
        """טוקן עם SECRET_KEY שגוי - נדחה ומחזיר None."""
        payload = {
            "sub": test_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, "wrong_secret_key", algorithm=settings.ALGORITHM)

        result = decode_access_token(token)
        assert result is None


class TestDecodeRefreshToken:
    """טסטים ל-decode_refresh_token() - פענוח טוקן ארוך (Refresh Token)."""

    def test_valid_refresh_token_returns_payload(self, valid_refresh_token, test_user_id):
        """טוקן refresh תקין - מחזיר payload עם type=refresh."""
        payload = decode_refresh_token(valid_refresh_token)

        assert payload is not None
        assert payload["sub"] == test_user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_access_token_as_refresh_returns_none(self, valid_access_token):
        """טוקן access (לא refresh) - נדחה ומחזיר None."""
        result = decode_refresh_token(valid_access_token)
        assert result is None  # כי אין type="refresh"

    def test_refresh_token_expired_returns_none(self, expired_refresh_token):
        """טוקן refresh פג תוקף - נדחה ומחזיר None."""
        result = decode_refresh_token(expired_refresh_token)
        assert result is None

    def test_refresh_token_without_type_returns_none(self, test_user_id):
        """טוקן refresh בלי type=refresh - נדחה ומחזיר None."""
        payload = {
            "sub": test_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            # אין "type": "refresh"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        result = decode_refresh_token(token)
        assert result is None
