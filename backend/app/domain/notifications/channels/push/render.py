import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def render_push_content(template_config: dict, **context) -> tuple[str, str]:
    """
    Safe render for push title/body templates.
    """
    # 1. Load title/body templates
    title_tpl = template_config.get("title", "עדכון מ-LinkUp")
    body_tpl = template_config.get("body", "")

    try:
        # 2. Safe str.format via defaultdict (missing keys → empty string)
        safe_context = defaultdict(lambda: "", **context)

        final_title = title_tpl.format_map(safe_context)
        final_body = body_tpl.format_map(safe_context)

        return final_title.strip(), final_body.strip()

    except Exception as e:
        # Malformed template fallback
        logger.error(f"❌ Critical Error rendering push: {e}")
        return title_tpl, body_tpl
