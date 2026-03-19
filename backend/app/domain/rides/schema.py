from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import List, Any, Dict, Optional
from uuid import UUID
from app.domain.rides.enum import RideStatus
from app.core.utils.validators import validate_future_datetime
from uuid import uuid4

# שים לב לתיקון הנתיב אם צריך - שמרתי על המקור שלך
from app.domain.geo.schema import RouteOptionData
# --- 0. אובייקטי עזר (Reusable Mixins) ---


class LocationMixin(BaseModel):
    origin_name: str = Field(..., min_length=2)
    destination_name: str = Field(..., min_length=2)


class CoordinatesMixin(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float


# --- 1. סכמות לקלט (Requests) ---


class RidePreviewCreate(BaseModel):
    """יצירת תצוגה מקדימה לנסיעה. מוצא: טקסט (origin_name) או מיקום נוכחי (origin_lat/origin_lon) – כמו אצל נוסע."""

    driver_id: UUID
    origin_name: Optional[str] = (
        None  # טקסט או ריק כשנשלחים origin_lat/origin_lon (מיקום נוכחי)
    )
    destination_name: str
    departure_time: datetime
    available_seats: int = Field(default=4, ge=1)
    price: float = Field(default=0.0, ge=0.0)
    origin_lat: Optional[float] = Field(None, ge=-90, le=90)
    origin_lon: Optional[float] = Field(None, ge=-180, le=180)
    group_id: Optional[UUID] = None

    @field_validator("departure_time")
    @classmethod
    def time_validation(cls, v: datetime) -> datetime:
        return validate_future_datetime(v)


class RideCreate(BaseModel):
    session_id: str
    selected_route_index: int = 0
    group_id: Optional[UUID] = None


class RideUpdate(BaseModel):
    """עדכון חלקי לנסיעה – רק זמן יציאה ומספר מושבים (כל השדות אופציונליים)."""

    departure_time: Optional[datetime] = None
    available_seats: Optional[int] = Field(None, ge=1)

    @field_validator("departure_time")
    @classmethod
    def time_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        return validate_future_datetime(v)


# --- 2. סכמות לתצוגה מקדימה (Preview) ---


class RouteOption(BaseModel):
    route_index: int
    summary: str
    duration_min: float
    distance_km: float
    coords: List[List[float]]


class RidePreviewResponse(LocationMixin):
    session_id: str
    origin_coords: List[float]  # [lat, lon]
    destination_coords: List[float]
    routes: List[RouteOption]

    @classmethod
    def from_processor(
        cls,
        geo_data: Dict[str, Any],
        preview_in: "RidePreviewCreate",
        origin_address: str,
    ) -> "RidePreviewResponse":
        """
        Factory Method מקצועית.
        1. מייצרת את ה-session_id פנימית (Encapsulation).
        2. מקבלת את ה-origin_address המוחלט מה-Service.
        """
        routes_data: List[RouteOptionData] = geo_data["routes"]
        routes = [
            RouteOption(
                route_index=i,
                summary=r.summary,
                duration_min=r.duration_min,
                distance_km=r.distance_km,
                coords=r.coords,
            )
            for i, r in enumerate(routes_data)
        ]
        return cls(
            session_id=str(uuid4()),  # היצירה עברה לכאן!
            origin_name=origin_address,
            destination_name=preview_in.destination_name,
            origin_coords=[geo_data["origin"].lat, geo_data["origin"].lon],
            destination_coords=[geo_data["dest"].lat, geo_data["dest"].lon],
            routes=routes,
        )


# --- 3. הליבה (Internal & DB Contract) ---


class RideBase(LocationMixin):
    """בסיס לנסיעה – בלי וולידציית 'זמן עתידי' (תשובות מה-DB כוללות נסיעות בעבר)."""

    driver_id: UUID
    departure_time: datetime
    estimated_arrival_time: datetime
    available_seats: int = Field(default=4, ge=1)
    price: float = Field(default=0.0, ge=0.0)


class RideCreateInternal(RideBase, CoordinatesMixin):
    """הסכימה הסופית שעוברת ל-CRUD – וולידציית זמן עתידי רק ביצירה."""

    route_coords: List[List[float]]
    total_distance_km: float
    total_duration_min: float
    status: RideStatus = RideStatus.OPEN
    group_id: Optional[UUID] = None

    @field_validator("departure_time", "estimated_arrival_time")
    @classmethod
    def validate_times_future(cls, v: datetime) -> datetime:
        return validate_future_datetime(v)

    model_config = ConfigDict(from_attributes=True)


# --- 4. תגובות (Responses) ---


class RideResponse(RideBase):
    """מחזיר נסיעה מלאה מה-DB"""

    ride_id: UUID
    status: RideStatus
    created_at: datetime
    user_booking_status: Optional[str] = None
    group_id: Optional[UUID] = None
    group_name: Optional[str] = None
    total_distance_km: float = Field(..., validation_alias="distance_km")
    total_duration_min: float = Field(..., validation_alias="duration_min")
    # שימוש ב-Alias כדי למשוך מה-Property של SQLAlchemy
    route_coords: List[List[float]] = Field(..., validation_alias="route_coords_list")
    route_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RideSearchResponse(BaseModel):
    """תצוגה מקוצרת לחיפוש"""

    ride_id: UUID
    origin_name: str
    destination_name: str
    departure_time: datetime
    estimated_arrival_time: datetime
    price: float
    status: RideStatus


class DriverInfoResponse(BaseModel):
    """פרטי נהג לתצוגה (לנוסע) – רק כשהנוסע לוחץ 'הצג פרטי הנהג'."""

    full_name: str
    phone_number: Optional[str] = None
