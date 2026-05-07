from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import NOTIFICATIONS_DEFAULT_LIMIT
from app.domain.bookings.enum import BookingStatus


# 1. Create join request body
class BookingCreate(BaseModel):
    ride_id: UUID
    request_id: UUID
    num_seats: int = Field(default=1, ge=1)


# 2. Generic server response shape
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


# 3. Driver manifest schema
class BookingManifestItem(BaseModel):
    booking_id: UUID
    passenger_id: UUID
    passenger_name: str
    phone: str
    num_seats: int
    whatsapp_link: str | None = None
    status: BookingStatus
    # Pickup stop details and time
    pickup_name: str | None = None
    pickup_time: datetime | None = None
    destination_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# 4. Full manifest response
class RideManifestResponse(BaseModel):
    ride_id: UUID
    confirmed_total: int = Field(ge=0, description="כל שורות confirmed לנסיעה (COUNT)")
    pending_total: int = Field(ge=0, description="כל שורות pending לנסיעה (COUNT)")
    manifest_truncated: bool = Field(
        ...,
        description="True אם confirmed_total + pending_total חורגים מ-manifest row limit והרשימה נחתכה",
    )
    total_confirmed_passengers: int = Field(
        ge=0,
        description="תואם confirmed_total לתאימות לאחור; ספירת מאושרים ב-DB לאורך הנסיעה",
    )
    available_seats_left: int
    passengers: list[BookingManifestItem]

    model_config = ConfigDict(from_attributes=True)


# 5. Compact schema for request management
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
    """User bookings with page-based pagination."""

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


class RideWithPassengersItem(BaseModel):
    """Single ride with embedded confirmed/pending passengers."""

    ride_id: UUID
    origin_name: str | None
    destination_name: str | None
    departure_time: datetime
    estimated_arrival_time: datetime | None
    available_seats: int
    price: float
    status: str  # RideStatus.value
    group_id: UUID | None = None
    group_name: str | None = None
    passengers: list[BookingManifestItem]

    model_config = ConfigDict(from_attributes=True)


class DriverSummaryInfo(BaseModel):
    full_name: str
    phone_number: str | None = None


class PassengerBookingSummaryItem(BaseModel):
    """Single booking with ride and driver info embedded."""

    booking_id: UUID
    booking_status: BookingStatus
    ride_id: UUID
    origin_name: str | None
    destination_name: str | None
    departure_time: datetime
    estimated_arrival_time: datetime | None
    ride_status: str
    group_id: UUID | None = None
    group_name: str | None = None
    driver: DriverSummaryInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class DriverActiveResponse(BaseModel):
    rides: list[RideWithPassengersItem]

    model_config = ConfigDict(from_attributes=True)


class DriverHistoryResponse(BaseModel):
    rides: list[RideWithPassengersItem]
    next_cursor: str | None = None
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


class PassengerActiveResponse(BaseModel):
    bookings: list[PassengerBookingSummaryItem]

    model_config = ConfigDict(from_attributes=True)


class PassengerHistoryResponse(BaseModel):
    bookings: list[PassengerBookingSummaryItem]
    next_cursor: str | None = None
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


# Notification list item (driver + passenger views)
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


class PaginatedNotificationsResponse(BaseModel):
    """Cursor-paginated notifications for GET /users/me/notifications."""

    items: list[NotificationItemResponse] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = NOTIFICATIONS_DEFAULT_LIMIT

    model_config = ConfigDict(from_attributes=True)
