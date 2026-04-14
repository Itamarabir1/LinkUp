"""
Email renderer — delegates to the React Email microservice.
Drop-in replacement for the old Jinja2 renderer.
Interface is identical: render_email_template(template_name, **context) -> str
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def render_email_template(template_name: str, **context: Any) -> str:
    """
    Calls the React Email renderer service and returns an HTML string.
    Returns "" on any error (same behaviour as old Jinja2 renderer).
    """
    try:
        response = httpx.post(
            f"{settings.EMAIL_RENDERER_URL.rstrip('/')}/render",
            json={"template": template_name, "props": context},
            timeout=10.0,
        )
        response.raise_for_status()
        html = response.json().get("html", "")
        if not html:
            logger.error("[email-renderer] Empty HTML returned for template=%s", template_name)
        return html

    except httpx.HTTPStatusError as e:
        logger.error(
            "[email-renderer] HTTP %s for template=%s: %s",
            e.response.status_code,
            template_name,
            e.response.text,
        )
        return ""

    except Exception as e:
        logger.error(
            "[email-renderer] Failed to render template=%s: %s",
            template_name,
            e,
            exc_info=True,
        )
        return ""
