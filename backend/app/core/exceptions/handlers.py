import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions.base import LinkupError

logger = logging.getLogger("linkup")


# שים לב: הורדתי את הגרשיים מה-LinkupError בפרמטר exc
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
