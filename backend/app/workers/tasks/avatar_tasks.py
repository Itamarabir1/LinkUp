"""
עיבוד אירועי העלאת ומחיקת אווטאר – תור נפרד (avatar_upload_queue).
ה-worker מקבל הודעות מ-exchange 'tasks' עם routing_key user.avatar_upload או user.avatar_remove.
"""

import logging
from typing import Any
from uuid import UUID

from app.core.exceptions.infrastructure import WorkerTaskFailed
from app.db.session import SessionLocal
from app.domain.users.crud import crud_user
from app.infrastructure.s3.client import s3_client
from app.infrastructure.s3.image_processor import process_and_save_avatar
from app.infrastructure.s3.service import storage_service

logger = logging.getLogger(__name__)

AVATAR_UPLOAD_EVENT = "user.avatar_upload"
AVATAR_REMOVE_EVENT = "user.avatar_remove"


async def handle_avatar_upload_event(data: dict[str, Any], routing_key: str) -> None:
    """
    מעבד אירועי אווטאר: העלאה או מחיקה.
    - user.avatar_upload: עיבוד תמונה (resize ל-3 גדלים) + עדכון avatar_key במסד.
    - user.avatar_remove: מחיקה מ-S3 (DB כבר עודכן ב-API).
    """
    if routing_key == AVATAR_UPLOAD_EVENT:
        await _handle_avatar_upload(data)
    elif routing_key == AVATAR_REMOVE_EVENT:
        await _handle_avatar_remove(data)
    else:
        logger.warning("Ignoring non-avatar event: %s", routing_key)


async def _handle_avatar_upload(data: dict[str, Any]) -> None:
    """
    מעבד אירוע העלאת אווטאר: הורדה מ-staging, resize ל-3 גדלים, העלאה ל-avatars/{user_id}/, עדכון avatar_key.
    payload: { "user_id": str/uuid, "staging_key": str }
    """
    user_id = data.get("user_id")
    staging_key = data.get("staging_key")
    if user_id is None or not staging_key:
        logger.error(
            "Invalid avatar_upload payload: user_id=%s, staging_key=%s",
            user_id,
            staging_key,
        )
        raise WorkerTaskFailed(message="חסרים user_id או staging_key")

    user_id = UUID(str(user_id))
    uid_str = str(user_id)

    async with SessionLocal() as db:
        try:
            user = await crud_user.get_by_id(db, id=user_id)
            if not user:
                logger.error("User not found for avatar finalize: user_id=%s", user_id)
                raise WorkerTaskFailed(message=f"משתמש לא נמצא: {user_id}")

            avatar_key = await process_and_save_avatar(
                staging_key=staging_key,
                user_id=uid_str,
                s3_client=s3_client,
                storage_service=storage_service,
            )
            user.avatar_key = avatar_key
            user.avatar_staging_key = None
            user.avatar_status = "ready"
            db.add(user)

            await db.commit()
            await db.refresh(user)
            logger.info("Avatar processed for user %s: avatar_key=%s", user_id, avatar_key)

        except Exception as e:
            await db.rollback()
            try:
                user = await crud_user.get_by_id(db, id=user_id)
                if user:
                    user.avatar_status = "failed"
                    db.add(user)
                    await db.commit()
            except Exception:
                await db.rollback()
            logger.exception("Avatar upload processing failed: user_id=%s", user_id)
            raise WorkerTaskFailed() from e


async def _handle_avatar_remove(data: dict[str, Any]) -> None:
    """
    מעבד אירוע מחיקת אווטאר: מוחק מ-S3 את avatars/{user_id}/.
    payload: { "user_id": str/uuid }
    הערה: avatar_key כבר אופס ב-DB ב-API.
    """
    user_id = data.get("user_id")
    if user_id is None:
        logger.error("Invalid avatar_remove payload: user_id=%s", user_id)
        raise WorkerTaskFailed(message="חסר user_id ב-payload")

    user_id = UUID(str(user_id))

    async with SessionLocal() as db:
        try:
            user = await crud_user.get_by_id(db, id=user_id)
            if not user:
                logger.error("User not found for avatar removal: user_id=%s", user_id)
                raise WorkerTaskFailed(message=f"משתמש לא נמצא: {user_id}")

            await storage_service.delete_user_avatar_folder(user_id)

            logger.info("Avatar removed from S3 for user %s", user_id)

        except Exception as e:
            logger.exception("Avatar removal processing failed: user_id=%s", user_id)
            raise WorkerTaskFailed() from e
