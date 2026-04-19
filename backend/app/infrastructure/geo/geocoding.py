import logging

import httpx

from app.core.config import settings
from app.core.exceptions.infrastructure import InfrastructureError
from app.infrastructure.geo.circuit_breaker import google_geocoding_cb

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    שירות גיאוקודינג - המרות גיאוגרפיות עם Google Maps Geocoding API.
    שתי פונקציות: כתובת → קואורדינטות ו-קואורדינטות → כתובת.
    משתמש ב-httpx async ישירות ל-Google Maps Geocoding API.
    """

    GOOGLE_MAPS_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    TIMEOUT = 10.0

    @staticmethod
    async def get_coordinates_from_address(
        address: str,
    ) -> tuple[float | None, float | None]:
        """
        Geocoding: הופך כתובת לקואורדינטות (lat, lon).
        משתמש ב-Google Maps Geocoding API.

        Args:
            address: כתובת טקסטואלית (למשל "רחוב הרצל 5, תל אביב")

        Returns:
            Tuple[lat, lon] או (None, None) אם נכשל
        """
        if not address or not address.strip():
            logger.warning("Empty address provided for geocoding")
            return None, None

        if not google_geocoding_cb.allow_request():
            logger.warning("CircuitBreaker OPEN: skipping geocoding for '%s'", address)
            return None, None

        url = GeocodingService.GOOGLE_MAPS_BASE_URL
        params = {
            "address": address,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "he",
        }
        try:
            async with httpx.AsyncClient(timeout=GeocodingService.TIMEOUT) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        location = data["results"][0]["geometry"]["location"]
                        lat = float(location.get("lat", 0))
                        lng = float(location.get("lng", 0))
                        logger.info("Geocoded '%s' → (%s, %s)", address, lat, lng)
                        google_geocoding_cb.record_success()
                        return lat, lng
                    status = data.get("status", "UNKNOWN")
                    logger.warning("Google Maps geocoding failed for '%s': %s", address, status)
                    google_geocoding_cb.record_failure()
                    return None, None
                logger.error(
                    "Google Maps geocoding API error: %s for '%s'",
                    response.status_code,
                    address,
                )
                google_geocoding_cb.record_failure()
                return None, None
        except httpx.TimeoutException:
            logger.error("Geocoding timeout for address: %s", address)
            google_geocoding_cb.record_failure()
            return None, None
        except Exception as e:
            logger.error("Geocoding exception for '%s': %s", address, e, exc_info=True)
            google_geocoding_cb.record_failure()
            return None, None

    @staticmethod
    async def get_address_from_gps(lat: float, lon: float) -> str | None:
        """
        Reverse Geocoding: הופך קואורדינטות לכתובת קריאה.
        משתמש ב-Google Maps Geocoding API.

        Args:
            lat: קו רוחב (-90 עד 90)
            lon: קו אורך (-180 עד 180)

        Returns:
            כתובת טקסטואלית או None אם נכשל
        """
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            logger.warning("Invalid coordinates: lat=%s, lon=%s", lat, lon)
            return None

        if not google_geocoding_cb.allow_request():
            logger.warning("CircuitBreaker OPEN: skipping reverse geocoding for (%s, %s)", lat, lon)
            return None

        url = GeocodingService.GOOGLE_MAPS_BASE_URL
        params = {
            "latlng": f"{lat},{lon}",
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "he",
        }
        try:
            async with httpx.AsyncClient(timeout=GeocodingService.TIMEOUT) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        address = data["results"][0].get("formatted_address")
                        if address:
                            logger.info("Reverse geocoded (%s, %s) → '%s'", lat, lon, address)
                            google_geocoding_cb.record_success()
                            return address
                        logger.warning("No formatted_address for (%s, %s)", lat, lon)
                        return None
                    status = data.get("status", "UNKNOWN")
                    logger.warning("Reverse geocoding failed for (%s, %s): %s", lat, lon, status)
                    google_geocoding_cb.record_failure()
                    return None
                if response.status_code == 429:
                    logger.warning("Google Maps rate limit (429) for (%s, %s)", lat, lon)
                    google_geocoding_cb.record_failure()
                    raise InfrastructureError(
                        message="שירות geocoding לא זמין כרגע עקב הגבלת תעבורה.",
                        detail="Google Maps API returned 429 Too Many Requests",
                        error_code="GEO_SERVICE_UNAVAILABLE",
                    )
                logger.error(
                    "Reverse geocoding API error: %s for (%s, %s)",
                    response.status_code,
                    lat,
                    lon,
                )
                google_geocoding_cb.record_failure()
                return None
        except httpx.TimeoutException:
            logger.error("Reverse geocoding timeout for (%s, %s)", lat, lon)
            google_geocoding_cb.record_failure()
            return None
        except InfrastructureError:
            raise
        except Exception as e:
            logger.error(
                "Reverse geocoding exception for (%s, %s): %s",
                lat,
                lon,
                e,
                exc_info=True,
            )
            google_geocoding_cb.record_failure()
            return None
