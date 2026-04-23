"""
מקור אמת יחיד ל-metadata של אירועים: exchange ו-routing_key.
מתאים לכל מערכת הנוטיפיקציות – ה-Worker והצרכנים מצפים לנתונים האלו.

כללים (גישה סניורית: הפרדה לפי מטרה, לא לפי ישות):
- exchange = סוג העבודה (מטרה), לא "שיוך למשתמש". לכן:
  - "user" (ו-ride, booking) = אירועים שמסתיימים בשליחת התראה (מייל/פוש). רישום, איפוס סיסמה, user.registered → כולם exchange "user".
  - "tasks" = משימות כבדות/אסינכרוניות (S3, עיבוד קבצים). העלאת אווטאר → exchange "tasks".
- גם רישום וגם איפוס סיסמה וגם העלאת תמונה קשורים ל-user, אבל רישום ואיפוס = "שלח מייל"
  (אותו consumer), העלאת תמונה = "עבד קובץ ב-S3" (consumer אחר). לכן שני exchanges: user vs tasks.
- routing_key = מזהה האירוע בתוך ה-exchange: auth.email_verification, auth.password_reset_code, user.avatar_upload.

האם בלאגן כשיש שני תורים לאותו exchange?
  לא. אצלנו אין שני תורים לאותו exchange: notifications_queue מקשיב ל-user/ride/booking; avatar_upload_queue מקשיב רק ל-tasks. אין חפיפה.
  אם היו שני תורים קשורים לאותו exchange עם אותו routing pattern – כל הודעה הייתה מגיעה
  לשניהם (fan-out). זה רצוי רק כששני צרכנים צריכים את אותה הודעה; אחרת מפרידים ב-exchange או
  ב-routing pattern.

מתי להחליף מפתח (routing_key)?
  כשמוסיפים סוג אירוע חדש באותו סוג עיבוד (אותו exchange).
  לדוגמה auth.email_verification vs auth.password_reset_code – מפתח שונה, אותו exchange "user".

מתי לשנות exchange?
  כשמשנים סוג העבודה: התראות (user/ride/booking) vs משימות כבדות (tasks). או דומיין עסקי אחר (ride, booking).

מה קובע כמות תורים וכמות וורקרים?
  - תור אחד לכל "סוג צריכה": notifications_queue להתראות, avatar_upload_queue למשימות S3.
  - כל תור מקשיב ל-exchange(es) שמתאימים לו בלבד. לא מערבבים התראות ומשימות כבדות באותו תור.
"""

from typing import Any

# event_name prefix → exchange
_EXCHANGE_BY_PREFIX: dict[str, str] = {
    "auth.": "user",
    "billing.": "user",
    "user.": "user",
    "ride.": "ride",
    "booking.": "booking",
    "chat.": "user",  # אירועי צ'אט הולכים ל-exchange "user" (אותו consumer של notifications)
}

DEFAULT_EXCHANGE = "system_events"
TASKS_EXCHANGE = "tasks"

# Heavy tasks (image upload, etc.) — queue separate from notifications
_TASK_EVENT_NAMES: list[str] = [
    "user.avatar_upload",
    "user.avatar_remove",
]

# Notification queue consumes these exchanges (one queue, one worker for mail/push)
NOTIFICATION_EXCHANGES: list[str] = [
    "user",
    "ride",
    "booking",
    DEFAULT_EXCHANGE,
]

# Avatar / media upload queue binds to tasks exchange
AVATAR_UPLOAD_EXCHANGES: list[str] = [TASKS_EXCHANGE]

# Scheduled jobs (maintenance, reminders, fuel) — dedicated queue, not domain events
SCHEDULED_EXCHANGE = "scheduled"
SCHEDULED_TASKS_QUEUE = "scheduled_tasks_queue"
SCHEDULED_EXCHANGES: list[str] = [SCHEDULED_EXCHANGE]

# routing_key for scheduled tasks (publisher → consumer contract)
ROUTING_KEY_FUEL_SCAN = "fuel_scan"
ROUTING_KEY_MAINTENANCE = "maintenance"
ROUTING_KEY_REMINDERS = "reminders"
ROUTING_KEY_CHAT_TIMEOUT = "chat_timeout"


def get_routing_metadata(event_name: str) -> dict[str, Any]:
    """
    מחזיר metadata לשליחה ל-RabbitMQ: exchange ו-routing_key.
    אירועי משימות (avatar_upload) → exchange "tasks"; שאר אירועים → לפי קידומת דומיין.
    """
    if event_name in _TASK_EVENT_NAMES:
        return {"exchange": TASKS_EXCHANGE, "routing_key": event_name}
    exchange = DEFAULT_EXCHANGE
    for prefix, ex in _EXCHANGE_BY_PREFIX.items():
        if event_name.startswith(prefix):
            exchange = ex
            break
    return {
        "exchange": exchange,
        "routing_key": event_name,
    }
