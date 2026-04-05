# app/infrastructure/events/publishers/base.py
from abc import ABC, abstractmethod

from app.domain.events.model import DispatchTarget, Event  # תיקון הנתיב ל-Domain


class EventPublisher(ABC):
    """
    Interface (Base Class) לכל מפיצי האירועים במערכת.
    מגדיר חוזה אחיד כך שהדיספצר יוכל לעבוד עם כולם בצורה גנרית.
    """

    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """
        שולח את האירוע ליעד הספציפי.
        מחזיר True אם השליחה הצליחה, אחרת זורק שגיאה או מחזיר False.
        """
        pass

    @abstractmethod
    def supports_target(self, target: DispatchTarget) -> bool:
        """
        בודק האם הפבלישר הזה יודע לטפל ביעד מסוים (למשל RABBITMQ).
        """
        pass
