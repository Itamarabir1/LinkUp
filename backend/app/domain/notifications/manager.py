import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.notifications.exceptions import (
    PermanentNotificationError,
    TransientNotificationError,
)
from app.domain.notifications.providers.email_provider import EmailProvider
from app.domain.notifications.providers.push_provider import PushProvider
from app.domain.notifications.providers.websocket_provider import WebSocketProvider

logger = logging.getLogger(__name__)

DEDUP_TTL_SECONDS = 86400  # 24 h


class NotificationCommand(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: Any
    template: str
    channels: list[str]
    context: dict[str, Any]
    event_key: str
    db: Any | None = None


class NotificationManager:
    def __init__(self):
        self.providers = {
            "email": EmailProvider(),
            "push": PushProvider(),
            "websocket": WebSocketProvider(),
        }

    async def _dedup_key(self, cmd: NotificationCommand) -> str | None:
        """Build a dedup key; returns None if not enough info to deduplicate."""
        user_id = getattr(cmd.user, "user_id", getattr(cmd.user, "id", None))
        msg_id = cmd.context.get("message_id") or cmd.context.get("booking_id") or cmd.context.get("ride_id")
        if not user_id or not msg_id:
            return None
        return f"notif_dedup:{cmd.event_key}:{user_id}:{msg_id}"

    async def _is_duplicate(self, key: str) -> bool:
        """Check Redis; fail-open (False) if Redis is unreachable."""
        try:
            from app.infrastructure.redis.client import redis_client

            if redis_client.client is None:
                return False
            return bool(await redis_client.client.exists(key))
        except Exception as e:
            logger.warning("Dedup check failed key=%s: %s — sending anyway", key, e)
            return False

    async def _mark_sent(self, key: str) -> None:
        try:
            from app.infrastructure.redis.client import redis_client

            if redis_client.client is None:
                return
            await redis_client.client.set(key, "1", ex=DEDUP_TTL_SECONDS)
        except Exception as e:
            logger.warning("Dedup mark failed key=%s: %s", key, e)

    async def process_and_send(self, cmd: NotificationCommand):
        """
        Fan out to providers in parallel.  Permanent errors are logged and
        swallowed; transient errors are collected and re-raised so the
        RabbitMQ consumer can nack → broker retry.
        """
        user_id = getattr(cmd.user, "user_id", getattr(cmd.user, "id", "?"))
        email_provider = self.providers.get("email")
        can_email = email_provider.can_send(cmd.user) if email_provider else False
        logger.info(
            "[NOTIF] Manager: event=%s channels=%s user_id=%s can_send_email=%s",
            cmd.event_key,
            cmd.channels,
            user_id,
            can_email,
        )

        dedup_key = await self._dedup_key(cmd)
        if dedup_key and await self._is_duplicate(dedup_key):
            logger.info("[NOTIF] Duplicate skipped: %s", dedup_key)
            return

        tasks = []
        channel_names: list[str] = []
        for channel in cmd.channels:
            provider = self.providers.get(channel)
            if provider and provider.can_send(cmd.user):
                tasks.append(self._safe_send(provider, channel, cmd))
                channel_names.append(channel)
            elif provider and not provider.can_send(cmd.user):
                logger.warning(
                    "Channel %s skipped for event %s: user cannot receive (user_id=%s)",
                    channel,
                    cmd.event_key,
                    user_id,
                )

        if not tasks:
            logger.info("No active channels to send for event %s", cmd.event_key)
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)

        transient_failures: list[str] = []
        for ch_name, result in zip(channel_names, results):
            if result is None:
                continue
            if isinstance(result, PermanentNotificationError):
                logger.warning(
                    "[NOTIF] %s permanent failure for %s (user_id=%s): %s",
                    ch_name,
                    cmd.event_key,
                    user_id,
                    result,
                )
            elif isinstance(result, TransientNotificationError):
                transient_failures.append(f"{ch_name}: {result}")
            elif isinstance(result, BaseException):
                transient_failures.append(f"{ch_name}: {result}")

        if transient_failures:
            raise TransientNotificationError(
                f"{len(transient_failures)} channel(s) failed transiently for "
                f"event={cmd.event_key} user_id={user_id}: " + "; ".join(transient_failures)
            )

        if dedup_key:
            await self._mark_sent(dedup_key)

    async def _safe_send(self, provider, channel_name: str, cmd: NotificationCommand):
        """Run a single provider; returns None on success, exception instance on failure."""
        try:
            ctx = {**cmd.context, "event_key": cmd.event_key}
            await provider.send(cmd.user, cmd.template, ctx, db=cmd.db)
            logger.info(
                "%s sent to user_id=%s",
                channel_name,
                getattr(cmd.user, "user_id", getattr(cmd.user, "id", "N/A")),
            )
            return None
        except (PermanentNotificationError, TransientNotificationError):
            raise
        except Exception as exc:
            logger.error(
                "%s unexpected error for user_id=%s: %s",
                channel_name,
                getattr(cmd.user, "user_id", getattr(cmd.user, "id", "N/A")),
                exc,
            )
            raise TransientNotificationError(f"{channel_name}: unexpected error: {exc}") from exc


notification_manager = NotificationManager()
