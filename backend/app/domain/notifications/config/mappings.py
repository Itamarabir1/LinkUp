"""
מקור אמת יחיד: Event → Builder + template key + channels.
נתיב תבנית + subject/push ממולאים ב-Handler מ-EMAIL_MAP ו-PUSH_TEMPLATES.
"""

from app.domain.notifications.constants import NotificationEvent

from app.domain.notifications.core.builders.user_builder import UserBuilder
from app.domain.notifications.core.builders.ride_builder import RideBuilder
from app.domain.notifications.core.builders.booking_builder import BookingBuilder
from app.domain.notifications.core.builders.chat_builder import ChatBuilder


NOTIFICATION_STRATEGY = {
    # --- Auth & User Management ---
    # אחרי רישום שולחים רק מייל אימות (auth.email_verification) – ברוכים הבאים + קוד באותו מייל
    NotificationEvent.USER_REGISTERED: {
        "role": "self",
        "builder": UserBuilder(),
        "template": "welcome",
        "channels": [],  # לא מייל נפרד – התוכן מופיע במייל האימות
    },
    NotificationEvent.EMAIL_VERIFICATION: {
        "role": "self",
        "builder": UserBuilder(),
        "template": "email_verification",
        "channels": ["email"],
    },
    NotificationEvent.PASSWORD_RESET_REQUESTED: {
        "role": "self",
        "builder": UserBuilder(),
        "template": "password_reset_code",
        "channels": ["email"],
    },
    # --- Ride Lifecycle (Ride Object) ---
    NotificationEvent.RIDE_CREATED_FOR_PASSENGERS: {
        "role": "passenger",
        "builder": RideBuilder(),
        "template": "ride_created_for_passengers",
        "channels": ["email"],
    },
    NotificationEvent.RIDE_CANCELLED_BY_DRIVER: {
        "role": "passenger",
        "builder": RideBuilder(),
        "template": "ride_cancelled_by_driver",
        "channels": ["email", "push", "websocket"],
    },
    # --- Booking & Interaction (Booking Object) ---
    NotificationEvent.PASSENGER_JOIN_REQUEST: {
        "role": "driver",
        "builder": BookingBuilder(),
        "template": "new_ride_request",
        "channels": ["email", "push", "websocket"],
    },
    NotificationEvent.BOOKING_APPROVED_BY_DRIVER: {
        "role": "passenger",
        "builder": BookingBuilder(),
        "template": "booking_confirmed",
        "channels": ["email", "push", "websocket"],
    },
    NotificationEvent.BOOKING_REJECTED_BY_DRIVER: {
        "role": "passenger",
        "builder": BookingBuilder(),
        "template": "booking_rejected",
        "channels": ["email", "push", "websocket"],
    },
    # --- Reminders (מהסקדיולר) ---
    NotificationEvent.PICKUP_REMINDER_PASSENGER: {
        "role": "passenger",
        "builder": BookingBuilder(),
        "template": "reminder_passenger",
        "channels": ["email"],
    },
    NotificationEvent.RIDE_START_DRIVER: {
        "role": "driver",
        "builder": RideBuilder(),
        "template": "reminder_driver",
        "channels": ["email"],
    },
    # --- Chat ---
    NotificationEvent.CONVERSATION_COMPLETED: {
        "role": "both",  # שולח לשני המשתתפים
        "builder": ChatBuilder(),
        "template": "conversation_summary",
        "channels": ["email"],
    },
}
