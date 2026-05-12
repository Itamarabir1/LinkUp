import logging
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# Exceptions — imports aligned with the split exception modules
from app.core.exceptions.auth import (
    GoogleAuthFailed,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidRefreshTokenError,
    InvalidResetCodeError,
    UserNotVerifiedError,
)
from app.core.exceptions.user import (
    EmailAlreadyRegisteredError,
    PhoneAlreadyRegisteredError,
    UserNotFoundError,
)

# Core & Security
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.infrastructure.redis.client import redis_client

# Model import so the IDE resolves methods on new_user
# Note: validation is usually raised from schemas, not the service — kept here for safety
from app.core.utils.validators import normalize_email_for_auth
from app.domain.auth.google_auth import verify_google_id_token
from app.domain.auth.schema import ChangePasswordRequest, UserRegister
from app.domain.auth.verification_service import verification_service
from app.domain.events.enum import DispatchTarget

# Domain & Infrastructure
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.domain.users.schema import UserCreate

# Single import block for outbox / messaging
from app.infrastructure.outbox.model import OutboxEvent
from app.infrastructure.outbox.repository import OutboxRepository
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.metrics import auth_failures_total, auth_logins_total, auth_registrations_total

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.redis = redis_client
        self.rabbit = rabbit_client
        self.crud_user = crud_user
        self.outbox_repo = OutboxRepository()

    # app/domain/auth/service.py

    # app/services/auth_service.py
    async def register_new_user(self, db: AsyncSession, user_in: UserRegister) -> User:
        await self._validate_unique_user(db, user_in)
        hashed_password = await get_password_hash(user_in.password)

        # 1. Create user (no commit inside CRUD)
        new_user = await self.crud_user.create(db, obj_in=user_in, hashed_password=hashed_password)

        # 2. Create verification code
        code = await verification_service.create_verification_event(user_id=str(new_user.user_id), event_name="email_verification")

        # 3. Outbox events — routing_key / exchange are not set here;
        #    they are derived from event_name when the outbox runs: OutboxService calls
        #    get_routing_metadata(event_name) (domain.events.routing) → { exchange, routing_key }.
        await self.outbox_repo.save_event(
            db,
            OutboxEvent(
                event_name="auth.email_verification",
                payload={
                    "user_id": str(new_user.user_id),
                    "data": {"code": code, "email": new_user.email},
                },
                targets=[DispatchTarget.RABBITMQ.value],
            ),
        )
        await self.outbox_repo.save_event(
            db,
            OutboxEvent(
                event_name="user.registered",
                payload={"user_id": str(new_user.user_id)},
                targets=[DispatchTarget.RABBITMQ.value],
            ),
        )

        # Dev (DEBUG): allow login immediately after signup without email verification
        if getattr(settings, "DEBUG", False):
            new_user.is_verified = True
            db.add(new_user)

        # 4. Final commit for the whole transaction
        try:
            await db.commit()
            await db.refresh(new_user)
            auth_registrations_total.labels(provider="email").inc()
            return new_user
        except Exception as e:
            await db.rollback()
            logger.error("register_new_user failed: %s", e)
            # Could wrap in LinkUpError here if desired
            # raise LinkUpError(
            #     message=f"Registration failed: {str(e)}",
            #     status_code=500
            # )
            raise

    async def verify_user_email(self, db: AsyncSession, email: str, code: str):
        # Normalize email before lookup (same as register)
        normalized_email = normalize_email_for_auth(email)
        logger.info(f"[VERIFY] Verifying email - Original: '{email}', Normalized: '{normalized_email}'")
        user = await self.crud_user.get_by_email(db, email=normalized_email)
        if not user:
            logger.error(f"[ERROR] User not found for email: '{normalized_email}' (original: '{email}')")
            raise UserNotFoundError()
        logger.info(f"[OK] User found: user_id={user.user_id}, email={user.email}")

        # Single Redis-backed OTP verification
        await verification_service.verify_otp(str(user.user_id), "email_verification", code)

        await self.crud_user.mark_as_verified(db, user=user)
        await db.commit()
        return {"message": "Account verified successfully", "status": "success"}

    async def request_password_reset(self, db: AsyncSession, email: str):
        """
        Send reset code by email. Like registration — code in Redis, delivery via Outbox.
        Same queue (notifications_queue), same exchange (user), different key: auth.password_reset_code.
        """
        user = await self.crud_user.get_by_email(db, email=email)
        if not user:
            return {"message": "If the email exists, a code was sent."}

        code = await verification_service.create_verification_event(str(user.user_id), "password_reset")
        await self.outbox_repo.save_event(
            db,
            OutboxEvent(
                event_name="auth.password_reset_code",
                payload={
                    "user_id": str(user.user_id),
                    "data": {
                        "code": code,
                        "user_name": user.full_name,
                        "email": user.email,
                    },
                },
                targets=[DispatchTarget.RABBITMQ.value],
            ),
        )
        await db.commit()
        return {"message": "If the email exists, a code was sent."}

    async def _validate_unique_user(self, db: AsyncSession, user_in: UserRegister):
        """Pre-checks before starting a transaction."""
        if user_in.phone_number and await self.crud_user.get_by_phone(db, phone=user_in.phone_number):
            raise PhoneAlreadyRegisteredError(phone=user_in.phone_number)

        if user_in.email and await self.crud_user.get_by_email(db, email=user_in.email):
            raise EmailAlreadyRegisteredError(email=user_in.email)

    async def initiate_email_verification(self, db: AsyncSession, email: str):
        normalized_email = normalize_email_for_auth(email)
        user = await self.crud_user.get_by_email(db, email=normalized_email)
        if not user:
            raise UserNotFoundError(identifier=email)

        if user.is_verified:
            return {"message": "Account already verified", "status": "success"}

        # Store code in Redis under the same key verify_user_email uses (user_id + event_name)
        verification_code = await verification_service.create_verification_event(str(user.user_id), "email_verification")

        await self.outbox_repo.save_event(
            db,
            OutboxEvent(
                event_name="auth.email_verification",
                payload={
                    "user_id": str(user.user_id),
                    "data": {"code": verification_code, "email": user.email},
                },
                targets=[DispatchTarget.RABBITMQ.value],
            ),
        )
        await db.commit()
        return {"message": "Verification code sent to email", "status": "success"}

    async def authenticate_and_create_token(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """
        Auth: load user by email, verify_password, check is_verified.
        Returns token + user payload for welcome UI.
        """
        # 1. Load user from DB (async CRUD)
        user = await self.crud_user.get_by_email(db, email=email)

        # 2. User + password check (uniform response to prevent enumeration)
        if not user or not await verify_password(password, user.hashed_password):
            auth_failures_total.labels(reason="invalid_credentials").inc()
            raise InvalidCredentialsError()

        # 3. Email verification status
        if not user.is_verified:
            # Raise with email in payload for the client
            logger.warning(f"Login blocked: User {email} is not verified yet.")
            auth_failures_total.labels(reason="not_verified").inc()
            raise UserNotVerifiedError(email=user.email)

        # 4. Issue access (short) + refresh (long) tokens
        access_token = create_access_token(data={"sub": str(user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

        # 5. Persist refresh token (enables logout / revoke)
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=refresh_token)
        await db.commit()

        logger.info("User %s logged in successfully.", email)
        auth_logins_total.labels(provider="email").inc()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "is_admin": bool(user.is_admin),
            },
        }

    async def authenticate_with_google(
        self,
        db: AsyncSession,
        id_token: str,
    ) -> dict[str, Any]:
        """
        Sign-in / sign-up via Google OAuth.

        Flow:
        1. Verify ID token with Google
        2. Look up user by email
        3. If missing → auto-signup:
           - email, full_name from Google
           - hashed_password = dummy (unused)
           - phone_number = placeholder (updatable later)
           - is_verified = True (Google verified email)
        4. Return access_token + refresh_token + user (same as password login)
        """
        # 1. Verify Google ID token
        try:
            google_user = verify_google_id_token(id_token)
        except GoogleAuthFailed:
            raise

        email = google_user.get("email")
        if not email:
            logger.error("Google ID token missing email claim")
            raise InvalidCredentialsError()

        # Normalize email (lowercase)
        email = normalize_email_for_auth(email)

        # 2. Existing user?
        user = await self.crud_user.get_by_email(db, email=email)

        if user:
            logger.info(
                "[Google] user from DB: user_id=%s type=%s",
                user.user_id,
                type(user.user_id).__name__,
            )

        if not user:
            # Auto-signup: Google-only account — no phone, no usable password
            dummy_password = secrets.token_urlsafe(32)
            hashed_password = await get_password_hash(dummy_password)

            user_create = UserCreate(
                full_name=google_user.get("name", "Google User"),
                email=email,
                phone_number=None,
                password=dummy_password,
                fcm_token=None,
            )

            user = await self.crud_user.create(db, obj_in=user_create, hashed_password=hashed_password)

            google_sub = google_user.get("sub")
            if google_sub:
                await self.crud_user.link_google_account(db, user=user, google_sub=google_sub)
            else:
                await self.crud_user.mark_as_verified(db, user=user)

            await self.outbox_repo.save_event(
                db,
                OutboxEvent(
                    event_name="user.registered",
                    payload={"user_id": str(user.user_id), "auth_provider": "google"},
                    targets=[DispatchTarget.RABBITMQ.value],
                ),
            )

            # Single atomic commit: user + google link + outbox event
            await db.commit()

            logger.info("Auto-signup via Google: %s", email)
            auth_registrations_total.labels(provider="google").inc()

        else:
            # Existing user — link google_id if missing
            google_sub = google_user.get("sub")
            if google_sub and not getattr(user, "google_id", None):
                logger.info(
                    "[Google] linking google_id for user_id=%s type=%s",
                    user.user_id,
                    type(user.user_id).__name__,
                )
                await self.crud_user.link_google_account(db, user=user, google_sub=google_sub)
                await db.commit()

        # 4. Issue tokens (new or existing user)
        access_token = create_access_token(data={"sub": str(user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

        # 5+6. Save refresh token (hashed via CRUD) + last_login in one commit
        await self.crud_user.update_last_login(db, user=user)
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=refresh_token)
        await db.commit()

        logger.info(f"User {email} authenticated via Google successfully.")
        auth_logins_total.labels(provider="google").inc()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "is_admin": bool(user.is_admin),
            },
        }

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> dict[str, Any]:
        """
        Decode refresh token, verify it matches DB, return new access + refresh (rotation).
        """
        payload = decode_refresh_token(refresh_token)
        if not payload:
            raise InvalidRefreshTokenError()

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidRefreshTokenError()

        user = await self.crud_user.get_by_id(db, id=UUID(str(user_id)))
        if not user or not user.is_active:
            raise InvalidRefreshTokenError()
        if not self.crud_user.verify_refresh_token(user, refresh_token):
            raise InvalidRefreshTokenError()

        new_access_token = create_access_token(data={"sub": str(user.user_id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=new_refresh_token)
        await db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "is_admin": bool(user.is_admin),
            },
        }

    async def logout(self, db: AsyncSession, user: User, access_token: str | None = None) -> None:
        """Clear refresh token; optionally denylist current access token jti until exp."""
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=None)
        await db.commit()
        if not access_token:
            return
        payload = decode_access_token(access_token)
        if not payload:
            return
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or exp is None:
            return
        now = datetime.now(UTC).timestamp()
        exp_ts = float(exp.timestamp()) if hasattr(exp, "timestamp") else float(exp)
        ttl = max(0, int(exp_ts - now))
        if ttl > 0:
            await redis_client.add_to_denylist(str(jti), ttl)

    async def _invalidate_sessions(self, db: AsyncSession, user) -> None:
        """Clear refresh token so no existing session can renew."""
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=None)

    async def change_password(self, db: AsyncSession, user_id: UUID, data: ChangePasswordRequest) -> dict:
        """
        Change password for logged-in user: verify old password, set new hash.
        Match/strength validation lives on the schema (same as registration).
        """
        user = await self.crud_user.get_by_id(db, id=user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)
        if not await verify_password(data.old_password, user.hashed_password):
            raise InvalidPasswordError()
        hashed = await get_password_hash(data.new_password)
        await self.crud_user.update_password(db, user=user, hashed_password=hashed)
        await self._invalidate_sessions(db, user)
        await db.commit()
        return {"message": "הסיסמה עודכנה בהצלחה", "status": "success"}

    async def reset_password_with_code(self, db: AsyncSession, email: str, code: str, new_password: str):
        """Verify reset code from Redis, update password, invalidate code after use."""
        user = await self.crud_user.get_by_email(db, email=email)
        if not user:
            raise InvalidResetCodeError(email=email)

        await verification_service.verify_otp(str(user.user_id), "password_reset", code)
        hashed = await get_password_hash(new_password)
        await self.crud_user.update_password(db, user=user, hashed_password=hashed)
        await self._invalidate_sessions(db, user)
        await db.commit()
        return {"message": "Password reset successfully.", "status": "success"}
