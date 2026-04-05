"""
לקוח S3 (aioboto3) – העלאה, הורדה, העתקה ומחיקה.
משמש את StorageService והעיבוד ברקע (presigned upload → worker מעבד ל-avatars/{user_id}/).

הערה: כשהפרונט מעלה ישירות ל-S3 עם presigned URL, ה-bucket חייב להגדיר CORS שמאפשר
PUT מ-origin של הפרונט (למשל http://localhost:5173 בפיתוח). ראה docs/S3_CORS.md.
"""

import logging
from urllib.parse import quote

from aioboto3 import Session

from app.core.config import settings
from app.core.exceptions.infrastructure import (
    ExternalServiceError,
    S3DeleteFailed,
    S3UploadFailed,
)

logger = logging.getLogger(__name__)


class S3Client:
    def __init__(self):
        self._session = Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def _public_url(self, key: str) -> str:
        # חשוב: key יכול לכלול תווים בעברית. URL חייב להיות percent-encoded כדי שהדפדפן יטען אותו אמין.
        encoded_key = quote(key, safe="/")
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{encoded_key}"

    async def upload_fileobj(self, file_data, key: str, content_type: str) -> str:
        """העלאה בסיסית – מחזיר URL ציבורי."""
        try:
            async with self._session.client("s3") as s3:
                await s3.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    key,
                    ExtraArgs={"ContentType": content_type or "application/octet-stream"},
                )
            return self._public_url(key)
        except Exception as e:
            logger.error("S3 upload failed: %s", e, exc_info=True)
            raise S3UploadFailed() from e

    async def copy_object(self, source_key: str, dest_key: str) -> str:
        """העתקה בתוך אותו bucket (למשל staging → final). שומר content-type של המקור."""
        try:
            copy_source = {"Bucket": self.bucket_name, "Key": source_key}
            async with self._session.client("s3") as s3:
                await s3.copy_object(
                    CopySource=copy_source,
                    Bucket=self.bucket_name,
                    Key=dest_key,
                )
            return self._public_url(dest_key)
        except Exception as e:
            logger.error("S3 copy failed: %s", e, exc_info=True)
            raise S3UploadFailed() from e

    async def delete_object(self, key: str) -> None:
        """מחיקה לפי key."""
        try:
            async with self._session.client("s3") as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info("S3 delete_object OK: bucket=%s key=%s", self.bucket_name, key)
        except Exception as e:
            logger.error(
                "S3 delete failed bucket=%s key=%s: %s",
                self.bucket_name,
                key,
                e,
                exc_info=True,
            )
            raise S3DeleteFailed() from e

    async def get_object_bytes(self, key: str) -> bytes:
        """מוריד אובייקט כ-bytes (לעיבוד תמונה ב-worker)."""
        try:
            async with self._session.client("s3") as s3:
                resp = await s3.get_object(Bucket=self.bucket_name, Key=key)
                body = await resp["Body"].read()
                return body
        except Exception as e:
            logger.error("S3 get_object failed key=%s: %s", key, e, exc_info=True)
            raise ExternalServiceError() from e

    async def list_objects_by_prefix(self, prefix: str) -> list[str]:
        """מחזיר רשימת keys עם prefix נתון."""
        keys = []
        try:
            async with self._session.client("s3") as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    for obj in page.get("Contents") or []:
                        k = obj.get("Key")
                        if k:
                            keys.append(k)
        except Exception as e:
            logger.error("S3 list_objects failed prefix=%s: %s", prefix, e, exc_info=True)
            raise ExternalServiceError() from e
        return keys

    async def generate_presigned_upload_url(self, key: str, content_type: str, expiration: int = 300) -> str:
        """
        יוצר presigned URL להעלאה ישירה ל-S3.
        expiration: זמן תוקף בשניות (ברירת מחדל: 5 דקות).
        מחזיר URL עם חתימה דיגיטלית שמאפשר העלאה ישירה מהלקוח.
        """
        try:
            async with self._session.client("s3") as s3:
                # aiobotocore: generate_presigned_url הוא async (חייב await)
                presigned_url = await s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=expiration,
                )
                logger.info(
                    "Generated presigned URL for key=%s (expires in %ds)",
                    key,
                    expiration,
                )
                return presigned_url
        except Exception as e:
            logger.error("Failed to generate presigned URL for key=%s: %s", key, e, exc_info=True)
            raise S3UploadFailed() from e


s3_client = S3Client()
