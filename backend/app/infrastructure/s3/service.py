"""
S3 storage service — avatars: presigned upload to staging, worker processes to versioned prefix:
avatars/staging/{user_id}_{uuid}.webp → avatars/{user_id}/v{version}/ (immutable) + three sizes.
Group image: GROUPS/<group_id>/<uuid>.webp — direct upload, single file per group.
"""

import logging
import uuid
from urllib.parse import quote
from uuid import UUID

from app.core.config import settings
from app.core.exceptions.infrastructure import S3DeleteFailed
from app.infrastructure.s3.client import S3_DELETE_OBJECTS_MAX_KEYS, s3_client

logger = logging.getLogger(__name__)

STAGING_PREFIX = "avatars/staging/"
GROUPS_PREFIX = "GROUPS/"


class StorageService:
    def __init__(self):
        self.client = s3_client

    async def generate_avatar_upload_url(
        self,
        user_id: UUID | str,
        filename: str | None = None,
        expiration: int = 300,
    ) -> tuple[str, str]:
        """
        Creates a presigned URL for direct upload to S3 staging. Always WebP.
        Returns: (presigned_url, staging_key). staging_key = avatars/staging/{user_id}_{uuid}.webp
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
        """Deletes all objects under prefix using streamed listing and DeleteObjects batches."""
        buf: list[str] = []
        total_deleted = 0
        batches = 0
        try:
            async for key in self.client.iter_prefix_keys(prefix):
                buf.append(key)
                if len(buf) >= S3_DELETE_OBJECTS_MAX_KEYS:
                    await self.client.delete_object_keys_batch(buf)
                    batches += 1
                    total_deleted += len(buf)
                    buf.clear()
            if buf:
                await self.client.delete_object_keys_batch(buf)
                batches += 1
                total_deleted += len(buf)
            logger.info(
                "S3 prefix delete complete: prefix=%s batches=%s deleted_total=%s",
                prefix,
                batches,
                total_deleted,
            )
        except S3DeleteFailed:
            raise
        except Exception as e:
            logger.error("S3 prefix delete failed prefix=%s: %s", prefix, e, exc_info=True)
            raise S3DeleteFailed() from e

    async def delete_avatar_prefix(self, prefix: str) -> None:
        """Deletes all objects under the given prefix (legacy avatar version cleanup)."""
        p = prefix.strip()
        if not p:
            return
        if not p.endswith("/"):
            p = f"{p}/"
        await self.list_and_delete_prefix(p)
        logger.info("Deleted avatar prefix: %s", p)

    async def delete_user_avatar_folder(self, user_id: UUID | str) -> None:
        """Deletes everything under avatars/{user_id}/ (all versions + legacy layout without v/)."""
        uid_str = str(user_id)
        prefix = f"avatars/{uid_str}/"
        await self.list_and_delete_prefix(prefix)
        logger.info("Deleted avatar folder for user %s", uid_str)

    async def generate_group_image_upload_url(self, group_id: UUID | str, expiration: int = 300) -> tuple[str, str]:
        """
        Creates a presigned URL for direct S3 upload of a group image.
        Key: GROUPS/<group_id>/<uuid>.webp
        Returns: (presigned_url, key).
        """
        gid_str = str(group_id)
        key = f"{GROUPS_PREFIX}{gid_str}/{uuid.uuid4().hex}.webp"
        content_type = "image/webp"
        presigned_url = await self.client.generate_presigned_upload_url(key=key, content_type=content_type, expiration=expiration)
        logger.info("Generated presigned URL for group image: key=%s", key)
        return presigned_url, key

    def generate_read_url(self, key: str, expiration: int = 900) -> str:
        """Read URL: CloudFront if configured, otherwise presigned GET to S3."""
        if settings.CLOUDFRONT_DOMAIN:
            encoded_key = quote(key, safe="/")
            return f"https://{settings.CLOUDFRONT_DOMAIN}/{encoded_key}"
        return self.client.generate_presigned_read_url(key=key, expiration=expiration)

    def build_avatar_url(self, avatar_key: str | None, filename: str) -> str | None:
        """Single source of truth for building a user avatar URL (not groups)."""
        if not avatar_key or not settings.S3_BUCKET_NAME:
            return None
        if avatar_key.startswith("avatars/staging/"):
            key = avatar_key
        else:
            key = f"{avatar_key.rstrip('/')}/{filename}"
        try:
            return self.generate_read_url(key)
        except Exception as e:
            logger.warning("Failed to build avatar URL for key=%s: %s", avatar_key, e, exc_info=True)
            return None

    async def delete_group_image_folder(self, group_id: UUID | str) -> None:
        """Deletes all objects under GROUPS/<group_id>/."""
        gid_str = str(group_id)
        prefix = f"{GROUPS_PREFIX}{gid_str}/"
        await self.list_and_delete_prefix(prefix)
        logger.info("Deleted group image folder for group %s", gid_str)

    async def delete_file(self, file_url: str) -> None:
        """Deletes a file by URL (extracts object key)."""
        try:
            key = file_url.split(".com/")[-1].split("?")[0]
            if key:
                await self.client.delete_object(key)
        except Exception as e:
            logger.error("Failed to delete file %s: %s", file_url, e, exc_info=True)
            raise S3DeleteFailed() from e


storage_service = StorageService()
