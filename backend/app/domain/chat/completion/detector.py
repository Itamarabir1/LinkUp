"""
Detect conversation-end messages using Hebrew keyword list (product data, not comments).
"""

# Keywords that indicate the user ended the conversation (Hebrew UI copy)
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
    Return True if the message body contains a completion keyword (substring match).

    Args:
        message_body: Raw message text

    Returns:
        True if a completion keyword appears in the message
    """
    if not message_body:
        return False

    # Normalize and lowercase
    message_lower = message_body.strip().lower()

    # Substring match against each keyword
    for keyword in COMPLETION_KEYWORDS:
        # Case-insensitive partial match (e.g. keyword matches longer sentence)
        if keyword.lower() in message_lower:
            return True

    return False
