# app/domain/geo/processor.py
import logging
from datetime import datetime

from app.core.exceptions.validation import InvalidLocationError
from app.domain.geo.schema import GeoLocation, RouteOptionData
from app.infrastructure.geo.client import geo_client
from app.infrastructure.geo.geocode_cache import get_coordinates
from app.infrastructure.geo.geocoding import GeocodingService

logger = logging.getLogger(__name__)


async def resolve_origin_address(name: str | None, lat: float | None, lon: float | None) -> str:
    """
    Resolve origin label: prefer place name, else reverse-geocode GPS.
    Raises if neither yields a usable address.
    """
    # 1. Prefer explicit place name from user input
    if name and name.strip():
        return name

    # 2. Else reverse-geocode GPS to address
    if lat is not None and lon is not None:
        address = await GeocodingService.get_address_from_gps(lat, lon)
        if address:
            return address

    # 3. Fallback when name and GPS are missing/invalid
    raise InvalidLocationError(detail="חובה לספק כתובת מוצא או מיקום GPS תקין")


async def get_full_routing_data(
    origin_name: str,
    dest_name: str,
    departure_time: datetime | None = None,
) -> dict | None:
    """
    Orchestrate external directions API and map results to domain route DTOs.
    """
    # 1. Coordinates via Redis-backed cache (+ stampede protection on miss)
    origin_coords = await get_coordinates(origin_name)
    dest_coords = await get_coordinates(dest_name)
    if origin_coords is None or dest_coords is None:
        logger.warning(f"Could not find coordinates for: {origin_name} or {dest_name}")
        return None
    lat_o, lon_o = origin_coords
    lat_d, lon_d = dest_coords

    # 2. Up to 3 routes from GeoClient / Directions (1–3 as returned)
    raw_routes = await geo_client.fetch_raw_routes((lat_o, lon_o), (lat_d, lon_d), departure_time)

    if not raw_routes:
        logger.error(f"No routes found between {origin_name} and {dest_name}")
        return None

    # Normalize routes to a list
    if not isinstance(raw_routes, list):
        raw_routes = [raw_routes] if raw_routes else []

    logger.info(f"Passing {len(raw_routes)} route(s) to preview for {origin_name} -> {dest_name}")

    # 3. Map to Pydantic (Directions: duration sec, distance m, coords [lat,lon])
    processed_routes = [
        RouteOptionData(
            summary=r.get("summary", "מסלול"),
            duration_min=round(r.get("duration", 0) / 60, 1),
            distance_km=round(r.get("distance", 0) / 1000, 1),
            coords=r.get("coords", []),
        )
        for r in raw_routes
    ]

    return {
        "origin": GeoLocation(lat=lat_o, lon=lon_o),
        "dest": GeoLocation(lat=lat_d, lon=lon_d),
        "routes": processed_routes,
    }


async def get_address_from_gps(lat: float, lon: float) -> str | None:
    """
    Reverse-geocode coordinates to a human-readable address via GeocodingService.
    """
    return await GeocodingService.get_address_from_gps(lat, lon)
