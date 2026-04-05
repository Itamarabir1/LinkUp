"""
זיהוי הודעות סיום שיחה - keywords בעברית.
"""

# רשימת keywords שמעידים על סיום שיחה
COMPLETION_KEYWORDS: list[str] = [
    "תודה",
    "תודה רבה",
    "תודה לך",
    "סגור",
    "אוקיי",
    "מעולה",
    "נתראה",
    "בסדר",
    "סיימתי",
    "סיימנו",
    "ניפגש",
    "ניפגש",
    "בהצלחה",
    "בהצלחה לך",
    "סבבה",
    "יופי",
    "מצוין",
]


def is_conversation_completion_message(message_body: str) -> bool:
    """
    בודק אם הודעה היא הודעת סיום שיחה.

    Args:
        message_body: תוכן ההודעה

    Returns:
        True אם ההודעה מכילה keyword שמעיד על סיום
    """
    if not message_body:
        return False

    # ניקוי והמרה לאותיות קטנות
    message_lower = message_body.strip().lower()

    # בדיקה אם אחד מה-keywords מופיע בהודעה (חלקי או מלא)
    for keyword in COMPLETION_KEYWORDS:
        # בדיקה case-insensitive + חלקי (למשל "תודה רבה" יעבור גם אם כתוב "תודה רבה לך")
        if keyword.lower() in message_lower:
            return True

    return False
