import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.notifications.providers.email_provider import EmailProvider
from app.domain.notifications.providers.push_provider import PushProvider
from app.domain.notifications.providers.websocket_provider import WebSocketProvider

logger = logging.getLogger(__name__)


# Command object — contract between Handler and Manager
class NotificationCommand(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: Any  # User object from Resolver
    template: str
    channels: list[str]
    context: dict[str, Any]
    event_key: str
    db: Any | None = None  # AsyncSession — Any to avoid Pydantic complexity


class NotificationManager:
    def __init__(self):
        # Provider registry (lazy loading scales better; eager init is fine here)
        self.providers = {
            "email": EmailProvider(),
            "push": PushProvider(),
            "websocket": WebSocketProvider(),
        }

    async def process_and_send(self, cmd: NotificationCommand):
        """
        Main entry: takes a command and fans out to providers.
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

            # Skip if provider missing or user cannot use this channel
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

        # Parallel send — main strength of this design
        await asyncio.gather(*tasks)

    async def _safe_send(self, provider, channel_name, cmd: NotificationCommand):
        try:
            ctx = {**cmd.context, "event_key": cmd.event_key}
            await provider.send(cmd.user, cmd.template, ctx, db=cmd.db)
            logger.info(f"✅ {channel_name} sent to user_id={getattr(cmd.user, 'user_id', getattr(cmd.user, 'id', 'N/A'))}")
        except Exception as e:
            # Do not re-raise — other channels should still complete
            logger.error(f"❌ {channel_name} failed for {cmd.event_key}: {e!s}")


notification_manager = NotificationManager()
