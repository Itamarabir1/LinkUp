import re
import uuid

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

# Import domain models before admin loads (avoids "expression 'Group' failed to locate a name")
import app.db.models

# Firebase Admin SDK init (side-effect import; safe idempotent)
import app.infrastructure.firebase_core.firebase
from app.admin.setup import setup_admin
from app.api.v1.api_router import api_router
from app.core.config import settings
from app.core.exceptions.base import LinkUpError
from app.core.exceptions.handlers import (
    integrity_error_handler,
    link_up_exception_handler,
    request_validation_exception_handler,
    sqlalchemy_error_handler,
)
from app.core.lifespan import lifespan
from app.core.logging import request_id_ctx, setup_logging
from app.core.middleware import HTTPSRedirectMiddleware, SecurityHeadersMiddleware
from app.db.session import engine
from app.infrastructure.health.health_service import check_health, check_liveness, check_readiness

setup_logging()

if settings.ENVIRONMENT.lower() == "production" and getattr(settings, "DEBUG", False):
    raise RuntimeError(
        "DEBUG=True is not allowed in production. "
        "Set DEBUG=False in backend/.env.production."
    )

logger = structlog.get_logger(__name__)

# CORS: origins from config or FRONTEND_URL (computed before app creation)
_cors_origins = getattr(settings, "CORS_ORIGINS", None) or []
if not _cors_origins:
    _cors_origins = [getattr(settings, "FRONTEND_URL", "https://linkup.co.il").rstrip("/")]
_allow_origin_regex = None
if getattr(settings, "DEBUG", False):
    _allow_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a short request_id (8 chars) per request; add to response header and log context."""

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


# Middleware: add CORS headers to every response (including 500) — runs first on the response path
class EnsureCORSHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if "/api/v1/" in path:
            logger.debug("request %s %s", request.method, path)
        response = await call_next(request)
        if "/api/v1/" in path:
            logger.debug("response status=%s %s", response.status_code, path)
        origin = request.headers.get("origin")
        if origin and (origin in _cors_origins or (_allow_origin_regex and re.match(_allow_origin_regex, origin))):
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return response


app = FastAPI(
    title="LinkUp API",
    version="1.0.0",
    lifespan=lifespan,
    servers=[{"url": "http://127.0.0.1:8000", "description": "Local"}],
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.API_DOCS_ENABLED else None,
)

# Standard CORS (preflight / normal requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# Fallback: CORS on responses that might bypass middleware (e.g. some 500s)
app.add_middleware(EnsureCORSHeadersMiddleware)

# Request ID — early so all logs during a request share request_id
app.add_middleware(RequestIDMiddleware)

# Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# HTTPS: redirect HTTP → HTTPS when behind a proxy (enable in prod with FORCE_HTTPS_REDIRECT=True)
if getattr(settings, "FORCE_HTTPS_REDIRECT", False):
    app.add_middleware(HTTPSRedirectMiddleware)

# Metrics — expose /metrics for Prometheus scraping
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Admin panel and exception handlers (order: specific → generic)
setup_admin(app, engine)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(LinkUpError, link_up_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return 500 as JSON with CORS headers. Does not catch HTTPException."""
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


# Single include_router call
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def read_root():
    return {"status": "running", "version": "1.0.0", "project": settings.PROJECT_NAME}


@app.get("/api/v1/health", tags=["Health"])
async def api_health(response: Response):
    """Health check: DB, Redis, RabbitMQ. 503 if any dependency is down."""
    health = await check_health()
    response.status_code = 200 if health["status"] == "healthy" else 503
    return health


@app.get("/livez", tags=["Health"], include_in_schema=False)
async def livez():
    """Liveness probe: process is running."""
    return await check_liveness()


@app.get("/readyz", tags=["Health"], include_in_schema=False)
async def readyz(response: Response):
    """Readiness probe: dependencies are reachable."""
    health = await check_readiness()
    response.status_code = 200 if health["status"] == "healthy" else 503
    return health


logger.info("LinkUp backend started")
