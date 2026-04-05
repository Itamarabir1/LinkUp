from sqladmin import ModelView

from app.domain.bookings.model import Booking
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.users.model import User


# תצוגת משתמשים
class UserAdmin(ModelView, model=User):
    column_list = [User.user_id, User.full_name, User.email, User.is_admin]
    column_searchable_list = [User.full_name, User.email]
    icon = "fa-solid fa-user"


# תצוגת בקשות נוסע
class RequestAdmin(ModelView, model=PassengerRequest):
    column_list = [
        PassengerRequest.request_id,
        PassengerRequest.status,
        PassengerRequest.pickup_name,
        PassengerRequest.is_notification_active,
    ]
    column_filters = [PassengerRequest.status]
    icon = "fa-solid fa-hand-holding-heart"


# תצוגת נסיעות נהגים
class RideAdmin(ModelView, model=Ride):
    column_list = [Ride.ride_id, Ride.driver_id, Ride.departure_time, Ride.status]
    icon = "fa-solid fa-car"


# תצוגת הזמנות (שידוכים)
class BookingAdmin(ModelView, model=Booking):
    column_list = [Booking.booking_id, Booking.status, Booking.created_at]
    icon = "fa-solid fa-calendar-check"
