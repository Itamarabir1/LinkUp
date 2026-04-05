# app/domain/geo/processor.py
import logging
from datetime import datetime
from typing import Dict, Optional

from app.core.exceptions.validation import InvalidLocationError
from app.domain.geo.schema import GeoLocation, RouteOptionData
from app.infrastructure.geo.client import geo_client
from app.infrastructure.geo.geocoding import GeocodingService

logger = logging.getLogger(__name__)


async def resolve_origin_address(name: str | None, lat: float | None, lon: float | None) -> str:
    """
    מבצע 'החלטה' גיאוגרפית: שם מקום או GPS.
    מחזיר כתובת טקסטואלית או זורק שגיאה אם אין כלום.
    """
    # 1. עדיפות ראשונה: שם המקום שהמשתמש הקליד
    if name and name.strip():
        return name

    # 2. עדיפות שנייה: המרה מ-GPS לכתובת (Reverse Geocoding)
    if lat is not None and lon is not None:
        address = await GeocodingService.get_address_from_gps(lat, lon)
        if address:
            return address

    # 3. Fallback: אם אין שם ואין GPS תקין
    raise InvalidLocationError(detail="חובה לספק כתובת מוצא או מיקום GPS תקין")


async def get_full_routing_data(
    origin_name: str,
    dest_name: str,
    departure_time: datetime | None = None,
) -> dict | None:
    """
    מתזמר שליפת נתונים מ-API חיצוני והמרתם לסכימות של הדומיין.
    """
    # 1. שליפת קואורדינטות מ-GeocodingService
    lat_o, lon_o = await GeocodingService.get_coordinates_from_address(origin_name)
    lat_d, lon_d = await GeocodingService.get_coordinates_from_address(dest_name)

    if lat_o is None or lat_d is None:
        logger.warning(f"Could not find coordinates for: {origin_name} or {dest_name}")
        return None

    # 2. שליפת עד 3 מסלולים מ-Google Directions API (GeoClient) – מחזיר כמה שגוגל מחזירה (1–3)
    raw_routes = await geo_client.fetch_raw_routes((lat_o, lon_o), (lat_d, lon_d), departure_time)

    if not raw_routes:
        logger.error(f"No routes found between {origin_name} and {dest_name}")
        return None

    # וידוא ש-routes היא רשימה (לא אובייקט בודד)
    if not isinstance(raw_routes, list):
        raw_routes = [raw_routes] if raw_routes else []

    logger.info(f"Passing {len(raw_routes)} route(s) to preview for {origin_name} -> {dest_name}")

    # 3. טרנספורמציה לסכימות Pydantic (פורמט מ-Directions: duration שניות, distance מטרים, coords [lat,lon])
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
    Reverse Geocoding: הופך קואורדינטות לכתובת קריאה.
    משתמש ב-GeocodingService.
    """
    return await GeocodingService.get_address_from_gps(lat, lon)
