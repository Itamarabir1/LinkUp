import asyncio
import logging

from firebase_admin import messaging
from firebase_admin.exceptions import (
    UnavailableError,
    InternalError,
    DeadlineExceededError,
    UnknownError,
)
from firebase_admin.messaging import UnregisteredError, SenderIdMismatchError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class FCMClient:
    """
    קליינט Push מקצועי: תומך ב-Async וב-Retries ללא חסימת ה-Event Loop.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(
            (
                UnavailableError,
                InternalError,
                DeadlineExceededError,
                UnknownError,
            )
        ),
        before_sleep=lambda retry_state: logger.info(f"⏳ Push failed, retrying... (Attempt {retry_state.attempt_number})"),
    )
    async def send(self, token: str, title: str, body: str, data: dict | None = None):
        """
        שם הפונקציה שונה ל-'send' כדי להתאים לממשק ה-Provider.
        """
        if not token:
            logger.warning("⚠️ Skipping push: No token provided")
            return None

        # Firebase SDK message — data payload only; all FCM values must be strings
        message = messaging.Message(
            data={
                "title": title,
                "body": body,
                **{k: str(v) for k, v in (data or {}).items()},
            },
            token=token,
        )

        loop = asyncio.get_running_loop()
        try:
            # Run in executor to avoid blocking the event loop
            response = await loop.run_in_executor(None, lambda: messaging.send(message))
            logger.info(f"✅ Push sent successfully: {response}")
            return response
        except (UnregisteredError, SenderIdMismatchError) as e:
            logger.warning(f"⚠️ FCM token invalid (not retrying): {e}")
            raise
        except Exception as e:
            logger.error(f"❌ FCM Send Error: {e}")
            raise


# Singleton
fcm_client = FCMClient()
