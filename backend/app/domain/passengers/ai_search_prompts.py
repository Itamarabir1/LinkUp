"""
Few-shot examples and system prompt for Groq ride-search parsing.

Separated from orchestration (API calls, validation, fallbacks) in ai_search_service.py
so product/prompt edits do not churn the execution path.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta


def build_few_shot(now_jlm: datetime) -> list[dict[str, str]]:
    """Dynamic few-shot examples covering all edge cases."""
    tomorrow = (now_jlm + timedelta(days=1)).date()
    tomorrow_d = tomorrow.isoformat()
    t_morning = f"{tomorrow_d}T08:00:00"
    t_morning_end = f"{tomorrow_d}T10:00:00"
    t_nine = f"{tomorrow_d}T09:00:00"
    t_evening = f"{tomorrow_d}T18:30:00"

    return [
        # 1. Happy path — all fields provided
        {
            "role": "user",
            "content": "טרמפ מתל אביב לחיפה מחר בבוקר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "חיפה",
                    "departure_time": t_morning,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 3.0,
                    "confidence": 0.95,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה מחר ב-08:00",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        # 2. Missing date only
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
                    "search_radius": 3.0,
                    "confidence": 0.7,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה — תאריך לא צוין",
                    "needs_clarification": True,
                    "missing_fields": ["departure_date"],
                    "ambiguity_reasons": [],
                    "follow_up_question": "באיזה תאריך אתה מחפש נסיעה?",
                },
                ensure_ascii=False,
            ),
        },
        # 3. Missing pickup
        {
            "role": "user",
            "content": "לחיפה מחר בבוקר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": None,
                    "destination_name": "חיפה",
                    "departure_time": t_morning,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 3.0,
                    "confidence": 0.6,
                    "raw_interpretation": "נסיעה לחיפה מחר בבוקר — מוצא לא צוין",
                    "needs_clarification": True,
                    "missing_fields": ["pickup_name"],
                    "ambiguity_reasons": [],
                    "follow_up_question": "מאיפה אתה יוצא?",
                },
                ensure_ascii=False,
            ),
        },
        # 4. Vague direction — MUST NOT invent city name
        {
            "role": "user",
            "content": "רוצה טרמפ לצפון מחר",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": None,
                    "destination_name": None,
                    "departure_time": None,
                    "departure_time_to": None,
                    "departure_date": tomorrow_d,
                    "destination_radius": None,
                    "search_radius": 3.0,
                    "confidence": 0.2,
                    "raw_interpretation": "כיוון כללי (צפון) — לא ניתן לזהות עיר ספציפית",
                    "needs_clarification": True,
                    "missing_fields": ["pickup_name", "destination_name"],
                    "ambiguity_reasons": ["לא צוינה עיר ספציפית — רק כיוון כללי"],
                    "follow_up_question": "מאיפה ולאן אתה רוצה לנסוע?",
                },
                ensure_ascii=False,
            ),
        },
        # 5. Past date — must ask for future date
        {
            "role": "user",
            "content": "טרמפ מתל אביב לחיפה אתמול",
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
                    "search_radius": 3.0,
                    "confidence": 0.3,
                    "raw_interpretation": "תאריך בעבר — לא ניתן לחפש",
                    "needs_clarification": True,
                    "missing_fields": ["departure_date"],
                    "ambiguity_reasons": ["התאריך שצוין כבר עבר"],
                    "follow_up_question": "התאריך שציינת כבר עבר — באיזה תאריך אתה מחפש?",
                },
                ensure_ascii=False,
            ),
        },
        # 6. Multi-turn: user answers date follow-up
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
                    "search_radius": 3.0,
                    "confidence": 0.7,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה — תאריך לא צוין",
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
            "content": "מחר",
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
                    "search_radius": 3.0,
                    "confidence": 0.92,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה מחר (כל היום)",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        # 7. Multi-turn: user adds time after date was known
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
                    "search_radius": 3.0,
                    "confidence": 0.85,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה מחר",
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
            "content": "בשעה 9",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "חיפה",
                    "departure_time": t_nine,
                    "departure_time_to": None,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 3.0,
                    "confidence": 0.97,
                    "raw_interpretation": "נסיעה מתל אביב לחיפה מחר ב-09:00",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        # 8. Time range
        {
            "role": "user",
            "content": "מתל אביב לירושלים מחר בין 8 ל-10",
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "pickup_name": "תל אביב",
                    "destination_name": "ירושלים",
                    "departure_time": t_morning,
                    "departure_time_to": t_morning_end,
                    "departure_date": None,
                    "destination_radius": None,
                    "search_radius": 3.0,
                    "confidence": 0.95,
                    "raw_interpretation": "נסיעה מתל אביב לירושלים מחר בין 08:00 ל-10:00",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
        # 9. Evening ride
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
                    "search_radius": 3.0,
                    "confidence": 0.85,
                    "raw_interpretation": "נסיעה מירושלים לאילת מחר בערב",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "ambiguity_reasons": [],
                    "follow_up_question": None,
                },
                ensure_ascii=False,
            ),
        },
    ]


def build_system_prompt(now_jlm: datetime) -> str:
    iso_now = now_jlm.isoformat()
    # Split string literals so lines stay within Ruff E501; content is unchanged.
    return (
        f"You are a ride-search assistant for an Israeli carpool app. "
        f"Current time in Asia/Jerusalem: {iso_now}.\n"
        "Extract structured search parameters from the user's message. "
        "Respond with a single JSON object only (no markdown).\n\n"
        "JSON fields (use null when unknown, do not invent city names):\n"
        "- pickup_name: string or null — origin city/area in Hebrew context "
        "(e.g. תל אביב, חיפה). Do not guess wildly.\n"
        "- destination_name: string or null\n"
        "- departure_time: ISO 8601 string or null — interpret "
        '"היום", "מחר", "בערב", "בבוקר" relative to Jerusalem time.\n'
        "  If only a vague time, pick a reasonable hour or null. "
        "For a time range, set this to the range start.\n"
        "- departure_time_to: ISO 8601 string or null — end of departure time window "
        '(same calendar day as departure_time when user gives "בין X ל-Y"); '
        "null if not a range.\n"
        "- departure_date: YYYY-MM-DD string or null — use when the user specifies "
        'a calendar day but no specific clock time (e.g. "מחר" without morning/evening). '
        "Mutually exclusive with departure_time when possible: "
        "prefer departure_time when both apply.\n"
        "- destination_radius: number or null — km around destination for matching; "
        "optional; clamp 0.1–50 if set.\n"
        "- search_radius: number or null — default 5 km around pickup; "
        'use ~10–15 if user says "באזור", "בסביבה", "קרוב ל"; clamp 0.1–50.\n'
        "- confidence: number 0–1\n"
        "- raw_interpretation: short Hebrew summary of what you understood\n"
        "- needs_clarification: boolean — true if pickup, destination, or any required "
        "time information is missing (see rules).\n"
        "- missing_fields: array of strings, only from: pickup_name, destination_name, "
        "departure_time, departure_time_to, departure_date, destination_radius, "
        "search_radius\n"
        "- ambiguity_reasons: short Hebrew strings (max 100 chars each), "
        "why something is unclear\n"
        "- follow_up_question: Hebrew question (max 120 chars) when "
        "needs_clarification is true; otherwise null\n\n"
        "Rules:\n"
        "- If pickup or destination is missing, set follow_up_question in Hebrew "
        "(e.g. מאיפה אתה יוצא? / לאן אתה רוצה להגיע?).\n"
        "- If pickup and destination are present but neither departure_date nor "
        "departure_time is known, set needs_clarification true, include departure_date "
        "in missing_fields if appropriate, and follow_up_question e.g. "
        "באיזה תאריך אתה מחפש נסיעה?\n"
        "- departure_time_to requires departure_time; if only an end time is implied, "
        "still set departure_time to the start of the window.\n"
        "- Never output HTML or markdown inside strings.\n"
        "- Output valid JSON only."
    )
