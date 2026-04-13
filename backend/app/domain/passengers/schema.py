from datetime import datetime
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
    search_radius: int = Field(default=1000, ge=100, description="רדיוס חיפוש במטרים (אחיד עם חיפוש)")
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
    search_radius: int = Field(default=1000, ge=100, description="רדיוס חיפוש במטרים (אחיד)")
    departure_time: datetime | None = Field(
        None,
        description="מתי הנוסע צריך לצאת (אם ריק – יחפש מעכשיו)",
    )
    limit: int = Field(default=20, ge=1, le=50)
    after: UUID | None = Field(None, description="cursor: ride_id אחרייו להמשיך")
    group_id: UUID | None = Field(None, description="אם קיים — מסנן רק נסיעות של הקבוצה")


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
    radius: int = Query(2000, ge=100, le=10000)

    model_config = ConfigDict(from_attributes=True)
