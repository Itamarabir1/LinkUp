# app/infrastructure/websocket_bus.py
import logging

# התיקון הקריטי: ייבוא ישיר מהתשתית של רדיס
from app.infrastructure.redis.broadcast import broadcast

logger = logging.getLogger(__name__)


class WebSocketInfrastructure:
    """
    השכבה הטכנית ביותר.
    מתווכת בין ה-Drivers (כמו Redis) לבין ה-Services של ה-Domain.
    """

    @staticmethod
    async def get_subscriber(channel_name: str):
        """
        פותחת את הצינור הפיזי ל-Redis Pub/Sub.
        מחזירה אובייקט Context Manager של broadcaster.
        """
        try:
            # אנחנו מחזירים את ה-Context Manager עצמו
            return broadcast.subscribe(channel=channel_name)
        except Exception as e:
            logger.error(f"❌ Failed to create subscriber for channel {channel_name}: {e}")
            # כאן המקום להשתמש ב-LinkupError שלך אם תרצה לעטוף שגיאות תשתית
            raise


# ייצוא Singleton
ws_infra = WebSocketInfrastructure()
