"""
Integration tests for auth endpoints — register & login.

דרישות:
    DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME

הרצה:
    cd backend
    DATABASE_URL=postgresql+asyncpg://... pytest tests/test_auth.py -v
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.core.exceptions.auth import InvalidCredentialsError
from app.core.exceptions.user import EmailAlreadyRegisteredError, UserNotFoundError
from app.domain.auth.schema import UserRegister
from app.api.dependencies.services import get_auth_service

import app.db.models  # noqa: F401 — רישום כל המודלים ל-SQLAlchemy


# ============================================================
# Fixtures
# ============================================================


@pytest_asyncio.fixture
async def registered_user(db_session: AsyncSession):
    """
    יוצר משתמש רשום אחד — משותף לטסטים שצריכים משתמש קיים.
    Redis מוחלף ב-mock כדי שהטסט לא תלוי בחיבור Redis.
    """
    user_in = UserRegister(
        full_name="Test User",
        email="test_auth@example.com",
        phone_number="+972528765432",
        password="Test@1234!",
        confirm_password="Test@1234!",
    )
    with patch(
        "app.domain.auth.verification_service.verification_service.create_verification_event",
        new=AsyncMock(return_value="123456"),
    ):
        auth_svc = get_auth_service()
        return await auth_svc.register_new_user(db=db_session, user_in=user_in)


# ============================================================
# Register tests
# ============================================================


@pytest.mark.asyncio
async def test_register_success(db_session: AsyncSession):
    """Successful registration returns user_id and email."""
    user_in = UserRegister(
        full_name="New User",
        email="new_user@example.com",
        phone_number="+972527654321",
        password="Test@1234!",
        confirm_password="Test@1234!",
    )
    with patch(
        "app.domain.auth.verification_service.verification_service.create_verification_event",
        new=AsyncMock(return_value="123456"),
    ):
        auth_svc = get_auth_service()
        user = await auth_svc.register_new_user(db=db_session, user_in=user_in)

    assert user.user_id is not None
    assert user.email == "new_user@example.com"
    # ב-DEBUG=True המשתמש מאומת אוטומטית — בודקים רק שיש user_id
    assert user.user_id is not None


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(
    db_session: AsyncSession,
    registered_user,
):
    """Duplicate email raises EmailAlreadyRegisteredError."""
    duplicate = UserRegister(
        full_name="Another User",
        email="test_auth@example.com",
        phone_number="+972529999999",
        password="Test@1234!",
        confirm_password="Test@1234!",
    )
    with pytest.raises(EmailAlreadyRegisteredError):
        auth_svc = get_auth_service()
        await auth_svc.register_new_user(db=db_session, user_in=duplicate)


@pytest.mark.asyncio
async def test_register_password_mismatch_raises(db_session: AsyncSession):
    """Mismatched passwords fail pydantic validation."""
    with pytest.raises(Exception):
        UserRegister(
            full_name="User",
            email="mismatch@example.com",
            phone_number="+972521111111",
            password="Test@1234!",
            confirm_password="Wrong@5678!",
        )


# ============================================================
# Login tests
# ============================================================


@pytest.mark.asyncio
async def test_login_wrong_password_raises(
    db_session: AsyncSession,
    registered_user,
):
    """
    סיסמה שגויה — InvalidCredentialsError.
    אותה שגיאה גם כשאימייל לא קיים — מניעת username enumeration (OWASP).
    """
    with pytest.raises(InvalidCredentialsError):
        auth_svc = get_auth_service()
        await auth_svc.authenticate_and_create_token(
            db=db_session,
            email="test_auth@example.com",
            password="WrongPassword!",
        )


@pytest.mark.asyncio
async def test_login_nonexistent_email_raises(db_session: AsyncSession):
    """
    אימייל שלא קיים — אותה שגיאה כמו סיסמה שגויה.
    לא חושפים אם האימייל קיים או לא (OWASP).
    """
    with pytest.raises(InvalidCredentialsError):
        auth_svc = get_auth_service()
        await auth_svc.authenticate_and_create_token(
            db=db_session,
            email="ghost@example.com",
            password="Test@1234!",
        )


# ============================================================
# Resend verification tests
# ============================================================


@pytest.mark.asyncio
async def test_resend_verification_user_not_found(db_session: AsyncSession):
    auth_svc = get_auth_service()
    with pytest.raises(UserNotFoundError):
        await auth_svc.initiate_email_verification(db=db_session, email="missing@example.com")


@pytest.mark.asyncio
async def test_resend_verification_already_verified(db_session: AsyncSession, registered_user):
    auth_svc = get_auth_service()
    registered_user.is_verified = True
    db_session.add(registered_user)
    await db_session.flush()

    result = await auth_svc.initiate_email_verification(db=db_session, email=registered_user.email)
    assert result == {"message": "Account already verified", "status": "success"}


@pytest.mark.asyncio
async def test_resend_verification_success(db_session: AsyncSession, registered_user):
    auth_svc = get_auth_service()
    registered_user.is_verified = False
    db_session.add(registered_user)
    await db_session.flush()

    save_event_mock = AsyncMock()
    with patch(
        "app.domain.auth.verification_service.verification_service.create_verification_event",
        new=AsyncMock(return_value="654321"),
    ):
        with patch.object(auth_svc.outbox_repo, "save_event", save_event_mock):
            result = await auth_svc.initiate_email_verification(db=db_session, email=registered_user.email)

    assert result == {"message": "Verification code sent to email", "status": "success"}
    save_event_mock.assert_awaited_once()
    outbox_event = save_event_mock.await_args.args[1]
    assert outbox_event.event_name == "auth.email_verification"
    assert outbox_event.payload["user_id"] == str(registered_user.user_id)
    assert outbox_event.payload["data"]["email"] == registered_user.email
    assert outbox_event.payload["data"]["code"] == "654321"
