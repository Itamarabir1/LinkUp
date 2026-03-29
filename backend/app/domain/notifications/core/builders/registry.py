from .ride_builder import RideBuilder
from .booking_builder import BookingBuilder

CONTEXT_MAP = {
    "ride.cancelled_by_driver": {
        "builder": RideBuilder(),
        "schema": None,
    },
    "ride.created_for_passengers": {
        "builder": RideBuilder(),
        "schema": None,
    },
    "booking.passenger_join_request": {
        "builder": BookingBuilder(),
        "schema": None,
    },
    "booking.approved_by_driver": {
        "builder": BookingBuilder(),
        "schema": None,
    },
    "booking.rejected_by_driver": {
        "builder": BookingBuilder(),
        "schema": None,
    },
    "PICKUP_REMINDER_PASSENGER": {
        "builder": BookingBuilder(),
        "schema": None,
    },
    "RIDE_START_DRIVER": {
        "builder": RideBuilder(),
        "schema": None,
    },
}
