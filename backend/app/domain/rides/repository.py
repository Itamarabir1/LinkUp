# app/domain/rides/repository.py — ride cache (Redis)

import logging
from typing import Optional, Dict, Any
from app.domain.rides.schema import RidePreviewResponse, RidePreviewCreate
from app.infrastructure.redis.keys import get_ride_preview_key, RIDE_PREVIEW_TTL
from app.infrastructure.redis.client import redis_client
from app.core.exceptions.infrastructure import InfrastructureError

logger = logging.getLogger(__name__)


class RideCacheRepository:
    """
    אחריות: ניהול ה-State הזמני של נסיעות ברדיס (Caching Layer).
    שכבה זו מפרידה בין הלוגיקה העסקית לבין מימוש ה-Storage.
    """

    async def save_preview(
        self, preview: RidePreviewResponse, preview_in: RidePreviewCreate
    ) -> None:
        """שומר תצוגה מקדימה של נסיעה ב-Redis: 3 המסלולים (כולל זמן נסיעה וק\"מ) לתוקף 24 שעות."""
        try:
            # הכנת הנתונים (Serialization)
            cache_data = preview.model_dump()
            cache_data.update(
                {
                    "driver_id": str(preview_in.driver_id),
                    "departure_time": preview_in.departure_time.isoformat(),
                    "available_seats": preview_in.available_seats,
                    "price": preview_in.price,
                    "origin_lat": preview.origin_coords[0],
                    "origin_lon": preview.origin_coords[1],
                    "dest_lat": preview.destination_coords[0],
                    "dest_lon": preview.destination_coords[1],
                }
            )

            key = get_ride_preview_key(preview.session_id)
            # תוקף 24 שעות – חייב להיות בשניות (86400) כדי שהמשתמש יוכל לבחור מסלול בתוך 24 שעות
            ttl_seconds = max(
                RIDE_PREVIEW_TTL, 86400
            )  # מינימום 24h גם אם הקבוע שונה בטעות
            await redis_client.save(
                key=key,
                data=cache_data,
                expire=ttl_seconds,
            )
            logger.info(
                "Cached ride preview: key=%s, session_id=%s, routes=%s, ttl_seconds=%s (24h)",
                key,
                preview.session_id,
                len(preview.routes),
                ttl_seconds,
            )

        except Exception as e:
            logger.error(f"Failed to save ride preview to cache: {e}")
            raise InfrastructureError(
                f"Cache write error for session: {preview.session_id}", detail=str(e)
            )

    async def get_preview(self, session_id: str) -> Optional[Dict[str, Any]]:
        """שליפת נתונים מהקאש (תוקף 24 שעות)."""
        key = get_ride_preview_key(session_id)
        data = await redis_client.get(key)
        if data is None:
            logger.warning(
                "get_preview: key=%s not found or expired (check Redis with: GET %s)",
                key,
                key,
            )
        else:
            logger.debug(
                "get_preview: key=%s found, routes=%s", key, len(data.get("routes", []))
            )
        return data

    async def delete_preview(self, session_id: str) -> None:
        """ניקוי ידני של הקאש"""
        key = get_ride_preview_key(session_id)
        # אם אין מתודת delete ב-client, נוסיף אותה או נשתמש ב-client.delete
        try:
            await redis_client.client.delete(key)
        except Exception as e:
            logger.warning(f"Could not delete cache key {key}: {e}")


# מופע סינגלטון לשימוש ב-Service Layer
ride_cache_repo = RideCacheRepository()
