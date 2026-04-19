import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.infrastructure.geo.circuit_breaker import (
    google_directions_cb,
    google_distance_matrix_cb,
)

logger = logging.getLogger(__name__)

# --- Google Directions API (routes) ---
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
# --- Google Distance Matrix API (time & distance O–D) ---
GOOGLE_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
MAX_ROUTES = 3  # keep top 2–3 alternatives
TIMEOUT_DIRECTIONS = 15.0
TIMEOUT_DISTANCE_MATRIX = 10.0


def _decode_polyline(encoded: str) -> list[list[float]]:
    """
    Decode Google encoded polyline to [[lat, lon], ...].
    Standard Google algorithm (1e-5 degrees).
    """
    if not encoded:
        return []
    coords: list[list[float]] = []
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
    """Infrastructure client for external geo APIs (async)."""

    OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

    def __init__(self):
        # Legacy stub for backward compat in tests/old code paths.
        # No Nominatim; geocoding uses GeocodingService or test patches.
        class _GeoLocator:
            def geocode(self, _: str):
                return None

        self.geolocator = _GeoLocator()

    async def fetch_coordinates(self, address: str) -> tuple[float | None, float | None]:
        """
        Resolve address to coordinates with Redis cache.

        Source of truth: Google GeocodingService + cache.
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

        # If tests inject geolocator / monkeypatch, use it first
        try:
            loc = self.geolocator.geocode(address)
            if loc and getattr(loc, "latitude", None) is not None and getattr(loc, "longitude", None) is not None:
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

    async def fetch_distance_matrix(self, start: tuple[float, float], end: tuple[float, float]) -> tuple[int, int] | None:
        """
        Google Distance Matrix: travel time and distance (meters) between two points.
        Returns (duration_sec, distance_m) or None on failure.
        """
        if not google_distance_matrix_cb.allow_request():
            logger.warning("CircuitBreaker OPEN: skipping Distance Matrix")
            return None

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
                    logger.warning("Distance Matrix API error: %s", response.status_code)
                    google_distance_matrix_cb.record_failure()
                    return None
                data: dict[str, Any] = response.json()
                if data.get("status") != "OK":
                    logger.warning("Distance Matrix status: %s", data.get("status"))
                    google_distance_matrix_cb.record_failure()
                    return None
                rows = data.get("rows", [])
                if not rows or not rows[0].get("elements"):
                    google_distance_matrix_cb.record_failure()
                    return None
                el = rows[0]["elements"][0]
                if el.get("status") != "OK":
                    google_distance_matrix_cb.record_failure()
                    return None
                duration_sec = el.get("duration", {}).get("value", 0)
                distance_m = el.get("distance", {}).get("value", 0)
                google_distance_matrix_cb.record_success()
                return (int(duration_sec), int(distance_m))
            except Exception as e:
                logger.warning("Distance Matrix error: %s", e)
                google_distance_matrix_cb.record_failure()
                return None

    async def fetch_raw_routes(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        departure_time: datetime | None = None,
    ) -> list[dict]:
        """
        Fetch 2–3 routes from Google Directions.
        Per-route time/distance enriched from Distance Matrix when available.
        Returns dicts: summary, duration (sec), distance (m), coords [[lat,lon],...].
        """
        return await self.fetch_routes_google_directions(start, end, departure_time)

    async def fetch_routes_google_directions(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        departure_time: datetime | None = None,
    ) -> list[dict]:
        """
        Up to 3 routes from Google Directions (alternatives=true).
        Output shape matches processor: summary, duration (sec), distance (m), coords.
        """
        if not google_directions_cb.allow_request():
            logger.warning("CircuitBreaker OPEN: skipping Google Directions")
            return []

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
            params["departure_time"] = max(ts, now_ts + 60)
        else:
            params["departure_time"] = "now"

        async with httpx.AsyncClient(timeout=TIMEOUT_DIRECTIONS) as client:
            try:
                response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
                if response.status_code != 200:
                    logger.error("Google Directions API error: %s", response.status_code)
                    google_directions_cb.record_failure()
                    return []
                data = response.json()
                if data.get("status") != "OK":
                    logger.warning("Google Directions status: %s", data.get("status"))
                    google_directions_cb.record_failure()
                    return []
                raw_list = data.get("routes")
                if not isinstance(raw_list, list):
                    raw_list = [raw_list] if raw_list else []
                routes_raw = raw_list[:MAX_ROUTES]
                out: list[dict] = []
                for i, r in enumerate(routes_raw):
                    legs = r.get("legs", [])
                    duration_sec = sum(leg.get("duration", {}).get("value", 0) for leg in legs)
                    distance_m = sum(leg.get("distance", {}).get("value", 0) for leg in legs)
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
                google_directions_cb.record_success()

                dm_result = await self.fetch_distance_matrix(start, end)
                if dm_result:
                    duration_dm, distance_dm = dm_result
                    for route in out:
                        route["duration"] = duration_dm
                        route["distance"] = distance_dm
                    logger.info(
                        "Distance Matrix override: %ds, %dm on %d routes",
                        duration_dm,
                        distance_dm,
                        len(out),
                    )
                logger.info(
                    "Google Directions: %d routes for %s → %s",
                    len(out),
                    origin,
                    destination,
                )
                return out
            except Exception as e:
                logger.error("Google Directions error: %s", e, exc_info=True)
                google_directions_cb.record_failure()
                return []


geo_client = GeoClient()
