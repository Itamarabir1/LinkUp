import logging
from typing import Any
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import LinkUpError
from app.domain.bookings.crud import crud_booking

# Core, Mappings & Schemas
from app.domain.notifications.config.mappings import NOTIFICATION_STRATEGY
from app.domain.notifications.config.templates_map.email_conf import EMAIL_MAP
from app.domain.notifications.config.templates_map.push_conf import PUSH_TEMPLATES
from app.domain.notifications.constants import NotificationEvent
from app.domain.notifications.core.resolver import recipient_resolver
from app.domain.notifications.core.scheduled_reminder_source import ScheduledReminderSource
from app.domain.notifications.manager import (
    NotificationCommand,
    notification_manager,
)
from app.domain.passengers.crud import crud_passenger

# Domain Imports
from app.domain.rides.crud import crud_ride
from app.domain.users.crud import crud_user

logger = logging.getLogger(__name__)


class NotificationHandler:
    async def handle_event(self, db: AsyncSession, event_name: str, payload: dict):
        """
        Central entry: full notification lifecycle.
        Uses NotificationCommand for dispatch.
        """
        try:
            logger.info(
                "[NOTIF] Handler: start event=%s payload_keys=%s",
                event_name,
                list(payload.keys()) if isinstance(payload, dict) else "?",
            )
            event_key = self._resolve_event_key(event_name)
            if not event_key:
                return

            strategy = self._resolve_strategy(event_key)
            if not strategy:
                return

            source_data = await self._fetch_source(db, payload)
            if not source_data:
                logger.warning(
                    "[NOTIF] Handler: _fetch_source returned None (booking/ride not found?), skipping event=%s payload=%s",
                    event_key,
                    payload,
                )
                return

            if isinstance(source_data, ScheduledReminderSource):
                logger.info(
                    "[NOTIF] Handler: source_data=ScheduledReminderSource ride_id=%s recipient_user_id=%s",
                    getattr(source_data.ride, "ride_id", None),
                    source_data.recipient_user_id,
                )
            else:
                logger.info(
                    "[NOTIF] Handler: source_data loaded (booking_id=%s)",
                    getattr(source_data, "booking_id", payload.get("booking_id")),
                )

            resolved = await self._resolve_recipient(db, event_key, source_data, payload)
            context = self._build_context(event_key, source_data, strategy)
            context = self._enrich_context(event_key, context, payload, resolved)

            logger.info(
                "[NOTIF] Handler: recipient user_id=%s email=%s",
                getattr(resolved, "user_id", getattr(resolved, "id", None)) if resolved else None,
                getattr(resolved, "email", None) if resolved and not isinstance(resolved, dict) else None,
            )

            template_path = self._resolve_template(strategy, context)

            await self._dispatch(
                db,
                event_key,
                strategy,
                resolved,
                template_path,
                context,
                source_data,
            )

        except Exception as e:
            logger.error(f"❌ NotificationHandler Error [{event_name}]: {e!s}", exc_info=True)
            # When source_data is missing (e.g. stale message, booking_id not in DB), skip and ack – don't requeue
            if "Could not hydrate source data" in str(e):
                logger.warning(
                    "[NOTIF] Handler: skipping and acking message (stale/missing data) event=%s",
                    event_name,
                )
                return
            raise LinkUpError(f"Notification System Failure: {e!s}") from e

    def _resolve_event_key(self, event_name: str) -> NotificationEvent | None:
        """Map event string to NotificationEvent enum. Returns None if unknown."""
        try:
            return NotificationEvent(event_name)
        except ValueError:
            logger.warning("[NOTIF] Handler: event '%s' not registered. Skipping.", event_name)
            return None

    def _resolve_strategy(self, event_key: NotificationEvent) -> dict | None:
        """Load strategy blueprint. Returns None if missing."""
        strategy = NOTIFICATION_STRATEGY.get(event_key)
        if not strategy:
            logger.error("[NOTIF] Handler: no strategy for event=%s", event_key)
        return strategy

    async def _resolve_recipient(
        self,
        db: AsyncSession,
        event_key: NotificationEvent,
        source_data: Any,
        payload: dict,
    ) -> Any:
        """Resolve the user(s) to notify."""
        if isinstance(source_data, ScheduledReminderSource):
            return await crud_user.get(db, id=source_data.recipient_user_id)

        if payload.get("passenger_id") and event_key in (
            NotificationEvent.RIDE_CREATED_FOR_PASSENGERS,
            NotificationEvent.RIDE_CANCELLED_BY_DRIVER,
        ):
            pid = payload["passenger_id"]
            return await crud_user.get(db, id=UUID(str(pid)) if not isinstance(pid, UUID) else pid)

        return recipient_resolver.resolve(event_key, source_data)

    def _build_context(
        self,
        event_key: NotificationEvent,
        source_data: Any,
        strategy: dict,
    ) -> dict:
        """Build notification context from source_data via strategy builder."""
        builder = strategy["builder"]
        if isinstance(source_data, ScheduledReminderSource):
            return builder.build(source_data.ride, event_key.value)
        return builder.build(source_data, event_key.value)

    def _enrich_context(
        self,
        event_key: NotificationEvent,
        context: dict,
        payload: dict,
        resolved: Any,
    ) -> dict:
        """Merge code/token/user_name from payload into context; optional verify-email link."""
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        code_val = (
            context.get("code")
            or (data.get("code") if data else None)
            or (data.get("token") if data else None)
            or payload.get("code")
            or payload.get("token")
        )
        token_val = (
            context.get("token")
            or (data.get("token") if data else None)
            or (data.get("code") if data else None)
            or payload.get("token")
            or payload.get("code")
        )
        if code_val is not None:
            context["code"] = str(code_val)
        if token_val is not None:
            context["token"] = str(token_val)
        context["user_name"] = context.get("user_name") or (data.get("user_name") if data else None) or context.get("first_name", "")
        if event_key.value in ("auth.email_verification", "email_verification") and not context.get("code") and not context.get("token"):
            logger.warning(
                "⚠️ Email verification event without code/token in payload. Keys: %s",
                list(payload.keys()),
            )

        if event_key.value in ("auth.email_verification", "email_verification") and context.get("code") and not isinstance(resolved, dict):
            try:
                from app.core.config import settings

                api_base = (getattr(settings, "API_PUBLIC_URL", None) or "").rstrip("/")
                if api_base:
                    user = resolved
                    email_for_link = getattr(user, "email", None) if user else data.get("email", "")
                    if email_for_link:
                        context["action_url"] = (
                            f"{api_base}/api/v1/auth/verify-email/confirm?email={quote(email_for_link)}&code={quote(str(context['code']))}"
                        )
            except Exception:
                pass

        return context

    def _resolve_template(self, strategy: dict, context: dict) -> str:
        """Resolve template path and add subject/push fields to context."""
        template_key = strategy["template"]
        email_conf = EMAIL_MAP.get(template_key)
        push_conf = PUSH_TEMPLATES.get(template_key) if "push" in strategy.get("channels", []) else None
        if email_conf:
            context["subject"] = context.get("subject") or email_conf.get("subject", "Update from LinkUp")
        if push_conf:
            context["push_title"] = push_conf.get("title", "")
            context["push_body"] = push_conf.get("body", "")
        return email_conf["template"] if email_conf else template_key

    async def _dispatch(
        self,
        db: AsyncSession,
        event_key: NotificationEvent,
        strategy: dict,
        resolved: Any,
        template_path: str,
        context: dict,
        source_data: Any,
    ) -> None:
        """Build NotificationCommand and send via manager."""
        if isinstance(resolved, dict) and "user_id_1" in resolved and "user_id_2" in resolved:
            uid1 = resolved["user_id_1"]
            uid2 = resolved["user_id_2"]
            user1 = await crud_user.get(db, id=UUID(str(uid1)) if not isinstance(uid1, UUID) else uid1)
            user2 = await crud_user.get(db, id=UUID(str(uid2)) if not isinstance(uid2, UUID) else uid2)

            if user1:
                command1 = NotificationCommand(
                    event_key=event_key.value,
                    user=user1,
                    template=template_path,
                    channels=strategy.get("channels", ["email"]),
                    context={
                        **context,
                        "user_name": getattr(user1, "full_name", "") or getattr(user1, "first_name", ""),
                    },
                    db=db,
                )
                await notification_manager.process_and_send(command1)

            if user2:
                command2 = NotificationCommand(
                    event_key=event_key.value,
                    user=user2,
                    template=template_path,
                    channels=strategy.get("channels", ["email"]),
                    context={
                        **context,
                        "user_name": getattr(user2, "full_name", "") or getattr(user2, "first_name", ""),
                    },
                )
                await notification_manager.process_and_send(command2)

            logger.info(
                f"✅ Notification dispatched to both users: {event_key} -> user_id_1={resolved['user_id_1']}, user_id_2={resolved['user_id_2']}",
            )
            return

        user = resolved
        if not user:
            logger.warning(
                "⚠️ No recipient resolved for %s (source_data present: %s)",
                event_key.value,
                source_data is not None,
            )
            return
        if event_key == NotificationEvent.PASSENGER_JOIN_REQUEST:
            driver_email = getattr(user, "email", None) or ""
            if not (driver_email and "@" in driver_email):
                logger.warning(
                    "⚠️ booking.passenger_join_request: driver user_id=%s has no email; email will not be sent",
                    getattr(user, "user_id", None),
                )
        command = NotificationCommand(
            event_key=event_key.value,
            user=user,
            template=template_path,
            channels=strategy.get("channels", ["email"]),
            context=context,
            db=db,
        )
        logger.info(
            "[NOTIF] Handler: dispatching to manager event=%s user_id=%s",
            event_key.value,
            getattr(user, "user_id", None),
        )
        await notification_manager.process_and_send(command)
        logger.info(
            "[NOTIF] Handler: done event=%s -> %s",
            event_key.value,
            getattr(user, "email", "?"),
        )

    async def _fetch_source(self, db: AsyncSession, payload: dict) -> Any:
        """
        Load the relevant entity from DB from payload.
        For chat.conversation.completed, returns payload as-is (includes user_id_1, user_id_2).
        """
        # Chat events: return raw payload for the builder
        if payload.get("conversation_id") and payload.get("user_id_1") and payload.get("user_id_2"):
            return payload

        booking_id = payload.get("booking_id")
        ride_id = payload.get("ride_id")
        user_id = payload.get("user_id")
        passenger_id = payload.get("passenger_id")

        if booking_id is not None:
            try:
                bid = UUID(str(booking_id))
            except (TypeError, ValueError):
                bid = None
            if bid is not None:
                logger.info("[NOTIF] Handler: fetching booking_id=%s from DB", bid)
                booking = await crud_booking.get(db, id=bid)
                if not booking:
                    logger.warning("[NOTIF] Handler: no booking found for booking_id=%s", bid)
                return booking

        sched_raw = payload.get("scheduled_notification_id")
        if sched_raw and user_id and ride_id:
            try:
                sched_uuid = UUID(str(sched_raw))
                recipient_uuid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
                rid = UUID(str(ride_id)) if not isinstance(ride_id, UUID) else ride_id
            except (TypeError, ValueError) as e:
                logger.warning(
                    "[NOTIF] Handler: scheduled reminder payload UUID parse failed: %s keys=%s",
                    e,
                    list(payload.keys()),
                )
            else:
                ride = await crud_ride.get_for_notification(db, rid)
                if not ride:
                    logger.warning(
                        "[NOTIF] Handler: scheduled reminder ride not found ride_id=%s",
                        rid,
                    )
                else:
                    return ScheduledReminderSource(
                        ride=ride,
                        recipient_user_id=recipient_uuid,
                        scheduled_notification_id=sched_uuid,
                    )

        if ride_id:
            rid = UUID(str(ride_id)) if not isinstance(ride_id, UUID) else ride_id
            return await crud_ride.get_for_notification(db, rid)
        if passenger_id:
            pid = UUID(str(passenger_id)) if not isinstance(passenger_id, UUID) else passenger_id
            return await crud_passenger.get(db, id=pid)
        if user_id:
            uid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
            return await crud_user.get(db, id=uid)

        return payload


# Single instance for worker / API
notification_handler = NotificationHandler()
