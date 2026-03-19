"""
Structured Logging: JSON בפרודקשן, טקסט קריא בפיתוח.
Request ID מוזרק ל-LogRecord דרך contextvar כדי שיופיע בכל לוג בתוך בקשה.
"""
import logging
import sys
from contextvars import ContextVar

from app.core.config import settings

# מזהה בקשה — נקבע ב-RequestIDMiddleware, נגיש ללוגים
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """מוסיף request_id ל-LogRecord אם קיים ב-context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or ""
        return True


def setup_logging() -> None:
    """
    מגדיר לוגים: JSON עם שדות קבועים (פרודקשן) או טקסט קריא (פיתוח).
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == "json":
        from pythonjsonlogger import jsonlogger

        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
