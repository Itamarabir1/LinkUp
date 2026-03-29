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
    # TODO: Sentry — להסיר הערה כשעוברים לפרודקשן ומוסיפים SENTRY_DSN ל-.env
    # import sentry_sdk
    # from sentry_sdk.integrations.fastapi import FastApiIntegration
    # from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    # from sentry_sdk.integrations.redis import RedisIntegration
    #
    # if getattr(settings, "SENTRY_DSN", None):
    #     sentry_sdk.init(
    #         dsn=settings.SENTRY_DSN,
    #         integrations=[
    #             FastApiIntegration(),
    #             SqlalchemyIntegration(),
    #             RedisIntegration(),
    #         ],
    #         traces_sample_rate=0.1,
    #         send_default_pii=False,
    #         environment=getattr(settings, "ENVIRONMENT", "development"),
    #     )
    #
    # TODO: Sentry — להוסיף sentry_sdk.init גם ב:
    # - app/workers/main_worker.py (outbox-worker — תהליך נפרד, צריך init נפרד)
    # - chat-ws: sentry-go SDK נפרד (github.com/getsentry/sentry-go)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == "json":
        from pythonjsonlogger import json as jsonlogger

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
