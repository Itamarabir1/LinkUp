"""
HTTP response security headers — reduce XSS, clickjacking, and MIME sniffing risks.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _is_https(request: Request) -> bool:
    """Returns True if the request is over HTTPS (direct or via proxy)."""
    if request.url.scheme == "https":
        return True
    return request.headers.get("X-Forwarded-Proto", "").lower() == "https"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    # HSTS: max-age=1 year, includeSubDomains
    HSTS_VALUE = "max-age=31536000; includeSubDomains"

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # COOP: same-origin-allow-popups keeps Google OAuth popups working
        # Needed so the Google popup can postMessage back to the opener
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        if _is_https(request):
            response.headers["Strict-Transport-Security"] = self.HSTS_VALUE
        return response
