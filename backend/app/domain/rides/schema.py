from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.utils.validators import validate_future_datetime

# Adjust import path if your layout differs
from app.domain.geo.schema import RouteOptionData
from app.domain.rides.enum import RideStatus

# --- 0. Reusable mixins ---


class LocationMixin(BaseModel):
    origin_name: str = Field(..., min_length=2)
    destination_name: str = Field(..., min_length=2)


class CoordinatesMixin(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float


# --- 1. Request bodies ---


class RidePreviewCreate(BaseModel):
    """יצירת תצוגה מקדימה לנסיעה. מוצא: טקסט (origin_name) או מיקום נוכחי (origin_lat/origin_lon) – כמו אצל נוסע."""

    driver_id: UUID
    origin_name: str | None = None  # טקסט או ריק כשנשלחים origin_lat/origin_lon (מיקום נוכחי)
    destination_name: str
    departure_time: datetime
    available_seats: int = Field(default=4, ge=1)
    price: float = Field(default=0.0, ge=0.0)
    origin_lat: float | None = Field(None, ge=-90, le=90)
    origin_lon: float | None = Field(None, ge=-180, le=180)
    group_id: UUID | None = None

    @field_validator("departure_time")
    @classmethod
    def time_validation(cls, v: datetime) -> datetime:
        return validate_future_datetime(v)


class RideCreate(BaseModel):
    session_id: str
    selected_route_index: int = 0
    group_id: UUID | None = None


class RideUpdate(BaseModel):
    """עדכון חלקי לנסיעה – רק זמן יציאה ומספר מושבים (כל השדות אופציונליים)."""

    departure_time: datetime | None = None
    available_seats: int | None = Field(None, ge=1)

    @field_validator("departure_time")
    @classmethod
    def time_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return validate_future_datetime(v)


# --- 2. Preview / route selection ---


class RouteOption(BaseModel):
    route_index: int
    summary: str
    duration_min: float
    distance_km: float
    coords: list[list[float]]


class RidePreviewResponse(LocationMixin):
    session_id: str
    origin_coords: list[float]  # [lat, lon]
    destination_coords: list[float]
    routes: list[RouteOption]

    @classmethod
    def from_processor(
        cls,
        geo_data: dict[str, Any],
        preview_in: "RidePreviewCreate",
        origin_address: str,
    ) -> "RidePreviewResponse":
        """
        Factory Method מקצועית.
        1. מייצרת את ה-session_id פנימית (Encapsulation).
        2. מקבלת את ה-origin_address המוחלט מה-Service.
        """
        routes_data: list[RouteOptionData] = geo_data["routes"]
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


# --- 3. Internal / DB contract ---


class RideBase(LocationMixin):
    """בסיס לנסיעה – בלי וולידציית 'זמן עתידי' (תשובות מה-DB כוללות נסיעות בעבר)."""

    driver_id: UUID
    departure_time: datetime
    estimated_arrival_time: datetime
    available_seats: int = Field(default=4, ge=1)
    price: float = Field(default=0.0, ge=0.0)


class RideCreateInternal(RideBase, CoordinatesMixin):
    """הסכימה הסופית שעוברת ל-CRUD – וולידציית זמן עתידי רק ביצירה."""

    route_coords: list[list[float]]
    total_distance_km: float
    total_duration_min: float
    status: RideStatus = RideStatus.OPEN
    group_id: UUID | None = None

    @field_validator("departure_time", "estimated_arrival_time")
    @classmethod
    def validate_times_future(cls, v: datetime) -> datetime:
        return validate_future_datetime(v)

    model_config = ConfigDict(from_attributes=True)


# --- 4. Responses ---


class RideResponse(RideBase):
    """מחזיר נסיעה מלאה מה-DB"""

    ride_id: UUID
    status: RideStatus
    created_at: datetime
    user_booking_status: str | None = None
    group_id: UUID | None = None
    group_name: str | None = None
    total_distance_km: float = Field(..., validation_alias="distance_km")
    total_duration_min: float = Field(..., validation_alias="duration_min")
    # Field alias from SQLAlchemy hybrid/property
    route_coords: list[list[float]] = Field(..., validation_alias="route_coords_list")
    route_summary: str | None = None

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
    phone_number: str | None = None
