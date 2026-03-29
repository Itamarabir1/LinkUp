import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _get_base_url_for_links() -> str:
    """
    בסיס ללינקים במייל – משתמש ב-FRONTEND_URL.
    חשוב: כדי שלחיצה על הקישור במייל (מהטלפון) תפתח את האפליקציה בלי אזהרת אבטחה,
    הגדר ב-.env את FRONTEND_URL לכתובת הציבורית של האפליקציה עם HTTPS תקין (למשל https://linkup.co.il).
    """
    try:
        from app.core.config import settings

        base = getattr(settings, "FRONTEND_URL", "") or "https://linkup.co.il"
        base = (base or "").strip().rstrip("/")
        if not base:
            return "https://linkup.co.il"
        # קישורים במייל חייבים HTTPS כדי שלא יופיע "החיבור שלך פרטי" (מלבד localhost לפיתוח)
        if base.startswith("http://") and "localhost" not in base and "127.0.0.1" not in base:
            base = "https://" + base[7:]
        return base
    except Exception:
        return "https://linkup.co.il"


class BaseContextBuilder(ABC):
    """
    Abstract Base Class for all Context Builders.
    Senior approach: Supports SQLAlchemy Models, Pydantic Schemas, and Dicts.
    """

    BASE_URL = "https://itamarabir.com"

    # שימוש ב-Hex Codes - חובה למיילים (Gmail/Outlook לא תמיד אוהבים "red")
    COLOR_SUCCESS = "#28a745"  # ירוק
    COLOR_DANGER = "#dc3545"  # אדום
    COLOR_INFO = "#17a2b8"  # כחול

    @abstractmethod
    def build(self, data: Union[BaseModel, Any], event_key: str) -> Dict[str, Any]:
        """
        החוזה המחייב: מקבל נתונים (סכמה או אובייקט DB) ומחזיר מילון לעיבוד טמפלייט.
        """
        pass

    # --- Utility Methods (Protected) ---

    def _resolve_attr(self, obj: Any, path: str, default: Any = "") -> Any:
        """
        Safe Navigation Utility.
        סניור תומך גם ב-getattr (אובייקט) וגם ב-get (מילון/סכמה).
        דוגמה: 'ride.driver.full_name' יעבוד גם אם זה Dict וגם אם זה Model.
        """
        if obj is None:
            return default

        current = obj
        try:
            for attr in path.split("."):
                if isinstance(current, dict):
                    current = current.get(attr)
                elif isinstance(current, BaseModel):
                    current = getattr(current, attr, None)
                else:
                    current = getattr(current, attr, None)

                if current is None:
                    return default
            return current
        except Exception as e:
            logger.debug(f"🔍 Path resolution failed for {path}: {e}")
            return default

    def _format_date(self, dt: Any) -> str:
        """Standardized date formatting for the entire notification system."""
        if isinstance(dt, datetime):
            return dt.strftime("%d/%m/%Y %H:%M")
        return str(dt) if dt else "N/A"

    def _determine_color(self, event_key: Optional[str]) -> str:
        """Visual logic shared across all notification types using professional hex codes."""
        if not event_key:
            return self.COLOR_SUCCESS

        danger_keywords = {"cancel", "reject", "fail", "delete", "stop", "urgent"}
        event_lower = event_key.lower()

        if any(word in event_lower for word in danger_keywords):
            return self.COLOR_DANGER

        return self.COLOR_SUCCESS

    def _get_cta_url(self, path: str) -> str:
        """בונה לינק לכפתור במייל – משתמש ב-FRONTEND_URL כדי שהלינק יפתח את האפליקציה."""
        clean_path = path.lstrip("/")
        base = _get_base_url_for_links()
        return f"{base.rstrip('/')}/{clean_path}" if base else f"{self.BASE_URL}/{clean_path}"
