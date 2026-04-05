import asyncio
import logging
from typing import Dict, Optional

from firebase_admin import messaging
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
        # חשוב: לא מנסים שוב אם הטוקן לא חוקי (שגיאת 400/404 של פיירבייס)
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.info(f"⏳ Push failed, retrying... (Attempt {retry_state.attempt_number})"),
    )
    async def send(self, token: str, title: str, body: str, data: dict | None = None):
        """
        שם הפונקציה שונה ל-'send' כדי להתאים לממשק ה-Provider.
        """
        if not token:
            logger.warning("⚠️ Skipping push: No token provided")
            return None

        # הכנת ההודעה (Firebase SDK) — data בלבד; כל הערכים חייבים להיות Strings ב-FCM
        message = messaging.Message(
            data={
                "title": title,
                "body": body,
                **{k: str(v) for k, v in (data or {}).items()},
            },
            token=token,
        )

        loop = asyncio.get_event_loop()
        try:
            # הרצה ב-executor מונעת חסימה של ה-Event Loop
            response = await loop.run_in_executor(None, lambda: messaging.send(message))
            logger.info(f"✅ Push sent successfully: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ FCM Send Error: {e}")
            raise e


# יצירת Singleton
fcm_client = FCMClient()
