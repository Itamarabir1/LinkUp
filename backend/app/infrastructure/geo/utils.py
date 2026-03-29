import asyncio
import logging
from typing import List, Tuple, Optional
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString

logger = logging.getLogger(__name__)


def get_coords_from_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Sync wrapper על Google Geocoding עם Redis cache.
    משמש קוד sync שלא יכול לקרוא async ישירות.
    Fail open — אם נכשל מחזיר (None, None).
    """
    if not address or not address.strip():
        return None, None

    from app.infrastructure.geo.geocode_cache import get_coordinates

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(asyncio.run, get_coordinates(address)).result(timeout=10)
        else:
            result = loop.run_until_complete(get_coordinates(address))

        if result:
            return result
    except Exception as e:
        logger.warning(f"get_coords_from_address failed for '{address}': {e}")

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
