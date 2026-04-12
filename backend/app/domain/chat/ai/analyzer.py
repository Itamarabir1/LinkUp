"""
Chat ride-summary extraction via Groq API.
"""

import json
import logging

from groq import APIError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.domain.chat.ai.client import get_groq_client
from app.domain.chat.ai.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.domain.chat.ai.schema import RideSummary

logger = logging.getLogger(__name__)


def _is_retryable_error(exception):
    """
    בודק אם שגיאה היא מסוג שניתן לנסות שוב.
    """
    if isinstance(exception, APIError):
        # Rate limit / server errors — retry
        if exception.status_code in [429, 500, 502, 503, 504]:
            return True
        # Client/auth errors — do not retry
        if exception.status_code in [400, 401, 403]:
            return False

    # Transient network errors — retry
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
    """Invoke Groq chat completion with tenacity retries."""
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
    Parse carpool chat transcript into RideSummary.

    Args:
        chat_text: driver/passenger conversation text
        temperature: model temperature (default 0.2 for structured extraction)

    Returns:
        RideSummary on success, None on failure
    """
    try:
        user_message = f"{USER_PROMPT}\n\nConversation:\n{chat_text}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Groq call with retries
        completion = _call_api_with_retry(
            messages=messages,
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        response_content = completion.choices[0].message.content
        response_json = json.loads(response_content)

        # Validate against Pydantic schema
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
