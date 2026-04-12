import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _get_base_url_for_links() -> str:
    """
    Base URL for email links — uses FRONTEND_URL.
    For mobile mail clients to open the app without security warnings, set FRONTEND_URL
    in .env to the public HTTPS app URL (e.g. https://linkup.co.il).
    """
    try:
        from app.core.config import settings

        base = getattr(settings, "FRONTEND_URL", "") or "https://linkup.co.il"
        base = (base or "").strip().rstrip("/")
        if not base:
            return "https://linkup.co.il"
        # Email links should use HTTPS to avoid "connection not private" (except localhost dev)
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

    # Hex colors — reliable in email clients (named CSS colors are flaky)
    COLOR_SUCCESS = "#28a745"  # green
    COLOR_DANGER = "#dc3545"  # red
    COLOR_INFO = "#17a2b8"  # blue

    @abstractmethod
    def build(self, data: BaseModel | Any, event_key: str) -> dict[str, Any]:
        """
        Contract: accept schema or DB object, return dict for template rendering.
        """
        pass

    # --- Utility Methods (Protected) ---

    def _resolve_attr(self, obj: Any, path: str, default: Any = "") -> Any:
        """
        Safe navigation: getattr on objects, .get on dicts/schemas.
        Example: 'ride.driver.full_name' works for dict or ORM model.
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

    def _determine_color(self, event_key: str | None) -> str:
        """Visual logic shared across all notification types using professional hex codes."""
        if not event_key:
            return self.COLOR_SUCCESS

        danger_keywords = {"cancel", "reject", "fail", "delete", "stop", "urgent"}
        event_lower = event_key.lower()

        if any(word in event_lower for word in danger_keywords):
            return self.COLOR_DANGER

        return self.COLOR_SUCCESS

    def _get_cta_url(self, path: str) -> str:
        """Build mail CTA URL from FRONTEND_URL so links open the web app."""
        clean_path = path.lstrip("/")
        base = _get_base_url_for_links()
        return f"{base.rstrip('/')}/{clean_path}" if base else f"{self.BASE_URL}/{clean_path}"
