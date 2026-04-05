from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.bookings.enum import BookingStatus


# 1. יצירת בקשת הצטרפות
class BookingCreate(BaseModel):
    ride_id: UUID
    request_id: UUID
    num_seats: int = Field(default=1, ge=1)


# 2. מה חוזר מהשרת (Response כללי) - עודכן!
class BookingResponse(BaseModel):
    booking_id: UUID
    ride_id: UUID
    request_id: UUID | None = None
    passenger_id: UUID
    num_seats: int
    status: BookingStatus
    created_at: datetime

    passenger_name: str | None = None
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


# 3. סכימה עבור הנהג (המניפסט) - עודכן!
class BookingManifestItem(BaseModel):
    booking_id: UUID
    passenger_id: UUID
    passenger_name: str
    phone: str
    num_seats: int
    whatsapp_link: str | None = None
    status: BookingStatus
    # פרטי תחנת עלייה ושעה
    pickup_name: str | None = None
    pickup_time: datetime | None = None
    destination_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# 4. תגובה מרוכזת של המניפסט - ללא שינוי
class RideManifestResponse(BaseModel):
    ride_id: UUID
    total_confirmed_passengers: int
    available_seats_left: int
    passengers: list[BookingManifestItem]

    model_config = ConfigDict(from_attributes=True)


# 5. סכימה קצרה לניהול בקשות - עודכן!
class BookingShortInfo(BaseModel):
    booking_id: UUID
    request_id: UUID
    passenger_name: str
    num_seats: int
    status: BookingStatus
    created_at: datetime


class TripStats(BaseModel):
    count: int
    total_km: float
    total_hours: float


class PaginatedBookingsResponse(BaseModel):
    """הזמנות משתמש עם page-based pagination."""

    items: list[BookingResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


class TripHistoryResponse(BaseModel):
    trips: list[BookingResponse]
    stats: TripStats

    model_config = ConfigDict(from_attributes=True)


# פריט התראה למסך ההתראות (נהג + נוסע)
class NotificationItemResponse(BaseModel):
    type: str  # ride_request | booking_confirmed | booking_rejected | pending_approval
    title: str
    body: str | None = None
    action_url: str | None = None
    created_at: datetime
    booking_id: UUID
    ride_id: UUID
    other_party_name: str | None = None
    ride_origin: str | None = None
    ride_destination: str | None = None
    status: str | None = None  # לנוסע: confirmed / rejected / pending_approval
