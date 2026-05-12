# app/db/models.py
# No logic here — registers domain models needed for API loading and relationships.
# Not intended to export every possible model in the repo (e.g. internal infra models).
# Must be imported before SQLAlchemy resolves string-based relationships (e.g. User.owned_groups).

from app.domain.bookings.model import Booking
from app.domain.billing.model import IdempotencyKey, Payment
from app.domain.groups.model import Group, GroupMember
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.notifications.model import NotificationRead
from app.domain.scheduled_notifications.model import ScheduledNotification
from app.domain.users.model import User
from app.infrastructure.audit.model import AuditLog

__all__ = [
    "AuditLog",
    "Booking",
    "Group",
    "GroupMember",
    "IdempotencyKey",
    "NotificationRead",
    "PassengerRequest",
    "Payment",
    "Ride",
    "ScheduledNotification",
    "User",
]
