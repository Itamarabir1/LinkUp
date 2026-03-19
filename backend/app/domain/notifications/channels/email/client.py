import logging
import asyncio
import sib_api_v3_sdk
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from sib_api_v3_sdk.rest import ApiException
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailClient:
    def __init__(self):
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key["api-key"] = settings.BREVO_API_KEY
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(self.configuration)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ApiException, ConnectionError)),
    )
    async def send(
        self, recipient: str, subject: str, body: str, recipient_name: str = "User"
    ):
        if not (getattr(settings, "BREVO_API_KEY", None) or "").strip():
            raise ValueError(
                "BREVO_API_KEY is not set in .env. Set it in backend/.env to send emails (e.g. verification, password reset)."
            )
        sender = {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        }
        # Brevo דורש name ב-to – וודא תמיד מחרוזת לא ריקה
        name = (str(recipient_name).strip() if recipient_name else None) or "User"
        to = [{"email": recipient, "name": name}]

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=body, sender=sender, subject=subject
        )

        # הרצה ב-Executor כדי לא לחסום את ה-Event Loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.api_instance.send_transac_email(send_smtp_email)
        )


email_client = EmailClient()
