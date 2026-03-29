from typing import Optional, Union
from uuid import UUID
from .base import LinkupError

# --- Ride Discovery & General Errors ---


class RideNotFoundError(LinkupError):
    status_code = 404
    error_code = "RIDE_NOT_FOUND"

    def __init__(self, ride_id: Union[int, str, UUID]):
        super().__init__(
            message=f"נסיעה {ride_id} לא נמצאה",
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"ride_id": ride_id},
        )


class InvalidRideStatusError(LinkupError):
    status_code = 400
    error_code = "RIDE_INVALID_STATUS"

    def __init__(self, status: str, action: Optional[str] = None):
        super().__init__(
            message=f"פעולה {f'({action}) ' if action else ''}לא חוקית לסטטוס הנסיעה הנוכחי: {status}",
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"current_status": status, "requested_action": action},
        )


# --- Logic & Validation Errors ---


class InvalidRouteError(LinkupError):
    status_code = 400
    error_code = "RIDE_INVALID_ROUTE"
    message = "מסלול הנסיעה שסופק אינו תקין או שאינו נתמך"

    def __init__(
        self,
        detail: Optional[str] = None,
        details: Optional[str] = None,
        index: Optional[int] = None,
    ):
        msg = detail or details or self.message
        if index is not None:
            msg = f"{msg} (אינדקס: {index})"
        payload = {"index": index} if index is not None else None
        super().__init__(message=msg, payload=payload)


class InvalidDateTimeError(LinkupError):
    status_code = 400
    error_code = "RIDE_INVALID_DATETIME"
    message = "זמן הנסיעה שנבחר אינו תקין"

    def __init__(self, provided_dt: Optional[str] = None, details: Optional[str] = None):
        msg = details if details else self.message
        super().__init__(
            message=msg,
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"provided_datetime": provided_dt} if provided_dt else None,
        )


# --- Booking Errors ---


class NoConfirmedBookingsError(LinkupError):
    """נזרקת כאשר מנסים להתחיל נסיעה בלי אף נוסע מאושר."""

    status_code = 400
    error_code = "RIDE_NO_CONFIRMED_BOOKINGS"
    message = "אין נוסעים מאושרים לנסיעה"

    def __init__(self, ride_id: Optional[Union[UUID, str]] = None):
        super().__init__(
            message=self.message,
            payload={"ride_id": str(ride_id)} if ride_id is not None else None,
        )


class RideFullError(LinkupError):
    status_code = 400
    error_code = "RIDE_IS_FULL"
    message = "הנסיעה מלאה, לא ניתן להוסיף נוסעים נוספים"

    def __init__(self, ride_id: Optional[int] = None):
        msg = f"נסיעה {ride_id} לא נמצאה" if ride_id is not None else "הנסיעה לא נמצאה או שאינך מורשה לבצע פעולה זו"
        super().__init__(message=msg, payload={"ride_id": ride_id} if ride_id is not None else None)


class SessionExpiredError(LinkupError):
    """נזרקת כאשר ה-Session ID ברדיס פג תוקף או לא קיים."""

    status_code = 410
    error_code = "RIDE_SESSION_EXPIRED"
    message = "פג תוקף הצעת הנסיעה, אנא בצע חיפוש מחדש"

    def __init__(self, session_id: Optional[str] = None):
        msg = f"הסשן {session_id} פג תוקף או אינו קיים." if session_id else self.message
        super().__init__(message=msg, payload={"session_id": session_id} if session_id else None)


class RideAlreadyCancelledError(LinkupError):
    status_code = 400
    error_code = "RIDE_ALREADY_CANCELLED"
    message = "הנסיעה כבר בוטלה בעבר"
