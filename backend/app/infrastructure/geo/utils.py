import asyncio
import json
import logging
from typing import List, Tuple, Optional
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString
from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)


def get_coords_from_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Sync geocoding עם Redis cache.

    הסדר:
    1. בדוק Redis cache (async → sync wrapper)
    2. אם לא נמצא — קרא ל-Nominatim
    3. שמור ב-cache לשימוש הבא

    Fail open: אם Redis לא זמין — ממשיך ישירות ל-Nominatim.
    """
    if not address or not address.strip():
        return None, None

    # בדוק cache — sync wrapper על async
    try:
        from app.infrastructure.geo.geocode_cache import get_cached_coords, set_cached_coords

        async def _check_cache():
            return await get_cached_coords(address)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # רצים בתוך async context (FastAPI) — השתמש בThread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, _check_cache())
                    cached = future.result(timeout=1.0)
            else:
                cached = loop.run_until_complete(_check_cache())

            if cached:
                return cached
        except Exception as e:
            logger.debug(f"Cache check skipped: {e}")

    except ImportError:
        pass

    # קרא ל-Nominatim
    try:
        geolocator = Nominatim(user_agent="linkup-backend", timeout=10)
        location = geolocator.geocode(address)
        if not location:
            return None, None

        # שמור ב-cache (fire and forget — לא חוסם)
        try:
            async def _save_cache():
                from app.infrastructure.geo.geocode_cache import set_cached_coords
                await set_cached_coords(address, location.latitude, location.longitude)

            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(_save_cache())
                # אם loop רץ — דלג, לא שווה לחסום
            except Exception:
                pass
        except Exception:
            pass

        return location.latitude, location.longitude
    except Exception as e:
        logger.warning(f"Geocoding failed for '{address}': {e}")
        return None, None


def to_geo_point(lat: float, lon: float, srid: int = 4326):
    """
    Technical utility to convert coordinates to PostGIS-friendly format.
    """
    return from_shape(Point(lon, lat), srid=srid)


def to_geo_line(coords: List[Tuple[float, float]], srid: int = 4326):
    """
    Technical utility to convert a list of points to a PostGIS LineString.
    """
    # המרה ל-Lon/Lat עבור תקן GeoJSON/PostGIS
    fmt_coords = [(p[1], p[0]) for p in coords]
    return from_shape(LineString(fmt_coords), srid=srid)
