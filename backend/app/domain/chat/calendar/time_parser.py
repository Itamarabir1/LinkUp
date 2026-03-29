"""
פרסור זמן בעברית לאובייקט datetime.
"""

from datetime import datetime, timedelta
from typing import Optional
import re


def parse_hebrew_time(time_str: str, base_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    מפרסר זמן בעברית (למשל "08:00", "16:00", "מחר ב-08:00") לאובייקט datetime.

    Args:
        time_str: מחרוזת זמן בעברית
        base_date: תאריך בסיס לחישוב (אם לא מוגדר, משתמש בתאריך הנוכחי)

    Returns:
        datetime object או None אם לא ניתן לפרסר
    """
    if not time_str or time_str == "לא צוין":
        return None

    if base_date is None:
        base_date = datetime.now()

    # ניקוי המחרוזת
    time_str = time_str.strip()

    # חיפוש תאריך - "מחר", "היום", "מחרתיים"
    days_offset = 0
    if "מחר" in time_str:
        days_offset = 1
        time_str = time_str.replace("מחר", "").strip()
    elif "מחרתיים" in time_str:
        days_offset = 2
        time_str = time_str.replace("מחרתיים", "").strip()
    elif "היום" in time_str:
        days_offset = 0
        time_str = time_str.replace("היום", "").strip()

    # חיפוש יום בשבוע - "בראשון", "בשני", וכו'
    weekday_map = {
        "ראשון": 6,  # Sunday
        "שני": 0,  # Monday
        "שלישי": 1,  # Tuesday
        "רביעי": 2,  # Wednesday
        "חמישי": 3,  # Thursday
        "שישי": 4,  # Friday
        "שבת": 5,  # Saturday
    }

    for day_name, weekday_num in weekday_map.items():
        if day_name in time_str:
            # חישוב יום בשבוע הבא
            current_weekday = base_date.weekday()
            days_until = (weekday_num - current_weekday) % 7
            if days_until == 0:
                days_until = 7  # אם היום הוא היום, קח את השבוע הבא
            days_offset = days_until
            time_str = re.sub(rf"ב?{day_name}\s*", "", time_str).strip()
            break

    # חיפוש שעה בפורמט HH:MM או HH:MM:SS
    time_match = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if not time_match:
        return None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    second = int(time_match.group(3)) if time_match.group(3) else 0

    # חיפוש "בוקר", "צהריים", "ערב" לתיקון שעה
    if "בוקר" in time_str or 'אחה"צ' in time_str or "אחר הצהריים" in time_str:
        # אם השעה קטנה מ-12, זה בבוקר/אחר הצהריים
        pass
    elif "ערב" in time_str or "לילה" in time_str:
        # אם השעה קטנה מ-12, זה בערב
        if hour < 12:
            hour += 12

    # חישוב התאריך הסופי
    target_date = base_date + timedelta(days=days_offset)
    target_datetime = target_date.replace(hour=hour, minute=minute, second=second, microsecond=0)

    return target_datetime
