"""
Enum של כל אירועי הנוטיפיקציה.
הערכים חייבים להתאים ל-routing_key שמגיע מ-RabbitMQ (או מאוטבוקס).
"""

from enum import Enum


class NotificationEvent(str, Enum):
    # Auth & User
    USER_REGISTERED = "user.registered"
    EMAIL_VERIFICATION = "auth.email_verification"
    PASSWORD_RESET_REQUESTED = "auth.password_reset_code"
    # Ride
    RIDE_CREATED_FOR_PASSENGERS = "ride.created_for_passengers"
    RIDE_CANCELLED_BY_DRIVER = "ride.cancelled_by_driver"
    # Booking
    PASSENGER_JOIN_REQUEST = "booking.passenger_join_request"
    BOOKING_APPROVED_BY_DRIVER = "booking.approved_by_driver"
    BOOKING_REJECTED_BY_DRIVER = "booking.rejected_by_driver"
    # Reminder events (strings must match reminder_scheduler)
    PICKUP_REMINDER_PASSENGER = "PICKUP_REMINDER_PASSENGER"
    RIDE_START_DRIVER = "RIDE_START_DRIVER"
    # Chat
    CONVERSATION_COMPLETED = "chat.conversation.completed"
