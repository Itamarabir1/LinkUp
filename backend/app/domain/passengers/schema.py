from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
from app.domain.passengers.enum import PassengerStatus
from app.core.utils.validators import validate_future_datetime
from fastapi import Query
from typing import Optional, List
from uuid import UUID
from app.domain.rides.schema import RideResponse

# --- 1. סכמות בסיס ליצירת בקשה ---


class Passenger(BaseModel):
    """השרת ממלא passenger_id מהמשתמש המחובר – לא מהגוף."""

    passenger_id: Optional[UUID] = Field(None, description="ממולא בשרת מהטוקן; התעלם בקליינט")
    num_passengers: int = Field(default=1, ge=1)
    pickup_name: str = Field(..., min_length=1, description="שם מקום איסוף (טקסט או ממיקום נוכחי)")
    destination_name: str = Field(..., min_length=1)
    requested_departure_time: Optional[datetime] = Field(
        None,
        description="אופציונלי – אם ריק יחפש 'מעכשיו'",
    )
    search_radius: int = Field(default=1000, ge=100, description="רדיוס חיפוש במטרים (אחיד עם חיפוש)")
    is_notification_active: bool = Field(default=True, description="התראות מייל ופוש לבקשה זו")
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90)
    pickup_lon: Optional[float] = Field(None, ge=-180, le=180)

    @field_validator("requested_departure_time")
    @classmethod
    def time_validation(cls, v: Optional[datetime]) -> Optional[datetime]:
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
    group_id: Optional[UUID] = None


class PassengerRequestResponse(BaseModel):
    """נתוני הבקשה הבסיסיים כפי שנשמרו ב-DB"""

    request_id: UUID
    passenger_id: UUID
    group_id: Optional[UUID] = None
    num_passengers: int
    pickup_name: str
    destination_name: str
    requested_departure_time: datetime
    status: PassengerStatus
    created_at: datetime
    booking_id: Optional[UUID] = None
    # מחזירים את מצב הכפתור בתשובה מהשרת
    is_notification_active: bool

    model_config = ConfigDict(from_attributes=True)


# --- הוספה חדשה: תשובה הכוללת התאמות מיידיות ---


class PassengerRequestWithMatches(PassengerRequestResponse):
    """
    הסכמה הזו מחזירה גם את נתוני הבקשה וגם את הנהגים שנמצאו באותו רגע.
    יורשת אוטומטית את is_notification_active מ-PassengerRequestResponse.
    """

    matching_rides: List[RideResponse] = Field(default=[], description="רשימת נהגים רלוונטיים שנמצאו מיד")


# --- 2. סכמות לעדכון (Partial Update) ---


class PassengerRequestUpdateNotifications(BaseModel):
    """סכימה ייעודית לשינוי מצב הכפתור בלבד"""

    is_notification_active: bool


# --- 3. סכמות לחיפוש (Request Parameters) ---


class RideSearchRequest(BaseModel):
    """סכמת קלט לחיפוש; passenger_id ממולא בשרת אם יש auth (אופציונלי)."""

    passenger_id: Optional[UUID] = Field(None, description="ממולא בשרת כשמשתמש מחובר")
    pickup_name: str = Field(..., min_length=2)
    destination_name: str = Field(..., min_length=2)
    search_radius: int = Field(default=1000, ge=100, description="רדיוס חיפוש במטרים (אחיד)")
    departure_time: Optional[datetime] = Field(
        None,
        description="מתי הנוסע צריך לצאת (אם ריק – יחפש מעכשיו)",
    )
    limit: int = Field(default=20, ge=1, le=50)
    after: Optional[UUID] = Field(None, description="cursor: ride_id אחרייו להמשיך")
    group_id: Optional[UUID] = Field(None, description="אם קיים — מסנן רק נסיעות של הקבוצה")


class RideSearchResponse(BaseModel):
    """תשובת חיפוש נסיעות עם cursor-based pagination."""

    items: List[RideResponse] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(None, description="ride_id להבא (after=)")
    has_more: bool = False


class RequestRideFromSearch(BaseModel):
    """בקשת הצטרפות לנסיעה מתוך תוצאות חיפוש."""

    ride_id: UUID
    request_id: Optional[UUID] = Field(None, description="מזהה הבקשה מהחיפוש (אם קיים)")
    pickup_name: str = Field(..., min_length=1)
    destination_name: str = Field(..., min_length=1)
    num_seats: int = Field(default=1, ge=1)


class PassengerSearchRequest(BaseModel):
    origin_name: str = Query(..., min_length=2)
    destination_name: str = Query(..., min_length=2)
    radius: int = Query(2000, ge=100, le=10000)

    model_config = ConfigDict(from_attributes=True)
