# app/domain/notifications/core/builders/user_builder.py
from typing import Any

from .base import BaseContextBuilder


class UserBuilder(BaseContextBuilder):
    """
    מטפל באירועים שבהם המקור (Source) הוא אובייקט User.
    אירועים לדוגמה: USER_REGISTERED, PASSWORD_RESET_REQUESTED, EMAIL_VERIFICATION.
    """

    def build(self, user: Any, event_key: str) -> dict[str, Any]:
        # 1. חילוץ נתוני בסיס מהמשתמש (באופן בטוח)
        first_name = getattr(user, "first_name", "אורח/ת")
        user_email = getattr(user, "email", "")

        context = {
            "first_name": first_name,
            "user_email": user_email,
            "color": self._determine_color(event_key),
            "support_email": "support@itamarabir.com",
        }

        # 2. מיפוי תוכן לפי סוג האירוע
        event_content_map = {
            "registered": {
                "subject": f"ברוך הבא ל-Linkup, {first_name}!",
                "hero_text": "שמחים שהצטרפת אלינו",
                "description": "חשבונך נוצר בהצלחה. עכשיו אפשר להתחיל לחפש טרמפים או להציע נסיעות משלך.",
                "cta_label": "מעבר לפרופיל שלי",
                "cta_path": "/profile",
            },
            "password": {
                "subject": "שחזור סיסמה - Linkup",
                "hero_text": "איפוס סיסמה",
                "description": "קיבלנו בקשה לאיפוס הסיסמה שלך. אם לא ביקשת זאת, אפשר להתעלם מהמייל.",
                "cta_label": "בחר סיסמה חדשה",
                "cta_path": "/reset-password",  # במציאות כאן יבוא טוקן
            },
            "verify": {
                "subject": "אמת את כתובת המייל שלך",
                "hero_text": "רק עוד צעד אחד...",
                "description": "כדי שנוכל להתחיל לעבוד, אנחנו צריכים לוודא שכתובת המייל הזו אכן שייכת לך.",
                "cta_label": "אמת מייל עכשיו",
                "cta_path": "/verify-email",
            },
        }

        # 3. התאמת התוכן
        matched_content = next(
            (content for key, content in event_content_map.items() if key in event_key.lower()),
            self._get_default_content(),
        )

        # 4. בניית ה-URL הסופי ל-CTA
        context.update(matched_content)
        context["action_url"] = self._get_cta_url(matched_content.get("cta_path", ""))

        return context

    def _get_default_content(self) -> dict[str, str]:
        return {
            "subject": "עדכון מחשבון Linkup",
            "hero_text": "עדכון מערכת",
            "description": "שלום, יש לנו עדכון לגבי החשבון שלך במערכת.",
            "cta_label": "כניסה לאתר",
            "cta_path": "/",
        }
