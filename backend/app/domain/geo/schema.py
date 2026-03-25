from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class GeoLocation(BaseModel):
    lat: float
    lon: float


class AddressFromCoordsResponse(BaseModel):
    """תשובה משותפת ל־reverse geocoding – נהג ונוסע ממלאים שדה מקום ממיקום נוכחי."""

    address: str = Field(..., description="כתובת קריאה (reverse geocode)")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class RouteOptionData(BaseModel):
    summary: str
    duration_min: float
    distance_km: float
    coords: List[List[float]]  # רשימה של [lat, lon]


class DriverLocationReport(BaseModel):
    """גוף בקשה לדיווח מיקום נהג (POST /bookings/{booking_id}/location)."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = None
    speed: Optional[float] = None


class PassengerLocationReport(BaseModel):
    """גוף בקשה לדיווח מיקום נוסע (POST /bookings/{booking_id}/passenger-location)."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading: Optional[float] = None
    speed: Optional[float] = None


class LocationUpdate(BaseModel):
    booking_id: int
    latitude: float = Field(..., alias="lat")  # תמיכה גם ב-lat וגם ב-latitude
    longitude: float = Field(..., alias="lon")
    heading: Optional[float] = 0.0  # כיוון הנסיעה באייקון
    speed: float = 0.0

    model_config = ConfigDict(populate_by_name=True)
