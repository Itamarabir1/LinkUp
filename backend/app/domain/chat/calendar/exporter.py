"""
ייצוא טרמפים לקובצי iCal (.ics).
"""

from datetime import datetime
from typing import List, Optional

from ..ai.schema import RideSummary
from .builder import create_calendar_from_rides


def export_to_ical(rides: list[RideSummary], output_path: str, base_date: datetime | None = None) -> bool:
    """
    מייצא רשימת טרמפים לקובץ iCal (.ics).

    Args:
        rides: רשימת RideSummary
        output_path: נתיב לקובץ הפלט
        base_date: תאריך בסיס לחישוב תאריכים

    Returns:
        True אם הצליח, False אחרת
    """
    try:
        cal = create_calendar_from_rides(rides, base_date)

        with open(output_path, "wb") as f:
            f.write(cal.to_ical())

        return True
    except Exception as e:
        print(f"שגיאה ביצירת קובץ לוח שנה: {e}")
        return False


def export_rides_to_ical_bytes(rides: list[RideSummary], base_date: datetime | None = None) -> bytes:
    """
    מייצא רשימת טרמפים ל-bytes של קובץ iCal (.ics).

    Args:
        rides: רשימת RideSummary
        base_date: תאריך בסיס לחישוב תאריכים

    Returns:
        bytes של קובץ iCal
    """
    from .builder import create_calendar_from_rides

    cal = create_calendar_from_rides(rides, base_date)
    return cal.to_ical()


def export_batch_to_ical(
    rides_groups: list[list[RideSummary]],
    output_paths: list[str],
    base_date: datetime | None = None,
) -> list[bool]:
    """
    מייצא מספר קבוצות של טרמפים לקבצי iCal נפרדים.

    Args:
        rides_groups: רשימת קבוצות טרמפים
        output_paths: רשימת נתיבים לקבצי פלט (חייב להיות אותו אורך)
        base_date: תאריך בסיס לחישוב תאריכים

    Returns:
        רשימת bool — True לכל קובץ שיוצא בהצלחה
    """
    if len(rides_groups) != len(output_paths):
        raise ValueError("rides_groups and output_paths must have the same length")
    return [export_to_ical(rides, path, base_date) for rides, path in zip(rides_groups, output_paths)]
