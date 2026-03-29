"""
יצירת אירועי לוח שנה מטרמפים.
"""

from datetime import datetime, timedelta
from typing import Optional

from icalendar import Event

from ..ai.schema import RideSummary
from .time_parser import parse_hebrew_time


def create_calendar_event(ride: RideSummary, base_date: Optional[datetime] = None) -> Optional[Event]:
    """
    יוצר אירוע לוח שנה מטרמפ.

    Args:
        ride: RideSummary עם פרטי הטרמפ
        base_date: תאריך בסיס לחישוב תאריכים

    Returns:
        Event object או None אם לא ניתן ליצור אירוע
    """
    # פרסור זמן המפגש
    meeting_datetime = parse_hebrew_time(ride.meeting_time, base_date)
    if not meeting_datetime:
        return None

    # יצירת אירוע
    event = Event()
    event.add("summary", f"טרמפ: {ride.driver_name} → {ride.passenger_name}")
    event.add("dtstart", meeting_datetime)

    # משך האירוע - שעה אחת (ניתן לשנות)
    event.add("dtend", meeting_datetime + timedelta(hours=1))

    # תיאור האירוע
    description_parts = [
        f"נהג: {ride.driver_name}",
        f"נוסע: {ride.passenger_name}",
        f"מיקום איסוף: {ride.pickup_location}",
        f"זמן מפגש: {ride.meeting_time}",
        "",
        f"סיכום: {ride.summary_hebrew}",
    ]
    event.add("description", "\n".join(description_parts))

    # מיקום
    if ride.pickup_location and ride.pickup_location != "לא צוין":
        event.add("location", ride.pickup_location)

    # זמן יצירה
    event.add("dtstamp", datetime.now())

    # מזהה ייחודי לאירוע
    event.add(
        "uid",
        f"linkup-{ride.driver_name}-{ride.passenger_name}-{meeting_datetime.isoformat()}",
    )

    return event
