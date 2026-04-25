"""
הפנת HTTP → HTTPS כשהאפליקציה רצה מאחורי Proxy (Nginx, Cloudflare) שעושה TLS.
משתמש ב־X-Forwarded-Proto ו־X-Forwarded-Host שהפרוקסי מעביר.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# loopback hosts share the container's trust boundary - bypass HTTPS redirect
# (Docker healthcheck, docker exec debug, internal monitoring scripts)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    אם FORCE_HTTPS_REDIRECT=True ובקשה הגיעה כ־HTTP (לפי X-Forwarded-Proto או scheme),
    מפנה ל־HTTPS עם אותו host ו־path.
    """

    async def dispatch(self, request: Request, call_next):
        if not getattr(settings, "FORCE_HTTPS_REDIRECT", False):
            return await call_next(request)

        client_host = request.client.host if request.client else ""
        if client_host in LOOPBACK_HOSTS:
            return await call_next(request)

        proto = request.headers.get("x-forwarded-proto", "").strip().lower() or request.url.scheme
        if proto == "https":
            return await call_next(request)

        host = request.headers.get("x-forwarded-host", "").strip() or request.url.netloc
        path = request.url.path
        query = request.url.query
        url = f"https://{host}{path}"
        if query:
            url += f"?{query}"
        logger.debug("HTTPS redirect: %s -> %s", request.url, url)
        return RedirectResponse(url=url, status_code=301)
