import logging
import os

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger(__name__)

# 1. Absolute paths so templates resolve on any cwd
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# templates/ next to this module
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "templates")

# 2. Single shared Jinja environment
# trim_blocks / lstrip_blocks keep HTML compact
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_email_template(template_name: str, **context) -> str:
    """טוען קובץ HTML ומזריק לתוכו נתונים"""
    try:
        # Relative paths like 'driver/new_ride.html'
        template = env.get_template(template_name)
        return template.render(**context)

    except TemplateNotFound:
        # Loud log — missing template is a deploy/config issue
        logger.error(f"❌ Template not found: {template_name} | Searched in: {TEMPLATE_DIR}")
        return ""  # Safer to skip send than ship broken HTML

    except Exception as e:
        logger.error(f"❌ Rendering error for {template_name}: {e!s}")
        return ""
