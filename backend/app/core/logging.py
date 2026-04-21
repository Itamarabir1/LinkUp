"""
Structured logging via structlog.

- Local (LOG_FORMAT=text): colored ConsoleRenderer
- Production (LOG_FORMAT=json): JSONRenderer
- request_id from ContextVar + RequestIDFilter on LogRecord
- stdlib logs (uvicorn, SQLAlchemy, FastAPI) bridged through structlog
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import sentry_sdk
import structlog
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings

# Request id from RequestIDMiddleware (logging context)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """Attach request_id to LogRecord when present in context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or ""
        return True


def add_request_id(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """structlog processor: inject request_id from ContextVar."""
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog and stdlib logging; processors apply to app and library logs.
    """
    if getattr(settings, "SENTRY_DSN", None):
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=getattr(settings, "ENVIRONMENT", "development"),
        )

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
