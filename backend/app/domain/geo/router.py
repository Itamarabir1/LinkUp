"""
Shared geo router — single source of truth for current location (reverse geocode).
Driver and passenger call GET /geo/address when the user chooses “use my location”.
"""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.exceptions.validation import InvalidLocationError
from app.domain.geo.processor import get_address_from_gps
from app.domain.geo.schema import AddressFromCoordsResponse
from app.domain.users.model import User

router = APIRouter(tags=["Geo"])


@router.get(
    "/maps-key",
    summary="מפתח Google Maps לתצוגת מפה בפרונט",
    description="מחזיר את מפתח ה-API המוגדר בבקאנד (GOOGLE_MAPS_API_KEY). הפרונט משתמש בו ל-Maps JavaScript API.",
)
async def get_maps_api_key(current_user: User = Depends(get_current_user)):
    """Maps API key is set in backend .env — single source of truth."""
    return {"google_maps_api_key": settings.GOOGLE_MAPS_API_KEY or ""}


@router.get(
    "/address",
    response_model=AddressFromCoordsResponse,
    summary="כתובת ממיקום נוכחי (Reverse Geocode)",
    description="מקבל קואורדינטות ומחזיר כתובת קריאה. לשימוש בכפתור 'השתמש במיקום שלי' אצל נהג ונוסע. דורש authentication.",
)
async def get_address_from_coords(
    lat: float = Query(..., ge=-90, le=90, description="קו רוחב"),
    lon: float = Query(..., ge=-180, le=180, description="קו אורך"),
    current_user: User = Depends(get_current_user),
):
    """
    Converts GPS coordinates to a human-readable address.
    Requires an authenticated user.
    """
    address = await get_address_from_gps(lat, lon)
    if not address:
        raise InvalidLocationError(detail="לא נמצאה כתובת למיקום זה")
    return AddressFromCoordsResponse(address=address, lat=lat, lon=lon)
