"""
יצירת לוח שנה (Calendar) מטרמפים.
"""

from datetime import datetime
from typing import List, Optional

from icalendar import Calendar

from ..ai.schema import RideSummary
from .event import create_calendar_event


def create_calendar_from_rides(rides: list[RideSummary], base_date: datetime | None = None) -> Calendar:
    """
    יוצר לוח שנה (Calendar) מרשימת טרמפים.

    Args:
        rides: רשימת RideSummary
        base_date: תאריך בסיס לחישוב תאריכים

    Returns:
        Calendar object עם כל האירועים
    """
    cal = Calendar()
    cal.add("prodid", "-//LinkUp//Calendar//HE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("X-WR-CALNAME", "טרמפים - LinkUp")
    cal.add("X-WR-CALDESC", "אירועי טרמפ שנוצרו מ-LinkUp")
    cal.add("X-WR-TIMEZONE", "Asia/Jerusalem")

    for ride in rides:
        event = create_calendar_event(ride, base_date)
        if event:
            cal.add_component(event)

    return cal
