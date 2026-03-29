"""
ניתוח AI של שיחות צ'אט באמצעות Groq API.
"""

import json
import logging
from groq import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.domain.chat.ai.client import get_groq_client
from app.domain.chat.ai.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.domain.chat.ai.schema import RideSummary

logger = logging.getLogger(__name__)


def _is_retryable_error(exception):
    """
    בודק אם שגיאה היא מסוג שניתן לנסות שוב.
    """
    if isinstance(exception, APIError):
        # Rate limit או server error - ניתן לנסות שוב
        if exception.status_code in [429, 500, 502, 503, 504]:
            return True
        # Validation או authentication - לא לנסות שוב
        if exception.status_code in [400, 401, 403]:
            return False

    # Network errors - ניתן לנסות שוב
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True

    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable_error),
    reraise=True,
)
def _call_api_with_retry(messages, model, response_format, temperature):
    """קורא ל-Groq API עם retry logic."""
    client = get_groq_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature,
    )
    return completion


def analyze_conversation(chat_text: str, temperature: float = 0.2) -> RideSummary | None:
    """
    מנתח שיחת טרמפ ומחזיר RideSummary.

    Args:
        chat_text: טקסט השיחה בין נהג לנוסע
        temperature: טמפרטורה למודל (0.0-2.0). ברירת מחדל 0.2 לחילוץ מדויק

    Returns:
        RideSummary אם הצליח, None אם יש שגיאה
    """
    try:
        user_message = f"{USER_PROMPT}\n\nConversation:\n{chat_text}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # קריאה ל-API עם retry logic
        completion = _call_api_with_retry(
            messages=messages,
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        response_content = completion.choices[0].message.content
        response_json = json.loads(response_content)

        # אימות שהתשובה תואמת לסכמה
        ride_summary = RideSummary(**response_json)
        return ride_summary

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in AI analysis: {e}")
        return None
    except (APIError, ConnectionError, TimeoutError) as e:
        logger.error(f"API error in AI analysis: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in AI analysis: {e}", exc_info=True)
        return None
