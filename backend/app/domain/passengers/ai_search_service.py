"""
Groq-based synchronous parsing of free-text ride search into structured fields.
Runs in a thread pool from the router (run_in_executor) so the event loop is not blocked.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from groq import APIError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.domain.chat.ai.client import get_groq_client
from app.domain.passengers.ai_search_prompts import build_few_shot, build_system_prompt
from app.domain.passengers.ai_search_schema import AISearchResult, ConversationTurn

logger = logging.getLogger(__name__)

_JERUSALEM = ZoneInfo("Asia/Jerusalem")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_GROQ_MODEL = "llama-3.3-70b-versatile"
_REQUEST_TIMEOUT_S = 3.5


def _is_retryable_error(exception: BaseException) -> bool:
    if isinstance(exception, APIError):
        if exception.status_code in (429, 500, 502, 503, 504):
            return True
        if exception.status_code in (400, 401, 403):
            return False
    if isinstance(exception, (ConnectionError, TimeoutError, OSError)):
        return True
    return False


def _sanitize_query(q: str) -> str:
    q = _URL_RE.sub("", q)
    q = " ".join(q.split())
    return q[:400]


def _clamp_radius(v: float | int | None) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return max(0.1, min(50.0, x))


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    retry=retry_if_exception(_is_retryable_error),
    reraise=True,
)
def _call_groq(messages: list[dict[str, str]]) -> str:
    client = get_groq_client()
    completion = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.2,
        timeout=_REQUEST_TIMEOUT_S,
    )
    choice = completion.choices[0]
    content = choice.message.content
    if not content:
        raise ValueError("empty completion")
    return content


def _fallback_parse_error(message_he: str) -> AISearchResult:
    """Soft failure for the client — always returns a valid AISearchResult."""
    return AISearchResult(
        pickup_name=None,
        destination_name=None,
        departure_time=None,
        departure_time_to=None,
        departure_date=None,
        destination_radius=None,
        search_radius=None,
        confidence=0.0,
        raw_interpretation="",
        needs_clarification=True,
        missing_fields=["pickup_name", "destination_name"],
        ambiguity_reasons=[],
        follow_up_question=message_he,
    )


def parse_ride_search_query(
    query: str,
    conversation_history: list[ConversationTurn] | None = None,
) -> AISearchResult:
    """
    Parse free-text + optional conversation into AISearchResult.
    Does not raise to callers — returns fallback with follow_up on failure.
    """
    history = conversation_history or []
    clean = _sanitize_query(query)
    if not clean.strip():
        return _fallback_parse_error("נא לתאר את הנסיעה שאתה מחפש (מוצא, יעד, מתי).")

    try:
        get_groq_client()
    except ValueError:
        logger.warning("ai_parse_search: Groq API key not configured")
        return _fallback_parse_error("שירות הניתוח זמנית לא זמין. נסה למלא את הטופס ידנית.")

    now_jlm = datetime.now(_JERUSALEM)
    system = build_system_prompt(now_jlm)
    few_shot = build_few_shot(now_jlm)

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(few_shot)

    for turn in history[-6:]:
        messages.append({"role": turn.role, "content": turn.content[:500]})

    messages.append({"role": "user", "content": clean})

    try:
        raw = _call_groq(messages)
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError, APIError, OSError) as e:
        logger.warning("ai_parse_search: parse or API failed: %s", e)
        return _fallback_parse_error("לא הצלחנו לנתח את הטקסט. נסה ניסוח אחר או מלא ידנית.")
    except Exception as e:
        logger.warning("ai_parse_search: unexpected error: %s", e, exc_info=True)
        return _fallback_parse_error("אירעה שגיאה. נסה שוב או מלא את הטופס ידנית.")

    if not isinstance(data, dict):
        return _fallback_parse_error("תשובה לא תקינה מהשירות. נסה שוב.")

    # departure_time_to without departure_time is invalid
    if data.get("departure_time_to") and not data.get("departure_time"):
        data["departure_time_to"] = None

    # Both departure_time and departure_date → prefer departure_time
    if data.get("departure_time") and data.get("departure_date"):
        data["departure_date"] = None

    # clamp destination_radius
    if data.get("destination_radius") is not None:
        try:
            data["destination_radius"] = max(0.1, min(50.0, float(data["destination_radius"])))
        except (TypeError, ValueError):
            data["destination_radius"] = None

    if "search_radius" in data and data["search_radius"] is not None:
        data["search_radius"] = _clamp_radius(data["search_radius"])

    try:
        return AISearchResult(**data)
    except Exception as e:
        logger.warning("ai_parse_search: validation failed: %s", e)
        return _fallback_parse_error("לא הצלחנו לאמת את התוצאה. נסה שוב או מלא ידנית.")
