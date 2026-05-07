from datetime import date, datetime
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.utils.validators import validate_future_datetime
from app.domain.passengers.enum import PassengerStatus
from app.domain.rides.schema import RideResponse

# --- 1. Base schemas: create request ---


class Passenger(BaseModel):
    """Server fills passenger_id from the authenticated user, not from the body."""

    passenger_id: UUID | None = Field(None, description="ממולא בשרת מהטוקן; התעלם בקליינט")
    num_passengers: int = Field(default=1, ge=1)
    pickup_name: str = Field(..., min_length=1, description="שם מקום איסוף (טקסט או ממיקום נוכחי)")
    destination_name: str = Field(..., min_length=1)
    requested_departure_time: datetime | None = Field(
        None,
        description="אופציונלי – אם ריק יחפש 'מעכשיו'",
    )
    search_radius: float = Field(default=1.0, ge=0.1, le=50, description="רדיוס חיפוש בקילומטרים (אחיד עם חיפוש)")
    is_notification_active: bool = Field(default=True, description="התראות מייל ופוש לבקשה זו")
    pickup_lat: float | None = Field(None, ge=-90, le=90)
    pickup_lon: float | None = Field(None, ge=-180, le=180)

    @field_validator("requested_departure_time")
    @classmethod
    def time_validation(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return validate_future_datetime(v)

    @model_validator(mode="after")
    def coords_pair(self):
        if (self.pickup_lat is None) != (self.pickup_lon is None):
            raise ValueError("pickup_lat ו-pickup_lon חייבים להישלח יחד")
        return self


class PassengerRequestCreate(Passenger):
    is_auto_generated: bool = Field(default=False, description="האם נוצר מחיפוש אוטומטי")
    group_id: UUID | None = None


class PassengerRequestResponse(BaseModel):
    """Core passenger request fields as stored in the database."""

    request_id: UUID
    passenger_id: UUID
    group_id: UUID | None = None
    num_passengers: int
    pickup_name: str
    destination_name: str
    requested_departure_time: datetime
    status: PassengerStatus
    created_at: datetime
    booking_id: UUID | None = None
    # Button state echoed from server
    is_notification_active: bool

    model_config = ConfigDict(from_attributes=True)


class PaginatedPassengerRequestsResponse(BaseModel):
    """Paginated passenger requests for GET /passengers/me."""

    items: list[PassengerRequestResponse] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Response including immediate matches ---


class PassengerRequestWithMatches(PassengerRequestResponse):
    """
    Response including the saved request plus immediately matching rides.
    Inherits is_notification_active from PassengerRequestResponse.
    """

    matching_rides: list[RideResponse] = Field(default=[], description="רשימת נהגים רלוונטיים שנמצאו מיד")


# --- 2. Partial update schemas ---


class PassengerRequestUpdateNotifications(BaseModel):
    """Schema for toggling notification preference only."""

    is_notification_active: bool


# --- 3. Search / query params ---


class RideSearchRequest(BaseModel):
    """Ride search input; passenger_id set server-side when authenticated (optional)."""

    passenger_id: UUID | None = Field(None, description="ממולא בשרת כשמשתמש מחובר")
    pickup_name: str = Field(..., min_length=2)
    destination_name: str = Field(..., min_length=2)
    search_radius: float = Field(default=1.0, ge=0.1, le=50, description="רדיוס חיפוש בקילומטרים (אחיד)")
    destination_radius: float | None = Field(None, ge=0.1, le=50, description="רדיוס יעד בקילומטרים (אופציונלי)")
    departure_date: date | None = Field(
        None,
        description="יום יציאה בלוח השנה Asia/Jerusalem (00:00–24:00 מקומי). הדדי ל־departure_time.",
    )
    departure_time: datetime | None = Field(
        None,
        description="נקודת זמן: עם departure_time_to — טווח כולל; לבד — חיפוש ±2 שעות סביב הערך.",
    )
    departure_time_to: datetime | None = Field(
        None,
        description="יחד עם departure_time — מסיים טווח כולל [departure_time, departure_time_to]. דורש departure_time.",
    )
    limit: int = Field(default=20, ge=1, le=50)
    after: str | None = Field(None, description="opaque cursor להמשך")
    group_id: UUID | None = Field(None, description="אם קיים — מסנן רק נסיעות של הקבוצה")

    @model_validator(mode="after")
    def departure_filters_consistent(self) -> "RideSearchRequest":
        if self.departure_date is not None and (self.departure_time is not None or self.departure_time_to is not None):
            raise ValueError("departure_date is mutually exclusive with departure_time and departure_time_to")
        if self.departure_time_to is not None and self.departure_time is None:
            raise ValueError("departure_time_to requires departure_time")
        if self.departure_time is not None and self.departure_time_to is not None and self.departure_time_to < self.departure_time:
            raise ValueError("departure_time_to must not be before departure_time")
        return self


class RideSearchResponse(BaseModel):
    """Ride search results with cursor-based pagination."""

    items: list[RideResponse] = Field(default_factory=list)
    next_cursor: str | None = Field(None, description="ride_id להבא (after=)")
    has_more: bool = False


class RequestRideFromSearch(BaseModel):
    """Join a ride from search results."""

    ride_id: UUID
    request_id: UUID | None = Field(None, description="מזהה הבקשה מהחיפוש (אם קיים)")
    pickup_name: str = Field(..., min_length=1)
    destination_name: str = Field(..., min_length=1)
    num_seats: int = Field(default=1, ge=1)


class PassengerSearchRequest(BaseModel):
    origin_name: str = Query(..., min_length=2)
    destination_name: str = Query(..., min_length=2)
    radius: float = Query(2.0, ge=0.1, le=50)

    model_config = ConfigDict(from_attributes=True)
