from .ride_builder import RideContextBuilder
from .booking_builder import BookingContextBuilder

CONTEXT_MAP = {
    # אירועי נסיעה - כולם משתמשים ב-RideContextBuilder כי הם מקבלים אובייקט Ride
    "ride_cancelled": RideContextBuilder(),
    "ride_started": RideContextBuilder(),
    # אירועי הזמנה ובקשת הצטרפות - מקור הנתונים הוא Booking (המייל לנהג משתמש ב-action_url → הזמנות שלי)
    "new_ride_request": BookingContextBuilder(),
    "booking_confirmed": BookingContextBuilder(),
    "booking_rejected": BookingContextBuilder(),
    "booking_reminder": BookingContextBuilder(),
}
