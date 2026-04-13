"""
Avatar image processing — resize to three sizes and upload to S3.
Requires: Pillow>=10.0.0

Each upload writes to an immutable versioned prefix: avatars/{user_id}/v{version}/ — no delete-before-upload
(deleting the previous version happens in the worker after DB commit).
"""

import io
import logging
import secrets
import time
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from app.infrastructure.s3.client import S3Client

logger = logging.getLogger(__name__)

SIZES = {
    "original.webp": (800, 800),
    "400x400.webp": (400, 400),
    "150x150.webp": (150, 150),
}
WEBP_QUALITY = 85


def _crop_center_square(img: Image.Image) -> Image.Image:
    """Center-crop to a square (side = min(width, height))."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _resize_and_encode_webp(img: Image.Image, size: tuple[int, int], quality: int = WEBP_QUALITY) -> bytes:
    """Resizes to size, encodes WebP, returns raw bytes."""
    resized = img.resize(size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="WEBP", quality=quality)
    return buf.getvalue()


def new_avatar_version_id() -> str:
    """Near-collision-free version id for S3 paths (nanoseconds + random hex)."""
    return f"{time.time_ns()}_{secrets.token_hex(4)}"


async def process_and_save_avatar(
    staging_key: str,
    user_id: str,
    s3_client: "S3Client",
) -> str:
    """
    1. Download image from staging_key
    2. Resize to three sizes (center square crop), WebP
    3. Upload to avatars/{user_id}/v{version}/ (new immutable prefix)
    4. Delete staging object

    Does not delete older versions — worker does that after a successful DB update.

    Returns avatar_key = "avatars/{user_id}/v{version}/"
    """
    if not staging_key.startswith("avatars/staging/"):
        raise ValueError(f"Invalid staging key: {staging_key}")

    body = await s3_client.get_object_bytes(staging_key)
    img = Image.open(io.BytesIO(body)).convert("RGB")

    squared = _crop_center_square(img)
    uploads = []
    for filename, (w, h) in SIZES.items():
        blob = _resize_and_encode_webp(squared, (w, h))
        uploads.append((filename, blob))

    version = new_avatar_version_id()
    prefix = f"avatars/{user_id}/v{version}/"

    for filename, blob in uploads:
        key = f"{prefix}{filename}"
        await s3_client.upload_fileobj(
            file_data=io.BytesIO(blob),
            key=key,
            content_type="image/webp",
        )
        logger.info("Uploaded avatar variant: %s", key)

    await s3_client.delete_object(staging_key)
    logger.info("Deleted staging: %s", staging_key)

    return prefix
