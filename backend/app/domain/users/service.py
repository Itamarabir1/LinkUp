import logging

from sqlalchemy.ext.asyncio import AsyncSession

# 1. Core, Security & Exceptions
from app.core.exceptions.auth import PermissionDeniedError
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
        # Bind imported singletons to self
        self.s3 = storage_service
        self.crud = crud_user

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User:
        user = await self.crud.get_by_id(db, id=user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)
        return user

    async def get_avatar_upload_url(self, user_id, filename: str | None = None, expiration: int = 300) -> tuple[str, str]:
        """
        Return presigned URL for direct upload to S3 staging.
        Returns: (presigned_url, staging_key)
        """
        presigned_url, staging_key = await self.s3.generate_avatar_upload_url(user_id=user_id, filename=filename, expiration=expiration)
        logger.info("Generated presigned URL for user %s: staging_key=%s", user_id, staging_key)
        return presigned_url, staging_key

    async def confirm_avatar_upload(self, db: AsyncSession, user: User, staging_key: str) -> None:
        """
        Confirm upload after client PUT to S3. Updates DB optimistically and enqueues background
        resize + copy to avatars/{user_id}/.
        Security: staging_key must belong to the authenticated user_id.
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

        user.avatar_staging_key = staging_key
        user.avatar_status = "processing"
        db.add(user)
        await db.flush()

        await publish_to_outbox(
            db,
            event_name="user.avatar_upload",
            payload={"user_id": str(user.user_id), "staging_key": staging_key},
        )
        await db.commit()
        logger.info(
            "Avatar upload confirmed for user %s (staging_key=%s, status=processing)",
            user.user_id,
            staging_key,
        )

    async def remove_avatar(self, db: AsyncSession, user_id) -> None:
        """
        Clear avatar in DB and publish user.avatar_remove to the outbox (same transaction).
        S3 deletion under avatars/{user_id}/ runs asynchronously in task-worker (avatar queue).
        No-op if already empty.
        """
        user = await self.get_user_by_id(db, user_id=user_id)

        if not user.avatar_key or not str(user.avatar_key).strip():
            await db.commit()
            logger.info("Avatar already empty for user %s", user_id)
            return

        user.avatar_key = None
        user.avatar_staging_key = None
        user.avatar_status = "none"
        db.add(user)
        await db.flush()

        await publish_to_outbox(db, "user.avatar_remove", {"user_id": str(user.user_id)})
        await db.commit()
        logger.info("Avatar removed for user %s (outbox user.avatar_remove)", user_id)

    async def update_user_location(self, db: AsyncSession, user_id: int, lat: float, lon: float) -> bool:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or (lat == 0 and lon == 0):
            raise InvalidLocationError(lat=lat, lon=lon)

        success = await self.crud.update_location(db, user_id=user_id, lat=lat, lon=lon)
        if not success:
            raise UserNotFoundError(user_id=user_id)
        await db.commit()
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

        # Apply field updates in the same transaction (single commit)
        protected_fields = ["user_id", "created_at", "hashed_password"]
        for field, value in update_dict.items():
            if hasattr(db_user, field) and field not in protected_fields:
                setattr(db_user, field, value)
        db.add(db_user)

        # Flush without commit so outbox sees updated row state
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
        await db.commit()
        return True


# Module-level singleton
user_service = UserService()
