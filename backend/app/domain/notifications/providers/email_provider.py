import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.infrastructure import EmailProviderCircuitOpenError
from app.domain.notifications.channels.email.client import email_client
from app.domain.notifications.channels.email.renderer import render_email_template
from app.domain.notifications.exceptions import (
    PermanentNotificationError,
    TransientNotificationError,
)
from app.domain.notifications.providers.base import BaseNotificationProvider
from app.domain.users.model import User

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):
    def _render_subject(self, subject: str, context: dict[str, Any]) -> str:
        """Replace subject placeholders (e.g. {passenger_name}) with context values."""
        if not subject or "{" not in subject:
            return subject or "Update from LinkUp"
        result = subject
        for key, value in context.items():
            if key and value is not None:
                result = result.replace("{" + key + "}", str(value).strip())
        return result

    async def send(
        self,
        user: User,
        template_name: str,
        context: dict[str, Any],
        db: AsyncSession | None = None,
    ):
        try:
            raw_subject = context.get("subject", "Update from LinkUp")
            subject = self._render_subject(raw_subject, context)

            html_content = render_email_template(template_name, **context)

            if html_content:
                recipient_name = (
                    context.get("user_name") or context.get("driver_name") or getattr(user, "full_name", None) or getattr(user, "first_name", None)
                )
                if recipient_name is not None:
                    recipient_name = str(recipient_name).strip()
                recipient_name = recipient_name or "User"
                logger.info(
                    "[NOTIF] Email: sending to=%s name=%s subject=%s",
                    user.email,
                    recipient_name,
                    (subject or "")[:60],
                )
                await email_client.send(
                    recipient=user.email,
                    subject=subject,
                    body=html_content,
                    recipient_name=recipient_name,
                )
                logger.info("[NOTIF] Email: sent to=%s", user.email)
            else:
                logger.warning(
                    "[NOTIF] Email: no html_content, skip send to=%s",
                    getattr(user, "email", "?"),
                )

        except (ValueError, EmailProviderCircuitOpenError) as e:
            logger.error("[NOTIF] Email: permanent failure to=%s: %s", getattr(user, "email", "?"), e)
            raise PermanentNotificationError(f"Email permanent failure: {e}") from e

        except Exception as e:
            logger.error("[NOTIF] Email: transient failure to=%s: %s", getattr(user, "email", "?"), e, exc_info=True)
            raise TransientNotificationError(f"Email send failed: {e}") from e

    def can_send(self, user) -> bool:
        return bool(user and hasattr(user, "email") and "@" in user.email)
