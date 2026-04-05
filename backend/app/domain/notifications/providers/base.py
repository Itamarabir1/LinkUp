from abc import ABC, abstractmethod
from typing import Any


class BaseNotificationProvider(ABC):
    """
    ממשק שמגדיר איך 'ספק' נראה במערכת LinkUp.
    זה לא פלסטר, זה החוזה הארכיטקטוני.
    """

    @abstractmethod
    async def send(self, user: Any, channel_config: dict[str, Any], context: dict[str, Any]) -> None:
        """חובה לממש לוגיקת שליחה אסינכרונית"""
        pass

    def can_send(self, user: Any) -> bool:
        """ברירת מחדל: תמיד אפשר לשלוח. ספקים ספציפיים ידרסו את זה."""
        return True
