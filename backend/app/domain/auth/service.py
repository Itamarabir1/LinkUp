import logging
import secrets
from datetime import UTC, datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# Exceptions - ניתוב מדויק לפי החלוקה החדשה
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
    decode_refresh_token,
    get_password_hash,
    verify_password,
)

# ייבוא של המודל (כדי שה-IDE יזהה את המתודות של new_user)
# שים לב: וולידציה בדרך כלל לא נזרקת מהסרוויס אלא מהסכימה, אבל הן כאן ליתר ביטחון
from app.core.utils.validators import normalize_email_for_auth
from app.domain.auth.google_auth import verify_google_id_token
from app.domain.auth.schema import ChangePasswordRequest, UserRegister
from app.domain.auth.verification_service import verification_service
from app.domain.events.enum import DispatchTarget

# Domain & Infrastructure
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.domain.users.schema import UserCreate

# הסר את כל הכפילויות ושמור רק על זה:
from app.infrastructure.outbox.model import OutboxEvent
from app.infrastructure.outbox.repository import OutboxRepository
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.redis.client import redis_client

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

        # 1. יצירת המשתמש (בלי commit בתוך ה-CRUD!)
        new_user = await self.crud_user.create(db, obj_in=user_in, hashed_password=hashed_password)

        # 2. יצירת קוד אימות
        code = await verification_service.create_verification_event(user_id=str(new_user.user_id), event_name="email_verification")

        # 3. אירועים לאאוטבוקס. המפתח (routing_key) וה-exchange לא מוגדרים כאן –
        #    הם נגזרים מ-event_name כשהאוטבוקס מעבד את האירוע: OutboxService קורא
        #    get_routing_metadata(event_name) (domain.events.routing) ומקבל { exchange, routing_key }.
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

        # בפיתוח (DEBUG): מאפשרים כניסה מיד אחרי הרשמה בלי אימות אימייל
        if getattr(settings, "DEBUG", False):
            new_user.is_verified = True
            db.add(new_user)

        # 4. ה-Commit הסופי שסוגר את כל הפעולות ביחד
        try:
            await db.commit()
            await db.refresh(new_user)
            return new_user
        except Exception as e:
            await db.rollback()
            logger.error("register_new_user failed: %s", e)
            # כאן נכנס השימוש ב-LinkupError שביקשת לרשת ממנו
            # raise LinkupError(
            #     message=f"Registration failed: {str(e)}",
            #     status_code=500
            # )
            raise

    async def verify_user_email(self, db: AsyncSession, email: str, code: str):
        # נרמול האימייל לפני החיפוש (כמו ב-register)
        normalized_email = normalize_email_for_auth(email)
        logger.info(f"🔍 Verifying email - Original: '{email}', Normalized: '{normalized_email}'")
        user = await self.crud_user.get_by_email(db, email=normalized_email)
        if not user:
            logger.error(f"❌ User not found for email: '{normalized_email}' (original: '{email}')")
            raise UserNotFoundError()
        logger.info(f"✅ User found: user_id={user.user_id}, email={user.email}")

        # קריאה אחת פשוטה שבודקת הכל מול רדיס
        await verification_service.verify_otp(str(user.user_id), "email_verification", code)

        await self.crud_user.update(db, db_obj=user, obj_in={"is_verified": True})
        return {"message": "Account verified successfully", "status": "success"}

    async def request_password_reset(self, db: AsyncSession, email: str):
        """
        שולח קוד איפוס למייל. כמו רישום – הקוד ב-Redis, השליחה במייל דרך Outbox.
        אותו תור (notifications_queue), אותו exchange (user), מפתח שונה: auth.password_reset_code.
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
        """בדיקות מקדימות לפני תחילת טרנזקציה"""
        if await self.crud_user.get_by_phone(db, phone=user_in.phone_number):
            raise PhoneAlreadyRegisteredError(phone=user_in.phone_number)

        if user_in.email and await self.crud_user.get_by_email(db, email=user_in.email):
            raise EmailAlreadyRegisteredError(email=user_in.email)

    async def initiate_email_verification(self, db: AsyncSession, email: str):
        normalized_email = normalize_email_for_auth(email)
        user = await self.crud_user.get_by_email(db, email=normalized_email)
        if not user:
            raise UserNotFoundError(identifier=email)

        if user.is_verified:
            return {"detail": "Account already verified"}

        # שמירת הקוד ב-Redis באותו מפתח ש-verify_user_email בודק (user_id + event_name)
        verification_code = await verification_service.create_verification_event(str(user.user_id), "email_verification")

        # אותו פורמט כמו ב-outbox: ה-consumer מצפה ל-user_id + data עם code/email
        await self.rabbit.publish(
            message={
                "user_id": str(user.user_id),
                "data": {
                    "email": user.email,
                    "code": verification_code,
                    "user_name": getattr(user, "full_name", None) or "",
                },
            },
            routing_key="auth.email_verification",
            exchange_name="user",
        )
        return {"detail": "Verification code sent to email"}

    async def authenticate_and_create_token(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """
        אימות: שליפת משתמש לפי מייל, בדיקת סיסמה (verify_password), בדיקת is_verified.
        מחזיר טוקן + פרטי משתמש להצגת 'ברוך הבא, {full_name}'.
        """
        # 1. שליפת משתמש מה-DB (שימוש ב-await כי ה-CRUD שלך אסינכרוני)
        user = await self.crud_user.get_by_email(db, email=email)

        # 2. בדיקת קיום משתמש וסיסמה (Security: תשובה אחידה למניעת Enumeration)
        if not user or not await verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        # 3. בדיקת סטטוס אימות מייל - שימוש בעמודה החדשה שלך
        if not user.is_verified:
            # כאן אנחנו זורקים את השגיאה שביקשת, כולל המייל ל-Payload
            logger.warning(f"Login blocked: User {email} is not verified yet.")
            raise UserNotVerifiedError(email=user.email)

        # 4. יצירת Access Token (קצר) + Refresh Token (ארוך)
        access_token = create_access_token(data={"sub": str(user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

        # 5. שמירת Refresh Token ב-DB (לאפשר ביטול ב-logout)
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=refresh_token)

        logger.info("User %s logged in successfully.", email)

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
        אימות/רישום דרך Google OAuth.

        זרימה:
        1. מאמת את ה-ID token עם Google
        2. בודק אם משתמש עם email זה קיים
        3. אם לא קיים → יוצר משתמש חדש (auto-signup):
           - email, full_name, avatar_url מ-Google
           - hashed_password = ערך דמה (לא בשימוש)
           - phone_number = placeholder (ניתן לעדכן מאוחר יותר)
           - is_verified = True (Google מאמת את ה-email)
        4. מחזיר access_token + refresh_token + user (כמו authenticate_and_create_token)
        """
        # 1. אימות ה-ID token עם Google
        try:
            google_user = verify_google_id_token(id_token)
        except GoogleAuthFailed:
            raise

        email = google_user.get("email")
        if not email:
            logger.error("Google ID token missing email claim")
            raise InvalidCredentialsError()

        # נרמול email (lowercase)
        email = normalize_email_for_auth(email)

        # 2. בדיקה אם משתמש קיים
        user = await self.crud_user.get_by_email(db, email=email)

        if user:
            logger.info(
                "[Google] user from DB: user_id=%s type=%s",
                user.user_id,
                type(user.user_id).__name__,
            )

        if not user:
            # 3. Auto-signup: יצירת משתמש חדש
            # מספר טלפון זמני – 10 ספרות כמו מספר רגיל (05X-XXXXXXX), ב-E.164: +9725 + 8 ספרות
            google_sub = "".join(c for c in (google_user.get("sub") or "00000000") if c.isdigit())[:8]
            google_sub = google_sub.ljust(8, "0")  # בדיוק 8 ספרות
            placeholder_phone = f"+9725{google_sub}"  # +972 5X XXXXXXX = 12 ספרות, תקני E.164

            # יצירת סיסמה דמה (לא בשימוש, אבל נדרש ב-DB)
            # נשתמש ב-random string ארוך שלא ניתן לנחש
            dummy_password = secrets.token_urlsafe(32)
            hashed_password = await get_password_hash(dummy_password)

            # יצירת UserCreate object (password דמה - לא בשימוש)
            user_create = UserCreate(
                full_name=google_user.get("name", "Google User"),
                email=email,
                phone_number=placeholder_phone,
                password=dummy_password,  # דמה - לא בשימוש
                fcm_token=None,
            )

            # יצירת המשתמש
            user = await self.crud_user.create(db, obj_in=user_create, hashed_password=hashed_password)

            # עדכון שדות נוספים מ-Google (avatar_key נשאר None — אווטאר מ-S3 רק בהעלאה מפורשת)
            user.is_verified = True  # Google כבר מאמת את ה-email

            await db.commit()
            await db.refresh(user)

            logger.info(f"Auto-signup via Google: {email}")

            # אירוע user.registered (אם צריך)
            await self.outbox_repo.save_event(
                db,
                OutboxEvent(
                    event_name="user.registered",
                    payload={"user_id": str(user.user_id), "auth_provider": "google"},
                    targets=[DispatchTarget.RABBITMQ.value],
                ),
            )
            await db.commit()

        else:
            # משתמש קיים – קישור Google ID אם עדיין לא מקושר
            google_sub = google_user.get("sub")
            if google_sub and not getattr(user, "google_id", None):
                logger.info(
                    "[Google] linking google_id for user_id=%s type=%s",
                    user.user_id,
                    type(user.user_id).__name__,
                )
                user.google_id = google_sub
                user.is_verified = True
                await db.commit()
                await db.refresh(user)

        # 4. יצירת tokens (גם למשתמש חדש וגם למשתמש קיים)
        access_token = create_access_token(data={"sub": str(user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

        # 5+6. שמירת Refresh Token + עדכון last_login ב-commit אחד
        user.refresh_token = refresh_token
        user.last_login = datetime.now(UTC)
        db.add(user)
        await db.commit()

        logger.info(f"User {email} authenticated via Google successfully.")

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
        מפענח Refresh Token, בודק שהוא תואם ל-DB, מחזיר Access Token חדש + Refresh Token חדש (רוטציה).
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
        if user.refresh_token != refresh_token:
            raise InvalidRefreshTokenError()

        new_access_token = create_access_token(data={"sub": str(user.user_id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=new_refresh_token)

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

    async def logout(self, db: AsyncSession, user: User) -> None:
        """מבטל את ה-Refresh Token של המשתמש (logout – התנתקות מכל המכשירים)."""
        await self.crud_user.update_refresh_token(db, user=user, refresh_token=None)

    async def change_password(self, db: AsyncSession, user_id: UUID, data: ChangePasswordRequest) -> dict:
        """
        שינוי סיסמה למשתמש מחובר: אימות סיסמה ישנה, עדכון לסיסמה חדשה.
        ולידציית התאמה וחוזק כבר בסכמה (כמו ברישום).
        """
        user = await self.crud_user.get_by_id(db, id=user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)
        if not await verify_password(data.old_password, user.hashed_password):
            raise InvalidPasswordError()
        hashed = await get_password_hash(data.new_password)
        await self.crud_user.update_password(db, user=user, hashed_password=hashed)
        return {"message": "הסיסמה עודכנה בהצלחה", "status": "success"}

    async def reset_password_with_code(self, db: AsyncSession, email: str, code: str, new_password: str):
        """מאמת קוד איפוס (מ-Redis), מעדכן סיסמה ומחזיר הצלחה. הקוד נמחק אחרי שימוש."""
        user = await self.crud_user.get_by_email(db, email=email)
        if not user:
            raise InvalidResetCodeError(email=email)

        await verification_service.verify_otp(str(user.user_id), "password_reset", code)
        hashed = await get_password_hash(new_password)
        await self.crud_user.update_password(db, user=user, hashed_password=hashed)
        return {"message": "Password reset successfully.", "status": "success"}
