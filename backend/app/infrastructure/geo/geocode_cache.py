"""
geocode_cache.py — מקור אמת יחיד לcache של geocoding.

עקרונות:
- כל geocoding בפרויקט עובר דרך כאן
- Fail open: אם Redis לא זמין — geocoding ממשיך לעבוד רגיל
- TTL: 24 שעות — כתובות מנורמלות (מGoogle autocomplete) לא משתנות
- cache key: f"geocode:{address.strip()}" — כתובת מנורמלת
"""

import json
import logging

from app.core.constants import GEOCODE_CACHE_TTL
from app.infrastructure.geo.geocoding import GeocodingService
from app.infrastructure.metrics import geo_cache_hits_total, geo_cache_misses_total
from app.infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)


async def get_cached_coords(address: str) -> tuple[float, float] | None:
    """
    מחזיר קואורדינטות מcache אם קיימות.
    מחזיר None אם לא נמצא או אם Redis לא זמין (fail open).
    """
    if not address or not address.strip():
        return None
    try:
        cache_key = f"geocode:{address.strip()}"
        cached = await redis_client.get(cache_key)
        if cached:
            data = cached if isinstance(cached, dict) else json.loads(cached)
            logger.debug(f"Geocode cache hit: '{address}'")
            geo_cache_hits_total.inc()
            return float(data["lat"]), float(data["lon"])
    except Exception as e:
        logger.warning(f"Geocode cache read failed (fail open): {e}")
    return None


async def set_cached_coords(
    address: str,
    lat: float,
    lon: float,
) -> None:
    """
    שומר קואורדינטות בcache.
    שקט בשגיאה — cache הוא אופטימיזציה, לא תלות.
    """
    if not address or not address.strip():
        return
    try:
        cache_key = f"geocode:{address.strip()}"
        await redis_client.save(
            cache_key,
            {"lat": lat, "lon": lon},
            expire=GEOCODE_CACHE_TTL,
        )
        logger.debug(f"Geocode cached: '{address}' → ({lat}, {lon})")
    except Exception as e:
        logger.warning(f"Geocode cache write failed (fail open): {e}")


async def get_coordinates(address: str) -> tuple[float, float] | None:
    """
    מחזיר קואורדינטות לכתובת.
    בודק Redis cache קודם — אם לא נמצא, קורא ל-Google ושומר.
    """
    if not address or not address.strip():
        return None

    cached = await get_cached_coords(address)
    if cached:
        return cached
    geo_cache_misses_total.inc()

    lat, lon = await GeocodingService.get_coordinates_from_address(address)
    if lat is None or lon is None:
        return None

    await set_cached_coords(address, lat, lon)
    return lat, lon
