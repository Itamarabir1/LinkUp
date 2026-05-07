"""
S3 client (aioboto3) — upload, download, copy, delete.
Prefix cleanup uses streamed ListObjects + DeleteObjects batches (≤1000 keys per call).
Used by StorageService and background workers (presigned upload → finalize under avatars/{user_id}/).

Note: for browser PUT to presigned URLs, the bucket must allow CORS from the frontend origin
(e.g. http://localhost:5173 in dev). See docs/S3_CORS.md.
"""

import logging
from collections.abc import AsyncIterator, Sequence
from urllib.parse import quote

import boto3
from aioboto3 import Session
from botocore.config import Config

from app.core.config import settings
from app.core.exceptions.infrastructure import (
    ExternalServiceError,
    S3DeleteFailed,
    S3UploadFailed,
)

logger = logging.getLogger(__name__)

# AWS DeleteObjects accepts at most this many keys per request.
S3_DELETE_OBJECTS_MAX_KEYS = 1000


class S3Client:
    def __init__(self):
        self._session = Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def _public_url(self, key: str) -> str:
        # Keys may include non-ASCII; percent-encode path for reliable browser loads.
        encoded_key = quote(key, safe="/")
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{encoded_key}"

    async def upload_fileobj(self, file_data, key: str, content_type: str) -> str:
        """Basic upload — returns public URL."""
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
        """Copy within same bucket (e.g. staging → final). Preserves source content-type."""
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
        """Delete object by key."""
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
        """Download object as bytes (image worker processing)."""
        try:
            async with self._session.client("s3") as s3:
                resp = await s3.get_object(Bucket=self.bucket_name, Key=key)
                body = await resp["Body"].read()
                return body
        except Exception as e:
            logger.error("S3 get_object failed key=%s: %s", key, e, exc_info=True)
            raise ExternalServiceError() from e

    async def iter_prefix_keys(self, prefix: str) -> AsyncIterator[str]:
        """Stream object keys under prefix (listing only; callers batch-delete)."""
        try:
            async with self._session.client("s3") as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    for obj in page.get("Contents") or []:
                        k = obj.get("Key")
                        if k:
                            yield k
        except Exception as e:
            logger.error("S3 list_objects iter failed prefix=%s: %s", prefix, e, exc_info=True)
            raise ExternalServiceError() from e

    async def delete_object_keys_batch(self, keys: Sequence[str]) -> None:
        """
        Delete up to many keys using DeleteObjects (chunked to S3_DELETE_OBJECTS_MAX_KEYS per call).
        """
        filtered = [k for k in keys if k]
        if not filtered:
            return
        for i in range(0, len(filtered), S3_DELETE_OBJECTS_MAX_KEYS):
            chunk = filtered[i : i + S3_DELETE_OBJECTS_MAX_KEYS]
            try:
                async with self._session.client("s3") as s3:
                    resp = await s3.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
                    )
            except Exception as e:
                logger.error(
                    "S3 delete_objects failed bucket=%s count=%s: %s",
                    self.bucket_name,
                    len(chunk),
                    e,
                    exc_info=True,
                )
                raise S3DeleteFailed() from e
            errors = resp.get("Errors") or []
            if errors:
                err0 = errors[0]
                logger.error(
                    "S3 delete_objects partial failure bucket=%s key=%s code=%s message=%s (%d errors)",
                    self.bucket_name,
                    err0.get("Key"),
                    err0.get("Code"),
                    err0.get("Message"),
                    len(errors),
                )
                raise S3DeleteFailed()

    async def list_objects_by_prefix(self, prefix: str) -> list[str]:
        """List object keys under a prefix."""
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
        Presigned PUT URL for direct client upload.
        expiration: seconds until expiry (default 5 minutes).
        """
        try:
            async with self._session.client("s3") as s3:
                # aiobotocore: generate_presigned_url is async (must await)
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

    def generate_presigned_read_url(self, key: str, expiration: int = 900) -> str:
        """
        Presigned GET URL (sync — safe for Pydantic computed fields and similar).
        """
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                config=Config(signature_version="s3v4"),
            )
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        except Exception as e:
            logger.error("Failed to generate presigned read URL for key=%s: %s", key, e, exc_info=True)
            raise ExternalServiceError() from e


s3_client = S3Client()
