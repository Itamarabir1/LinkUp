"""
Groq API client for AI analysis of conversations.
"""

import os

from groq import Groq

# Singleton OpenAI (or compatible) client
_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    """Returns the Groq client (singleton)."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY or GROQ_API_KEY environment variable is required")
        _groq_client = Groq(api_key=api_key)
    return _groq_client
