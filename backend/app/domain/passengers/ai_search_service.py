"""
Groq-based synchronous parsing of free-text ride search into structured fields.
Runs in a thread pool from the router (run_in_executor) so the event loop is not blocked.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from groq import APIError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.domain.chat.ai.client import get_groq_client
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


def _build_few_shot(now_jlm: datetime) -> list[dict[str, str]]:
    """Dynamic few-shot examples (no stale placeholder dates)."""
    tomorrow = (now_jlm + timedelta(days=1)).date()
    day_after = (now_jlm + timedelta(days=2)).date()
    t_morning = tomorrow.isoformat() + "T08:00:00"
    t_morning_end = tomorrow.isoformat() + "T10:00:00"
    t_evening = tomorrow.isoformat() + "T18:30:00"
    t_day2 = day_after.isoformat() + "T09:00:00"
    tomorrow_d = tomorrow.isoformat()
    return [
        {
            "role": "user",
            "content": "טרמפ מתל אביב לחיפה",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "חיפה",
                    "departure_time": None,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 5.0,
                    "confidence": 0.85,
                    "raw_interpretation": "מוצא ויעד ברורים, חסר תאריך/שעה",
                    "needs_clarification": True,
                    "missing_fields": ["departure_date"],
                    "ambiguity_reasons": [],
                    "follow_up_question": "באיזה תאריך אתה מחפש נסיעה?",
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "user",
            "content": "טרמפ מתל אביב לחיפה מחר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "חיפה",
                    "departure_time": None,
                    "departure_time_to": None,
                    "departure_date": tomorrow_d,
                    "destination_radius": None,
                    "search_radius": 5.0,
                    "confidence": 0.9,
                    "raw_interpretation": "נסיעה מחר ללא שעה ספציפית",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "user",
            "content": "טרמפ מתל אביב לחיפה מחר בין 8 ל-10",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "חיפה",
                    "departure_time": t_morning,
                    "departure_time_to": t_morning_end,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 5.0,
                    "confidence": 0.92,
                    "raw_interpretation": "מחר טווח 08:00–10:00",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "user",
            "content": "לחיפה מחר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": None,
                    "destination_name": "חיפה",
                    "departure_time": None,
                    "departure_time_to": None,
                    "departure_date": tomorrow_d,
                    "destination_radius": None,
                    "search_radius": 5.0,
                    "confidence": 0.75,
                    "raw_interpretation": "יעד ותאריך, חסר מוצא",
                    "needs_clarification": True,
                    "missing_fields": ["pickup_name"],
                    "ambiguity_reasons": [],
                    "follow_up_question": "מאיפה אתה יוצא?",
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "user",
            "content": "מירושלים לאילת ערב מחר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "ירושלים",
                    "destination_name": "אילת",
                    "departure_time": t_evening,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 10.0,
                    "confidence": 0.85,
                    "raw_interpretation": "ערב מחר",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        {
            "role": "user",
            "content": "רוצה טרמפ לצפון",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": None,
                    "destination_name": None,
                    "departure_time": t_day2,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 5.0,
                    "confidence": 0.3,
                    "raw_interpretation": "חסר מוצא ויעד מדויק",
                    "needs_clarification": True,
                    "missing_fields": ["pickup_name", "destination_name"],
                    "ambiguity_reasons": ["לא צוין מאיפה ולאן"],
                    "follow_up_question": "מאיפה ולאן אתה רוצה לנסוע?",
                },
                ensure_ascii=False,
            ),
        },
    ]


def _build_system_prompt(now_jlm: datetime) -> str:
    iso_now = now_jlm.isoformat()
    return f"""You are a ride-search assistant for an Israeli carpool app. Current time in Asia/Jerusalem: {iso_now}.
Extract structured search parameters from the user's message. Respond with a single JSON object only (no markdown).

JSON fields (use null when unknown, do not invent city names):
- pickup_name: string or null — origin city/area in Hebrew context (e.g. תל אביב, חיפה). Do not guess wildly.
- destination_name: string or null
- departure_time: ISO 8601 string or null — interpret "היום", "מחר", "בערב", "בבוקר" relative to Jerusalem time.
  If only a vague time, pick a reasonable hour or null. For a time range, set this to the range start.
- departure_time_to: ISO 8601 string or null — end of departure time window (same calendar day as departure_time when user gives "בין X ל-Y"); null if not a range.
- departure_date: YYYY-MM-DD string or null — use when the user specifies a calendar day but no specific clock time (e.g. "מחר" without morning/evening). Mutually exclusive with departure_time when possible: prefer departure_time when both apply.
- destination_radius: number or null — km around destination for matching; optional; clamp 0.1–50 if set.
- search_radius: number or null — default 5 km around pickup; use ~10–15 if user says "באזור", "בסביבה", "קרוב ל"; clamp 0.1–50.
- confidence: number 0–1
- raw_interpretation: short Hebrew summary of what you understood
- needs_clarification: boolean — true if pickup, destination, or any required time information is missing (see rules).
- missing_fields: array of strings, only from: pickup_name, destination_name, departure_time, departure_time_to, departure_date, destination_radius, search_radius
- ambiguity_reasons: short Hebrew strings (max 100 chars each), why something is unclear
- follow_up_question: Hebrew question (max 120 chars) when needs_clarification is true; otherwise null

Rules:
- If pickup or destination is missing, set follow_up_question in Hebrew (e.g. מאיפה אתה יוצא? / לאן אתה רוצה להגיע?).
- If pickup and destination are present but neither departure_date nor departure_time is known, set needs_clarification true, include departure_date in missing_fields if appropriate, and follow_up_question e.g. באיזה תאריך אתה מחפש נסיעה?
- departure_time_to requires departure_time; if only an end time is implied, still set departure_time to the start of the window.
- Never output HTML or markdown inside strings.
- Output valid JSON only."""


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
    system = _build_system_prompt(now_jlm)
    few_shot = _build_few_shot(now_jlm)

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
            data["destination_radius"] = max(
                0.1, min(50.0, float(data["destination_radius"]))
            )
        except (TypeError, ValueError):
            data["destination_radius"] = None

    if "search_radius" in data and data["search_radius"] is not None:
        data["search_radius"] = _clamp_radius(data["search_radius"])

    try:
        return AISearchResult(**data)
    except Exception as e:
        logger.warning("ai_parse_search: validation failed: %s", e)
        return _fallback_parse_error("לא הצלחנו לאמת את התוצאה. נסה שוב או מלא ידנית.")
