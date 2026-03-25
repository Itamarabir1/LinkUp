import httpx
import logging
from typing import Optional, Tuple
from app.core.config import settings

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
    ) -> Tuple[Optional[float], Optional[float]]:
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

        url = GeocodingService.GOOGLE_MAPS_BASE_URL
        params = {
            "address": address,
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "he",  # עברית
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
                        logger.info(f"Geocoded '{address}' → ({lat}, {lng})")
                        return lat, lng
                    else:
                        status = data.get("status", "UNKNOWN")
                        logger.warning(
                            f"Google Maps geocoding failed for '{address}': {status}"
                        )
                        return None, None
                else:
                    logger.error(
                        f"Google Maps geocoding API error: {response.status_code} for address: {address}"
                    )
                    return None, None

        except httpx.TimeoutException:
            logger.error(f"Geocoding timeout for address: {address}")
            return None, None
        except Exception as e:
            logger.error(f"Geocoding exception for '{address}': {e}", exc_info=True)
            return None, None

    @staticmethod
    async def get_address_from_gps(lat: float, lon: float) -> Optional[str]:
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
            logger.warning(f"Invalid coordinates: lat={lat}, lon={lon}")
            return None

        url = GeocodingService.GOOGLE_MAPS_BASE_URL
        params = {
            "latlng": f"{lat},{lon}",
            "key": settings.GOOGLE_MAPS_API_KEY,
            "language": "he",  # עברית
        }

        try:
            async with httpx.AsyncClient(timeout=GeocodingService.TIMEOUT) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        address = data["results"][0].get("formatted_address")
                        if address:
                            logger.info(
                                f"Reverse geocoded ({lat}, {lon}) → '{address}'"
                            )
                            return address
                        else:
                            logger.warning(
                                f"No formatted_address found for coordinates: ({lat}, {lon})"
                            )
                            return None
                    else:
                        status = data.get("status", "UNKNOWN")
                        logger.warning(
                            f"Google Maps reverse geocoding failed for ({lat}, {lon}): {status}"
                        )
                        return None
                elif response.status_code == 429:
                    # Rate limiting (Too Many Requests)
                    logger.warning(
                        f"Google Maps rate limit exceeded (429) for ({lat}, {lon})"
                    )
                    from app.core.exceptions.infrastructure import InfrastructureError

                    raise InfrastructureError(
                        message="שירות geocoding לא זמין כרגע עקב הגבלת תעבורה. אנא נסה שוב בעוד כמה שניות.",
                        detail="Google Maps API returned 429 Too Many Requests",
                        error_code="GEO_SERVICE_UNAVAILABLE",
                    )
                else:
                    logger.error(
                        f"Reverse geocoding API error: {response.status_code} for ({lat}, {lon}). Response: {response.text[:200]}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error(f"Reverse geocoding timeout for ({lat}, {lon})")
            return None
        except Exception as e:
            logger.error(
                f"Reverse geocoding exception for ({lat}, {lon}): {e}", exc_info=True
            )
            return None
