"""
Firebase Admin SDK initialization.

Pattern (from Firebase docs):
    import firebase_admin
    from firebase_admin import credentials
    cred = credentials.Certificate("path/to/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

Here: path comes from FIREBASE_SERVICE_ACCOUNT_PATH (local) or
FIREBASE_CREDENTIALS_JSON (production). Do not commit real credentials; the real
file is in .gitignore. For local dev, copy firebase-credentials.example.json
to firebase-credentials.json and set FIREBASE_SERVICE_ACCOUNT_PATH to its path.
"""

import json
import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)


def initialize_firebase():
    """Initializes Firebase Admin SDK once for the application."""
    try:
        if not firebase_admin._apps:
            credentials_json = settings.FIREBASE_CREDENTIALS_JSON
            source = None
            if credentials_json:
                # Production: load from environment variable JSON payload.
                credentials_dict = json.loads(credentials_json)
                cred = credentials.Certificate(credentials_dict)
                source = "env:FIREBASE_CREDENTIALS_JSON"
            elif settings.FIREBASE_SERVICE_ACCOUNT_PATH and settings.ENVIRONMENT.lower() != "production":
                # Local development: load from file path (e.g. path/to/serviceAccountKey.json).
                cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
                source = "file:FIREBASE_SERVICE_ACCOUNT_PATH"
            else:
                logger.warning(
                    "Firebase Admin SDK not initialized: missing credentials for environment=%s. "
                    "Set FIREBASE_CREDENTIALS_JSON (production) or FIREBASE_SERVICE_ACCOUNT_PATH (local dev).",
                    settings.ENVIRONMENT,
                )
                return
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase Admin SDK initialized in Core (source=%s)", source)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firebase in Core: {e}")


# Initialize Firebase on module import
initialize_firebase()
