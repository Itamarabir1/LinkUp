"""
שירות אימות Google OAuth - אימות ID tokens מ-Google Sign-In.
מאמת את ה-ID token עם Google ומחזיר את ה-payload (email, name, picture, sub).
"""

import logging
from typing import Dict, Any
from google.auth.transport import requests
from google.oauth2 import id_token
from app.core.config import settings
from app.core.exceptions.auth import GoogleAuthFailed

logger = logging.getLogger(__name__)


def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """
    מאמת ID token מ-Google Sign-In.

    בודקת:
    - Signature (חתימה דיגיטלית)
    - Expiration (תוקף)
    - Audience (GOOGLE_CLIENT_ID)
    - Issuer (accounts.google.com)

    מחזירה את ה-payload (email, name, picture, sub, וכו').

    Raises:
        GoogleAuthFailed: אם ה-token לא תקין או השירות לא זמין
    """
    if not settings.GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured")
        raise GoogleAuthFailed(message="שירות Google לא מוגדר בשרת")

    try:
        request = requests.Request()
        logger.info("Verifying Google ID token...")
        idinfo = id_token.verify_oauth2_token(
            id_token_str, request, settings.GOOGLE_CLIENT_ID
        )
        logger.info("Google ID token verified successfully")

        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.error("Google token wrong issuer: %s", idinfo.get("iss"))
            raise GoogleAuthFailed()

        return {
            "sub": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "email_verified": idinfo.get("email_verified", False),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "given_name": idinfo.get("given_name"),
            "family_name": idinfo.get("family_name"),
        }

    except GoogleAuthFailed:
        raise
    except ValueError as e:
        logger.error("Google ID token verification failed: %s", e, exc_info=True)
        raise GoogleAuthFailed() from e
    except Exception as e:
        logger.error(
            "Unexpected error verifying Google ID token: %s", e, exc_info=True
        )
        raise GoogleAuthFailed() from e
