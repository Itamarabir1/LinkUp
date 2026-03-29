import logging
from typing import Any, List

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions.base import LinkupError

logger = logging.getLogger("linkup")


def _error_json(
    *,
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or ""
    body: dict = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "trace_id": request_id,
    }
    if details is not None:
        body["details"] = details
    response = JSONResponse(status_code=status_code, content=body)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def linkup_exception_handler(request: Request, exc: LinkupError):
    """
    Handler מרכזי שתופס את כל סוגי השגיאות שלנו
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "LinkupError: %s | trace_id=%s | message=%s",
        exc.error_code,
        exc.trace_id,
        exc.message,
        extra={"request_id": request_id or ""},
    )

    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": exc.error_code,
            "trace_id": exc.trace_id,
            "details": exc.payload,
        },
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    request_id = getattr(request.state, "request_id", None) or ""
    fields: List[dict] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        parts = [str(x) for x in loc if x not in ("body", "query", "path")]
        field = ".".join(parts) if parts else str(loc[-1]) if loc else "request"
        fields.append({"field": field, "message": str(err.get("msg", ""))})

    logger.warning(
        "RequestValidationError | request_id=%s | fields=%s",
        request_id,
        fields,
        extra={"request_id": request_id},
    )
    return _error_json(
        request=request,
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="שגיאת וולידציה בנתונים שהתקבלו",
        details={"fields": fields},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    request_id = getattr(request.state, "request_id", None) or ""
    logger.warning(
        "IntegrityError: %s | request_id=%s",
        exc,
        request_id,
        exc_info=True,
        extra={"request_id": request_id},
    )
    return _error_json(
        request=request,
        status_code=409,
        error_code="DATABASE_CONFLICT",
        message="פעולה זו אינה אפשרית עקב נתונים קיימים",
        details=None,
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", None) or ""
    logger.error(
        "SQLAlchemyError: %s | request_id=%s",
        exc,
        request_id,
        exc_info=True,
        extra={"request_id": request_id},
    )
    return _error_json(
        request=request,
        status_code=500,
        error_code="DATABASE_ERROR",
        message="שגיאת מסד נתונים",
        details=None,
    )
