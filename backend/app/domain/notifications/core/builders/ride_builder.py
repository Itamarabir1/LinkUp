from typing import Any

from .base import BaseContextBuilder


class RideBuilder(BaseContextBuilder):
    """
    Senior Implementation: Uses declarative mapping instead of imperative if/else.
    """

    def build(self, ride: Any, event_key: str = "") -> dict[str, Any]:
        # 1. הכנת נתוני הבסיס (הזרקה לכל סוגי ההודעות)
        driver_name = self._resolve_attr(ride, "driver.first_name", "נהג")
        origin = getattr(ride, "origin_name", "N/A")
        destination = getattr(ride, "destination_name", "N/A")
        ride_date = self._format_date(getattr(ride, "departure_time", None))

        ride_id = getattr(ride, "ride_id", None) or getattr(ride, "id", "")
        context = {
            "ride_id": ride_id,
            "origin": origin,
            "destination": destination,
            "ride_date": ride_date,
            "driver_name": driver_name,
            "ride_url": self._get_cta_url(f"rides/{ride_id}"),
            "color": self._determine_color(event_key),
        }

        # 2. מיפוי התוכן לפי אירוע (במקום if/else)
        # זה מאפשר להוסיף 20 אירועים בלי לשנות את הלוגיקה של הפונקציה
        event_content_map = {
            "created_for_passengers": {
                "subject": "נסיעה חדשה שמתאימה לך",
                "hero_text": "נסיעה חדשה בדרך",
                "description": f"נרשמה נסיעה מ{origin} ל{destination}, יוצאת ב{ride_date}. הנהג: {driver_name}. לחץ להצטרפות.",
                "cta_label": "לצפייה בנסיעה ובקשת הצטרפות",
            },
            "cancelled": {
                "subject": "עדכון חשוב: הנסיעה בוטלה",
                "hero_text": "הנסיעה בוטלה",
                "description": f"מצטערים, הנסיעה מ{origin} ל{destination} בוטלה על ידי {driver_name}.",
                "cta_label": "חפש נסיעה חלופית",
            },
            "reminder": {
                "subject": "תזכורת: הנסיעה שלך מתקרבת!",
                "hero_text": "יוצאים לדרך בקרוב",
                "description": f"תזכורת: הנסיעה מ{origin} מחכה לך ב-{ride_date}.",
                "cta_label": "צפה בפרטי הנסיעה",
            },
            "ride_start_driver": {
                "subject": "תזכורת: זמן לצאת לנסיעה",
                "hero_text": "יוצאים לדרך בקרוב",
                "description": f"תזכורת לנהג: הנסיעה מ{origin} ל{destination} ב-{ride_date}.",
                "cta_label": "צפה בפרטי הנסיעה",
            },
        }

        # 3. חילוץ התוכן המתאים או שימוש בברירת מחדל
        # אנחנו מחפשים מילת מפתח בתוך ה-event_key (כמו cancelled או reminder)
        event_key_lower = (event_key or "").lower()
        matched_content = next(
            (content for key, content in event_content_map.items() if key in event_key_lower),
            self._get_default_content(),
        )

        return {**context, **matched_content}

    def _get_default_content(self) -> dict[str, str]:
        return {
            "subject": "עדכון לגבי נסיעה ב-Linkup",
            "hero_text": "עדכון נסיעה",
            "description": "חלו שינויים בפרטי הנסיעה שלך.",
            "cta_label": "לפרטים נוספים",
        }
