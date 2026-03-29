import logging
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.core.logging import setup_logging, request_id_ctx
from app.core.lifespan import lifespan
from app.core.exceptions.base import LinkupError
from app.core.exceptions.handlers import (
    linkup_exception_handler,
    request_validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
)
from app.core.middleware import HTTPSRedirectMiddleware, SecurityHeadersMiddleware
from app.db.session import engine
from app.api.v1.api_router import api_router
from app.infrastructure.health.health_service import check_health

# רישום כל המודלים לפני טעינת admin (מניעת "expression 'Group' failed to locate a name")
import app.db.models  # noqa: F401

# Firebase Admin SDK init (side-effect import; safe idempotent)
import app.infrastructure.firebase_core.firebase  # noqa: F401

from app.admin.setup import setup_admin

setup_logging()
logger = logging.getLogger(__name__)

# CORS: origins ממ-config או FRONTEND_URL (מחשבים לפני יצירת app)
_cors_origins = getattr(settings, "CORS_ORIGINS", None) or []
if not _cors_origins:
    _cors_origins = [getattr(settings, "FRONTEND_URL", "https://linkup.co.il").rstrip("/")]
_allow_origin_regex = None
if getattr(settings, "DEBUG", False):
    _allow_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """מקצה request_id קצר (8 תווים) לכל בקשה; מוסיף ל-response header ול-context ללוגים."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


# Middleware שמוסיף CORS לכל תגובה (כולל 500) – רץ ראשון על התגובה
class EnsureCORSHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if "/api/v1/" in path:
            print("[Linkup] >>> בקשה: {} {}".format(request.method, path), flush=True)
        response = await call_next(request)
        if "/api/v1/" in path:
            print("[Linkup] <<< תגובה: status={}".format(response.status_code), flush=True)
        origin = request.headers.get("origin")
        if origin and (origin in _cors_origins or (_allow_origin_regex and re.match(_allow_origin_regex, origin))):
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return response


app = FastAPI(
    title="Linkup API",
    version="1.0.0",
    lifespan=lifespan,
    servers=[{"url": "http://127.0.0.1:8000", "description": "Local"}],
)

# CORS רגיל (לבקשות רגילות)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# גיבוי: הוספת CORS גם לתגובות שעשויות לדלג על ה-middleware (למשל 500)
app.add_middleware(EnsureCORSHeadersMiddleware)

# Request ID — ראשון כדי שכל לוג בתוך בקשה יקבל request_id
app.add_middleware(RequestIDMiddleware)

# Security headers (X-Content-Type-Options, X-Frame-Options, וכו')
app.add_middleware(SecurityHeadersMiddleware)

# HTTPS: הפנת HTTP → HTTPS כשמאחורי Proxy (להפעיל בפרודקשן עם FORCE_HTTPS_REDIRECT=True)
if getattr(settings, "FORCE_HTTPS_REDIRECT", False):
    app.add_middleware(HTTPSRedirectMiddleware)

# רישום ה-Admin וה-Exception Handlers (סדר: ספציפי → כללי)
setup_admin(app, engine)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(LinkupError, linkup_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """מחזיר 500 כ-JSON עם CORS headers. לא תופס HTTPException."""
    if isinstance(exc, HTTPException):
        raise exc
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled exception: %s",
        exc,
        extra={"request_id": request_id or ""},
    )

    origin = request.headers.get("origin")
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    if origin and (origin in _cors_origins or (_allow_origin_regex and re.match(_allow_origin_regex, origin))):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "request_id": request_id,
        },
        headers=headers,
    )


# שים לב! שורה אחת במקום ארבע
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def read_root():
    return {"status": "running", "version": "1.0.0", "project": settings.PROJECT_NAME}


@app.get("/api/v1/health", tags=["Health"])
async def api_health(response: Response):
    """בדיקת תשתיות: DB, Redis, RabbitMQ. 503 אם אחד מהם לא זמין."""
    health = await check_health()
    response.status_code = 200 if health["status"] == "healthy" else 503
    return health


# הדפסה בעלייה – לוודא שהקוד הנכון רץ
print("[Linkup] Backend נטען (main.py) – CORS + לוגים פעילים", flush=True)
