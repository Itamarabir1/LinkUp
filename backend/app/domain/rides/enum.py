import enum


class RideStatus(str, enum.Enum):
    """
    מצב נסיעה (5 מצבים). קונבנציה: שם באותיות גדולות, ערך באותיות קטנות (PostgreSQL).
    """

    OPEN = "open"
    FULL = "full"
    ACTIVE = "active"  # נסיעה בתנועה — נהג התחיל/יסיים; שידור GPS
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RideBroadcastAction(str, enum.Enum):
    """
    אירוע שידור WebSocket (לא מצב ב-DB). נסיעה חדשה / עדכון ברשימה.
    """

    CREATED = "CREATED"
    UPDATED = "UPDATED"
