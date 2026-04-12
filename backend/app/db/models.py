# app/db/models.py
# No logic here — registers domain models needed for API loading and relationships.
# Not intended to export every possible model in the repo (e.g. internal infra models).
# Must be imported before SQLAlchemy resolves string-based relationships (e.g. User.owned_groups).

from app.domain.bookings.model import Booking
from app.domain.groups.model import Group, GroupMember
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.scheduled_notifications.model import ScheduledNotification
from app.domain.users.model import User

__all__ = ["Booking", "Group", "GroupMember", "PassengerRequest", "Ride", "ScheduledNotification", "User"]
