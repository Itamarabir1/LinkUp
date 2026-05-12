"""
HTTP response security headers — reduce XSS, clickjacking, and MIME sniffing risks.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Strictest possible CSP for a JSON API — no scripts, no styles, no frames.
CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

# Relaxed CSP for Swagger UI / ReDoc (dev/staging only).
CSP_DOCS = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "frame-ancestors 'none'"
)

_DOCS_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def _is_https(request: Request) -> bool:
    """Returns True if the request is over HTTPS (direct or via proxy)."""
    if request.url.scheme == "https":
        return True
    return request.headers.get("X-Forwarded-Proto", "").lower() == "https"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    HSTS_VALUE = "max-age=31536000; includeSubDomains"

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"

        if request.url.path.startswith(_DOCS_PREFIXES):
            response.headers["Content-Security-Policy"] = CSP_DOCS
        else:
            response.headers["Content-Security-Policy"] = CSP_API

        if _is_https(request):
            response.headers["Strict-Transport-Security"] = self.HSTS_VALUE
        return response
