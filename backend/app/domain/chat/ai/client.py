"""
Groq API client לניתוח AI של שיחות.
"""

import os
from groq import Groq

# יצירת client (singleton)
_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    """מחזיר Groq client (singleton)."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY or GROQ_API_KEY environment variable is required")
        _groq_client = Groq(api_key=api_key)
    return _groq_client
