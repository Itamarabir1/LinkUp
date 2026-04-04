"""
Structured Logging with structlog.

- לוקאלי (LOG_FORMAT=text): צבעוני + קריא עם ConsoleRenderer
- פרודקשן (LOG_FORMAT=json): JSON נקי עם JSONRenderer
- request_id מוזרק אוטומטית לכל log דרך ContextVar (structlog) + RequestIDFilter על LogRecord
- stdlib logging (uvicorn, sqlalchemy, FastAPI) מנותב דרך structlog (foreign_pre_chain)
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings

# מזהה בקשה — נקבע ב-RequestIDMiddleware, נגיש ללוגים
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """מוסיף request_id ל-LogRecord אם קיים ב-context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or ""
        return True


def add_request_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """structlog processor — מוסיף request_id מה-ContextVar."""
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging() -> None:
    """
    מגדיר structlog + stdlib logging.
    structlog processors רצים על כל log — גם מקוד האפליקציה וגם מ-uvicorn/sqlalchemy.
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

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
