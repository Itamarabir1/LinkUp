import time
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# --- Google Directions API (מסלולים) ---
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
# --- Google Distance Matrix API (זמן ומרחק ל־OD) ---
GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
MAX_ROUTES = 3  # 2-3 מסלולים הכי טובים
TIMEOUT_DIRECTIONS = 15.0
TIMEOUT_DISTANCE_MATRIX = 10.0


def _decode_polyline(encoded: str) -> List[List[float]]:
    """
    מפענח Google encoded polyline לרשימת [lat, lon].
    אלגוריתם סטנדרטי של Google (1e-5 degrees).
    """
    if not encoded:
        return []
    coords: List[List[float]] = []
    i = 0
    lat, lon = 0, 0
    n = len(encoded)
    while i < n:
        for _ in (0, 1):  # lat then lng
            shift, result = 0, 0
            while True:
                if i >= n:
                    break
                byte = ord(encoded[i]) - 63
                i += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if _ == 0:
                lat += delta
            else:
                lon += delta
        coords.append([lat / 1e5, lon / 1e5])
    return coords


class GeoClient:
    """אחריות: התממשקות טכנית (Infrastructure) מול API חיצוני ב-Async"""

    OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

    def __init__(self):
        # נשאר לשמירת תאימות לאחור בבדיקות/קוד ותיק.
        # אין שימוש ב-Nominatim; geocode מתבצע דרך Google (GeocodingService) או דרך patch בבדיקות.
        class _GeoLocator:
            def geocode(self, _: str):
                return None

        self.geolocator = _GeoLocator()

    async def fetch_coordinates(
        self, address: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        הופך כתובת לקואורדינטות (Geocoding) — עם Redis cache.

        מקור אמת: Google Geocoding (GeocodingService) + cache.
        """
        if not address or not address.strip():
            return None, None

        from app.infrastructure.geo.geocode_cache import (
            get_cached_coords,
            set_cached_coords,
        )

        cached = await get_cached_coords(address)
        if cached:
            return cached

        # אם הוזרק geolocator בבדיקות/מונקי-פאצ׳ינג, השתמש בו.
        try:
            loc = self.geolocator.geocode(address)
            if loc and getattr(loc, "latitude", None) is not None and getattr(
                loc, "longitude", None
            ) is not None:
                await set_cached_coords(address, float(loc.latitude), float(loc.longitude))
                return float(loc.latitude), float(loc.longitude)
        except Exception as e:
            logger.error("Legacy geolocator.geocode failed for '%s': %s", address, e)

        from app.infrastructure.geo.geocoding import GeocodingService

        lat, lon = await GeocodingService.get_coordinates_from_address(address)
        if lat is None or lon is None:
            return None, None
        await set_cached_coords(address, lat, lon)
        return lat, lon

    async def fetch_distance_matrix(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> Optional[Tuple[int, int]]:
        """
        קריאה ל-Google Distance Matrix API לזמן נסיעה ומרחק (מטרים) בין מוצא ליעד.
        מחזיר (duration_sec, distance_m) או None אם נכשל.
        """
        origin = f"{start[0]},{start[1]}"
        destination = f"{end[0]},{end[1]}"
        params = {
            "origins": origin,
            "destinations": destination,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "he",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT_DISTANCE_MATRIX) as client:
            try:
                response = await client.get(GOOGLE_DISTANCE_MATRIX_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"Distance Matrix API error: {response.status_code}")
                    return None
                data: Dict[str, Any] = response.json()
                if data.get("status") != "OK":
                    logger.warning(f"Distance Matrix status: {data.get('status')}")
                    return None
                rows = data.get("rows", [])
                if not rows or not rows[0].get("elements"):
                    return None
                el = rows[0]["elements"][0]
                if el.get("status") != "OK":
                    return None
                duration_sec = el.get("duration", {}).get("value", 0)
                distance_m = el.get("distance", {}).get("value", 0)
                return (int(duration_sec), int(distance_m))
            except Exception as e:
                logger.warning(f"Distance Matrix error: {e}")
                return None

    async def fetch_raw_routes(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        departure_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        שליפת 2-3 מסלולים מ-Google Directions API.
        זמן ומרחק לכל מסלול מגיעים מ-Distance Matrix API (fallback ל-Directions אם נכשל).
        מחזיר רשימת dict עם: summary, duration (שניות), distance (מטרים), coords [[lat,lon],...].
        """
        return await self.fetch_routes_google_directions(start, end, departure_time)

    async def fetch_routes_google_directions(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        departure_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        שליפת עד 3 מסלולים מ-Google Directions API (alternatives=true).
        מחזיר רשימה בפורמט תואם ל-processor: summary, duration (שניות), distance (מטרים), coords.
        """
        origin = f"{start[0]},{start[1]}"
        destination = f"{end[0]},{end[1]}"
        params = {
            "origin": origin,
            "destination": destination,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "alternatives": "true",
            "language": "he",
        }
        if departure_time:
            ts = int(departure_time.timestamp())
            now_ts = int(time.time())
            # Google דורש departure_time בעתיד (לפחות ~דקה מהעכשיו)
            params["departure_time"] = max(ts, now_ts + 60)
        else:
            params["departure_time"] = "now"
        async with httpx.AsyncClient(timeout=TIMEOUT_DIRECTIONS) as client:
            try:
                response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
                if response.status_code != 200:
                    logger.error(f"Google Directions API error: {response.status_code}")
                    return []
                data = response.json()
                if data.get("status") != "OK":
                    logger.warning(f"Google Directions status: {data.get('status')}")
                    return []
                # גוגל מחזירה רשימת מסלולים (alternatives=true) – לוקחים עד MAX_ROUTES, בלי לחתוך אם יש פחות
                raw_list = data.get("routes")
                if not isinstance(raw_list, list):
                    raw_list = [raw_list] if raw_list else []
                routes_raw = raw_list[:MAX_ROUTES]
                out: List[Dict] = []
                for i, r in enumerate(routes_raw):
                    legs = r.get("legs", [])
                    duration_sec = sum(
                        leg.get("duration", {}).get("value", 0) for leg in legs
                    )
                    distance_m = sum(
                        leg.get("distance", {}).get("value", 0) for leg in legs
                    )
                    poly = r.get("overview_polyline", {}).get("points", "")
                    coords = _decode_polyline(poly) if poly else []
                    summary = r.get("summary") or f"מסלול {i + 1}"
                    out.append(
                        {
                            "summary": summary,
                            "duration": duration_sec,
                            "distance": distance_m,
                            "coords": coords,
                        }
                    )
                # זמן ומרחק Distance Matrix API (זמן נסיעה וק"מ לכל מסלול)
                dm_result = await self.fetch_distance_matrix(start, end)
                if dm_result:
                    duration_dm, distance_dm = dm_result
                    for route in out:
                        route["duration"] = duration_dm
                        route["distance"] = distance_dm
                    logger.info(
                        f"Distance Matrix: duration={duration_dm}s, distance={distance_dm}m applied to {len(out)} routes"
                    )
                logger.info(
                    f"Google Directions: {len(out)} routes for {origin} -> {destination}"
                )
                return out
            except Exception as e:
                logger.error(f"Google Directions error: {e}", exc_info=True)
                return []


geo_client = GeoClient()
