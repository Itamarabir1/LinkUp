import logging
from typing import Any

from app.domain.notifications.channels.email.client import email_client
from app.domain.notifications.channels.email.renderer import render_email_template
from app.domain.notifications.providers.base import BaseNotificationProvider
from app.domain.users.model import User

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):
    def _render_subject(self, subject: str, context: dict[str, Any]) -> str:
        """Replace subject placeholders (e.g. {passenger_name}) with context values."""
        if not subject or "{" not in subject:
            return subject or "Update from Linkup"
        result = subject
        for key, value in context.items():
            if key and value is not None:
                result = result.replace("{" + key + "}", str(value).strip())
        # Leave placeholders not in context as-is (if a value is missing)
        return result

    async def send(self, user: User, template_name: str, context: dict[str, Any]):
        try:
            # Subject may come from context (builder prepared it) — substitute placeholders
            raw_subject = context.get("subject", "Update from Linkup")
            subject = self._render_subject(raw_subject, context)

            # 1. Render HTML
            html_content = render_email_template(template_name, **context)

            # 2. Send via EmailClient (Brevo) — recipient = driver/user; Brevo requires non-empty name in to
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
                logger.info(
                    "[EMAIL DEBUG] action_url=%s ride_url=%s",
                    context.get("action_url"),
                    context.get("ride_url"),
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
        except Exception as e:
            logger.error(
                "[NOTIF] Email: FAILED to=%s: %s",
                getattr(user, "email", "?"),
                e,
                exc_info=True,
            )
            raise

    def can_send(self, user) -> bool:
        return bool(user and hasattr(user, "email") and "@" in user.email)
