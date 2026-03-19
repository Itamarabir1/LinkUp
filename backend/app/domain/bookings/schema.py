from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.domain.bookings.enum import BookingStatus


# 1. יצירת בקשת הצטרפות - נשאר ללא שינוי (המשתמש לא שולח reminder_sent)
class BookingCreate(BaseModel):
    ride_id: UUID
    request_id: UUID
    num_seats: int = Field(default=1, ge=1)


# 2. מה חוזר מהשרת (Response כללי) - עודכן!
class BookingResponse(BaseModel):
    booking_id: UUID
    ride_id: UUID
    request_id: UUID
    passenger_id: UUID
    num_seats: int
    status: BookingStatus
    # --- השדה החדש ---
    reminder_sent: bool
    created_at: datetime

    passenger_name: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# 3. סכימה עבור הנהג (המניפסט) - עודכן!
class BookingManifestItem(BaseModel):
    booking_id: UUID
    passenger_id: UUID
    passenger_name: str
    phone: str
    num_seats: int
    whatsapp_link: Optional[str] = None
    status: BookingStatus
    # הוספה כאן עוזרת לנהג לדעת אם המערכת כבר תזכרה את הנוסע שלו
    reminder_sent: bool
    # פרטי תחנת עלייה ושעה
    pickup_name: Optional[str] = None
    pickup_time: Optional[datetime] = None
    destination_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# 4. תגובה מרוכזת של המניפסט - ללא שינוי
class RideManifestResponse(BaseModel):
    ride_id: UUID
    total_confirmed_passengers: int
    available_seats_left: int
    passengers: List[BookingManifestItem]

    model_config = ConfigDict(from_attributes=True)


# 5. סכימה קצרה לניהול בקשות - עודכן!
class BookingShortInfo(BaseModel):
    booking_id: UUID
    request_id: UUID
    passenger_name: str
    num_seats: int
    status: BookingStatus
    # הוספנו כאן למען השקיפות בניהול
    reminder_sent: bool
    created_at: datetime


class TripStats(BaseModel):
    count: int
    total_km: float
    total_hours: float


class PaginatedBookingsResponse(BaseModel):
    """הזמנות משתמש עם page-based pagination."""

    items: List[BookingResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


class TripHistoryResponse(BaseModel):
    trips: List[BookingResponse]
    stats: TripStats

    model_config = ConfigDict(from_attributes=True)


# פריט התראה למסך ההתראות (נהג + נוסע)
class NotificationItemResponse(BaseModel):
    type: str  # ride_request | booking_confirmed | booking_rejected | pending_approval
    title: str
    body: Optional[str] = None
    created_at: datetime
    booking_id: UUID
    ride_id: UUID
    other_party_name: Optional[str] = None
    ride_origin: Optional[str] = None
    ride_destination: Optional[str] = None
    status: Optional[str] = None  # לנוסע: confirmed / rejected / pending_approval
