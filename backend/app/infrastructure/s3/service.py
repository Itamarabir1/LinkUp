"""
שירות אחסון S3 – אווטאר: presigned upload ל-staging, worker מעבד ל-avatars/{user_id}/.
מבנה: avatars/staging/{user_id}_{uuid}.webp → worker → avatars/{user_id}/original.webp, 400x400.webp, 150x150.webp.
תמונת קבוצה: GROUPS/<group_id>/<uuid>.webp — העלאה ישירה, קובץ יחיד per group.
"""

import logging
import uuid
from typing import Optional, Union
from uuid import UUID

from app.core.exceptions.infrastructure import S3DeleteFailed
from app.infrastructure.s3.client import s3_client

logger = logging.getLogger(__name__)

STAGING_PREFIX = "avatars/staging/"
GROUPS_PREFIX = "GROUPS/"


class StorageService:
    def __init__(self):
        self.client = s3_client

    async def generate_avatar_upload_url(
        self, user_id: UUID | int | str, filename: str | None = None, expiration: int = 300,
    ) -> tuple[str, str]:
        """
        יוצר presigned URL להעלאה ישירה ל-S3 staging. תמיד webp.
        מחזיר: (presigned_url, staging_key). staging_key = avatars/staging/{user_id}_{uuid}.webp
        """
        uid_str = str(user_id)
        staging_key = f"{STAGING_PREFIX}{uid_str}_{uuid.uuid4().hex}.webp"
        content_type = "image/webp"

        presigned_url = await self.client.generate_presigned_upload_url(
            key=staging_key,
            content_type=content_type,
            expiration=expiration,
        )

        logger.info("Generated presigned URL for avatar upload: key=%s", staging_key)
        return presigned_url, staging_key

    async def list_and_delete_prefix(self, prefix: str) -> None:
        """מוחק את כל האובייקטים עם prefix נתון."""
        keys = await self.client.list_objects_by_prefix(prefix)
        for key in keys:
            try:
                await self.client.delete_object(key)
                logger.info("S3 deleted: key=%s", key)
            except Exception as e:
                logger.error("S3 delete failed for key=%s: %s", key, e, exc_info=True)
                raise S3DeleteFailed() from e

    async def delete_user_avatar_folder(self, user_id: UUID | str) -> None:
        """מוחק את כל תוכן התיקייה avatars/{user_id}/."""
        uid_str = str(user_id)
        prefix = f"avatars/{uid_str}/"
        await self.list_and_delete_prefix(prefix)
        logger.info("Deleted avatar folder for user %s", uid_str)

    async def generate_group_image_upload_url(self, group_id: UUID | str, expiration: int = 300) -> tuple[str, str]:
        """
        יוצר presigned URL להעלאה ישירה ל-S3 לתמונת קבוצה.
        מפתח: GROUPS/<group_id>/<uuid>.webp
        מחזיר: (presigned_url, key).
        """
        gid_str = str(group_id)
        key = f"{GROUPS_PREFIX}{gid_str}/{uuid.uuid4().hex}.webp"
        content_type = "image/webp"
        presigned_url = await self.client.generate_presigned_upload_url(key=key, content_type=content_type, expiration=expiration)
        logger.info("Generated presigned URL for group image: key=%s", key)
        return presigned_url, key

    async def delete_group_image_folder(self, group_id: UUID | str) -> None:
        """מוחק את כל תוכן התיקייה GROUPS/<group_id>/."""
        gid_str = str(group_id)
        prefix = f"{GROUPS_PREFIX}{gid_str}/"
        await self.list_and_delete_prefix(prefix)
        logger.info("Deleted group image folder for group %s", gid_str)

    async def delete_file(self, file_url: str) -> None:
        """מחיקת קובץ לפי URL (חילוץ key)."""
        try:
            key = file_url.split(".com/")[-1].split("?")[0]
            if key:
                await self.client.delete_object(key)
        except Exception as e:
            logger.error("Failed to delete file %s: %s", file_url, e, exc_info=True)
            raise S3DeleteFailed() from e


storage_service = StorageService()
