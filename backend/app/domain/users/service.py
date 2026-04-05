import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

# 1. Core, Security & Exceptions
from app.core.exceptions.auth import PermissionDeniedError
from app.core.exceptions.infrastructure import S3DeleteFailed
from app.core.exceptions.user import (
    EmailAlreadyRegisteredError,
    UserNotFoundError,
)
from app.core.exceptions.validation import InvalidLocationError
from app.domain.events.enum import DispatchTarget
from app.domain.events.outbox import publish_to_outbox
from app.domain.notifications.constants import NotificationEvent
from app.domain.users.crud import crud_user

# 2. Domain Schemas & Models
from app.domain.users.model import User
from app.domain.users.schema import UserUpdate

# 3. Infrastructure & Services
from app.infrastructure.s3.service import storage_service

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        # הצמדת המופעים שהזרקנו מהייבוא ל-self
        self.s3 = storage_service
        self.crud = crud_user

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User:
        user = await self.crud.get_by_id(db, id=user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)
        return user

    async def get_avatar_upload_url(self, user_id, filename: str | None = None, expiration: int = 300) -> tuple[str, str]:
        """
        מחזיר presigned URL להעלאה ישירה ל-S3 staging.
        מחזיר: (presigned_url, staging_key)
        """
        presigned_url, staging_key = await self.s3.generate_avatar_upload_url(user_id=user_id, filename=filename, expiration=expiration)
        logger.info("Generated presigned URL for user %s: staging_key=%s", user_id, staging_key)
        return presigned_url, staging_key

    async def confirm_avatar_upload(self, db: AsyncSession, user: User, staging_key: str) -> None:
        """
        מאשר העלאה לאחר שהלקוח העלה ישירות ל-S3. מעדכן avatar_key ב-DB מיידית (אופטימי)
        ודוחף אירוע לתור לעיבוד ברקע (resize + העלאה ל-avatars/{user_id}/).
        ולידציית אבטחה: staging_key חייב להכיל את user_id של המשתמש המחובר.
        """
        expected_prefix = f"avatars/staging/{user.user_id}_"
        if not staging_key.startswith(expected_prefix):
            logger.warning(
                "Invalid staging_key for user %s: %s (must start with %s)",
                user.user_id,
                staging_key,
                expected_prefix,
            )
            raise PermissionDeniedError(message="מפתח העלאה לא תואם למשתמש המחובר")

        # עדכון מיידי ב-DB (אופטימי — הפרונט יכול להציג תמונה מ-staging עד שה-worker יסיים)
        await self.crud.update(db, db_obj=user, obj_in={"avatar_key": staging_key})

        await publish_to_outbox(
            db,
            event_name="user.avatar_upload",
            payload={"user_id": str(user.user_id), "staging_key": staging_key},
        )
        await db.commit()
        logger.info(
            "Avatar upload confirmed for user %s (staging_key=%s)",
            user.user_id,
            staging_key,
        )

    async def remove_avatar(self, db: AsyncSession, user_id) -> None:
        """
        מסיר תמונת פרופיל: מוחק את תיקיית avatars/{user_id}/ מ-S3 ומאפס avatar_key ב-DB.
        אם אין תמונה – no-op.
        """
        user = await self.get_user_by_id(db, user_id=user_id)

        if not user.avatar_key or not str(user.avatar_key).strip():
            await db.commit()
            logger.info("Avatar already empty for user %s", user_id)
            return

        try:
            await self.s3.delete_user_avatar_folder(user.user_id)
        except S3DeleteFailed as e:
            logger.warning("Could not delete avatar folder for user %s: %s", user_id, e.message)

        await self.crud.update(db, db_obj=user, obj_in={"avatar_key": None})
        await db.commit()
        logger.info("Avatar removed for user %s", user_id)

    async def update_user_location(self, db: AsyncSession, user_id: int, lat: float, lon: float) -> bool:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or (lat == 0 and lon == 0):
            raise InvalidLocationError(lat=lat, lon=lon)

        success = self.crud.update_location(db, user_id=user_id, lat=lat, lon=lon)
        if not success:
            raise UserNotFoundError(user_id=user_id)
        return True

    async def update_user_info(self, db: AsyncSession, user_id: int, update_data: UserUpdate) -> User:
        db_user = await self.get_user_by_id(db, user_id=user_id)
        update_dict = update_data.model_dump(exclude_unset=True)

        email_changed = False
        if "email" in update_dict and update_dict["email"] != db_user.email:
            if await self.crud.get_by_email(db, email=update_dict["email"]):
                raise EmailAlreadyRegisteredError(email=update_dict["email"])

            update_dict["is_verified"] = False
            email_changed = True

        # עדכון השדות בפועל באותה טרנזקציה (commit אחד בלבד)
        protected_fields = ["user_id", "created_at", "hashed_password"]
        for field, value in update_dict.items():
            if hasattr(db_user, field) and field not in protected_fields:
                setattr(db_user, field, value)
        db.add(db_user)

        # שמירה ב-DB בלי commit כדי ש-Outbox יקבל את הנתונים המעודכנים
        await db.flush()

        if email_changed:
            await publish_to_outbox(
                db,
                NotificationEvent.EMAIL_VERIFICATION.value,
                {
                    "user_id": str(db_user.user_id),
                    "data": {
                        "email": db_user.email,
                        "user_name": (db_user.full_name or ""),
                    },
                },
                [DispatchTarget.RABBITMQ.value],
            )

        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def update_fcm_token(self, db: AsyncSession, user_id: int, fcm_token: str | None) -> bool:
        db_user = await self.get_user_by_id(db, user_id=user_id)
        await self.crud.update_fcm_token(db, user=db_user, token=fcm_token)
        return True


# יצירת המופע היחיד (Singleton)
user_service = UserService()
