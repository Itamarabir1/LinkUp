"""
מקור הידרציה לתזכורות מתוזמנות (ReminderScheduler).

חוזה payload (מול handler._fetch_source):
  scheduled_notification_id — מזהה רשומת scheduled_notifications
  user_id — הנמען (UUID)
  ride_id — הנסיעה לבניית קונטקסט תבנית (UUID)

כאשר שלושת השדות קיימים, ה-handler מחזיר ScheduledReminderSource במקום Ride גולמי,
כדי להפריד בין ישות התבנית (Ride + RideBuilder) לבין המשתמש שאליו שולחים.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.rides.model import Ride


@dataclass(frozen=True)
class ScheduledReminderSource:
    """Ride לתבנית; recipient_user_id לשליחה — בלי לכפות passenger resolver על Ride."""

    ride: Ride
    recipient_user_id: UUID
    scheduled_notification_id: UUID | None
