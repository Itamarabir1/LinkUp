"""
Hydration source for scheduled reminders (ReminderScheduler).

Payload contract (for handler._fetch_source):
  scheduled_notification_id — scheduled_notifications row id
  user_id — recipient (UUID)
  ride_id — ride used to build template context (UUID)

When all three fields are present, the handler returns ScheduledReminderSource instead of a raw Ride,
to separate template entity (Ride + RideBuilder) from the user who receives the notification.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.rides.model import Ride


@dataclass(frozen=True)
class ScheduledReminderSource:
    """Ride for template context; recipient_user_id for delivery — without forcing passenger resolver on Ride."""

    ride: Ride
    recipient_user_id: UUID
    scheduled_notification_id: UUID | None
