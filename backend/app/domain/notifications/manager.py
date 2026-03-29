import asyncio
import logging
from typing import Any, Dict, List

from pydantic import BaseModel
from app.domain.notifications.providers.email_provider import EmailProvider
from app.domain.notifications.providers.push_provider import PushProvider
from app.domain.notifications.providers.websocket_provider import WebSocketProvider

logger = logging.getLogger(__name__)


# אובייקט הפקודה - החוזה בין ה-Handler למנג'ר
class NotificationCommand(BaseModel):
    user: Any  # אובייקט המשתמש שהגיע מה-Resolver
    template: str
    channels: List[str]
    context: Dict[str, Any]
    event_key: str


class NotificationManager:
    def __init__(self):
        # אתחול ה-Providers (Lazy loading עדיף במערכות גדולות, אבל זה מצוין להתחלה)
        self.providers = {
            "email": EmailProvider(),
            "push": PushProvider(),
            "websocket": WebSocketProvider(),
        }

    async def process_and_send(self, cmd: NotificationCommand):
        """
        הכניסה הראשית. מקבלת אובייקט פקודה ומפזרת לפרוויידרים.
        """
        email_provider = self.providers.get("email")
        can_email = email_provider.can_send(cmd.user) if email_provider else False
        logger.info(
            "[NOTIF] Manager: event=%s channels=%s user_id=%s can_send_email=%s",
            cmd.event_key,
            cmd.channels,
            getattr(cmd.user, "user_id", getattr(cmd.user, "id", "?")),
            can_email,
        )
        tasks = []
        for channel in cmd.channels:
            provider = self.providers.get(channel)

            # בדיקה: האם הפרוויידר קיים והאם המשתמש מאפשר שליחה בערוץ זה
            if provider and provider.can_send(cmd.user):
                tasks.append(self._safe_send(provider, channel, cmd))
            elif provider and not provider.can_send(cmd.user):
                logger.warning(
                    "ℹ️ Channel %s skipped for event %s: user has no valid email (user_id=%s)",
                    channel,
                    cmd.event_key,
                    getattr(cmd.user, "user_id", getattr(cmd.user, "id", "?")),
                )

        if not tasks:
            logger.info(f"ℹ️ No active channels to send for event {cmd.event_key}")
            return

        # שליחה מקבילית - פה הכוח של המערכת
        await asyncio.gather(*tasks)

    async def _safe_send(self, provider, channel_name, cmd: NotificationCommand):
        try:
            ctx = {**cmd.context, "event_key": cmd.event_key}
            await provider.send(cmd.user, cmd.template, ctx)
            logger.info(f"✅ {channel_name} sent to user_id={getattr(cmd.user, 'user_id', getattr(cmd.user, 'id', 'N/A'))}")
        except Exception as e:
            # אנחנו לא זורקים LinkupError כאן כדי לא להפיל ערוצים אחרים!
            logger.error(f"❌ {channel_name} failed for {cmd.event_key}: {str(e)}")


notification_manager = NotificationManager()
