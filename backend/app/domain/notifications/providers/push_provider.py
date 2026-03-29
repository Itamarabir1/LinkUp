import logging
from typing import Dict, Any
from app.domain.notifications.providers.base import BaseNotificationProvider
from app.domain.notifications.channels.push.client import fcm_client
from app.domain.notifications.channels.push.render import render_push_content
from app.domain.users.model import User

logger = logging.getLogger(__name__)


class PushProvider(BaseNotificationProvider):
    def can_send(self, user: User) -> bool:
        return bool(user and user.fcm_token)

    async def send(self, user: User, template_name: str, context: Dict[str, Any]):
        if not user or not getattr(user, "fcm_token", None):
            logger.warning("⚠️ Push skipped: no user or fcm_token")
            return
        try:
            title_tpl = context.get("push_title", "עדכון מ-LinkUp")
            body_tpl = context.get("push_body", "")
            title, body = render_push_content({"title": title_tpl, "body": body_tpl}, **context)
            # נתונים נוספים לאפליקציה (FCM דורש מפתחות וערכים כ-string)
            data = {}
            for key in ("ride_id", "booking_id", "event_key"):
                if key in context and context[key] is not None:
                    data[key] = str(context[key])
            await fcm_client.send(user.fcm_token, title, body, data or None)
            logger.info(f"✅ Push sent to user_id={getattr(user, 'user_id', 'N/A')}")
        except Exception as e:
            self._handle_push_error(e, user)
            raise

    def _handle_push_error(self, e: Exception, user: User):
        err_str = str(e).lower()
        uid = getattr(user, "user_id", None) or getattr(user, "id", "N/A")
        if "not-registered" in err_str or "invalid" in err_str or "unregistered" in err_str:
            logger.warning(f"🗑️ Invalid/expired FCM token for user_id={uid}")
            # כאן אפשר לקרוא ל-CRUD ולאפס user.fcm_token ל-None
        else:
            logger.error(f"❌ Push failed for user_id={uid}: {e}")
