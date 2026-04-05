import logging
import os

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger(__name__)

# 1. שימוש ב-Path מוחלט כדי למנוע בעיות בשרתים שונים
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# מוודאים שהתיקייה היא אכן templates שנמצאת באותה רמה של הקובץ הזה
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "templates")

# 2. אתחול ה-Environment פעם אחת בלבד (Singleton-like)
# הוספת trim_blocks הופכת את ה-HTML הנקי יותר (בלי שורות ריקות מיותרות)
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_email_template(template_name: str, **context) -> str:
    """טוען קובץ HTML ומזריק לתוכו נתונים"""
    try:
        # Jinja2 תומך בנתיבים יחסיים כמו 'driver/new_ride.html'
        template = env.get_template(template_name)
        return template.render(**context)

    except TemplateNotFound:
        # סניור נותן לוג מפורט שיעזור לו ב-3 בלילה להבין מה חסר
        logger.error(f"❌ Template not found: {template_name} | Searched in: {TEMPLATE_DIR}")
        return ""  # במייל עדיף להחזיר ריק או שגיאה ברורה כדי לא לשלוח ג'יבריש ללקוח

    except Exception as e:
        logger.error(f"❌ Rendering error for {template_name}: {e!s}")
        return ""
