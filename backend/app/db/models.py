# app/db/models.py
# הקובץ הזה לא מכיל לוגיקה; הוא רושם את מודלי הדומיין שנדרשים לטעינת ה-API וה-relationships.
# אין כאן כוונה לייצא "כל מודל אפשרי" בריפו (למשל מודלי תשתית פנימיים).
# חייב להיות מיובא לפני ש-SQLAlchemy פותר relationship מחרוזות (למשל ב-User.owned_groups)

from app.domain.bookings.model import Booking
from app.domain.groups.model import Group, GroupMember
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.scheduled_notifications.model import ScheduledNotification
from app.domain.users.model import User

__all__ = ["Booking", "Group", "GroupMember", "PassengerRequest", "Ride", "ScheduledNotification", "User"]
