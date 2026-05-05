import logging
from typing import Any

from firebase_admin.messaging import SenderIdMismatchError, UnregisteredError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications.channels.push.client import fcm_client
from app.domain.notifications.channels.push.render import render_push_content
from app.domain.notifications.providers.base import BaseNotificationProvider
from app.domain.users.crud import crud_user
from app.domain.users.model import User

logger = logging.getLogger(__name__)


class PushProvider(BaseNotificationProvider):
    def can_send(self, user: User) -> bool:
        return bool(user and user.fcm_token)

    async def send(
        self,
        user: User,
        template_name: str,
        context: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> None:
        if not user or not getattr(user, "fcm_token", None):
            logger.warning("⚠️ Push skipped: no user or fcm_token")
            return

        try:
            title, body = render_push_content(
                {
                    "title": context.get("push_title", "עדכון מ-LinkUp"),
                    "body": context.get("push_body", ""),
                },
                **context,
            )

            data = {key: str(context[key]) for key in ("ride_id", "booking_id", "event_key") if context.get(key) is not None}

            await fcm_client.send(user.fcm_token, title, body, data or None)
            logger.info("✅ Push sent to user_id=%s", getattr(user, "user_id", "N/A"))

        except (UnregisteredError, SenderIdMismatchError):
            uid = getattr(user, "user_id", "N/A")
            logger.warning("🗑️ Invalid FCM token for user_id=%s — clearing from DB", uid)
            if db is not None:
                await crud_user.update_fcm_token(db, user=user, token=None)
            raise

        except Exception as e:
            logger.error("❌ Push failed for user_id=%s: %s", getattr(user, "user_id", "N/A"), e)
            raise
